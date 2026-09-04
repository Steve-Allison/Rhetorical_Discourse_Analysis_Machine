"""Structured techniques receive only caller-declared input, never inferred input."""

from rdam import AggregateRequest, Machine, Technique, UnavailableOutcome, UnavailableReason
from rdam.dung.provider import DungProvider
from rdam.ibis.provider import IbisProvider


def test_no_cross_technique_derivation() -> None:
    machine = Machine((DungProvider(), IbisProvider()))
    result = machine.analyse(AggregateRequest.for_text("A supports B.", (Technique.DUNG, Technique.IBIS)))
    assert result.lineage == ()
    assert all(isinstance(outcome, UnavailableOutcome) and outcome.reason is UnavailableReason.MISSING_STRUCTURED_INPUT
               for outcome in result.outcomes)
    assert all(provider.declaration.content_requirement is None for provider in machine.providers.values())
