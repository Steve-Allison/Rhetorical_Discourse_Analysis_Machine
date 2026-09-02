"""Build and freeze the executable eRST experiment protocol."""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from rdam.rst.contracts.analysis import DiscourseSignal
from rdam.rst.contracts.erst import (
    ErstDecoderConfig,
    PrivateCorpusVerificationReceipt,
)
from workbench.research.erst.configuration import ExperimentConfigurationBundle
from workbench.research.erst.contracts import (
    ExperimentProtocol,
    ExperimentSystemSpec,
)
from workbench.research.erst.data import (
    CandidateRecord,
    ScreeningCorpusPayload,
)
from workbench.research.erst.runner import PreparedExperimentData
from workbench.research.erst.technology import TechnologyMatrix


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _system_config_sha256(technology: BaseModel, configuration: BaseModel) -> str:
    return _sha256_json(
        {
            "technology": technology.model_dump(mode="json"),
            "configuration": configuration.model_dump(mode="json"),
        }
    )


def _source_tree_sha256(paths: tuple[Path, ...], repository_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(repository_root).as_posix()
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\n")
    return digest.hexdigest()


def _environment_lock_sha256(repository_root: Path) -> str:
    locks = (repository_root / "pixi.lock",)
    if any(not path.is_file() for path in locks):
        raise ValueError("production Pixi lock must exist")
    return _source_tree_sha256(locks, repository_root)


def build_experiment_protocol(
    *,
    matrix: TechnologyMatrix,
    configurations: ExperimentConfigurationBundle,
    verification: PrivateCorpusVerificationReceipt,
    prepared_data: PreparedExperimentData[ScreeningCorpusPayload],
    repository_root: Path,
) -> ExperimentProtocol:
    """Bind corpus, candidates, features, and all typed system configs into one hash."""

    systems: list[ExperimentSystemSpec] = []
    for technology in matrix.systems:
        configuration = configurations.for_system(technology.system)
        config_payload = configuration.model_dump(mode="json")
        configured_model_id = config_payload.get("model_id")
        configured_revision = config_payload.get("model_revision")
        if configured_model_id != technology.model_id or configured_revision != technology.model_revision:
            if technology.model_id is not None:
                raise ValueError(f"system config model identity differs from matrix: {technology.system}")
        systems.append(
            ExperimentSystemSpec(
                system=technology.system,
                implementation=technology.implementation_module,
                model_id=technology.model_id,
                model_revision=technology.model_revision,
                model_license=technology.model_license,
                config_sha256=_system_config_sha256(technology, configuration),
            )
        )
    inventory = prepared_data.payload.raw_relation_inventory
    repository_root = repository_root.resolve()
    harness_sources = tuple(
        path
        for path in (repository_root / "workbench/research").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    production_sources = tuple(
        repository_root / relative
        for relative in (
            "rdam/rst/contracts/analysis.py",
            "rdam/rst/contracts/document.py",
            "rdam/rst/contracts/enums.py",
            "rdam/rst/contracts/erst.py",
            "rdam/rst/erst/candidates.py",
            "rdam/rst/erst/converter.py",
            "rdam/rst/erst/decoder.py",
            "rdam/rst/erst/relations.py",
            "rdam/rst/erst/rs4.py",
            "rdam/rst/erst/neural_scorer.py",
        )
    )
    decoder = ErstDecoderConfig(
        edge_threshold=0.5,
        raw_relation_inventory=inventory.labels,
    )
    return ExperimentProtocol(
        corpus_revision=verification.corpus_revision,
        environment_lock_sha256=_environment_lock_sha256(repository_root),
        harness_source_sha256=_source_tree_sha256(harness_sources, repository_root),
        production_source_sha256=_source_tree_sha256(production_sources, repository_root),
        corpus_receipt_sha256=verification.receipt_sha256,
        split_manifest_sha256=prepared_data.identity.split_manifest_sha256,
        candidate_schema_sha256=_sha256_json(CandidateRecord.model_json_schema()),
        signal_detector_sha256=_sha256_json(
            {
                "signal_contract": DiscourseSignal.model_json_schema(),
                "screening_source": "pinned_gum_imported_signals",
            }
        ),
        raw_relation_inventory_sha256=inventory.inventory_sha256,
        ontology_mapping_sha256=_sha256_json(inventory.concept_by_raw),
        decoder_config_sha256=decoder.config_sha256,
        systems=tuple(systems),
    )


def freeze_protocol_artifacts(
    *,
    protocol: ExperimentProtocol,
    configurations: ExperimentConfigurationBundle,
    output_root: Path,
) -> None:
    """Atomically persist the protocol and its complete typed configurations."""

    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        output_root / "experiment-protocol.json": protocol.model_dump_json(indent=2) + "\n",
        output_root / "system-configurations.json": configurations.model_dump_json(indent=2) + "\n",
    }
    for path, content in artifacts.items():
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        if path.exists() or temporary.exists():
            raise RuntimeError(f"frozen protocol artifact already exists: {path.name}")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)


__all__ = ["build_experiment_protocol", "freeze_protocol_artifacts"]
