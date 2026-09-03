"""The PDTB provider through its independent and aggregate contracts."""

from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest
from typing import Any

from rdam import (
    AggregateRequest,
    AvailableCapability,
    FailedOutcome,
    Machine,
    ProviderError,
    ProviderRequest,
    ResultOutcome,
    SourceIdentity,
    Technique,
    UnavailableCapability,
    UnavailableReason,
    technique_curie,
)
from rdam.pdtb import PROVIDER_ID_PREFIX, PdtbProvider, source_identity
from rdam.toulmin import ToulminProvider

MODEL = "openai:gpt-5.6-sol"
TEXT = "Rain so traffic"
VALID_ANALYSIS: dict[str, Any] = {
    "relations": [
        {
            "relation_id": "r1",
            "relation_type": "Explicit",
            "arg1": {"spans": [{"start": 0, "end": 4, "text": "Rain"}]},
            "arg2": {"spans": [{"start": 8, "end": 15, "text": "traffic"}]},
            "senses": ["Contingency.Cause.Result"],
            "connective_spans": [{"start": 5, "end": 7, "text": "so"}],
        }
    ]
}


@pytest.fixture(autouse=True)
def never_a_real_request():
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_args, **_kwargs: None)


def proposing(payload: dict[str, Any]) -> FunctionModel:
    def behaviour(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        del messages
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=payload)])

    return FunctionModel(behaviour)


def test_declaration_is_native_available_and_side_effect_free(with_credentials: None) -> None:
    provider = PdtbProvider(model=MODEL)
    declaration = provider.declaration
    assert declaration.technique is Technique.PDTB
    assert declaration.technique_curie == technique_curie(Technique.PDTB)
    assert isinstance(declaration.capability, AvailableCapability)
    assert declaration.requires_structured_input is False
    assert provider.provider_id == f"{PROVIDER_ID_PREFIX}/{MODEL}"
    assert provider._analyst is None


def test_declaration_reports_model_unavailable_without_credentials(no_credentials: None) -> None:
    assert PdtbProvider(model=MODEL).declaration.capability == UnavailableCapability(
        reason=UnavailableReason.MODEL_UNAVAILABLE
    )


def test_provenance_names_model_source_and_licence(with_credentials: None) -> None:
    provenance = PdtbProvider(model=MODEL).declaration.provenance
    assert provenance.package == "rdam.pdtb"
    assert provenance.model_identity == MODEL
    assert provenance.source_revision == source_identity().hex_digest
    assert "MIT" in provenance.licence


def test_text_and_formalism_guards_precede_model_construction(with_credentials: None) -> None:
    provider = PdtbProvider(model=MODEL)
    with pytest.raises(ProviderError, match="text_required"):
        provider.analyse(ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None))
    with pytest.raises(ProviderError, match="formalism_not_declared"):
        provider.analyse(
            ProviderRequest(
                source=SourceIdentity.from_text("x"),
                text="x",
                structured_input=None,
                formalism_id="pdtb2",
            )
        )
    assert provider._analyst is None


def test_valid_proposal_becomes_native_result_with_attempt_evidence(with_credentials: None) -> None:
    provider = PdtbProvider(model=MODEL)
    with provider._built().agent.override(model=proposing(VALID_ANALYSIS)):
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text(TEXT, (Technique.PDTB,))
        ).outcome_for(Technique.PDTB)
    assert isinstance(outcome, ResultOutcome)
    relations = outcome.result.payload["relations"]
    extraction = outcome.result.payload["extraction"]
    assert isinstance(relations, list) and isinstance(relations[0], dict)
    assert isinstance(extraction, dict)
    assert relations[0]["relation_type"] == "Explicit"
    assert extraction["output_attempts"] == 1
    assert extraction["transport_attempts"] == 1


def test_malformed_proposal_is_one_failure_and_no_partial_result(with_credentials: None) -> None:
    provider = PdtbProvider(model=MODEL)
    malformed = {
        "relations": [{**VALID_ANALYSIS["relations"][0], "senses": ["Expansion.List"]}]
    }
    with provider._built().agent.override(model=proposing(malformed)):
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text(TEXT, (Technique.PDTB,))
        ).outcome_for(Technique.PDTB)
    assert isinstance(outcome, FailedOutcome)
    assert outcome.failure.code == "llm_output_failed_validation"
    assert ("output_attempts", "3") in outcome.failure.message_parameters


def test_source_mismatch_is_a_native_typed_failure(with_credentials: None) -> None:
    provider = PdtbProvider(model=MODEL)
    mismatch = {
        "relations": [
            {
                **VALID_ANALYSIS["relations"][0],
                "arg1": {"spans": [{"start": 0, "end": 4, "text": "Hail"}]},
            }
        ]
    }
    with provider._built().agent.override(model=proposing(mismatch)):
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text(TEXT, (Technique.PDTB,))
        ).outcome_for(Technique.PDTB)
    assert isinstance(outcome, FailedOutcome)
    assert outcome.failure.code == "invalid_pdtb_source"


def test_withholding_pdtb_does_not_change_toulmin_capability(with_credentials: None) -> None:
    toulmin = ToulminProvider(model=MODEL)
    with_pdtb = Machine([toulmin, PdtbProvider(model=MODEL)]).capabilities().capability_for(Technique.TOULMIN)
    without_pdtb = Machine([toulmin]).capabilities().capability_for(Technique.TOULMIN)
    assert with_pdtb.model_dump_json() == without_pdtb.model_dump_json()
