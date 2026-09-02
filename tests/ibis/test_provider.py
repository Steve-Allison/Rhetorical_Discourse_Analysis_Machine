"""The IBIS provider through the machine: supplied structure in, validated map out, nothing extracted."""

from collections.abc import Mapping
from datetime import UTC, datetime

from rdam import (
    AggregateRequest,
    AvailableCapability,
    CalibrationEvidence,
    CandidateIdentity,
    CompatibilityEvidence,
    FailedOutcome,
    FormalQualityEvidence,
    LatencyEvidence,
    LicensingEvidence,
    Machine,
    Measurement,
    PromotionDecision,
    PromotionOutcome,
    ProvenanceEvidence,
    Recommendation,
    ResultOutcome,
    Sha256Identity,
    SourceIdentity,
    StructuredInput,
    Technique,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
)
from rdam._strict import JsonValue
from rdam.ibis import PROVIDER_ID, IbisProvider, source_identity


def _decision(outcome: PromotionOutcome, artifact: Sha256Identity | None = None) -> PromotionDecision:
    return PromotionDecision(
        decision_id=f"ibis-fixture-{outcome.value}",
        decided_at=datetime(2026, 9, 2, tzinfo=UTC),
        decided_by="test",
        candidate=CandidateIdentity(technique=Technique.IBIS, candidate_id=PROVIDER_ID, artifact_identity=artifact or source_identity(), description="fixture"),
        output_quality=FormalQualityEvidence(correctness_arguments=("grammar",), property_tests=("tests/ibis/test_grammar.py",)),
        calibration=CalibrationEvidence(state="declared_absent", description="deterministic"),
        latency=LatencyEvidence(state="measured", platform="fixture", measurements=(Measurement(name="p50_ms", value=1.0, partition="fixture", unit="ms"),)),
        compatibility=CompatibilityEvidence(state="verified", environment="fixture", import_time_side_effects=False, packaging_declares_dependencies=True),
        provenance=ProvenanceEvidence(code_revision="fixture", configuration_identity="gibis-grammar-v1"),
        licensing=LicensingEvidence(licence="MIT", intended_use="local analysis", permits_intended_use=True, decision_note="own code, MIT"),
        outcome=outcome,
        recommendation=Recommendation(summary="fixture", strengths=("s",), limitations=("l",)),
    )


STRUCTURE = {
    "nodes": [
        {"id": "i1", "kind": "issue", "text": "Should the meeting move to Tuesdays?"},
        {"id": "p1", "kind": "position", "text": "Yes, move it."},
        {"id": "a1", "kind": "argument", "text": "Tuesday has fewer conflicts."},
        {"id": "a2", "kind": "argument", "text": "Two members cannot attend on Tuesdays."},
    ],
    "links": [
        {"from": "p1", "relation": "responds_to", "to": "i1"},
        {"from": "a1", "relation": "supports", "to": "p1"},
        {"from": "a2", "relation": "objects_to", "to": "p1"},
    ],
}


def _request(payload: Mapping[str, JsonValue]) -> AggregateRequest:
    return AggregateRequest(
        source=SourceIdentity.from_bytes(b"structure", media_type="application/json"),
        text=None,
        techniques=(Technique.IBIS,),
        structured_inputs=(StructuredInput(technique=Technique.IBIS, payload=payload),),
    )


class TestDeclaration:
    def test_stale_decision_does_not_promote(self) -> None:
        stale = _decision(PromotionOutcome.PROMOTE, artifact=Sha256Identity(hex_digest="0" * 64))
        assert IbisProvider(decision=stale).declaration.capability == UnavailableCapability(reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION)

    def test_promote_decision_naming_this_source_is_available(self) -> None:
        declaration = IbisProvider(decision=_decision(PromotionOutcome.PROMOTE)).declaration
        assert declaration.technique is Technique.IBIS
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.requires_structured_input is True


class TestThroughTheMachine:
    def test_supplied_structure_is_validated_and_mapped_with_no_extraction(self) -> None:
        machine = Machine([IbisProvider(decision=_decision(PromotionOutcome.PROMOTE))])
        outcome = machine.analyse(_request(STRUCTURE)).outcome_for(Technique.IBIS)
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        assert payload["input_origin"] == "supplied"
        assert payload["extraction"] is None
        deliberation = payload["map"]
        assert isinstance(deliberation, dict)
        assert deliberation["issues"] == [
            {
                "id": "i1",
                "positions": [{"id": "p1", "supporting": ["a1"], "objecting": ["a2"]}],
                "raised_by": [],
                "questions": [],
                "generalizes": [],
                "specializes": [],
                "replaces": [],
            }
        ]

    def test_grammar_violation_is_a_typed_deterministic_failure(self) -> None:
        bad = {**STRUCTURE, "links": [*STRUCTURE["links"], {"from": "a1", "relation": "responds_to", "to": "i1"}]}
        outcome = Machine([IbisProvider(decision=_decision(PromotionOutcome.PROMOTE))]).analyse(_request(bad)).outcome_for(Technique.IBIS)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "invalid_ibis_structure"

    def test_text_only_request_is_unavailable_not_failed(self) -> None:
        machine = Machine([IbisProvider(decision=_decision(PromotionOutcome.PROMOTE))])
        outcome = machine.analyse(AggregateRequest.for_text("a transcript", (Technique.IBIS,))).outcome_for(Technique.IBIS)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MISSING_STRUCTURED_INPUT
