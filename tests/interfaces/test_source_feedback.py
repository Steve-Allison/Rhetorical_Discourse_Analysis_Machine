"""Evidence retry feedback identifies coordinate errors without repairing results."""

import pytest

from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.toulmin.argument import LayoutError, ToulminAnalysis
from rdam.walton.schemes import SchemeError, WaltonAnalysis


def test_unique_literal_occurrence_has_actionable_character_coordinates() -> None:
    span = SourceEvidenceSpan(start=0, end=4, text="Éva.")
    with pytest.raises(ValueError, match=r"unique literal occurrence at \[6, 10\)"):
        span.validate_source("🧭 Dr. Éva.")
    assert span.start == 0 and span.end == 4, "validation must never repair model output"


def test_repeated_quote_does_not_guess_the_intended_occurrence() -> None:
    span = SourceEvidenceSpan(start=1, end=5, text="Éva.")
    with pytest.raises(ValueError, match="multiple literal occurrences"):
        span.validate_source("Éva. Éva.")


def test_absent_quote_does_not_offer_invented_coordinates() -> None:
    span = SourceEvidenceSpan(start=0, end=4, text="Éva.")
    with pytest.raises(ValueError, match="no literal occurrence"):
        span.validate_source("Lea.")


def test_correct_repeated_quote_is_valid_without_disambiguation() -> None:
    SourceEvidenceSpan(start=5, end=9, text="Éva.").validate_source("Éva. Éva.")


def test_toulmin_reports_all_bad_spans_in_one_validation_attempt() -> None:
    analysis = ToulminAnalysis.model_validate({"layouts": [{
        "claim": "B.", "grounds": ["A."], "warrant": "A licenses B.",
        "warrant_origin": "reconstructed", "warrant_evidence": [
            {"start": 1, "end": 3, "text": "A."}, {"start": 2, "end": 4, "text": "B."},
        ],
    }]})
    with pytest.raises(LayoutError) as caught:
        analysis.validate_source("A. B.")
    assert "/layouts/0/warrant_evidence/0" in str(caught.value)
    assert "/layouts/0/warrant_evidence/1" in str(caught.value)
    assert "[0, 2)" in str(caught.value) and "[3, 5)" in str(caught.value)


def test_walton_reports_all_bad_questions_in_one_validation_attempt() -> None:
    analysis = WaltonAnalysis.model_validate({"instances": [{
        "scheme_id": "sign", "conclusion": "B.", "premises": {"finding": "A.", "indicated": "B."},
        "critical_questions": [
            {"index": index, "status": "addressed", "note": "Taken up.", "evidence": [span]}
            for index, span in enumerate((
                {"start": 1, "end": 3, "text": "A."}, {"start": 2, "end": 4, "text": "B."},
            ))
        ],
    }]})
    with pytest.raises(SchemeError) as caught:
        analysis.validate_source("A. B.")
    assert "/instances/0/critical_questions/0/evidence/0" in str(caught.value)
    assert "/instances/0/critical_questions/1/evidence/0" in str(caught.value)
    assert "[0, 2)" in str(caught.value) and "[3, 5)" in str(caught.value)
