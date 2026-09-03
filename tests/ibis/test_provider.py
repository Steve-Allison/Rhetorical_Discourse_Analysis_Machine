"""The IBIS provider through the machine: supplied structure in, validated map out, nothing extracted."""

from collections.abc import Mapping

import pytest

from rdam import (
    AggregateRequest,
    AvailableCapability,
    FailedOutcome,
    Machine,
    ProviderError,
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
from rdam.ibis import PROVIDER_ID, IbisProvider, source_identity

NODES: list[JsonValue] = [
    {"id": "i1", "kind": "issue", "text": "Should the meeting move to Tuesdays?"},
    {"id": "p1", "kind": "position", "text": "Yes, move it."},
    {"id": "a1", "kind": "argument", "text": "Tuesday has fewer conflicts."},
    {"id": "a2", "kind": "argument", "text": "Two members cannot attend on Tuesdays."},
]
LINKS: list[JsonValue] = [
    {"from": "p1", "relation": "responds_to", "to": "i1"},
    {"from": "a1", "relation": "supports", "to": "p1"},
    {"from": "a2", "relation": "objects_to", "to": "p1"},
]
STRUCTURE: Mapping[str, JsonValue] = {"nodes": NODES, "links": LINKS}


def _request(payload: Mapping[str, JsonValue] = STRUCTURE) -> AggregateRequest:
    return AggregateRequest(
        source=SourceIdentity.from_bytes(b"structure", media_type="application/json"),
        text=None,
        techniques=(Technique.IBIS,),
        structured_inputs=(StructuredInput(technique=Technique.IBIS, payload=payload),),
    )


class TestDeclaration:
    def test_the_provider_is_available_and_names_its_own_source(self) -> None:
        declaration = IbisProvider().declaration
        assert declaration.technique is Technique.IBIS
        assert declaration.requires_structured_input is True
        assert declaration.capability == AvailableCapability(
            provider_id=PROVIDER_ID, contract_version=declaration.contract_version
        )
        assert declaration.provenance.source_revision
        first_identity = source_identity()
        assert source_identity() is first_identity
        assert first_identity.hex_digest != "0" * 64


class TestThroughTheMachine:
    def test_undeclared_formalism_is_a_typed_failure(self) -> None:
        with pytest.raises(ProviderError) as caught:
            IbisProvider().analyse(
                ProviderRequest(
                    source=SourceIdentity.from_bytes(b"s"),
                    text=None,
                    structured_input=STRUCTURE,
                    formalism_id="not_ibis",
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"

    def test_supplied_structure_is_validated_and_mapped_with_no_extraction(self) -> None:
        outcome = Machine([IbisProvider()]).analyse(_request()).outcome_for(Technique.IBIS)
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        assert payload["input_origin"] == "supplied"
        assert payload["extraction"] is None
        deliberation = payload["map"]
        assert isinstance(deliberation, Mapping)
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
        bad: Mapping[str, JsonValue] = {
            "nodes": NODES,
            "links": [*LINKS, {"from": "a1", "relation": "responds_to", "to": "i1"}],
        }
        outcome = Machine([IbisProvider()]).analyse(_request(bad)).outcome_for(Technique.IBIS)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "invalid_ibis_structure"

    def test_an_explicitly_derived_structure_names_its_upstream_result_and_still_extracts_nothing(self) -> None:
        """FR-017: the caller's derivation is recorded; ``extraction`` stays None because the provider extracted nothing."""

        reference = UpstreamResultReference(technique=Technique.RST, result_identity=Sha256Identity(hex_digest="b" * 64))
        result = IbisProvider().analyse(
            ProviderRequest(source=SourceIdentity.from_bytes(b"s"), text=None, structured_input=STRUCTURE, derived_from=reference)
        )
        assert result.payload["input_origin"] == "explicitly_derived"
        assert result.payload["extraction"] is None
        assert result.payload["derived_from"] == {"technique": "rst", "result_identity": "b" * 64}

    def test_text_only_request_is_unavailable_not_failed(self) -> None:
        machine = Machine([IbisProvider()])
        outcome = machine.analyse(AggregateRequest.for_text("a transcript", (Technique.IBIS,))).outcome_for(Technique.IBIS)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MISSING_STRUCTURED_INPUT
