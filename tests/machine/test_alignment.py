"""Two native formalisms share source anchors without sharing an analytical structure."""

from contextlib import ExitStack

from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import AggregateRequest, Machine, ResultOutcome, Technique
from rdam.toulmin.provider import ToulminProvider
from rdam.sdrt.provider import SdrtProvider


def test_native_findings_alignment_shares_only_source_coordinates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    text = "Evidence supports the decision."
    toulmin, sdrt = ToulminProvider(), SdrtProvider()
    proposals = (
        {"layouts": [{"claim": "Accept the decision.", "grounds": [text], "warrant": "Decisions supported by evidence merit acceptance."}]},
        {"edus": [{"unit_id": "e1", "text": text, "start": 0, "end": len(text)}], "relations": []},
    )
    with ExitStack() as stack:
        for provider, proposal in zip((toulmin, sdrt), proposals, strict=True):
            def respond(_messages: list[ModelMessage], info: AgentInfo, payload=proposal) -> ModelResponse:
                return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])
            stack.enter_context(provider._built().agent.override(model=FunctionModel(respond)))
        result = Machine([toulmin, sdrt]).analyse(AggregateRequest.for_text(text, (Technique.TOULMIN, Technique.SDRT)))
    first, second = result.outcomes
    assert isinstance(first, ResultOutcome) and isinstance(second, ResultOutcome)
    assert first.result.formalism_id == "toulmin_layout"
    assert second.result.formalism_id == "sdrs_graph"
    assert "layouts" in first.result.payload and "edus" not in first.result.payload
    assert "edus" in second.result.payload and "layouts" not in second.result.payload
    left = next(item for item in first.result.source_alignment if item.payload_path.endswith("/grounds/0"))
    right = next(item for item in second.result.source_alignment if item.payload_path.endswith("/text"))
    assert left.prepared_range == right.prepared_range
    assert left.source_anchors == right.source_anchors
    assert left.contributing_item_ids == right.contributing_item_ids
    assert result.lineage == ()
