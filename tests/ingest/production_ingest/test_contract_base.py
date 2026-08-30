"""Foundational invariants shared by every production contract model."""

from math import inf, nan

from pydantic import ValidationError
import pytest

from isanlp_rst.ingest.contracts.base import (
    CoverageUnit,
    ExactCoverage,
    SemanticVersion,
    Sha256Identity,
    StrictContractModel,
)


class _Nested(StrictContractModel):
    label: str


class _Container(StrictContractModel):
    nested: _Nested
    ordered: tuple[str, ...]
    score: float


@pytest.mark.parametrize("value", [inf, -inf, nan])
def test_contract_models_reject_non_finite_numbers(value: float) -> None:
    with pytest.raises(ValidationError):
        _Container(nested=_Nested(label="ok"), ordered=(), score=value)


def test_contract_models_are_recursive_strict_frozen_and_closed() -> None:
    with pytest.raises(ValidationError):
        _Container.model_validate(
            {
                "nested": {"label": "ok", "unexpected": "forbidden"},
                "ordered": (),
                "score": 1.0,
            }
        )

    value = _Container(nested=_Nested(label="ok"), ordered=("a", "b"), score=1.0)
    with pytest.raises(ValidationError):
        value.score = 2.0
    assert isinstance(value.ordered, tuple)


@pytest.mark.parametrize("value", ["2.0", "2.0.0-rc1", "v2.0.0", "02.0.0"])
def test_semantic_version_requires_normalized_release_triplet(value: str) -> None:
    with pytest.raises(ValidationError):
        SemanticVersion(root=value)


def test_sha256_identity_has_one_unambiguous_object_form() -> None:
    identity = Sha256Identity(hex_digest="a" * 64)
    assert identity.algorithm == "sha256"
    assert identity.model_dump(mode="json") == {
        "algorithm": "sha256",
        "hex_digest": "a" * 64,
    }
    with pytest.raises(ValidationError):
        Sha256Identity(hex_digest="A" * 64)


def test_exact_coverage_preserves_empty_and_complete_domains() -> None:
    empty = ExactCoverage(covered_units=0, total_units=0, unit=CoverageUnit.ITEMS)
    complete = ExactCoverage(covered_units=7, total_units=7, unit=CoverageUnit.ANCHORS)
    assert empty.ratio is None
    assert complete.ratio == 1.0
    with pytest.raises(ValidationError):
        ExactCoverage(covered_units=2, total_units=1, unit=CoverageUnit.SEGMENTS)
