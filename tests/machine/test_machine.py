"""The machine: N explicit outcomes, no suppression, no stubs, no retries (FR-014, FR-020, SC-005, SC-007, SC-010)."""

import pytest
from pydantic import ValidationError

from rdam.rst.provider import RstProvider
from rdam import (
    BOUNDARY_TECHNIQUES,
    AggregateRequest,
    FailedOutcome,
    Machine,
    MachineCapabilities,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    ProviderRequest,
    ResultOutcome,
    Retryability,
    SemanticVersion,
    SourceIdentity,
    StructuredInput,
    Technique,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    UnsupportedRecordError,
    UpstreamResultReference,
    canonical_json_bytes,
    load,
    serialize,
    production_machine,
)
from tests.machine.conftest import FakeProvider, dung_declaration, echo_result, rst_declaration, typed_failure


class TestCapabilities:
    def test_empty_machine_reports_every_boundary_unavailable_with_a_stable_reason(self) -> None:
        capabilities = Machine().capabilities()
        assert tuple(item.technique for item in capabilities.techniques) == BOUNDARY_TECHNIQUES
        for item in capabilities.techniques:
            assert item.capability == UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED)
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
            reason=UnavailableReason.NOT_IMPLEMENTED
        )

    def test_two_providers_for_one_boundary_are_rejected(self, rst_provider: FakeProvider) -> None:
        with pytest.raises(ValueError, match="exactly one provider"):
            Machine([rst_provider, FakeProvider(rst_declaration(), echo_result("rst_tree"))])

    def test_supported_production_composition_declares_all_seven_providers_without_loading_models(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
        machine = production_machine(model="openai:gpt-5.6-sol")
        assert tuple(machine.providers) == BOUNDARY_TECHNIQUES
        for item in machine.capabilities().techniques:
            assert item.capability.state == "available"
        assert all(getattr(provider, "_analyst", None) is None for provider in machine.providers.values())
        rst = machine.providers[Technique.RST]
        assert isinstance(rst, RstProvider)
        assert rst._parser is None


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
        assert pdtb.reason is UnavailableReason.NOT_IMPLEMENTED

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
            rst_declaration(capability=UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED)),
            echo_result("rst_tree"),
        )
        aggregate = Machine([withheld]).analyse(AggregateRequest.for_text("t", (Technique.RST,)))
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.NOT_IMPLEMENTED
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

    @pytest.mark.parametrize("defect", ("contract_version", "provenance"))
    def test_a_result_with_false_provider_identity_is_a_deterministic_failure(self, defect: str) -> None:
        declaration = rst_declaration()

        def false_identity(
            _declaration: ProviderDeclaration,
            request: ProviderRequest,
        ) -> NativeTechniqueResult:
            values: dict[str, object] = {
                "technique": Technique.RST,
                "formalism_id": "rst_tree",
                "provider_id": declaration.provider_id,
                "provider_contract_version": declaration.contract_version,
                "source": request.source,
                "payload": {},
                "provenance": declaration.provenance,
            }
            if defect == "contract_version":
                values["provider_contract_version"] = SemanticVersion(root="2.0.0")
            else:
                values["provenance"] = ProviderProvenance(
                    package="impostor",
                    version="9.9.9",
                    licence="unknown",
                )
            return NativeTechniqueResult.model_validate(values)

        aggregate = Machine([FakeProvider(declaration, false_identity)]).analyse(
            AggregateRequest.for_text("t", (Technique.RST,))
        )
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "provider_result_contract_violation"
        assert outcome.failure.message_template == f"result_{defect}_differs_from_declaration"

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        (
            ("technique", Technique.PDTB, "failure_technique_differs_from_declaration"),
            ("provider_id", "another-provider", "failure_names_a_different_provider"),
            ("failed_operation", "load", "failure_operation_is_not_analyse"),
        ),
    )
    def test_a_misidentified_typed_failure_becomes_a_contract_failure(
        self,
        field: str,
        value: object,
        message: str,
    ) -> None:
        declaration = rst_declaration()

        def false_failure(
            _declaration: ProviderDeclaration,
            _request: ProviderRequest,
        ) -> NativeTechniqueResult:
            failure = ProviderFailure(
                technique=Technique.RST,
                provider_id=declaration.provider_id,
                failed_operation="analyse",
                retryability=Retryability.NOT_RETRYABLE,
                code="fixture_failure",
                exception_type="FixtureError",
                message_template="the_fixture_was_told_to_fail",
            ).model_copy(update={field: value})
            raise ProviderError(failure)

        aggregate = Machine([FakeProvider(declaration, false_failure)]).analyse(
            AggregateRequest.for_text("t", (Technique.RST,))
        )
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "provider_failure_contract_violation"
        assert outcome.failure.message_template == message

    def test_an_unexpected_exception_is_a_bug_and_propagates(self) -> None:
        def broken(declaration: ProviderDeclaration, request: ProviderRequest) -> NativeTechniqueResult:
            raise KeyError("bug")

        provider = FakeProvider(rst_declaration(), broken)
        with pytest.raises(KeyError):
            Machine([provider]).analyse(AggregateRequest.for_text("t", (Technique.RST,)))


class TestLineage:
    """FR-015: a consumer of another technique's result names the exact upstream artifact and provider."""

    def _rst_result(self, rst_provider: FakeProvider, text: str) -> NativeTechniqueResult:
        outcome = Machine([rst_provider]).analyse(AggregateRequest.for_text(text, (Technique.RST,))).outcome_for(Technique.RST)
        assert isinstance(outcome, ResultOutcome)
        return outcome.result

    def _derived_request(self, upstream: NativeTechniqueResult) -> AggregateRequest:
        assert upstream.semantic_digest is not None
        return AggregateRequest(
            source=upstream.source,
            text=None,
            techniques=(Technique.DUNG,),
            structured_inputs=(
                StructuredInput(
                    technique=Technique.DUNG,
                    payload={"arguments": ["a", "b"], "attacks": [["a", "b"]]},
                    derived_from=UpstreamResultReference(technique=Technique.RST, result_identity=upstream.semantic_digest),
                ),
            ),
            upstream_results=(upstream,),
        )

    def test_declared_derivation_becomes_lineage_naming_the_exact_upstream_result(
        self, rst_provider: FakeProvider, dung_provider: FakeProvider
    ) -> None:
        upstream = self._rst_result(rst_provider, "The cat sat.")
        assert upstream.semantic_digest is not None
        aggregate = Machine([dung_provider]).analyse(self._derived_request(upstream))

        re_emitted = aggregate.outcome_for(Technique.RST)
        assert isinstance(re_emitted, ResultOutcome) and re_emitted.result == upstream, "the upstream artifact is carried verbatim"
        consumer = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(consumer, ResultOutcome)
        assert consumer.result.payload["structured"] == {"arguments": ["a", "b"], "attacks": [["a", "b"]]}
        assert len(aggregate.lineage) == 1
        reference = aggregate.lineage[0]
        assert reference.consumer_technique is Technique.DUNG and reference.consumer_provider_id == "fake-dung"
        assert reference.upstream_technique is Technique.RST and reference.upstream_provider_id == "fake-rst"
        assert reference.upstream_result_identity == upstream.semantic_digest
        assert reference.upstream_contract_version == upstream.provider_contract_version
        assert dung_provider.calls[0].derived_from == UpstreamResultReference(
            technique=Technique.RST, result_identity=upstream.semantic_digest
        ), "the consumer is told the input was explicitly derived, and from what"
        assert serialize(load(serialize(aggregate))) == serialize(aggregate)

    def test_a_failed_consumer_records_no_lineage(self, rst_provider: FakeProvider) -> None:
        upstream = self._rst_result(rst_provider, "The cat sat.")
        failing_dung = FakeProvider(dung_declaration(), typed_failure())
        aggregate = Machine([failing_dung]).analyse(self._derived_request(upstream))
        assert isinstance(aggregate.outcome_for(Technique.DUNG), FailedOutcome)
        assert aggregate.lineage == ()

    def test_a_derivation_from_a_result_the_request_does_not_carry_is_rejected(self, rst_provider: FakeProvider) -> None:
        upstream = self._rst_result(rst_provider, "The cat sat.")
        other = self._rst_result(rst_provider, "A different text.")
        assert other.semantic_digest is not None
        with pytest.raises(ValidationError, match="does not carry"):
            AggregateRequest(
                source=upstream.source,
                text=None,
                techniques=(Technique.DUNG,),
                structured_inputs=(
                    StructuredInput(
                        technique=Technique.DUNG,
                        payload={"arguments": [], "attacks": []},
                        derived_from=UpstreamResultReference(technique=Technique.RST, result_identity=other.semantic_digest),
                    ),
                ),
                upstream_results=(upstream,),
            )

    def test_an_upstream_result_about_another_source_is_rejected(self, rst_provider: FakeProvider) -> None:
        other = self._rst_result(rst_provider, "A different text.")
        with pytest.raises(ValidationError, match="about this request's source"):
            AggregateRequest.for_text("The cat sat.", (Technique.DUNG,), upstream_results=(other,))

    def test_an_upstream_technique_cannot_also_be_requested(self, rst_provider: FakeProvider) -> None:
        upstream = self._rst_result(rst_provider, "The cat sat.")
        with pytest.raises(ValidationError, match="cannot also be requested"):
            AggregateRequest.for_text("The cat sat.", (Technique.RST, Technique.DUNG), upstream_results=(upstream,))


class TestSerialization:
    def test_aggregate_and_capabilities_round_trip_byte_equal(self, rst_provider: FakeProvider) -> None:
        machine = Machine([rst_provider])
        aggregate = machine.analyse(AggregateRequest.for_text("The cat sat.", (Technique.RST, Technique.IBIS)))
        for record in (aggregate, machine.capabilities()):
            payload = serialize(record)
            assert serialize(load(payload)) == payload

    def test_tampered_payload_is_rejected(self, rst_provider: FakeProvider) -> None:
        payload = serialize(Machine([rst_provider]).capabilities()).decode("utf-8")
        tampered = payload.replace('"reason":"not_implemented"', '"reason":"model_unavailable"', 1)
        assert tampered != payload
        with pytest.raises(ValueError, match="digest mismatch"):
            load(tampered)

    def test_duplicate_keys_are_rejected_before_dispatch(self, rst_provider: FakeProvider) -> None:
        payload = serialize(Machine([rst_provider]).capabilities()).decode("utf-8")
        duplicate = payload.replace("{", '{"contract":"rdam.capabilities",', 1)
        with pytest.raises(ValueError, match="duplicate JSON object key"):
            load(duplicate)

    @pytest.mark.parametrize(
        "mutation",
        (
            ('"contract":"rdam.capabilities"', '"contract":"rdam.unknown"'),
            ('"contract_version":"1.0.0"', '"contract_version":"2.0.0"'),
        ),
    )
    def test_unknown_contract_or_version_is_rejected_before_digest_validation(
        self,
        rst_provider: FakeProvider,
        mutation: tuple[str, str],
    ) -> None:
        payload = serialize(Machine([rst_provider]).capabilities()).decode("utf-8")
        unknown = payload.replace(*mutation, 1)
        assert unknown != payload
        with pytest.raises(UnsupportedRecordError, match="unsupported"):
            load(unknown)
