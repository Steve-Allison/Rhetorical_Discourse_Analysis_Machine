"""Promotion authority rejects mutable, contradictory, or waiver-bearing evidence."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tools.production_ingest.contracts import (
    CandidateIdentity,
    PromotionDecision,
    SourceGateResult,
)
from isanlp_rst.ingest.contracts import SourceForm


def _candidate() -> CandidateIdentity:
    return CandidateIdentity(
        git_commit="1" * 40,
        git_dirty=False,
        wheel_sha256="2" * 64,
        model_release_id="release-1",
        model_digest="3" * 64,
        policy_digest="4" * 64,
        result_contract_version="1.0.0",
    )


def _source_result(*, passed: bool = True, inspected: bool = True) -> SourceGateResult:
    return SourceGateResult(
        source_id="source-1",
        source_form=SourceForm.TEXT,
        gates=(("identity", passed),),
        inspected=inspected,
    )


def test_promotion_decision_has_no_waiver_surface_or_protected_text_field() -> None:
    assert "waiver" not in PromotionDecision.model_fields
    assert "text" not in SourceGateResult.model_fields
    assert "text" not in CandidateIdentity.model_fields


@pytest.mark.parametrize(
    "result",
    [_source_result(passed=False), _source_result(inspected=False)],
)
def test_promotion_decision_cannot_contradict_a_failed_gate_or_inspection(result: SourceGateResult) -> None:
    with pytest.raises(ValidationError, match="must equal all per-source gates"):
        PromotionDecision(
            evidence_date=datetime(2026, 8, 25, tzinfo=UTC),
            candidate=_candidate(),
            source_results=(result, *(_source_result() for _ in range(19))),
            passed=True,
        )


def test_candidate_identity_rejects_changed_or_partial_digests() -> None:
    payload = _candidate().model_dump(mode="json")
    payload["model_digest"] = "changed"
    with pytest.raises(ValidationError, match="model_digest"):
        CandidateIdentity.model_validate(payload)
