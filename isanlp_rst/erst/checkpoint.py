"""Secure, content-addressed eRST completion-bundle save and reload."""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
from typing import Any

from pydantic import BaseModel
from safetensors.torch import load_model, save_model
import torch
from transformers import AutoConfig, AutoTokenizer

from isanlp_rst.contracts.erst import (
    ErstCalibrationState,
    ErstCheckpointBuildSpec,
    ErstCheckpointComponent,
    ErstCheckpointFile,
    ErstCheckpointFileRole,
    ErstCheckpointManifest,
    ErstCheckpointTestVector,
    ErstDecoderConfig,
    ErstGraphComponentConfig,
    ErstScorerConfig,
    RawRelationInventory,
)
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from isanlp_rst.erst.signals import RuleBasedSignalDetector, SignalPattern

_MANIFEST_NAME = "manifest.json"
_MAX_MANIFEST_BYTES = 4 * 1024 * 1024
_FORBIDDEN_SUFFIXES = {".bin", ".ckpt", ".joblib", ".pickle", ".pkl", ".pt", ".pth"}
_REQUIRED_COMPONENTS = {"scorer", "signal_detector", "graph"}
_REQUIRED_ROLES = {
    ErstCheckpointFileRole.SCORER_STATE,
    ErstCheckpointFileRole.SCORER_CONFIG,
    ErstCheckpointFileRole.ENCODER_CONFIG,
    ErstCheckpointFileRole.TOKENIZER,
    ErstCheckpointFileRole.SIGNAL_CONFIG,
    ErstCheckpointFileRole.GRAPH_CONFIG,
    ErstCheckpointFileRole.CALIBRATION,
    ErstCheckpointFileRole.RELATION_INVENTORY,
    ErstCheckpointFileRole.ONTOLOGY_MAPPING,
    ErstCheckpointFileRole.DECODER_CONFIG,
    ErstCheckpointFileRole.TEST_VECTOR,
}


class ErstCheckpointError(RuntimeError):
    """A completion bundle is unsafe, incomplete, inconsistent, or corrupt."""


class ErstCapabilityError(RuntimeError):
    """A requested eRST completion capability has no validated bundle."""


@dataclass(frozen=True, slots=True)
class LoadedErstCheckpoint:
    """Validated runtime components reconstructed from one local bundle."""

    manifest: ErstCheckpointManifest
    scorer: NeuralSecondaryEdgeScorer
    signal_detector: RuleBasedSignalDetector
    decoder_config: ErstDecoderConfig
    calibration: ErstCalibrationState
    relation_inventory: RawRelationInventory
    graph_config: ErstGraphComponentConfig
    test_vector: ErstCheckpointTestVector


def _canonical_json_bytes(value: BaseModel | Mapping[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _write_json(path: Path, value: BaseModel | Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(value))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _torch_dtype_name(dtype: torch.dtype) -> str:
    name = str(dtype).removeprefix("torch.")
    if name not in {"float16", "float32", "float64", "bfloat16"}:
        raise ErstCheckpointError(f"unsupported eRST checkpoint parameter dtype: {name}")
    return name


def _torch_dtype(value: str) -> torch.dtype:
    try:
        return {
            "float16": torch.float16,
            "float32": torch.float32,
            "float64": torch.float64,
            "bfloat16": torch.bfloat16,
        }[value]
    except KeyError as error:
        raise ErstCheckpointError(f"unsupported eRST checkpoint parameter dtype: {value}") from error


def _single_parameter_dtype(model: torch.nn.Module) -> torch.dtype:
    dtypes = {parameter.dtype for parameter in model.parameters() if parameter.is_floating_point()}
    if len(dtypes) != 1:
        raise ErstCheckpointError("eRST scorer parameters must use one floating-point dtype")
    return next(iter(dtypes))


def _role_for(path: str) -> ErstCheckpointFileRole:
    if path == "scorer/model.safetensors":
        return ErstCheckpointFileRole.SCORER_STATE
    if path == "scorer/scorer_config.json":
        return ErstCheckpointFileRole.SCORER_CONFIG
    if path == "scorer/encoder/config.json":
        return ErstCheckpointFileRole.ENCODER_CONFIG
    if path.startswith("tokenizer/"):
        return ErstCheckpointFileRole.TOKENIZER
    role = {
        "signal_detector/config.json": ErstCheckpointFileRole.SIGNAL_CONFIG,
        "graph/config.json": ErstCheckpointFileRole.GRAPH_CONFIG,
        "graph/model.safetensors": ErstCheckpointFileRole.GRAPH_STATE,
        "calibration.json": ErstCheckpointFileRole.CALIBRATION,
        "relation_inventory.json": ErstCheckpointFileRole.RELATION_INVENTORY,
        "ontology_mapping.json": ErstCheckpointFileRole.ONTOLOGY_MAPPING,
        "decoder_config.json": ErstCheckpointFileRole.DECODER_CONFIG,
        "test_vector.json": ErstCheckpointFileRole.TEST_VECTOR,
    }.get(path)
    if role is None:
        raise ErstCheckpointError(f"checkpoint contains an unrecognized file: {path}")
    return role


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


def _read_small_json(path: Path) -> bytes:
    if path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ErstCheckpointError(f"checkpoint control file exceeds {_MAX_MANIFEST_BYTES} bytes: {path.name}")
    return path.read_bytes()


def validate_erst_checkpoint_bundle(root: Path | str) -> ErstCheckpointManifest:
    """Validate exact membership, paths, roles, sizes, hashes, and component closure."""

    bundle = Path(root).resolve()
    if not bundle.is_dir() or bundle.is_symlink():
        raise ErstCheckpointError("eRST checkpoint must be a real local directory")
    manifest_path = bundle / _MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ErstCheckpointError("eRST checkpoint is missing a regular manifest.json")
    try:
        manifest = ErstCheckpointManifest.model_validate_json(_read_small_json(manifest_path))
    except Exception as error:
        raise ErstCheckpointError("eRST checkpoint manifest is invalid") from error

    declared = {record.path: record for record in manifest.files}
    actual: set[str] = set()
    for path in bundle.rglob("*"):
        if path.is_symlink():
            raise ErstCheckpointError(f"eRST checkpoint contains a symlink: {path.relative_to(bundle)}")
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix()
        if Path(relative).suffix.casefold() in _FORBIDDEN_SUFFIXES:
            raise ErstCheckpointError(f"eRST checkpoint contains a forbidden artifact: {relative}")
        if relative != _MANIFEST_NAME:
            actual.add(relative)
    if actual != set(declared):
        missing = sorted(set(declared) - actual)
        unlisted = sorted(actual - set(declared))
        raise ErstCheckpointError(f"eRST checkpoint membership mismatch; missing={missing}, unlisted={unlisted}")
    for relative, record in declared.items():
        path = bundle / relative
        if path.stat().st_size != record.size_bytes:
            raise ErstCheckpointError(f"eRST checkpoint size mismatch: {relative}")
        if _sha256_file(path) != record.sha256:
            raise ErstCheckpointError(f"eRST checkpoint SHA-256 mismatch: {relative}")
        if _role_for(relative) != record.role:
            raise ErstCheckpointError(f"eRST checkpoint role mismatch: {relative}")

    roles = {record.role for record in manifest.files}
    if not _REQUIRED_ROLES <= roles:
        raise ErstCheckpointError(f"eRST checkpoint is missing required roles: {sorted(_REQUIRED_ROLES - roles)}")
    components = {component.component_id: component for component in manifest.components}
    if set(components) != _REQUIRED_COMPONENTS:
        raise ErstCheckpointError("eRST checkpoint must declare scorer, signal-detector, and graph components")
    scorer_component = components["scorer"]
    if scorer_component.state_file is None or not scorer_component.state_file.endswith(".safetensors"):
        raise ErstCheckpointError("eRST scorer component requires safetensors state")
    graph_component = components["graph"]
    graph_config = ErstGraphComponentConfig.model_validate_json(
        _read_small_json(bundle / graph_component.config_file)
    )
    if graph_config.has_learned_state != (graph_component.state_file is not None):
        raise ErstCheckpointError("graph component state declaration is inconsistent")
    return manifest


def _load_signal_detector(path: Path) -> RuleBasedSignalDetector:
    try:
        payload: Any = json.loads(_read_small_json(path))
        provenance = payload["provenance"]
        patterns = tuple(SignalPattern.model_validate(item) for item in payload["patterns"])
        detector = RuleBasedSignalDetector(
            patterns=patterns,
            detector_version=str(provenance["detector_version"]),
        )
    except Exception as error:
        raise ErstCheckpointError("signal-detector configuration is invalid") from error
    if detector.provenance.model_dump(mode="json") != provenance:
        raise ErstCheckpointError("signal-detector provenance does not reproduce from its config")
    return detector


def load_erst_checkpoint_bundle(
    root: Path | str,
    *,
    device: str | torch.device = "cpu",
    verify_test_vector: bool = True,
) -> LoadedErstCheckpoint:
    """Reconstruct every runtime component locally and strict-load all scorer tensors."""

    bundle = Path(root).resolve()
    manifest = validate_erst_checkpoint_bundle(bundle)
    components = {component.component_id: component for component in manifest.components}
    try:
        scorer_config = ErstScorerConfig.model_validate_json(
            _read_small_json(bundle / components["scorer"].config_file)
        )
        relation_inventory = RawRelationInventory.model_validate_json(
            _read_small_json(bundle / "relation_inventory.json")
        )
        decoder_config = ErstDecoderConfig.model_validate_json(
            _read_small_json(bundle / "decoder_config.json")
        )
        calibration = ErstCalibrationState.model_validate_json(
            _read_small_json(bundle / "calibration.json")
        )
        graph_config = ErstGraphComponentConfig.model_validate_json(
            _read_small_json(bundle / components["graph"].config_file)
        )
        test_vector = ErstCheckpointTestVector.model_validate_json(
            _read_small_json(bundle / "test_vector.json")
        )
        encoder_config = AutoConfig.from_pretrained(
            bundle / "scorer/encoder",
            local_files_only=True,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            bundle / "tokenizer",
            use_fast=True,
            local_files_only=True,
        )
    except Exception as error:
        raise ErstCheckpointError("eRST checkpoint control files cannot be reconstructed") from error
    if not tokenizer.is_fast:
        raise ErstCheckpointError("eRST checkpoint tokenizer is not a fast tokenizer")
    if relation_inventory.labels != scorer_config.raw_relation_inventory:
        raise ErstCheckpointError("eRST checkpoint scorer and relation inventories differ")
    if decoder_config.raw_relation_inventory != scorer_config.raw_relation_inventory:
        raise ErstCheckpointError("eRST checkpoint decoder and relation inventories differ")
    if calibration.edge_threshold != decoder_config.edge_threshold:
        raise ErstCheckpointError("eRST checkpoint calibration and decoder thresholds differ")
    if graph_config.has_learned_state:
        raise ErstCheckpointError("no registered learned graph architecture can reconstruct this bundle")

    storage_dtype = _torch_dtype(scorer_config.parameter_dtype)
    scorer = NeuralSecondaryEdgeScorer(
        model_name_or_path=manifest.architecture,
        num_struct_features=scorer_config.num_struct_features,
        proj_dim=scorer_config.projection_dimension,
        raw_relation_inventory=scorer_config.raw_relation_inventory,
        device="cpu",
        torch_dtype=storage_dtype,
        encoder_config=encoder_config,
        tokenizer=tokenizer,
        calibration_temperature=calibration.temperature,
    )
    try:
        missing, unexpected = load_model(
            scorer,
            bundle / "scorer/model.safetensors",
            strict=True,
            device="cpu",
        )
    except Exception as error:
        raise ErstCheckpointError("eRST scorer safetensors state failed strict loading") from error
    if missing or unexpected:
        raise ErstCheckpointError(
            f"strict eRST scorer load returned missing={missing}, unexpected={unexpected}"
        )
    scorer.set_runtime_device(device, torch_dtype=storage_dtype)
    scorer.eval()
    signal_detector = _load_signal_detector(bundle / components["signal_detector"].config_file)
    if signal_detector.provenance.ruleset_digest != manifest.feature_schema.signal_detector_sha256:
        raise ErstCheckpointError("reloaded signal-detector hash differs from the manifest")
    loaded = LoadedErstCheckpoint(
        manifest=manifest,
        scorer=scorer,
        signal_detector=signal_detector,
        decoder_config=decoder_config,
        calibration=calibration,
        relation_inventory=relation_inventory,
        graph_config=graph_config,
        test_vector=test_vector,
    )
    if verify_test_vector:
        verify_erst_checkpoint_test_vector(loaded)
    return loaded


def verify_erst_checkpoint_test_vector(checkpoint: LoadedErstCheckpoint) -> None:
    """Reproduce the synthetic expected graph through every bundled runtime component."""

    from isanlp_rst.contracts import analysis_from_json, document_from_json
    from isanlp_rst.english.erst.completer import CompleterConfig, ErstCompleter

    vector = checkpoint.test_vector
    document = document_from_json(vector.document_json)
    primary_analysis = analysis_from_json(vector.primary_analysis_json)
    expected_analysis = analysis_from_json(vector.expected_analysis_json)
    if document.document_id != primary_analysis.document_id:
        raise ErstCheckpointError("checkpoint test-vector document identities differ")
    completer = ErstCompleter(
        config=CompleterConfig(
            min_confidence_threshold=checkpoint.decoder_config.edge_threshold,
        ),
        signal_detector=checkpoint.signal_detector,
        decoder_config=checkpoint.decoder_config,
    )
    actual_analysis = completer.complete_graph(
        document,
        primary_analysis,
        neural_scorer=checkpoint.scorer,
    )
    if (
        actual_analysis.document_id != expected_analysis.document_id
        or actual_analysis.formalism != expected_analysis.formalism
        or actual_analysis.nodes != expected_analysis.nodes
        or actual_analysis.primary_edges != expected_analysis.primary_edges
        or actual_analysis.signals != expected_analysis.signals
        or len(actual_analysis.secondary_edges) != len(expected_analysis.secondary_edges)
    ):
        raise ErstCheckpointError("checkpoint test-vector graph structure does not reproduce")
    for actual_edge, expected_edge in zip(
        actual_analysis.secondary_edges,
        expected_analysis.secondary_edges,
        strict=True,
    ):
        actual_identity = (
            actual_edge.edge_id,
            actual_edge.source_id,
            actual_edge.target_id,
            actual_edge.relation_raw,
            actual_edge.relation_concept,
            actual_edge.calibrated,
        )
        expected_identity = (
            expected_edge.edge_id,
            expected_edge.source_id,
            expected_edge.target_id,
            expected_edge.relation_raw,
            expected_edge.relation_concept,
            expected_edge.calibrated,
        )
        if (
            actual_edge.confidence is None
            or expected_edge.confidence is None
            or actual_identity != expected_identity
            or not math.isclose(
                actual_edge.confidence,
                expected_edge.confidence,
                rel_tol=1e-5,
                abs_tol=1e-6,
            )
        ):
            raise ErstCheckpointError("checkpoint test-vector decoded edge does not reproduce")
    if not actual_analysis.signals:
        raise ErstCheckpointError("checkpoint test-vector must exercise signal detection")
    if not actual_analysis.secondary_edges:
        raise ErstCheckpointError("checkpoint test-vector must exercise secondary-edge decoding")
    if any(
        not edge.calibrated or not edge.relation_raw or not edge.relation_concept
        for edge in actual_analysis.secondary_edges
    ):
        raise ErstCheckpointError("checkpoint test-vector edges lack calibrated raw and ontology labels")


__all__ = [
    "ErstCapabilityError",
    "ErstCheckpointError",
    "LoadedErstCheckpoint",
    "load_erst_checkpoint_bundle",
    "save_erst_checkpoint_bundle",
    "validate_erst_checkpoint_bundle",
    "verify_erst_checkpoint_test_vector",
]
