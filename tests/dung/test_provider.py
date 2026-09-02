"""The Dung provider through the machine: capability from its packaged decision, structured input only."""

from datetime import UTC, datetime

import pytest

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
    ProviderError,
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
from rdam_dung import PROVIDER_ID, DungProvider, packaged_decision, source_identity


def _decision(outcome: PromotionOutcome, artifact: Sha256Identity | None = None) -> PromotionDecision:
    return PromotionDecision(
        decision_id=f"dung-fixture-{outcome.value}",
        decided_at=datetime(2026, 9, 2, tzinfo=UTC),
        decided_by="test",
        candidate=CandidateIdentity(
            technique=Technique.DUNG,
            candidate_id=PROVIDER_ID,
            artifact_identity=artifact or source_identity(),
            description="fixture",
        ),
        output_quality=FormalQualityEvidence(correctness_arguments=("definitions",), property_tests=("tests/dung/test_semantics.py",)),
        calibration=CalibrationEvidence(state="declared_absent", description="deterministic"),
        latency=LatencyEvidence(state="measured", platform="fixture", measurements=(Measurement(name="p50_ms", value=1.0, partition="fixture", unit="ms"),)),
        compatibility=CompatibilityEvidence(state="verified", environment="fixture", import_time_side_effects=False, packaging_declares_dependencies=True),
        provenance=ProvenanceEvidence(code_revision="fixture", configuration_identity="exhaustive-subset-v1"),
        licensing=LicensingEvidence(licence="MIT", intended_use="local analysis", permits_intended_use=True, decision_note="own code, MIT"),
        outcome=outcome,
        recommendation=Recommendation(summary="fixture", strengths=("s",), limitations=("l",)),
    )


FRAMEWORK = {"arguments": ["a", "b", "c"], "attacks": [["a", "b"], ["b", "c"]]}


class TestDeclaration:
    def test_without_a_decision_the_provider_is_unavailable(self) -> None:
        provider = DungProvider(decision=None) if packaged_decision() is None else DungProvider(decision=_decision(PromotionOutcome.WITHHOLD))
        assert isinstance(provider.declaration.capability, UnavailableCapability)

    def test_a_decision_about_other_code_does_not_promote_this_code(self) -> None:
        stale = _decision(PromotionOutcome.PROMOTE, artifact=Sha256Identity(hex_digest="0" * 64))
        assert DungProvider(decision=stale).declaration.capability == UnavailableCapability(
            reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION
        )

    def test_a_promote_decision_naming_this_source_makes_it_available(self) -> None:
        declaration = DungProvider(decision=_decision(PromotionOutcome.PROMOTE)).declaration
        assert declaration.technique is Technique.DUNG
        assert declaration.requires_structured_input is True
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.provenance.source_revision == source_identity().hex_digest


class TestThroughTheMachine:
    def test_supplied_framework_is_evaluated_and_never_derived_from_text(self) -> None:
        machine = Machine([DungProvider(decision=_decision(PromotionOutcome.PROMOTE))])
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"framework", media_type="application/json"),
            text=None,
            techniques=(Technique.DUNG,),
            structured_inputs=(StructuredInput(technique=Technique.DUNG, payload=FRAMEWORK),),
        )
        outcome = machine.analyse(request).outcome_for(Technique.DUNG)
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        assert payload["input_origin"] == "supplied"
        extensions = payload["extensions"]
        assert isinstance(extensions, dict)
        assert extensions["grounded"] == ["a", "c"]
        assert extensions["stable"] == [["a", "c"]]

    def test_missing_structured_input_is_unavailable_not_failed(self) -> None:
        machine = Machine([DungProvider(decision=_decision(PromotionOutcome.PROMOTE))])
        outcome = machine.analyse(AggregateRequest.for_text("some text", (Technique.DUNG,))).outcome_for(Technique.DUNG)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MISSING_STRUCTURED_INPUT

    def test_malformed_framework_is_a_typed_deterministic_failure(self) -> None:
        machine = Machine([DungProvider(decision=_decision(PromotionOutcome.PROMOTE))])
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"bad", media_type="application/json"),
            text=None,
            techniques=(Technique.DUNG,),
            structured_inputs=(StructuredInput(technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": [["a", "zz"]]}),),
        )
        outcome = machine.analyse(request).outcome_for(Technique.DUNG)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "invalid_argumentation_framework"

    def test_over_capacity_is_refused_not_approximated(self) -> None:
        provider = DungProvider(decision=_decision(PromotionOutcome.PROMOTE), capacity=2)
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"big", media_type="application/json"),
            text=None,
            techniques=(Technique.DUNG,),
            structured_inputs=(StructuredInput(technique=Technique.DUNG, payload=FRAMEWORK),),
        )
        outcome = Machine([provider]).analyse(request).outcome_for(Technique.DUNG)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "framework_exceeds_declared_capacity"

    def test_direct_call_on_unavailable_provider_is_typed(self) -> None:
        provider = DungProvider(decision=_decision(PromotionOutcome.WITHHOLD))
        with pytest.raises(ProviderError) as caught:
            provider.analyse(
                __import__("rdam").ProviderRequest(
                    source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=FRAMEWORK
                )
            )
        assert caught.value.failure.code == "provider_not_available"
