"""Structured techniques receive only caller-declared input, never inferred input."""

from rdam import AggregateRequest, Machine, ResultOutcome, StructuredInput, Technique, UnavailableOutcome, UnavailableReason
from rdam.dung.provider import DungProvider
from rdam.ibis.provider import IbisProvider


def test_no_cross_technique_derivation() -> None:
    machine = Machine((DungProvider(), IbisProvider()))
    result = machine.analyse(
        AggregateRequest.for_text(
            "A supports B.",
            (Technique.IBIS, Technique.DUNG),
            structured_inputs=(
                StructuredInput(
                    technique=Technique.IBIS,
                    payload={"nodes": [{"id": "i1", "kind": "issue", "text": "Question?"}], "links": []},
                ),
            ),
        )
    )
    assert result.lineage == ()
    assert isinstance(result.outcome_for(Technique.IBIS), ResultOutcome)
    dung_outcome = result.outcome_for(Technique.DUNG)
    assert isinstance(dung_outcome, UnavailableOutcome)
    assert dung_outcome.reason is UnavailableReason.MISSING_STRUCTURED_INPUT
    assert DungProvider().declaration.content_requirement is None
