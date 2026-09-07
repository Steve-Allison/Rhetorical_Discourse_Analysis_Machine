"""PDTB retries receive all literal locations without repairing the proposal."""

import pytest

from rdam.pdtb.relations import PdtbAnalysis, RelationError


def test_source_feedback_identifies_every_incorrect_span_without_mutation() -> None:
    source = "Éva stayed because rain fell."
    analysis = PdtbAnalysis.model_validate({"relations": [{
        "relation_id": "r1", "relation_type": "Explicit",
        "arg1": {"spans": [{"start": 1, "end": 11, "text": "Éva stayed"}]},
        "arg2": {"spans": [{"start": 20, "end": 29, "text": "rain fell"}]},
        "senses": ["Contingency.Cause.Reason"],
        "connective_spans": [{"start": 12, "end": 19, "text": "because"}],
    }]})
    original = analysis.model_dump_json()
    with pytest.raises(RelationError) as caught:
        analysis.validate_source(source)
    message = str(caught.value)
    for quotation in ("Éva stayed", "rain fell", "because"):
        start = source.index(quotation)
        assert f"[{start}, {start + len(quotation)})" in message
    assert analysis.model_dump_json() == original


@pytest.mark.parametrize(("source", "expected"), [("Rain Rain", "multiple literal occurrences"), ("Snow", "no literal occurrence")])
def test_source_feedback_preserves_missing_or_ambiguous_quotations(source: str, expected: str) -> None:
    analysis = PdtbAnalysis.model_validate({"relations": [{
        "relation_id": "r1", "relation_type": "EntRel",
        "arg1": {"spans": [{"start": 1, "end": 5, "text": "Rain"}]},
        "arg2": {"spans": [{"start": 6, "end": 10, "text": "Rain"}]},
    }]})
    with pytest.raises(RelationError, match=expected):
        analysis.validate_source(source)
