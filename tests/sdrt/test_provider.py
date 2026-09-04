"""The SDRT provider through its independent and aggregate contracts."""

from collections.abc import Mapping
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest
from typing import Any
from pathlib import Path
from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.projection import project

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
from rdam.sdrt import PROVIDER_ID_PREFIX, SdrtProvider, source_identity
from rdam.toulmin import ToulminProvider

MODEL = "openai:gpt-5.6-sol"
TEXT = "One. Two."
VALID_GRAPH: dict[str, Any] = {
    "edus": [
        {"unit_id": "e1", "text": "One.", "start": 0, "end": 4},
        {"unit_id": "e2", "text": "Two.", "start": 5, "end": 9},
    ],
    "relations": [
        {
            "relation_id": "r1",
            "source_id": "e1",
            "target_id": "e2",
            "label": "Narration",
            "structural_type": "coordinating",
        }
    ],
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
    monkeypatch.setattr("rdam._llm._nearest_dotenv", lambda *_args, **_kwargs: None)


def proposing(payload: dict[str, Any]) -> FunctionModel:
    def behaviour(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        del messages
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=payload)])

    return FunctionModel(behaviour)


def test_declaration_is_native_available_and_side_effect_free(with_credentials: None) -> None:
    provider = SdrtProvider(model=MODEL)
    declaration = provider.declaration
    assert declaration.technique is Technique.SDRT
    assert declaration.technique_curie == technique_curie(Technique.SDRT)
    assert isinstance(declaration.capability, AvailableCapability)
    assert declaration.requires_structured_input is False
    assert provider.provider_id == f"{PROVIDER_ID_PREFIX}/{MODEL}"
    assert provider._analyst is None


def test_declaration_reports_model_unavailable_without_credentials(no_credentials: None) -> None:
    assert SdrtProvider(model=MODEL).declaration.capability == UnavailableCapability(
        reason=UnavailableReason.MODEL_UNAVAILABLE
    )


def test_provenance_names_model_source_and_licence(with_credentials: None) -> None:
    provenance = SdrtProvider(model=MODEL).declaration.provenance
    assert provenance.package == "rdam.sdrt"
    assert provenance.model_identity == MODEL
    assert provenance.source_revision
    first_identity = source_identity()
    assert source_identity() is first_identity
    assert first_identity.hex_digest != "0" * 64
    assert "MIT" in provenance.licence


def test_text_and_formalism_guards_precede_model_construction(with_credentials: None) -> None:
    provider = SdrtProvider(model=MODEL)
    with pytest.raises(ProviderError, match="text_required"):
        provider.analyse(ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None))
    with pytest.raises(ProviderError, match="formalism_not_declared"):
        provider.analyse(
            ProviderRequest(
                source=SourceIdentity.from_text("x"),
                text="x",
                structured_input=None,
                formalism_id="rst_tree",
            )
        )
    assert provider._analyst is None


def test_valid_proposal_becomes_native_result_with_attempt_evidence(with_credentials: None) -> None:
    provider = SdrtProvider(model=MODEL)
    with provider._built().agent.override(model=proposing(VALID_GRAPH)):
        outcome = (
            Machine([provider]).analyse(AggregateRequest.for_text(TEXT, (Technique.SDRT,))).outcome_for(Technique.SDRT)
        )
    assert isinstance(outcome, ResultOutcome)
    assert outcome.result.payload["right_frontier_validated"] is True
    extraction = outcome.result.payload["extraction"]
    assert isinstance(extraction, Mapping)
    assert extraction["output_attempts"] == 1
    assert extraction["transport_attempts"] == 1


def test_malformed_proposal_is_one_failure_and_no_partial_result(with_credentials: None) -> None:
    provider = SdrtProvider(model=MODEL)
    malformed = {**VALID_GRAPH, "relations": []}
    with provider._built().agent.override(model=proposing(malformed)):
        outcome = (
            Machine([provider]).analyse(AggregateRequest.for_text(TEXT, (Technique.SDRT,))).outcome_for(Technique.SDRT)
        )
    assert isinstance(outcome, FailedOutcome)
    assert outcome.failure.code == "llm_output_failed_validation"
    assert ("output_attempts", "3") in outcome.failure.message_parameters


def test_source_mismatch_is_a_native_typed_failure(with_credentials: None) -> None:
    provider = SdrtProvider(model=MODEL)
    mismatch = {
        **VALID_GRAPH,
        "edus": [{**VALID_GRAPH["edus"][0], "text": "Ones"}, VALID_GRAPH["edus"][1]],
    }
    with provider._built().agent.override(model=proposing(mismatch)):
        outcome = (
            Machine([provider]).analyse(AggregateRequest.for_text(TEXT, (Technique.SDRT,))).outcome_for(Technique.SDRT)
        )
    assert isinstance(outcome, FailedOutcome)
    assert outcome.failure.code == "invalid_sdrs_source"


def test_withholding_sdrt_does_not_change_toulmin_capability(with_credentials: None) -> None:
    toulmin = ToulminProvider(model=MODEL)
    with_sdrt = Machine([toulmin, SdrtProvider(model=MODEL)]).capabilities().capability_for(Technique.TOULMIN)
    without_sdrt = Machine([toulmin]).capabilities().capability_for(Technique.TOULMIN)
    assert with_sdrt.model_dump_json() == without_sdrt.model_dump_json()


def test_speaker_requirement_reports_unattributed_source_turns() -> None:
    provider = SdrtProvider(model=MODEL)
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(
        SourceArtifact.from_path(Path("tests/fixtures/pipeline/transcript.md")),
    ))
    projection = project(inventory, provider.content_requirement)
    assert provider.content_requirement.requires_speaker_identity
    assert len(projection.unmet_requirements) == 1
    assert projection.unmet_requirements[0].aspect == "speaker_identity"
    assert len(projection.unmet_requirements[0].affected_item_ids) == 2
