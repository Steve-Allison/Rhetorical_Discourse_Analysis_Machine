"""Classical Rhetoric provider tests: Aristotelian pisteis, kairos, stasis, and surface schemes."""

from pathlib import Path

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
from rdam.classical_rhetoric import FORMALISM_ID, ClassicalRhetoricProvider, source_identity
from rdam.classical_rhetoric.output import ClassicalRhetoricOutput
from rdam.classical_rhetoric.rhetoric import (
    AppealProposal,
    ClassicalRhetoricError,
    ClassicalRhetoricProposal,
    RhetoricalFigureProposal,
    StasisProposal,
)

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


class TestAristotelianAndSchemeInvariants:
    def test_ethos_and_logos_submodes_and_stasis_consistency_enforced(self) -> None:
        with pytest.raises(ValidationError, match="ethos sub_mode"):
            AppealProposal(
                appeal_id="ap_1",
                pistis="ethos",
                sub_mode="data_evidence",
                rationale="wrong submode",
                evidence=QuoteRef(quote="x", occurrence=1),
            )
        with pytest.raises(ValidationError, match="logos sub_mode"):
            AppealProposal(
                appeal_id="ap_2",
                pistis="logos",
                sub_mode="phronesis",
                rationale="wrong submode",
                evidence=QuoteRef(quote="x", occurrence=1),
            )
        with pytest.raises(ValidationError, match="dominant_stasis='none'"):
            StasisProposal(
                dominant_stasis="none",
                contested_question="Did it happen?",
                evidence=None,
            )
        with pytest.raises(ValidationError, match="requires both contested_question and evidence"):
            StasisProposal(
                dominant_stasis="qualitative",
                contested_question=None,
                evidence=None,
            )

    def test_rhetorical_question_and_lexical_repetition_schemes_verified_against_quote(self) -> None:
        text = "The delay cost three weeks. We must act now; we must act decisively. Who can ignore this risk?"
        bad_rq = ClassicalRhetoricProposal(
            figures=[
                RhetoricalFigureProposal(
                    figure_id="f_1",
                    scheme="rhetorical_question",
                    explanation="declarative misclassified as question",
                    evidence=QuoteRef(quote="The delay cost three weeks.", occurrence=1),
                ),
            ]
        )
        with pytest.raises(ClassicalRhetoricError, match="requires a question mark"):
            bad_rq.validate_source(text)

        bad_anaphora = ClassicalRhetoricProposal(
            figures=[
                RhetoricalFigureProposal(
                    figure_id="f_2",
                    scheme="anaphora",
                    explanation="no repeated word",
                    evidence=QuoteRef(quote="The delay cost three weeks.", occurrence=1),
                ),
            ]
        )
        with pytest.raises(ClassicalRhetoricError, match="requires lexical repetition"):
            bad_anaphora.validate_source(text)

        good = ClassicalRhetoricProposal(
            figures=[
                RhetoricalFigureProposal(
                    figure_id="f_3",
                    scheme="anaphora",
                    explanation="repeated clause opening 'we must act'",
                    evidence=QuoteRef(quote="We must act now; we must act decisively.", occurrence=1),
                ),
                RhetoricalFigureProposal(
                    figure_id="f_4",
                    scheme="rhetorical_question",
                    explanation="erotesis",
                    evidence=QuoteRef(quote="Who can ignore this risk?", occurrence=1),
                ),
            ]
        )
        _, _, _, fig_spans = good.validate_source(text)
        assert set(fig_spans) == {"f_3", "f_4"}


class TestThroughTheMachine:
    def test_unavailable_without_credentials(self, no_credentials: None) -> None:
        provider = ClassicalRhetoricProvider(model=MODEL)
        assert source_identity().hex_digest != "0" * 64
        outcome = Machine([provider]).analyse(
            AggregateRequest.for_text("Act before Friday.", (Technique.CLASSICAL_RHETORIC,))
        ).outcome_for(Technique.CLASSICAL_RHETORIC)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE

    def test_multimodal_doclang_extracts_ethos_logos_table_and_pathos_visual_description(
        self,
        tmp_path: Path,
        with_credentials: None,
    ) -> None:
        doc = tmp_path / "speech.dclg"
        doc.write_text(
            '<doclang version="0.9">'
            "<text>Our twenty years of audited safety engineering demand action before the winter freeze. "
            "Can we afford another outage?</text>"
            "<table><ched/>Option<ched/>Outage Rate<nl/><fcel/>Redundant Grid<fcel/>0.02% annual failure<nl/></table>"
            '<picture><label value="photograph"/><description>Emergency crews working in freezing floodwater '
            "beside a failed substation.</description></picture>"
            "</doclang>",
            encoding="utf-8",
        )
        proposal = {
            "appeals": [
                {
                    "appeal_id": "ap_1",
                    "pistis": "ethos",
                    "sub_mode": "phronesis",
                    "rationale": "Cites twenty years of audited safety engineering experience.",
                    "evidence": {"quote": "Our twenty years of audited safety engineering", "occurrence": 1},
                },
                {
                    "appeal_id": "ap_2",
                    "pistis": "logos",
                    "sub_mode": "data_evidence",
                    "rationale": "Quantitative failure rate from comparison table.",
                    "evidence": {"quote": "0.02% annual failure", "occurrence": 1},
                },
                {
                    "appeal_id": "ap_3",
                    "pistis": "pathos",
                    "sub_mode": "urgency_and_concern",
                    "rationale": "Visual depiction of crews in freezing floodwater.",
                    "evidence": {
                        "quote": "Emergency crews working in freezing floodwater beside a failed substation.",
                        "occurrence": 1,
                    },
                },
            ],
            "kairos_cues": [
                {
                    "cue_id": "k_1",
                    "urgency_or_timeliness": "Seasonal deadline before the winter freeze.",
                    "evidence": {"quote": "before the winter freeze.", "occurrence": 1},
                }
            ],
            "stasis": {
                "dominant_stasis": "qualitative",
                "contested_question": "Whether grid redundancy investment is warranted before winter.",
                "evidence": {"quote": "Can we afford another outage?", "occurrence": 1},
            },
            "figures": [
                {
                    "figure_id": "fig_1",
                    "scheme": "rhetorical_question",
                    "explanation": "Challenges complacency through erotesis.",
                    "evidence": {"quote": "Can we afford another outage?", "occurrence": 1},
                }
            ],
        }

        def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=proposal)])

        provider = ClassicalRhetoricProvider(model=MODEL)
        with provider.analyst.agent.override(model=FunctionModel(respond)):
            aggregate = Machine([provider]).analyse(
                AggregateRequest.for_source(doc, (Technique.CLASSICAL_RHETORIC,))
            )
        outcome = aggregate.outcome_for(Technique.CLASSICAL_RHETORIC)
        assert isinstance(outcome, ResultOutcome)
        assert outcome.result.formalism_id == FORMALISM_ID
        validated = ClassicalRhetoricOutput.model_validate_json(canonical_json_bytes(outcome.result.payload))
        assert validated.pistis_balance.model_dump() == {"ethos": 1, "pathos": 1, "logos": 1}
        xpaths = {entry.xpath for entry in aggregate.xpath_alignment}
        assert "/d:doclang/d:text[1]" in xpaths
        assert "/d:doclang/d:table[1]/d:fcel[2]" in xpaths
        assert "/d:doclang/d:picture[1]/d:description[1]" in xpaths
