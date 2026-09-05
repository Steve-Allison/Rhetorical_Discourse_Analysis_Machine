"""Native structure errors are preserved as failures, not silently discarded input."""

import pytest

from rdam import AggregateRequest, Machine, StructuredInput, Technique, FailedOutcome, ResultOutcome
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider


@pytest.mark.parametrize("technique,payload", [
    (Technique.DUNG, {"arguments": ["a"], "attacks": [], "surprise": True}),
    (Technique.IBIS, {"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}], "links": [], "surprise": True}),
    (Technique.IBIS, {"nodes": [{"id": "q", "kind": "issue", "text": "Why?", "surprise": True}], "links": []}),
    (Technique.IBIS, {"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}, {"id": "p", "kind": "position", "text": "Because."}],
                      "links": [{"from": "p", "relation": "responds_to", "to": "q", "surprise": True}]}),
])
def test_unknown_native_fields_fail(technique: Technique, payload: dict[str, object]) -> None:
    request = AggregateRequest.for_structured((StructuredInput.model_validate({"technique": technique, "payload": payload}),))
    result = Machine((DungProvider(), IbisProvider())).analyse(request)
    assert result.status == "unsuccessful"
    assert isinstance(result.outcomes[0], FailedOutcome)


def test_no_stable_extension_and_issue_without_positions_are_successes() -> None:
    request = AggregateRequest.for_structured((
        StructuredInput(technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": [["a", "a"]]}),
        StructuredInput(technique=Technique.IBIS, payload={"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}], "links": []}),
    ))
    result = Machine((DungProvider(), IbisProvider())).analyse(request)
    assert result.status == "complete"
    assert result.preparation is None
    assert all(isinstance(item, ResultOutcome) for item in result.outcomes)
