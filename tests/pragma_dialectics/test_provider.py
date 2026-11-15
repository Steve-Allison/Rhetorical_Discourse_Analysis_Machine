"""Pragma-Dialectics provider tests: 10 Critical Discussion Rules, strategic manoeuvring, and derailments."""

from pydantic import ValidationError
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import (
    AggregateRequest,
    Machine,
    ResultOutcome,
    Technique,
    UnavailableOutcome,
    UnavailableReason,
    canonical_json_bytes,
)
from rdam._grounding import QuoteRef
from rdam.pragma_dialectics import FORMALISM_ID, PragmaDialecticsProvider, source_identity
from rdam.pragma_dialectics.dialectics import (
    CriticalDiscussionProposal,
    DerailmentProposal,
    PragmaDialecticsError,
    StandpointProposal,
)
from rdam.pragma_dialectics.output import PragmaDialecticsOutput
from rdam.pragma_dialectics.rules import CRITICAL_DISCUSSION_RULES

MODEL = "openai:gpt-5.6-sol"


@pytest.fixture(autouse=True)
def never_a_real_request():
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


def _noop_dotenv(*_args: object, **_kwargs: object) -> None:
    return None


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", _noop_dotenv)
    monkeypatch.setattr("rdam._llm._nearest_dotenv", _noop_dotenv)


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")


class TestTenRulesAndFallacyVerification:
    def test_catalogue_contains_all_ten_critical_discussion_rules(self) -> None:
        assert len(CRITICAL_DISCUSSION_RULES) == 10
        assert [rule.number for rule in CRITICAL_DISCUSSION_RULES.values()] == list(range(1, 11))
        for rule in CRITICAL_DISCUSSION_RULES.values():
            assert rule.recognized_fallacies
            assert rule.primary_stages

    def test_mismatched_rule_and_fallacy_pair_rejected(self) -> None:
        with pytest.raises(ValidationError, match="does not belong to 'rule_1_freedom'"):
            DerailmentProposal(
                id="dr_1",
                stage="confrontation",
                rule_id="rule_1_freedom",
                fallacy_type="straw_man",
                explanation="straw_man belongs to rule_3_standpoint",
                evidence=QuoteRef(quote="x", occurrence=1),
            )
        valid = DerailmentProposal(
            id="dr_2",
            stage="confrontation",
            rule_id="rule_1_freedom",
            fallacy_type="ad_hominem",
            explanation="personal attack blocking antagonist doubt",
            evidence=QuoteRef(quote="x", occurrence=1),
        )
        assert valid.rule_id == "rule_1_freedom"

    def test_ungrounded_standpoint_raises_pragma_dialectics_error(self) -> None:
        proposal = CriticalDiscussionProposal(
            standpoints=[
                StandpointProposal(
                    id="sp_1",
                    protagonist="author",
                    polarity="positive",
                    proposition="We should adopt zero-trust networking",
                    evidence=QuoteRef(quote="Zero-trust is mandatory.", occurrence=1),
                ),
            ]
        )
        with pytest.raises(PragmaDialecticsError, match="does not appear in source text"):
            proposal.validate_source("Perimeter firewalls suffice.")


class TestThroughTheMachine:
    def test_unavailable_without_credentials(self, no_credentials: None) -> None:
        provider = PragmaDialecticsProvider(model=MODEL)
        assert source_identity().hex_digest != "0" * 64
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text("We must adopt zero-trust.", (Technique.PRAGMA_DIALECTICS,))
        ).outcome_for(Technique.PRAGMA_DIALECTICS)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_extracts_standpoints_stages_strategic_manoeuvres_and_derailments(
        self,
        with_credentials: None,
    ) -> None:
        source_text = (
            "We must mandate hardware security keys for all production engineers. "
            "Critics who question this policy have never run a serious incident response. "
            "Hardware keys eliminate phishing-based credential theft across 100% of audited trials."
        )
        proposal = {
            "standpoints": [
                {
                    "id": "sp_1",
                    "protagonist": "author",
                    "polarity": "positive",
                    "proposition": "Hardware security keys must be mandated for all production engineers",
                    "evidence": {
                        "quote": "We must mandate hardware security keys for all production engineers.",
                        "occurrence": 1,
                    },
                }
            ],
            "stage_segments": [
                {
                    "id": "st_1",
                    "stage": "confrontation",
                    "summary": "Advances positive policy standpoint and dismisses critics.",
                    "evidence": {
                        "quote": "We must mandate hardware security keys for all production engineers.",
                        "occurrence": 1,
                    },
                },
                {
                    "id": "st_2",
                    "stage": "argumentation",
                    "summary": "Advances empirical trial evidence against phishing.",
                    "evidence": {
                        "quote": "Hardware keys eliminate phishing-based credential theft across 100% of audited trials.",
                        "occurrence": 1,
                    },
                },
            ],
            "strategic_manoeuvres": [
                {
                    "id": "sm_1",
                    "stage": "argumentation",
                    "topical_potential": "Selects empirical phishing elimination evidence",
                    "audience_demand": "Addresses security-conscious engineering leadership",
                    "presentational_device": "Categorical quantitative framing ('100% of audited trials')",
                    "evidence": {
                        "quote": "Hardware keys eliminate phishing-based credential theft across 100% of audited trials.",
                        "occurrence": 1,
                    },
                }
            ],
            "derailments": [
                {
                    "id": "dr_1",
                    "stage": "confrontation",
                    "rule_id": "rule_1_freedom",
                    "fallacy_type": "ad_hominem",
                    "explanation": "Discredits critics personally rather than addressing their doubt.",
                    "evidence": {
                        "quote": "Critics who question this policy have never run a serious incident response.",
                        "occurrence": 1,
                    },
                }
            ],
        }

        def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=proposal)])

        provider = PragmaDialecticsProvider(model=MODEL)
        with provider.analyst.agent.override(model=FunctionModel(respond)):
            aggregate = Machine([provider]).analyse(
                AggregateRequest.for_text(source_text, (Technique.PRAGMA_DIALECTICS,))
            )
        outcome = aggregate.outcome_for(Technique.PRAGMA_DIALECTICS)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.formalism_id == FORMALISM_ID
        validated = PragmaDialecticsOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.derailment_count == 1
        assert validated.violated_rules == ("rule_1_freedom",)
        assert validated.derailments[0].rule_title == "Freedom Rule"
        assert len(outcome.result.source_alignment) == 5
