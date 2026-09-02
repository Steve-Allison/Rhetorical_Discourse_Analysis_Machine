"""Offline-only construction of secure eRST completion bundles."""

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from pydantic import BaseModel
from safetensors.torch import save_model
import torch

from rdam.rst.contracts.erst import (
    ErstCalibrationState,
    ErstCheckpointBuildSpec,
    ErstCheckpointComponent,
    ErstCheckpointFile,
    ErstCheckpointManifest,
    ErstCheckpointTestVector,
    ErstDecoderConfig,
    ErstGraphComponentConfig,
    ErstScorerConfig,
    RawRelationInventory,
)
from rdam.rst.erst.checkpoint import (
    ErstCheckpointError,
    _role_for,
    _sha256_file,
    validate_erst_checkpoint_bundle,
)
from rdam.rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from rdam.rst.erst.signals import RuleBasedSignalDetector

_MANIFEST_NAME = "manifest.json"


def _canonical_json_bytes(value: BaseModel | Mapping[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _write_json(path: Path, value: BaseModel | Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(value))


def _torch_dtype_name(dtype: torch.dtype) -> str:
    name = str(dtype).removeprefix("torch.")
    if name not in {"float16", "float32", "float64", "bfloat16"}:
        raise ErstCheckpointError(f"unsupported eRST checkpoint parameter dtype: {name}")
    return name


def _single_parameter_dtype(model: torch.nn.Module) -> torch.dtype:
    dtypes = {parameter.dtype for parameter in model.parameters() if parameter.is_floating_point()}
    if len(dtypes) != 1:
        raise ErstCheckpointError("eRST scorer parameters must use one floating-point dtype")
    return next(iter(dtypes))


def _inventory_files(root: Path) -> tuple[ErstCheckpointFile, ...]:
    inventory: list[ErstCheckpointFile] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ErstCheckpointError(f"checkpoint bundle cannot contain symlinks: {path.relative_to(root)}")
        if not path.is_file() or path.name == _MANIFEST_NAME:
            continue
        relative = path.relative_to(root).as_posix()
        inventory.append(
            ErstCheckpointFile(
                path=relative,
                role=_role_for(relative),
                size_bytes=path.stat().st_size,
                sha256=_sha256_file(path),
            )
        )
    return tuple(inventory)


def _validate_build_inputs(
    scorer: NeuralSecondaryEdgeScorer,
    build_spec: ErstCheckpointBuildSpec,
    signal_detector: RuleBasedSignalDetector,
    relation_inventory: RawRelationInventory,
    decoder_config: ErstDecoderConfig,
    calibration: ErstCalibrationState,
    graph_config: ErstGraphComponentConfig,
) -> None:
    features = build_spec.feature_schema
    if scorer.raw_relation_inventory != relation_inventory.labels:
        raise ErstCheckpointError("scorer and raw relation inventories differ")
    if decoder_config.raw_relation_inventory != relation_inventory.labels:
        raise ErstCheckpointError("decoder and raw relation inventories differ")
    if relation_inventory.inventory_sha256 != features.raw_relation_inventory_sha256:
        raise ErstCheckpointError("raw relation inventory hash differs from the build specification")
    if decoder_config.config_sha256 != features.decoder_config_sha256:
        raise ErstCheckpointError("decoder hash differs from the build specification")
    if signal_detector.provenance.ruleset_digest != features.signal_detector_sha256:
        raise ErstCheckpointError("signal-detector hash differs from the build specification")
    ontology_hash = hashlib.sha256(_canonical_json_bytes(relation_inventory.concept_by_raw)).hexdigest()
    if ontology_hash != features.ontology_mapping_sha256:
        raise ErstCheckpointError("ontology mapping hash differs from the build specification")
    if graph_config.feature_schema_sha256 != features.structural_feature_sha256:
        raise ErstCheckpointError("graph feature hash differs from the build specification")
    if calibration.edge_threshold != decoder_config.edge_threshold:
        raise ErstCheckpointError("calibration and decoder thresholds differ")
    if scorer.calibration_temperature != calibration.temperature:
        raise ErstCheckpointError("scorer and calibration temperatures differ")
    if build_spec.release_eligible and not calibration.calibrated:
        raise ErstCheckpointError("release-eligible checkpoint must contain fitted calibration")


def save_erst_checkpoint_bundle(
    target: Path | str,
    *,
    scorer: NeuralSecondaryEdgeScorer,
    build_spec: ErstCheckpointBuildSpec,
    signal_detector: RuleBasedSignalDetector,
    relation_inventory: RawRelationInventory,
    decoder_config: ErstDecoderConfig,
    calibration: ErstCalibrationState,
    graph_config: ErstGraphComponentConfig,
    test_vector: ErstCheckpointTestVector,
) -> ErstCheckpointManifest:
    """Atomically create a complete, private, pickle-free completion bundle."""

    destination = Path(target).resolve()
    if destination.exists():
        raise FileExistsError(f"checkpoint destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _validate_build_inputs(
        scorer,
        build_spec,
        signal_detector,
        relation_inventory,
        decoder_config,
        calibration,
        graph_config,
    )
    if graph_config.has_learned_state:
        raise ErstCheckpointError("the current bundle writer requires an explicit learned graph module")

    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        scorer_config = ErstScorerConfig(
            model_type=str(getattr(scorer.encoder.config, "model_type", "unknown")),
            num_struct_features=scorer.num_struct_features,
            projection_dimension=scorer.proj_dim,
            parameter_dtype=_torch_dtype_name(_single_parameter_dtype(scorer)),
            raw_relation_inventory=scorer.raw_relation_inventory,
        )
        _write_json(temporary / "scorer/scorer_config.json", scorer_config)
        scorer.encoder.config.save_pretrained(temporary / "scorer/encoder")
        scorer.tokenizer.save_pretrained(temporary / "tokenizer")
        _write_json(
            temporary / "signal_detector/config.json",
            {
                "provenance": signal_detector.provenance.model_dump(mode="json"),
                "patterns": [pattern.model_dump(mode="json") for pattern in signal_detector.patterns],
            },
        )
        _write_json(temporary / "graph/config.json", graph_config)
        _write_json(temporary / "calibration.json", calibration)
        _write_json(temporary / "relation_inventory.json", relation_inventory)
        _write_json(temporary / "ontology_mapping.json", relation_inventory.concept_by_raw)
        _write_json(temporary / "decoder_config.json", decoder_config)
        _write_json(temporary / "test_vector.json", test_vector)
        save_model(
            scorer,
            str(temporary / "scorer/model.safetensors"),
            metadata={
                "format": "pt",
                "package_version": build_spec.provenance.producer_version,
                "architecture": build_spec.architecture,
            },
        )

        files = _inventory_files(temporary)
        components = (
            ErstCheckpointComponent(
                component_id="scorer",
                architecture=build_spec.architecture,
                config_file="scorer/scorer_config.json",
                state_file="scorer/model.safetensors",
            ),
            ErstCheckpointComponent(
                component_id="signal_detector",
                architecture=signal_detector.provenance.detector_id,
                config_file="signal_detector/config.json",
                state_file=None,
            ),
            ErstCheckpointComponent(
                component_id="graph",
                architecture=graph_config.architecture,
                config_file="graph/config.json",
                state_file=None,
            ),
        )
        manifest = ErstCheckpointManifest(
            architecture=build_spec.architecture,
            upstream_revisions=build_spec.upstream_revisions,
            files=files,
            components=components,
            feature_schema=build_spec.feature_schema,
            research=build_spec.research,
            metrics=build_spec.metrics,
            licenses=build_spec.licenses,
            provenance=build_spec.provenance,
            release_eligible=build_spec.release_eligible,
        )
        _write_json(temporary / _MANIFEST_NAME, manifest)
        validate_erst_checkpoint_bundle(temporary)
        temporary.rename(destination)
        return manifest
    except BaseException:
        shutil.rmtree(temporary)
        raise


__all__ = ["save_erst_checkpoint_bundle"]
