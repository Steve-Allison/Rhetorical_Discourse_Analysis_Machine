"""Feature 019 regressions for native assessment and source-evidence contracts.

These authored proposals test real validators, not live-model semantic quality.
"""

import pytest
from pydantic import ValidationError

from rdam._strict import JsonValue
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.toulmin.argument import ToulminAnalysis, ToulminLayout
from rdam.walton.schemes import SCHEMES, SCHEME_SET_ID, CriticalQuestion, SchemeId, SchemeInstance, WaltonAnalysis

SOURCE = "Éva inspected the bridge. She reports that it is unsafe."
WARRANT_SOURCE = "Unstable bridges should close. This bridge is unstable."


def _span(source: str, quote: str) -> dict[str, JsonValue]:
    start = source.index(quote)
    return {"start": start, "end": start + len(quote), "text": quote}


def _instance(scheme_id: SchemeId = SchemeId.POSITION_TO_KNOW) -> dict[str, JsonValue]:
    return {
        "scheme_id": scheme_id.value,
        "conclusion": "The bridge is unsafe.",
        "premises": {role: f"Source content for {role}" for role in SCHEMES[scheme_id].premise_roles},
        "critical_questions": [
            {"index": index, "status": "open"}
            for index in range(len(SCHEMES[scheme_id].critical_questions))
        ],
    }


def _layout() -> dict[str, JsonValue]:
    return {
        "claim": "The bridge should close.",
        "grounds": ["This bridge is unstable."],
        "warrant": "Unstable bridges should close.",
        "warrant_origin": "explicit",
        "warrant_evidence": [_span(WARRANT_SOURCE, "Unstable bridges should close.")],
        "warrant_origin_reason": None,
    }


@pytest.mark.parametrize("scheme_id", tuple(SchemeId))
def test_walton_complete_questions_follow_catalogue_order(scheme_id: SchemeId) -> None:
    proposal = _instance(scheme_id)
    questions = proposal["critical_questions"]
    assert isinstance(questions, list)
    proposal["critical_questions"] = list(reversed(questions))
    instance = SchemeInstance.model_validate(proposal)
    assert [question.index for question in instance.critical_questions] == list(range(len(questions)))
    assert instance.open_questions == SCHEMES[scheme_id].critical_questions


@pytest.mark.parametrize("coverage", ("omitted", "empty", "partial"))
def test_walton_missing_assessments_are_not_fabricated_open(coverage: str) -> None:
    proposal = _instance()
    if coverage == "omitted":
        del proposal["critical_questions"]
    else:
        proposal["critical_questions"] = [] if coverage == "empty" else [{"index": 0, "status": "open"}]
    with pytest.raises(ValidationError):
        SchemeInstance.model_validate(proposal)


@pytest.mark.parametrize("index", (-1, True, 0.0, "0"))
def test_walton_question_indices_are_strict_nonnegative_integers(index: JsonValue) -> None:
    with pytest.raises(ValidationError):
        CriticalQuestion.model_validate({"index": index, "status": "open"})


@pytest.mark.parametrize("indices", ((0, 0, 2), (0, 1, 3)))
def test_walton_duplicate_and_unknown_indices_are_rejected(indices: tuple[int, ...]) -> None:
    with pytest.raises(ValidationError):
        SchemeInstance.model_validate({
            **_instance(),
            "critical_questions": [{"index": index, "status": "open"} for index in indices],
        })


def test_walton_addressed_note_without_evidence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        CriticalQuestion.model_validate({"index": 0, "status": "addressed", "note": "The source describes an inspection."})


@pytest.mark.parametrize("note", (None, "", "   "))
def test_walton_addressed_evidence_requires_an_explanatory_note(note: str | None) -> None:
    with pytest.raises(ValidationError):
        CriticalQuestion.model_validate({
            "index": 0, "status": "addressed", "note": note,
            "evidence": [_span(SOURCE, "Éva inspected the bridge.")],
        })


@pytest.mark.parametrize("reason", ("insufficient_context", "ambiguous_source"))
def test_walton_unresolved_state_is_not_open_and_counts_reconcile(reason: str) -> None:
    evidence = _span(SOURCE, "Éva inspected the bridge.")
    instance = SchemeInstance.model_validate({
        **_instance(),
        "critical_questions": [
            {"index": 2, "status": "not_assessable", "reason": reason},
            {"index": 0, "status": "addressed", "note": "The source describes an inspection.", "evidence": [evidence]},
            {"index": 1, "status": "open"},
        ],
    })
    payload = instance.to_payload()
    assert payload["question_count"] == 3
    assert payload["addressed_count"] == 1
    assert payload["open_question_count"] == 1
    assert payload["not_assessable_count"] == 1
    assert instance.open_questions == (SCHEMES[SchemeId.POSITION_TO_KNOW].critical_questions[1],)
    questions = payload["critical_questions"]
    assert isinstance(questions, list)
    assert isinstance(questions[0], dict)
    assert questions[0]["evidence"] == [evidence]
    assert isinstance(questions[2], dict)
    assert questions[2]["reason"] == reason
    analysis = WaltonAnalysis(instances=[instance]).to_payload()
    assert analysis["total_open_questions"] == 1
    assert analysis["scheme_set"] == SCHEME_SET_ID


@pytest.mark.parametrize("fields", (
    {"status": "not_assessable"},
    {"status": "not_assessable", "reason": "model_unsure"},
    {"status": "open", "reason": "insufficient_context"},
    {"status": "open", "note": "A proposed answer."},
    {"status": "open", "evidence": [_span(SOURCE, "Éva")]},
    {"status": "addressed", "note": "An inspection.", "evidence": [_span(SOURCE, "Éva")], "reason": "ambiguous_source"},
))
def test_walton_status_specific_fields_are_enforced(fields: dict[str, JsonValue]) -> None:
    with pytest.raises(ValidationError):
        CriticalQuestion.model_validate({"index": 0, **fields})


def test_walton_empty_analysis_remains_valid() -> None:
    payload = WaltonAnalysis().to_payload()
    assert payload["instances"] == []
    assert payload["instance_count"] == 0
    assert payload["total_open_questions"] == 0


def test_toulmin_missing_warrant_origin_is_rejected() -> None:
    proposal = _layout()
    for field in ("warrant_origin", "warrant_evidence", "warrant_origin_reason"):
        del proposal[field]
    with pytest.raises(ValidationError):
        ToulminLayout.model_validate(proposal)


@pytest.mark.parametrize("origin", ("explicit", "reconstructed"))
def test_toulmin_supported_origin_and_evidence_survive_payload(origin: str) -> None:
    proposal = {**_layout(), "warrant_origin": origin}
    payload = ToulminLayout.model_validate(proposal).to_payload()
    assert payload["warrant_origin"] == origin
    assert payload["warrant_evidence"] == proposal["warrant_evidence"]
    assert payload["warrant_origin_reason"] is None


@pytest.mark.parametrize("reason", ("insufficient_context", "ambiguous_source"))
def test_toulmin_undetermined_requires_and_retains_a_reason(reason: str) -> None:
    payload = ToulminLayout.model_validate({
        **_layout(), "warrant_origin": "undetermined", "warrant_evidence": [], "warrant_origin_reason": reason,
    }).to_payload()
    assert payload["warrant_origin"] == "undetermined"
    assert payload["warrant_origin_reason"] == reason
    assert payload["warrant_evidence"] == []


@pytest.mark.parametrize("changes", (
    {"warrant_origin": "explicit", "warrant_evidence": []},
    {"warrant_origin": "reconstructed", "warrant_evidence": []},
    {"warrant_origin": "explicit", "warrant_origin_reason": "ambiguous_source"},
    {"warrant_origin": "reconstructed", "warrant_origin_reason": "insufficient_context"},
    {"warrant_origin": "undetermined", "warrant_origin_reason": None},
    {"warrant_origin": "undetermined", "warrant_origin_reason": "model_unsure"},
))
def test_toulmin_origin_specific_evidence_and_reasons_are_enforced(changes: dict[str, JsonValue]) -> None:
    with pytest.raises(ValidationError):
        ToulminLayout.model_validate({**_layout(), **changes})


def test_toulmin_qualification_count_names_its_actual_rule() -> None:
    bare = ToulminLayout.model_validate(_layout())
    qualified = ToulminLayout.model_validate({**_layout(), "qualifier": "presumably"})
    rebutted = ToulminLayout.model_validate({**_layout(), "rebuttals": [{"condition": "Unless repairs restore stability."}]})
    assert qualified.elements_present == ("claim", "grounds", "warrant", "qualifier")
    assert qualified.is_qualified is True
    payload = ToulminAnalysis(layouts=[bare, qualified, rebutted]).to_payload()
    assert payload["layout_count"] == 3
    assert payload["qualified_layout_count"] == 2
    assert "fully_qualified_count" not in payload


def test_toulmin_empty_analysis_uses_current_count_name() -> None:
    assert ToulminAnalysis().to_payload() == {"layouts": [], "layout_count": 0, "qualified_layout_count": 0}


@pytest.mark.parametrize("status", ("addressed", "not_assessable"))
def test_walton_analysis_checks_all_native_evidence_against_source(status: str) -> None:
    question: dict[str, JsonValue] = {
        "index": 0, "status": status, "evidence": [_span(SOURCE, "Éva inspected the bridge.")],
    }
    if status == "addressed":
        question["note"] = "The passage describes an inspection."
    else:
        question["reason"] = "ambiguous_source"
    analysis = WaltonAnalysis.model_validate({"instances": [{
        **_instance(),
        "critical_questions": [question, {"index": 1, "status": "open"}, {"index": 2, "status": "open"}],
    }]})
    analysis.validate_source(SOURCE)
    with pytest.raises(ValueError):
        analysis.validate_source(SOURCE.replace("Éva", "Ada"))


@pytest.mark.parametrize("origin", ("explicit", "reconstructed", "undetermined"))
def test_toulmin_analysis_checks_evidence_even_for_unresolved_origins(origin: str) -> None:
    analysis = ToulminAnalysis.model_validate({"layouts": [{
        **_layout(), "warrant_origin": origin,
        "warrant_origin_reason": "ambiguous_source" if origin == "undetermined" else None,
    }]})
    analysis.validate_source(WARRANT_SOURCE)
    with pytest.raises(ValueError):
        analysis.validate_source(WARRANT_SOURCE.replace("Unstable", "Reliable"))


def test_source_evidence_uses_unicode_characters_without_normalizing_text() -> None:
    source = "É🙂 Cafe\u0301 — 桥"
    quote = "Cafe\u0301 — 桥"
    span = SourceEvidenceSpan.model_validate(_span(source, quote))
    span.validate_source(source)
    assert source[span.start:span.end] == quote
    with pytest.raises(ValueError):
        span.validate_source(source.replace("e\u0301", "é"))


@pytest.mark.parametrize(("start", "end", "text"), (
    (-1, 1, "ab"),
    (0, 0, "a"),
    (2, 1, "a"),
    (0, 1, ""),
    (0, 2, "a"),
    (True, 2, "a"),
    (0, True, "a"),
    (0.0, 1, "a"),
    (0, "1", "a"),
))
def test_source_evidence_rejects_invalid_ranges_and_coercion(start: JsonValue, end: JsonValue, text: str) -> None:
    with pytest.raises(ValidationError):
        SourceEvidenceSpan.model_validate({"start": start, "end": end, "text": text})


@pytest.mark.parametrize(("start", "end", "quote"), (
    (0, 3, "Ada"),
    (1, 4, "Éva"),
    (100, 103, "Éva"),
))
def test_source_evidence_rejects_fabricated_quotes_wrong_offsets_and_out_of_bounds(
    start: int, end: int, quote: str,
) -> None:
    span = SourceEvidenceSpan(start=start, end=end, text=quote)
    with pytest.raises(ValueError):
        span.validate_source(SOURCE)


def test_source_evidence_is_frozen_and_rejects_unknown_fields() -> None:
    span = SourceEvidenceSpan(start=0, end=3, text="Éva")
    with pytest.raises(ValidationError):
        span.start = 1
    with pytest.raises(ValidationError):
        SourceEvidenceSpan.model_validate({"start": 0, "end": 3, "text": "Éva", "confidence": 1})


def test_repeated_quotes_keep_the_declared_occurrence() -> None:
    source = "Éva saw Éva."
    start = source.rindex("Éva")
    span = SourceEvidenceSpan(start=start, end=start + len("Éva"), text="Éva")
    span.validate_source(source)
    assert span.start == start
