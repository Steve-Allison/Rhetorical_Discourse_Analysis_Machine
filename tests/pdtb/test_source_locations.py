"""Exercise the source-location tool through the actual agent/tool protocol."""

from collections.abc import Mapping

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.pdtb import PdtbProvider


def test_lookup_preserves_unicode_repeated_overlapping_and_missing_quotes() -> None:
    source = "Éva: aaa Éva"
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(parts=[ToolCallPart(tool_name="source_locations",
                args={"quotations": ["Éva", "aa", "missing", ""]})])
        returns = [part for message in messages if isinstance(message, ModelRequest)
                   for part in message.parts if isinstance(part, ToolReturnPart)]
        assert len(returns) == 1 and isinstance(returns[0].content, Mapping)
        locations = TypeAdapter(dict[str, tuple[SourceEvidenceSpan, ...]]).validate_python(returns[0].content)
        assert [(span.start, span.end) for span in locations["Éva"]] == [(0, 3), (9, 12)]
        assert [(span.start, span.end) for span in locations["aa"]] == [(5, 7), (6, 8)]
        assert locations["missing"] == locations[""] == ()
        for spans in locations.values():
            for span in spans:
                span.validate_source(source)
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args={"relations": []})])

    analyst = PdtbProvider(model="openai:test")._built()
    with analyst.agent.override(model=FunctionModel(respond)):
        extraction = analyst.extract(source)
    assert calls == extraction.transport_attempts == 2
    assert extraction.output_attempts == 1
