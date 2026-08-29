"""Technology-matrix tests for completeness, evidence, and non-substitution."""

from pathlib import Path

from pydantic import ValidationError
import pytest

from workbench.research.erst.contracts import MandatoryExperimentSystem
from workbench.research.erst.technology import (
    HubModelEvidence,
    TechnologyConstraint,
    TechnologyMatrix,
    build_technology_matrix,
    enrich_technology_matrix,
)

_ROOT = Path(__file__).resolve().parents[3]


def _required_revision(matrix: TechnologyMatrix, model_id: str) -> str:
    revision = next(system.model_revision for system in matrix.systems if system.model_id == model_id)
    assert revision is not None
    return revision


def test_matrix_retains_all_systems_and_explicit_constraints() -> None:
    matrix = build_technology_matrix(_ROOT / "config/erst/tokenizer-compatibility.json")

    assert tuple(system.system for system in matrix.systems) == tuple(MandatoryExperimentSystem)
    dual_encoder = matrix.systems[0]
    assert TechnologyConstraint.TOKENIZER_CONVERSION_REQUIRED in dual_encoder.constraints
    assert dual_encoder.tokenizer_probe_succeeded is False
    assert len(matrix.matrix_sha256) == 64


def test_matrix_rejects_dropped_system() -> None:
    matrix = build_technology_matrix(_ROOT / "config/erst/tokenizer-compatibility.json")

    with pytest.raises(ValidationError, match="every mandatory system"):
        TechnologyMatrix.model_validate(
            {**matrix.model_dump(), "systems": matrix.systems[:-1], "matrix_sha256": ""}
        )


def test_hub_evidence_must_cover_every_model_and_preserve_revision_and_license() -> None:
    matrix = build_technology_matrix(_ROOT / "config/erst/tokenizer-compatibility.json")
    evidence = tuple(
        HubModelEvidence(
            model_id=model_id,
            revision=_required_revision(matrix, model_id),
            model_license=next(
                system.model_license for system in matrix.systems if system.model_id == model_id
            ),
            weight_file_bytes=1024,
        )
        for model_id in dict.fromkeys(
            system.model_id for system in matrix.systems if system.model_id is not None
        )
    )

    enriched = enrich_technology_matrix(matrix, evidence)

    assert all(
        system.weight_file_bytes == 1024
        for system in enriched.systems
        if system.model_id is not None
    )
    assert enriched.matrix_sha256 != matrix.matrix_sha256


def test_frozen_live_matrix_has_weight_evidence_for_every_model_row() -> None:
    matrix = TechnologyMatrix.model_validate_json(
        (_ROOT / "workbench/research/erst/technology-matrix.json").read_text(encoding="utf-8")
    )

    assert len(matrix.systems) == 10
    assert all(
        system.weight_file_bytes is not None
        for system in matrix.systems
        if system.model_id is not None
    )
