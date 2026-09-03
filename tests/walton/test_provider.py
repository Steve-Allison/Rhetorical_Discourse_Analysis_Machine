"""The Walton provider through the machine: capability is whether the model can be reached."""

from collections.abc import Mapping, Sequence
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
    SourceIdentity,
    Technique,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    technique_curie,
)
from rdam.toulmin import ToulminProvider
from rdam.walton import SCHEMES, SCHEME_SET_ID, PROVIDER_ID_PREFIX, SchemeId, WaltonProvider, source_identity

MODEL = "openai:gpt-5.6-sol"

VALID_INSTANCE = {
    "scheme_id": "expert_opinion",
    "conclusion": "The bridge is unsafe.",
    "premises": {"source": "Dr Okonkwo", "domain": "structural engineering", "assertion": "it cannot carry its load"},
    "critical_questions": [{"index": 0, "status": "addressed", "note": "the passage names her chair"}],
}


@pytest.fixture(autouse=True)
def never_a_real_request(monkeypatch: pytest.MonkeyPatch):
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setattr("rdam._llm._nearest_dotenv", lambda *_a, **_k: None)


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used-for-any-request")


def _proposing(payload: object) -> FunctionModel:
    def behaviour(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args={"instances": payload})])

    return FunctionModel(behaviour)


class TestDeclaration:
    def test_available_when_the_model_can_be_reached(self, with_credentials: None) -> None:
        declaration = WaltonProvider(model=MODEL).declaration
        assert declaration.technique is Technique.WALTON
        assert declaration.technique_curie == technique_curie(Technique.WALTON)
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.requires_structured_input is False

    def test_unavailable_with_a_stable_reason_when_no_key_resolves(self, no_credentials: None) -> None:
        assert WaltonProvider(model=MODEL).declaration.capability == UnavailableCapability(
            reason=UnavailableReason.MODEL_UNAVAILABLE
        )

    def test_the_model_is_part_of_the_provider_identity(self, with_credentials: None) -> None:
        assert WaltonProvider(model=MODEL).provider_id == f"{PROVIDER_ID_PREFIX}/{MODEL}"

    def test_provenance_names_the_model_the_source_and_the_licence(self, with_credentials: None) -> None:
        provenance = WaltonProvider(model=MODEL).declaration.provenance
        assert provenance.package == "rdam.walton"
        assert provenance.model_identity == MODEL
        assert provenance.source_revision
        first_identity = source_identity()
        assert source_identity() is first_identity
        assert first_identity.hex_digest != "0" * 64
        assert "MIT" in provenance.licence

    def test_declaring_capability_never_builds_an_agent(self, with_credentials: None) -> None:
        provider = WaltonProvider(model=MODEL)
        assert provider.declaration is not None
        assert provider._analyst is None


class TestInstructions:
    """The prompt is generated from the table, so the two can never drift apart."""

    def test_every_scheme_and_every_critical_question_reaches_the_model(self) -> None:
        from rdam.walton import INSTRUCTIONS

        for scheme in SCHEMES.values():
            assert scheme.scheme_id.value in INSTRUCTIONS
            for role in scheme.premise_roles:
                assert role in INSTRUCTIONS
            for question in scheme.critical_questions:
                assert question in INSTRUCTIONS

    def test_the_model_is_told_not_to_answer_the_open_questions(self) -> None:
        from rdam.walton import INSTRUCTIONS

        assert "Do NOT answer the open questions" in INSTRUCTIONS


class TestAnalyseGuards:
    def test_an_unreachable_model_refuses_to_analyse(self, no_credentials: None) -> None:
        with pytest.raises(ProviderError) as caught:
            WaltonProvider(model=MODEL).analyse(
                ProviderRequest(source=SourceIdentity.from_text("t"), text="t", structured_input=None)
            )
        assert caught.value.failure.code == "provider_not_available"

    def test_text_is_required(self, with_credentials: None) -> None:
        with pytest.raises(ProviderError) as caught:
            WaltonProvider(model=MODEL).analyse(
                ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None)
            )
        assert caught.value.failure.code == "text_required"

    def test_an_undeclared_formalism_is_refused(self, with_credentials: None) -> None:
        with pytest.raises(ProviderError) as caught:
            WaltonProvider(model=MODEL).analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("t"), text="t", structured_input=None, formalism_id="nope"
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"


class TestThroughTheMachine:
    def test_a_valid_proposal_becomes_a_native_result(self, with_credentials: None) -> None:
        provider = WaltonProvider(model=MODEL)
        with provider._built().agent.override(model=_proposing([VALID_INSTANCE])):
            outcome = (
                Machine([provider])
                .analyse(
                    AggregateRequest.for_text("Dr Okonkwo says the bridge cannot carry its load.", (Technique.WALTON,))
                )
                .outcome_for(Technique.WALTON)
            )
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        assert payload["instance_count"] == 1
        instances = payload["instances"]
        assert isinstance(instances, Sequence)
        first = instances[0]
        assert isinstance(first, Mapping)
        assert first["scheme_id"] == SchemeId.EXPERT_OPINION.value
        assert payload["scheme_set"] == SCHEME_SET_ID
        extraction = payload["extraction"]
        assert isinstance(extraction, Mapping)
        assert extraction["output_attempts"] == 1
        assert extraction["transport_attempts"] == 1
        expected_open = len(SCHEMES[SchemeId.EXPERT_OPINION].critical_questions) - 1
        assert first["open_question_count"] == expected_open

    def test_a_passage_that_argues_nothing_yields_an_empty_analysis(self, with_credentials: None) -> None:
        provider = WaltonProvider(model=MODEL)
        with provider._built().agent.override(model=_proposing([])):
            outcome = (
                Machine([provider])
                .analyse(AggregateRequest.for_text("The meeting is at four.", (Technique.WALTON,)))
                .outcome_for(Technique.WALTON)
            )
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.payload["instance_count"] == 0

    def test_a_proposal_that_breaks_the_scheme_table_is_a_typed_failure(self, with_credentials: None) -> None:
        """The model proposes; the table disposes. A wrong-role instance is refused, not repaired."""

        broken = {**VALID_INSTANCE, "premises": {"source": "Dr Okonkwo"}}
        provider = WaltonProvider(model=MODEL)
        with provider._built().agent.override(model=_proposing([broken])):
            outcome = (
                Machine([provider])
                .analyse(AggregateRequest.for_text("some passage", (Technique.WALTON,)))
                .outcome_for(Technique.WALTON)
            )
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "llm_output_failed_validation"
        assert outcome.failure.retryability.value == "not_retryable"
        assert ("output_attempts", "3") in outcome.failure.message_parameters
        assert ("transport_attempts", "3") in outcome.failure.message_parameters

    def test_an_unreachable_model_is_unavailable_not_failed(self, no_credentials: None) -> None:
        outcome = (
            Machine([WaltonProvider(model=MODEL)])
            .analyse(AggregateRequest.for_text("Some text.", (Technique.WALTON,)))
            .outcome_for(Technique.WALTON)
        )
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_withholding_walton_does_not_change_toulmin_capability(self, with_credentials: None) -> None:
        toulmin = ToulminProvider(model=MODEL)
        with_walton = Machine([toulmin, WaltonProvider(model=MODEL)]).capabilities().capability_for(Technique.TOULMIN)
        without_walton = Machine([toulmin]).capabilities().capability_for(Technique.TOULMIN)
        assert with_walton.model_dump_json() == without_walton.model_dump_json()


@pytest.mark.live
@pytest.mark.slow
class TestAgainstTheRealModel:
    def test_the_machine_returns_validated_scheme_instances(self, live_model_requests: None) -> None:
        models.ALLOW_MODEL_REQUESTS = True
        text = (
            "We should not widen the road. Professor Lindqvist, who studies urban traffic, says that widening "
            "roads increases congestion within five years."
        )
        outcome = (
            Machine([WaltonProvider()])
            .analyse(AggregateRequest.for_text(text, (Technique.WALTON,)))
            .outcome_for(Technique.WALTON)
        )
        assert isinstance(outcome, ResultOutcome)
        instances = outcome.result.payload["instances"]
        assert isinstance(instances, Sequence) and instances, "the passage argues from expertise; a scheme is expected"
        first = instances[0]
        assert isinstance(first, Mapping)
        assert first["scheme_id"] in {scheme.value for scheme in SchemeId}
        assert isinstance(first["open_questions"], Sequence)
