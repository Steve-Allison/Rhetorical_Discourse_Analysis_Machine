"""The Dung provider through the machine: structured input only, never derived from text."""

from collections.abc import Mapping

import pytest

from rdam import (
    AggregateRequest,
    AvailableCapability,
    FailedOutcome,
    Machine,
    ProviderRequest,
    ResultOutcome,
    Sha256Identity,
    SourceIdentity,
    StructuredInput,
    Technique,
    UnavailableOutcome,
    UnavailableReason,
    UpstreamResultReference,
)
from rdam._strict import JsonValue
from rdam.dung import PROVIDER_ID, DungProvider, source_identity

FRAMEWORK: Mapping[str, JsonValue] = {"arguments": ["a", "b", "c"], "attacks": [["a", "b"], ["b", "c"]]}


def _request(payload: Mapping[str, JsonValue] = FRAMEWORK) -> AggregateRequest:
    return AggregateRequest(
        source=SourceIdentity.from_bytes(b"framework", media_type="application/json"),
        text=None,
        techniques=(Technique.DUNG,),
        structured_inputs=(StructuredInput(technique=Technique.DUNG, payload=payload),),
    )


class TestDeclaration:
    def test_the_provider_is_available_and_names_its_own_source(self) -> None:
        declaration = DungProvider().declaration
        assert declaration.technique is Technique.DUNG
        assert declaration.requires_structured_input is True
        assert declaration.capability == AvailableCapability(
            provider_id=PROVIDER_ID, contract_version=declaration.contract_version
        )
        assert declaration.provenance.source_revision == source_identity().hex_digest
        assert declaration.provenance.licence == "MIT (LICENSE)"


class TestThroughTheMachine:
    def test_supplied_framework_is_evaluated_and_never_derived_from_text(self) -> None:
        outcome = Machine([DungProvider()]).analyse(_request()).outcome_for(Technique.DUNG)
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        assert payload["input_origin"] == "supplied"
        extensions = payload["extensions"]
        assert isinstance(extensions, dict)
        assert extensions["grounded"] == ["a", "c"]
        assert extensions["stable"] == [["a", "c"]]

    def test_missing_structured_input_is_unavailable_not_failed(self) -> None:
        machine = Machine([DungProvider()])
        outcome = machine.analyse(AggregateRequest.for_text("some text", (Technique.DUNG,))).outcome_for(Technique.DUNG)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MISSING_STRUCTURED_INPUT

    def test_malformed_framework_is_a_typed_deterministic_failure(self) -> None:
        outcome = Machine([DungProvider()]).analyse(
            _request({"arguments": ["a"], "attacks": [["a", "zz"]]})
        ).outcome_for(Technique.DUNG)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "invalid_argumentation_framework"

    def test_over_capacity_is_refused_not_approximated(self) -> None:
        outcome = Machine([DungProvider(capacity=2)]).analyse(_request()).outcome_for(Technique.DUNG)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "framework_exceeds_declared_capacity"

    def test_an_explicitly_derived_framework_names_its_upstream_result(self) -> None:
        """FR-016: supplied vs explicitly derived is recorded in the payload, with the exact upstream identity."""

        reference = UpstreamResultReference(technique=Technique.RST, result_identity=Sha256Identity(hex_digest="a" * 64))
        result = DungProvider().analyse(
            ProviderRequest(source=SourceIdentity.from_bytes(b"f"), text=None, structured_input=FRAMEWORK, derived_from=reference)
        )
        assert result.payload["input_origin"] == "explicitly_derived"
        assert result.payload["derived_from"] == {"technique": "rst", "result_identity": "a" * 64}
        supplied = DungProvider().analyse(
            ProviderRequest(source=SourceIdentity.from_bytes(b"f"), text=None, structured_input=FRAMEWORK)
        )
        assert supplied.payload["input_origin"] == "supplied"
        assert "derived_from" not in supplied.payload

    def test_an_undeclared_formalism_is_a_typed_failure(self) -> None:
        from rdam import ProviderError

        with pytest.raises(ProviderError) as caught:
            DungProvider().analyse(
                ProviderRequest(
                    source=SourceIdentity.from_bytes(b"x"),
                    text=None,
                    structured_input=FRAMEWORK,
                    formalism_id="not_a_formalism",
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"
