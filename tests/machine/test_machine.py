"""The machine: N explicit outcomes, no suppression, no stubs, no retries (FR-014, FR-020, SC-005, SC-007, SC-010)."""

import pytest

from rdam import (
    BOUNDARY_TECHNIQUES,
    AggregateRequest,
    FailedOutcome,
    Machine,
    MachineCapabilities,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderRequest,
    ResultOutcome,
    Retryability,
    SourceIdentity,
    StructuredInput,
    Technique,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    canonical_json_bytes,
    load,
    serialize,
)
from tests.machine.conftest import FakeProvider, dung_declaration, echo_result, rst_declaration, typed_failure


class TestCapabilities:
    def test_empty_machine_reports_every_boundary_unavailable_with_a_stable_reason(self) -> None:
        capabilities = Machine().capabilities()
        assert tuple(item.technique for item in capabilities.techniques) == BOUNDARY_TECHNIQUES
        for item in capabilities.techniques:
            assert item.capability == UnavailableCapability(reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION)
            assert item.formalisms == ()
        assert capabilities.capability_for(Technique.DUNG).requires_structured_input is True
        assert capabilities.capability_for(Technique.RST).requires_structured_input is False

    def test_capability_reporting_never_calls_a_provider(self, rst_provider: FakeProvider) -> None:
        Machine([rst_provider]).capabilities()
        assert rst_provider.calls == []

    def test_withholding_one_provider_leaves_every_other_declaration_byte_identical(
        self, rst_provider: FakeProvider, dung_provider: FakeProvider
    ) -> None:
        with_dung = Machine([rst_provider, dung_provider]).capabilities()
        without_dung = Machine([rst_provider]).capabilities()
        for technique in BOUNDARY_TECHNIQUES:
            if technique is Technique.DUNG:
                continue
            assert serialize_capability(with_dung, technique) == serialize_capability(without_dung, technique)
        assert without_dung.capability_for(Technique.DUNG).capability == UnavailableCapability(
            reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION
        )

    def test_two_providers_for_one_boundary_are_rejected(self, rst_provider: FakeProvider) -> None:
        with pytest.raises(ValueError, match="exactly one provider"):
            Machine([rst_provider, FakeProvider(rst_declaration(), echo_result("rst_tree"))])


def serialize_capability(capabilities: MachineCapabilities, technique: Technique) -> bytes:
    return canonical_json_bytes(capabilities.capability_for(technique))


class TestAnalyse:
    def test_one_explicit_outcome_per_requested_technique(self, rst_provider: FakeProvider) -> None:
        request = AggregateRequest.for_text("The cat sat.", (Technique.RST, Technique.PDTB, Technique.SDRT))
        aggregate = Machine([rst_provider]).analyse(request)
        assert [type(item).__name__ for item in aggregate.outcomes] == [
            "ResultOutcome",
            "UnavailableOutcome",
            "UnavailableOutcome",
        ]
        result = aggregate.outcome_for(Technique.RST)
        assert isinstance(result, ResultOutcome)
        assert result.result.technique is Technique.RST
        assert result.result.payload["text"] == "The cat sat."
        assert result.result.source == request.source
        pdtb = aggregate.outcome_for(Technique.PDTB)
        assert isinstance(pdtb, UnavailableOutcome)
        assert pdtb.reason is UnavailableReason.NO_PROMOTED_IMPLEMENTATION

    def test_a_typed_failure_never_suppresses_another_success(self, rst_provider: FakeProvider) -> None:
        failing_dung = FakeProvider(dung_declaration(), typed_failure())
        request = AggregateRequest.for_text(
            "The cat sat.",
            (Technique.RST, Technique.DUNG),
            structured_inputs=(StructuredInput(technique=Technique.DUNG, payload={"arguments": [], "attacks": []}),),
        )
        aggregate = Machine([rst_provider, failing_dung]).analyse(request)
        assert isinstance(aggregate.outcome_for(Technique.RST), ResultOutcome)
        failed = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(failed, FailedOutcome)
        assert failed.failure.code == "fixture_failure"
        assert failed.failure.retryability is Retryability.NOT_RETRYABLE
        assert len(failing_dung.calls) == 1, "the machine never retries"

    def test_structured_technique_without_its_input_is_unavailable_not_failed(self, dung_provider: FakeProvider) -> None:
        request = AggregateRequest.for_text("text", (Technique.RST, Technique.DUNG))
        aggregate = Machine([dung_provider]).analyse(request)
        dung = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(dung, UnavailableOutcome)
        assert dung.reason is UnavailableReason.MISSING_STRUCTURED_INPUT
        assert dung_provider.calls == []

    def test_structured_input_reaches_the_provider(self, dung_provider: FakeProvider) -> None:
        payload = {"arguments": ["a", "b"], "attacks": [["a", "b"]]}
        request = AggregateRequest(
            source=SourceIdentity.from_bytes(b"framework", media_type="application/json"),
            text=None,
            techniques=(Technique.DUNG,),
            structured_inputs=(StructuredInput(technique=Technique.DUNG, payload=payload),),
        )
        aggregate = Machine([dung_provider]).analyse(request)
        result = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(result, ResultOutcome)
        assert result.result.payload["structured"] == payload

    def test_withheld_provider_reports_its_reason_and_is_not_called(self) -> None:
        withheld = FakeProvider(
            rst_declaration(capability=UnavailableCapability(reason=UnavailableReason.WITHHELD)),
            echo_result("rst_tree"),
        )
        aggregate = Machine([withheld]).analyse(AggregateRequest.for_text("t", (Technique.RST,)))
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.WITHHELD
        assert withheld.calls == []

    def test_a_result_outside_the_declaration_is_a_deterministic_failure(self) -> None:
        # Declares rst_tree only as available, but answers with erst_graph.
        provider = FakeProvider(rst_declaration(erst_loaded=False), echo_result("erst_graph"))
        aggregate = Machine([provider]).analyse(AggregateRequest.for_text("t", (Technique.RST,)))
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "provider_result_contract_violation"
        assert outcome.failure.message_template == "result_formalism_is_declared_unavailable"
        assert outcome.failure.retryability is Retryability.NOT_RETRYABLE

    def test_an_unexpected_exception_is_a_bug_and_propagates(self) -> None:
        def broken(declaration: ProviderDeclaration, request: ProviderRequest) -> NativeTechniqueResult:
            raise KeyError("bug")

        provider = FakeProvider(rst_declaration(), broken)
        with pytest.raises(KeyError):
            Machine([provider]).analyse(AggregateRequest.for_text("t", (Technique.RST,)))


class TestSerialization:
    def test_aggregate_and_capabilities_round_trip_byte_equal(self, rst_provider: FakeProvider) -> None:
        machine = Machine([rst_provider])
        aggregate = machine.analyse(AggregateRequest.for_text("The cat sat.", (Technique.RST, Technique.IBIS)))
        for record in (aggregate, machine.capabilities()):
            payload = serialize(record)
            assert serialize(load(payload)) == payload

    def test_tampered_payload_is_rejected(self, rst_provider: FakeProvider) -> None:
        payload = serialize(Machine([rst_provider]).capabilities()).decode("utf-8")
        tampered = payload.replace('"requires_structured_input":false', '"requires_structured_input":true', 1)
        assert tampered != payload
        with pytest.raises(ValueError, match="digest mismatch"):
            load(tampered)
