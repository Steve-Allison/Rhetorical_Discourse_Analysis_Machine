"""The Toulmin provider through the machine: native validity plus evidenced attempts."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from rdam.ingest.contracts.source import TableCoordinateAnchor

from pydantic_ai import models
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIResponsesModel
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
from rdam.toulmin import PROVIDER_ID_PREFIX, ToulminProvider, source_identity
from rdam.toulmin.argument import ToulminAnalysis
from rdam._llm import LlmError, StructuredAnalyst
from rdam.walton import WaltonProvider

MODEL = "openai:gpt-5.6-sol"

VALID_LAYOUT = {
    "claim": "The council should reject the proposal.",
    "grounds": ["The site is unstable."],
    "warrant": "A council should reject construction proposals for unstable sites.",
}


@pytest.fixture(autouse=True)
def never_a_real_request():
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """A machine with no key for the configured model, and no ``.env`` to fall back on."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("rdam._llm._nearest_dotenv", lambda *_args, **_kwargs: None)


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used-for-any-request")


def _proposing(layouts: object) -> FunctionModel:
    def behaviour(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        del messages
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args={"layouts": layouts})])

    return FunctionModel(behaviour)


@dataclass
class _Usage:
    requests: int


@dataclass
class _Result:
    output: ToulminAnalysis
    request_count: int = 1

    def usage(self) -> _Usage:
        return _Usage(requests=self.request_count)


class TestAttemptContract:
    def test_provider_sdk_retries_are_disabled_at_the_owned_boundary(self, with_credentials: None) -> None:
        model = ToulminProvider(model=MODEL)._built().agent.model
        assert isinstance(model, OpenAIResponsesModel)
        assert model.client.max_retries == 0

    def test_transient_failures_are_bounded_and_counted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        analyst = StructuredAnalyst(output_type=ToulminAnalysis, instructions="test", model=MODEL, transport_retries=2)
        outcomes: list[object] = [
            ModelHTTPError(503, MODEL, headers={"retry-after": "0"}),
            ModelHTTPError(503, MODEL),
            _Result(ToulminAnalysis()),
        ]
        delays: list[float] = []

        async def run(_text: str):
            item = outcomes.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        async def sleep(delay: float) -> None:
            delays.append(delay)

        monkeypatch.setattr(analyst, "_run", run)
        monkeypatch.setattr("rdam._llm.asyncio.sleep", sleep)
        monkeypatch.setattr("rdam._llm.random.uniform", lambda _low, high: high)
        extraction = analyst.extract("text")
        assert extraction.output_attempts == 1
        assert extraction.transport_attempts == 3
        assert len(delays) == 2 and delays[0] == 0.0

    def test_retry_after_is_honoured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        analyst = StructuredAnalyst(output_type=ToulminAnalysis, instructions="test", model=MODEL, transport_retries=1)
        outcomes: list[object] = [ModelHTTPError(429, MODEL, headers={"retry-after": "2"}), _Result(ToulminAnalysis())]
        delays: list[float] = []

        async def run(_text: str):
            item = outcomes.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        async def sleep(delay: float) -> None:
            delays.append(delay)

        monkeypatch.setattr(analyst, "_run", run)
        monkeypatch.setattr("rdam._llm.asyncio.sleep", sleep)
        extraction = analyst.extract("text")
        assert extraction.transport_attempts == 2
        assert delays == [2.0]

    def test_exhaustion_reports_the_exact_transport_attempts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        analyst = StructuredAnalyst(output_type=ToulminAnalysis, instructions="test", model=MODEL, transport_retries=1)

        async def fail(_text: str):
            raise ModelHTTPError(503, MODEL)

        async def no_wait(_delay: float) -> None:
            return None

        monkeypatch.setattr(analyst, "_run", fail)
        monkeypatch.setattr("rdam._llm.asyncio.sleep", no_wait)
        with pytest.raises(LlmError) as caught:
            analyst.extract("text")
        assert caught.value.code == "llm_request_rejected"
        assert caught.value.transport_attempts == 2
        assert caught.value.output_attempts == 0

    def test_output_exhaustion_is_not_mislabeled_as_transport_retry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        analyst = StructuredAnalyst(output_type=ToulminAnalysis, instructions="test", model=MODEL, output_retries=2)
        async def invalid(_text: str):
            raise UnexpectedModelBehavior("invalid output")

        monkeypatch.setattr(analyst, "_run", invalid)
        with pytest.raises(LlmError) as caught:
            analyst.extract("text")
        assert caught.value.code == "llm_output_failed_validation"
        assert caught.value.output_attempts == 3
        assert caught.value.transport_attempts == 3

    def test_transport_deadline_stops_before_an_over_budget_wait(self, monkeypatch: pytest.MonkeyPatch) -> None:
        analyst = StructuredAnalyst(
            output_type=ToulminAnalysis,
            instructions="test",
            model=MODEL,
            transport_retries=2,
            transport_deadline_seconds=0.01,
        )

        async def rejected(_text: str):
            raise ModelHTTPError(429, MODEL, headers={"retry-after": "2"})

        monkeypatch.setattr(analyst, "_run", rejected)
        with pytest.raises(LlmError) as caught:
            analyst.extract("text")
        assert caught.value.code == "llm_transport_deadline_exceeded"
        assert caught.value.transport_attempts == 1


class TestDeclaration:
    def test_the_model_is_part_of_the_provider_identity(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        assert provider.provider_id == f"{PROVIDER_ID_PREFIX}/{MODEL}"

    def test_available_when_the_model_can_be_reached(self, with_credentials: None) -> None:
        declaration = ToulminProvider(model=MODEL).declaration
        assert declaration.technique is Technique.TOULMIN
        assert declaration.technique_curie == technique_curie(Technique.TOULMIN)
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.requires_structured_input is False

    def test_unavailable_with_a_stable_reason_when_no_key_resolves(self, no_credentials: None) -> None:
        declaration = ToulminProvider(model=MODEL).declaration
        assert declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)

    def test_declaring_capability_never_builds_an_agent(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        assert provider.declaration is not None
        assert provider._analyst is None, "declaring capability must not construct the model client"

    def test_provenance_names_the_model_the_source_and_the_licence(self, with_credentials: None) -> None:
        provenance = ToulminProvider(model=MODEL).declaration.provenance
        assert provenance.package == "rdam.toulmin"
        assert provenance.model_identity == MODEL
        assert provenance.source_revision
        first_identity = source_identity()
        assert source_identity() is first_identity, "the compatibility source wrapper is stable and cached"
        assert first_identity.hex_digest != "0" * 64
        assert "MIT" in provenance.licence


class TestAnalyseGuards:
    def test_an_unreachable_model_refuses_to_analyse_with_a_typed_failure(self, no_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_text("t"), text="t", structured_input=None))
        assert caught.value.failure.code == "provider_not_available"
        assert caught.value.failure.message_parameters == (("detail", "model_unavailable"),)

    def test_text_is_required_before_any_model_call(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None))
        assert caught.value.failure.code == "text_required"
        assert provider._analyst is None

    def test_an_undeclared_formalism_is_refused(self, with_credentials: None) -> None:
        with pytest.raises(ProviderError) as caught:
            ToulminProvider(model=MODEL).analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("t"),
                    text="t",
                    structured_input=None,
                    formalism_id="not_a_formalism",
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"


class TestThroughTheMachine:
    def test_tabular_grounds_anchor_to_the_source_cell(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        proposal = {"claim": "Approve the replacement.", "grounds": ["80"],
                    "warrant": "Prefer the lower operating cost when service is equal."}
        with provider._built().agent.override(model=_proposing([proposal])):
            result = Machine([provider]).analyse(AggregateRequest.for_source(
                Path("tests/fixtures/pipeline/tabular-evidence.md"), (Technique.TOULMIN,),
            ))
        outcome = result.outcome_for(Technique.TOULMIN)
        assert isinstance(outcome, ResultOutcome)
        grounds = [alignment for alignment in outcome.result.source_alignment if alignment.payload_path == "/layouts/0/grounds/0"]
        assert grounds
        assert any(isinstance(anchor, TableCoordinateAnchor) and (anchor.row, anchor.column) == (2, 1)
                   for alignment in grounds for anchor in alignment.source_anchors)

    def test_a_valid_proposal_becomes_a_native_result_with_attempt_evidence(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        with provider._built().agent.override(model=_proposing([VALID_LAYOUT])):
            outcome = (
                Machine([provider])
                .analyse(
                    AggregateRequest.for_text("The site is unstable, so reject the proposal.", (Technique.TOULMIN,))
                )
                .outcome_for(Technique.TOULMIN)
            )
        assert isinstance(outcome, ResultOutcome)
        extraction = outcome.result.payload["extraction"]
        assert isinstance(extraction, Mapping)
        assert extraction["output_attempts"] == 1
        assert extraction["transport_attempts"] == 1

    def test_a_malformed_proposal_is_one_typed_failure_with_no_partial_result(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        broken = {**VALID_LAYOUT, "warrant": VALID_LAYOUT["claim"]}
        with provider._built().agent.override(model=_proposing([broken])):
            outcome = (
                Machine([provider])
                .analyse(AggregateRequest.for_text("Some argument.", (Technique.TOULMIN,)))
                .outcome_for(Technique.TOULMIN)
            )
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == "llm_output_failed_validation"
        assert ("output_attempts", "3") in outcome.failure.message_parameters
        assert ("transport_attempts", "3") in outcome.failure.message_parameters

    def test_an_unreachable_model_is_unavailable_not_failed(self, no_credentials: None) -> None:
        machine = Machine([ToulminProvider(model=MODEL)])
        outcome = machine.analyse(AggregateRequest.for_text("Some text.", (Technique.TOULMIN,))).outcome_for(
            Technique.TOULMIN
        )
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_withholding_toulmin_does_not_change_walton_capability(self, with_credentials: None) -> None:
        walton = WaltonProvider(model=MODEL)
        with_toulmin = Machine([walton, ToulminProvider(model=MODEL)]).capabilities().capability_for(Technique.WALTON)
        without_toulmin = Machine([walton]).capabilities().capability_for(Technique.WALTON)
        assert with_toulmin.model_dump_json() == without_toulmin.model_dump_json()


@pytest.mark.live
@pytest.mark.slow
class TestAgainstTheRealModel:
    """One real call: the layout the machine returns is the model's proposal, validated."""

    def test_the_machine_returns_a_validated_toulmin_layout(self, live_model_requests: None) -> None:
        models.ALLOW_MODEL_REQUESTS = True
        machine = Machine([ToulminProvider()])
        text = (
            "The council should reject the proposal. It would cost £4m that is not in the budget, "
            "and two independent surveys both found the site is unstable."
        )
        outcome = machine.analyse(AggregateRequest.for_text(text, (Technique.TOULMIN,))).outcome_for(Technique.TOULMIN)
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        layouts = payload["layouts"]
        assert isinstance(layouts, Sequence) and layouts, "the passage argues; a layout is expected"
        first = layouts[0]
        assert isinstance(first, Mapping)
        assert first["claim"], "a layout always carries a claim"
        assert first["grounds"], "a layout always carries grounds"
        assert first["warrant"], "FR-019: a layout always carries a recovered warrant"
        extraction = payload["extraction"]
        assert isinstance(extraction, Mapping)
        assert extraction["model"] == outcome.result.provenance.model_identity
