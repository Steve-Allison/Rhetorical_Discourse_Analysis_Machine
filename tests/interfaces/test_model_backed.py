"""Focused live semantic checks; never a substitute for native validators.

Run explicitly with RDAM_RUN_LIVE_MODEL_TESTS=1 and pytest -m 'live and slow'.
Sources and expectations are fixed before execution. Every result or typed failure
is printed for cold critique; no evaluator retries or model substitutions occur.
"""

from collections.abc import Iterator, Mapping, Sequence
import json
from pathlib import Path
from typing import cast

from pydantic_ai import models
import pytest

from rdam._llm import configured_model, load_dotenv, unavailable_reason
from rdam._strict import JsonValue, canonical_json_bytes
from rdam.contracts import NativeTechniqueResult, ProviderError, ProviderRequest, SourceIdentity
from rdam.pdtb import PdtbProvider
from rdam.sdrt import SdrtProvider
from rdam.toulmin import ToulminProvider
from rdam.walton import SCHEMES, SchemeId, WaltonProvider

EXPLICIT_RULE = "Anyone who has completed the safety briefing may use the laser cutter."
EXPLICIT = (
    f"Workshop rule: {EXPLICIT_RULE} "
    "Éva has completed the safety briefing. Therefore Éva may use the laser cutter."
)
EPISTEMIC = (
    "Dark clouds are gathering and the barometer is falling, "
    "so it may rain this afternoon."
)
RECONSTRUCTED = (
    "A faded poster from an unrelated theatre play reads, 'Everyone wearing a silver badge may enter.' "
    "That fictional rule does not govern the workshop. "
    "Éva points to Malik's silver badge and concludes that he may enter the workshop. "
    "She gives no rule for workshop admission."
)
UNDETERMINED = (
    "The sensor flashed red, so Leena concluded, 'The container must be sealed.' "
    "The next line is damaged: 'A red flash [unreadable] sealed container.' "
    "Editors cannot determine whether that line states Leena's inference rule "
    "or quotes an unrelated warning."
)
EXPERT = (
    "Dr Éva Chen is a qualified bridge engineer. She says, 'Bridge K is unsafe.' "
    "Therefore Bridge K is unsafe. Asked whether Chen is personally reliable, "
    "the speaker replies, 'She must be honest because I like her hat.'"
)
AMBIGUOUS_EXPERT = (
    "Dr Éva Chen is a bridge engineer. She says, 'Bridge K is unsafe.' "
    "Therefore Bridge K is unsafe. The only further recovered sentence is 'It is reliable.' "
    "The recording lost its referent: editors cannot determine whether 'it' refers "
    "to Chen's testimony or to an unrelated rain gauge."
)
EMPTY = "Inventory: one blue folder, two empty mugs, and a calendar dated Tuesday."
SUBORDINATE_REASON = "Because Léa had not received the key, she could not open the cabinet."
EXPLANATION = "Léa did not attend the meeting. She was ill."


@pytest.fixture
def authorized_model(live_model_requests: None) -> Iterator[None]:
    load_dotenv(Path(__file__).resolve().parents[2])
    model = configured_model()
    if unavailable_reason(model) is not None:
        pytest.skip(f"configured model unavailable: {model}; live semantics remain unverified")
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = True
    try:
        yield
    finally:
        models.ALLOW_MODEL_REQUESTS = previous


def _analyse(provider: ToulminProvider | WaltonProvider | PdtbProvider | SdrtProvider, text: str) -> NativeTechniqueResult:
    print(json.dumps({
        "source": text,
        "provider": provider.declaration.model_dump(mode="json"),
        "evaluation_retries": 0,
    }, ensure_ascii=False))
    try:
        result = provider.analyse(ProviderRequest(
            source=SourceIdentity.from_text(text, source_name="feature019-focused-live"),
            text=text, structured_input=None,
        ))
    except ProviderError as failure:
        print(failure.failure.model_dump_json())
        pytest.fail(f"Actual provider failure: {failure.failure.model_dump_json()}", pytrace=False)
    print(canonical_json_bytes(result).decode("utf-8"))
    assert result.contract_version == "2.0.0"
    assert str(result.provider_contract_version) == "2.0.0"
    assert result.provenance.model_identity == provider.model
    assert result.source_alignment == (), "direct text without a projection cannot claim original-file anchors"
    return result


def _objects(value: JsonValue) -> tuple[Mapping[str, JsonValue], ...]:
    assert isinstance(value, Sequence) and not isinstance(value, str)
    result: list[Mapping[str, JsonValue]] = []
    for item in value:
        assert isinstance(item, Mapping)
        result.append(cast(Mapping[str, JsonValue], item))
    return tuple(result)


def _spans(value: JsonValue, source: str) -> tuple[Mapping[str, JsonValue], ...]:
    spans = _objects(value)
    for span in spans:
        start, end, quote = span["start"], span["end"], span["text"]
        assert type(start) is int and type(end) is int and isinstance(quote, str)
        assert 0 <= start < end <= len(source)
        assert source[start:end] == quote
    return spans


def _assert_explicit_licence(value: JsonValue, source: str) -> None:
    spans = _spans(value, source)
    lexical_licence = EXPLICIT_RULE.removesuffix(".")
    assert any(lexical_licence in str(span["text"]) for span in spans), (
        "explicit support must contain the complete lexical inference licence"
    )


@pytest.mark.parametrize("quote", (EXPLICIT_RULE, EXPLICIT_RULE.removesuffix(".")))
def test_explicit_licence_assertion_accepts_optional_terminal_period(quote: str) -> None:
    start = EXPLICIT.index(quote)
    _assert_explicit_licence([{"start": start, "end": start + len(quote), "text": quote}], EXPLICIT)


@pytest.mark.parametrize("quote", (
    "Anyone who has completed the safety briefing",
    "may use the laser cutter",
    EXPLICIT_RULE.removesuffix(" cutter."),
))
def test_explicit_licence_assertion_rejects_lexical_truncation(quote: str) -> None:
    start = EXPLICIT.index(quote)
    with pytest.raises(AssertionError, match="complete lexical inference licence"):
        _assert_explicit_licence([{"start": start, "end": start + len(quote), "text": quote}], EXPLICIT)


def test_explicit_licence_assertion_still_rejects_inexact_source_span() -> None:
    quote = EXPLICIT_RULE.removesuffix(".")
    start = EXPLICIT.index(quote)
    with pytest.raises(AssertionError):
        _assert_explicit_licence([{"start": start, "end": start + len(quote) + 1, "text": quote}], EXPLICIT)


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_toulmin_explicit_warrant_quotes_the_actual_licence() -> None:
    result = _analyse(ToulminProvider(), EXPLICIT)
    layouts = _objects(result.payload["layouts"])
    assert len(layouts) == 1, "the source makes one explicit rule-based inference"
    layout = layouts[0]
    assert layout["warrant_origin"] == "explicit"
    assert layout["warrant_origin_reason"] is None
    _assert_explicit_licence(layout["warrant_evidence"], EXPLICIT)
    assert "Éva" in str(layout["claim"]) and "laser cutter" in str(layout["claim"])
    assert layout["qualifier"] is None, "permission to use equipment is the claim, not uncertainty about it"
    assert layout["is_qualified"] is False
    assert result.payload["qualified_layout_count"] == 0
    assert "fully_qualified_count" not in result.payload
    assert result.payload["qualified_layout_count"] == sum(bool(item["qualifier"] or item["rebuttals"]) for item in layouts)


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_toulmin_epistemic_may_retains_the_claims_uncertain_force() -> None:
    result = _analyse(ToulminProvider(), EPISTEMIC)
    layouts = _objects(result.payload["layouts"])
    assert len(layouts) == 1, "the weather observations support one tentative conclusion"
    layout = layouts[0]
    assert "rain" in str(layout["claim"]) and "afternoon" in str(layout["claim"])
    assert layout["qualifier"] is not None
    assert "may" in str(layout["qualifier"]).casefold(), "epistemic may must not be removed with deontic may"
    assert layout["is_qualified"] is True
    assert result.payload["qualified_layout_count"] == 1
    assert layout["warrant_origin"] == "reconstructed"
    assert _spans(layout["warrant_evidence"], EPISTEMIC)


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_toulmin_reconstruction_is_not_upgraded_by_an_irrelevant_literal_rule() -> None:
    result = _analyse(ToulminProvider(), RECONSTRUCTED)
    layouts = _objects(result.payload["layouts"])
    assert len(layouts) == 1, "the fictional poster is not a second asserted workshop argument"
    layout = layouts[0]
    assert layout["warrant_origin"] == "reconstructed"
    assert layout["warrant_origin_reason"] is None
    assert layout["rebuttals"] == [], "an explicitly irrelevant fictional rule is not a rebuttal in this argument"
    assert "Malik" in str(layout["claim"]) and "workshop" in str(layout["claim"])
    spans = _spans(layout["warrant_evidence"], RECONSTRUCTED)
    assert spans
    inference_start = RECONSTRUCTED.index("Éva points")
    assert all(isinstance(span["end"], int) and span["end"] > inference_start for span in spans), (
        "an unrelated fictional rule alone cannot support the actual arguer's warrant"
    )


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_toulmin_damaged_origin_remains_undetermined() -> None:
    result = _analyse(ToulminProvider(), UNDETERMINED)
    layouts = _objects(result.payload["layouts"])
    assert len(layouts) == 1, "a stated inference remains present despite damaged origin evidence"
    layout = layouts[0]
    assert layout["warrant_origin"] == "undetermined"
    assert layout["warrant_origin_reason"] in {"insufficient_context", "ambiguous_source"}
    _spans(layout["warrant_evidence"], UNDETERMINED)
    assert "container" in str(layout["claim"]) and "sealed" in str(layout["claim"])


def _expert_questions(result: NativeTechniqueResult, source: str) -> dict[int, Mapping[str, JsonValue]]:
    instances = _objects(result.payload["instances"])
    expert = [instance for instance in instances if instance["scheme_id"] == SchemeId.EXPERT_OPINION.value]
    assert len(expert) == 1, "the source explicitly argues from one bridge engineer's assertion"
    selected: dict[int, Mapping[str, JsonValue]] = {}
    for instance in instances:
        scheme = SCHEMES[SchemeId(str(instance["scheme_id"]))]
        questions = _objects(instance["critical_questions"])
        assert [question["index"] for question in questions] == list(range(len(scheme.critical_questions)))
        assert instance["question_count"] == len(questions)
        assert instance["addressed_count"] == sum(question["status"] == "addressed" for question in questions)
        assert instance["open_question_count"] == sum(question["status"] == "open" for question in questions)
        assert instance["not_assessable_count"] == sum(question["status"] == "not_assessable" for question in questions)
        for question in questions:
            spans = _spans(question["evidence"], source)
            if question["status"] == "addressed":
                assert question["note"] and spans and question["reason"] is None
            elif question["status"] == "open":
                assert not spans and question["note"] is None and question["reason"] is None
            else:
                assert question["reason"] in {"insufficient_context", "ambiguous_source"}
        if instance is expert[0]:
            selected = {cast(int, question["index"]): question for question in questions}
    return selected


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_walton_bad_answer_is_addressed_while_unmentioned_questions_stay_open() -> None:
    result = _analyse(WaltonProvider(), EXPERT)
    questions = _expert_questions(result, EXPERT)
    assert questions[3]["status"] == "addressed", "liking her hat is a bad answer, but reliability was taken up"
    assert any("hat" in str(span["text"]) for span in _spans(questions[3]["evidence"], EXPERT))
    assert questions[4]["status"] == "open", "the passage says nothing about other experts' agreement"
    assert questions[5]["status"] == "open", "the engineer's underlying evidence is not provided"


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_walton_unresolvable_referent_is_not_fabricated_as_expert_reliability() -> None:
    result = _analyse(WaltonProvider(), AMBIGUOUS_EXPERT)
    questions = _expert_questions(result, AMBIGUOUS_EXPERT)
    assert questions[3]["status"] == "not_assessable"
    assert questions[3]["reason"] == "ambiguous_source"
    assert questions[2]["status"] == "addressed", "the engineer's actual assertion remains explicit"


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_pdtb_fronted_reason_keeps_argument_direction_and_negation() -> None:
    result = _analyse(PdtbProvider(), SUBORDINATE_REASON)
    relations = _objects(result.payload["relations"])
    assert len(relations) == 1
    relation = relations[0]
    assert relation["relation_type"] == "Explicit"
    senses = relation["senses"]
    assert isinstance(senses, Sequence) and not isinstance(senses, str)
    assert "Contingency.Cause.Reason" in senses
    arg1, arg2 = relation["arg1"], relation["arg2"]
    assert isinstance(arg1, Mapping) and isinstance(arg2, Mapping)
    first = _spans(arg1["spans"], SUBORDINATE_REASON)
    second = _spans(arg2["spans"], SUBORDINATE_REASON)
    assert any("she could not open the cabinet" in str(span["text"]) for span in first)
    assert any("Léa had not received the key" in str(span["text"]) for span in second)
    connectives = _spans(relation["connective_spans"], SUBORDINATE_REASON)
    assert [span["text"] for span in connectives] == ["Because"]


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
def test_sdrt_explanation_preserves_negation_and_subordinate_attachment() -> None:
    result = _analyse(SdrtProvider(), EXPLANATION)
    edus = _spans(result.payload["edus"], EXPLANATION)
    assert len(edus) == 2
    assert "Léa did not attend the meeting" in str(edus[0]["text"])
    assert "She was ill" in str(edus[1]["text"])
    relations = _objects(result.payload["relations"])
    assert len(relations) == 1
    relation = relations[0]
    assert str(relation["label"]).casefold() == "explanation"
    assert relation["structural_type"] == "subordinating"
    assert relation["source_id"] == edus[0]["unit_id"]
    assert relation["target_id"] == edus[1]["unit_id"]
    assert result.payload["right_frontier_validated"] is True


@pytest.mark.live
@pytest.mark.slow
@pytest.mark.usefixtures("authorized_model")
@pytest.mark.parametrize("boundary", ("walton", "toulmin"))
def test_genuine_nonargument_source_does_not_invent_findings(boundary: str) -> None:
    provider = WaltonProvider() if boundary == "walton" else ToulminProvider()
    result = _analyse(provider, EMPTY)
    field = "instances" if boundary == "walton" else "layouts"
    assert _objects(result.payload[field]) == ()
