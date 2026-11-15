"""The dual-mode IBIS provider through the machine: supplied structure or grounded extraction."""

from collections.abc import Mapping

from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
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
from rdam.ibis import PROVIDER_ID_PREFIX, IbisProvider, source_identity

MODEL = "openai:gpt-5.6-sol"

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


@pytest.fixture(autouse=True)
def never_a_real_request():
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("rdam._llm._nearest_dotenv", lambda *_args, **_kwargs: None)


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used-for-any-request")


def _request(payload: Mapping[str, JsonValue] = STRUCTURE) -> AggregateRequest:
    return AggregateRequest(
        source=SourceIdentity.from_bytes(b"structure", media_type="application/json"),
        text=None,
        techniques=(Technique.IBIS,),
        structured_inputs=(StructuredInput(technique=Technique.IBIS, payload=payload),),
    )


class TestDeclaration:
    def test_the_provider_is_available_and_names_its_own_source(self) -> None:
        provider = IbisProvider(model=MODEL)
        declaration = provider.declaration
        assert declaration.technique is Technique.IBIS
        assert declaration.requires_structured_input is False
        assert declaration.accepts_structured_input is True
        assert declaration.capability == AvailableCapability(
            provider_id=f"{PROVIDER_ID_PREFIX}/{MODEL}", contract_version=declaration.contract_version
        )
        assert declaration.provenance.source_revision
        first_identity = source_identity()
        assert source_identity() is first_identity
        assert first_identity.hex_digest != "0" * 64


class TestThroughTheMachine:
    def test_undeclared_formalism_is_a_typed_failure(self) -> None:
        with pytest.raises(ProviderError) as caught:
            IbisProvider(model=MODEL).analyse(
                ProviderRequest(
                    source=SourceIdentity.from_bytes(b"s"),
                    text=None,
                    structured_input=STRUCTURE,
                    formalism_id="not_ibis",
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"

    def test_supplied_structure_is_validated_and_mapped_with_no_extraction(self) -> None:
        outcome = Machine([IbisProvider(model=MODEL)]).analyse(_request()).outcome_for(Technique.IBIS)
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
        outcome = Machine([IbisProvider(model=MODEL)]).analyse(_request(bad)).outcome_for(Technique.IBIS)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "invalid_ibis_structure"

    def test_an_explicitly_derived_structure_names_its_upstream_result_and_still_extracts_nothing(self) -> None:
        reference = UpstreamResultReference(technique=Technique.RST, result_identity=Sha256Identity(hex_digest="b" * 64))
        result = IbisProvider(model=MODEL).analyse(
            ProviderRequest(source=SourceIdentity.from_bytes(b"s"), text=None, structured_input=STRUCTURE, derived_from=reference)
        )
        assert result.payload["input_origin"] == "explicitly_derived"
        assert result.payload["extraction"] is None
        assert result.payload["derived_from"] == {"technique": "rst", "result_identity": "b" * 64}

    def test_text_only_request_without_credentials_is_unavailable_not_failed(self, no_credentials: None) -> None:
        machine = Machine([IbisProvider(model=MODEL)])
        outcome = machine.analyse(AggregateRequest.for_text("a transcript", (Technique.IBIS,))).outcome_for(Technique.IBIS)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_text_only_request_with_grounded_extraction_produces_aligned_ibis_map(self, with_credentials: None) -> None:
        provider = IbisProvider(model=MODEL)
        source_text = "Should we migrate to Postgres? Yes, adopt Postgres. It supports transactional DDL."
        proposal = {
            "nodes": [
                {
                    "id": "i1",
                    "kind": "issue",
                    "text": "Should we migrate to Postgres?",
                    "evidence": {"quote": "Should we migrate to Postgres?", "occurrence": 1},
                },
                {
                    "id": "p1",
                    "kind": "position",
                    "text": "Yes, adopt Postgres.",
                    "evidence": {"quote": "Yes, adopt Postgres.", "occurrence": 1},
                },
                {
                    "id": "a1",
                    "kind": "argument",
                    "text": "It supports transactional DDL.",
                    "evidence": {"quote": "It supports transactional DDL.", "occurrence": 1},
                },
            ],
            "links": [
                {"from": "p1", "relation": "responds_to", "to": "i1"},
                {"from": "a1", "relation": "supports", "to": "p1"},
            ],
        }

        def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=proposal)])

        with provider._built().agent.override(model=FunctionModel(respond)):
            aggregate = Machine([provider]).analyse(AggregateRequest.for_text(source_text, (Technique.IBIS,)))
        outcome = aggregate.outcome_for(Technique.IBIS)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.payload["input_origin"] == "extracted"
        assert len(outcome.result.source_alignment) == 3
        assert len(aggregate.xpath_alignment) >= 1
