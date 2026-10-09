"""Standalone downstream selection from persisted public results."""
from pathlib import Path
import json
import subprocess
import sys

from examples.concept_passages import records
from rdam.concepts import ConceptIndex, link_source
from rdam.concepts.serialization import export_jsonl, serialize
from rdam.ingest.contracts.source import SourceArtifact


def test_consumer_reads_json_and_jsonl_and_selects_identifier(tmp_path: Path) -> None:
    result = link_source(SourceArtifact.from_text("Adobe Analytics. Adobe Firefly.", source_name="test"), ConceptIndex.load())
    for name, payload in (("links.json", serialize(result)), ("mentions.jsonl", export_jsonl(result))):
        path = tmp_path / name
        path.write_bytes(payload)
        assert tuple(records(path))
        run = subprocess.run([sys.executable, "examples/concept_passages.py", str(path), "coe:entity/adobe/analytics"],
                             capture_output=True, text=True, check=False)
        assert run.returncode == 0, run.stderr
        assert '"quote": "Adobe Analytics"' in run.stdout
        assert '"status": "pending"' in run.stdout
        # The label and, overlapping it, Central's short-form term "Analytics".
        assert [json.loads(line)["quote"] for line in run.stdout.splitlines()] == ["Adobe Analytics", "Analytics"]
    old = tmp_path / "old.jsonl"
    old.write_text('{"schema_version":"5.2","slug":"old-card"}\n')
    assert tuple(records(old)) == ()


def test_consumer_joins_persisted_native_source_evidence(tmp_path: Path, monkeypatch: object) -> None:
    from collections.abc import AsyncGenerator
    from contextlib import asynccontextmanager

    import pytest
    from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    from examples.concept_passages import native_locations
    from rdam import AggregateRequest, Machine, Technique
    from rdam.concepts import link_inventory
    from rdam.concepts.serialization import mention_records
    from rdam.contracts import AggregateAnalysis, MachinePreparation
    from rdam.ingest.contracts.preparation import ContentInventory, PreparationWarning
    from rdam.sdrt.provider import SdrtProvider
    from rdam.serialization import load, serialize as serialize_analysis

    assert isinstance(monkeypatch, pytest.MonkeyPatch)
    text = "Adobe Analytics reports results."

    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "edus": [{"unit_id": "e1", "text": text, "start": 0, "end": len(text)}], "relations": [],
        })])

    @asynccontextmanager
    async def model_for_test(_model: str, *, timeout_seconds: float) -> AsyncGenerator[FunctionModel]:
        assert timeout_seconds > 0
        yield FunctionModel(respond)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr("rdam._llm._model_without_implicit_retries", model_for_test)
    analysis = Machine([SdrtProvider()]).analyse(AggregateRequest.for_text(text, (Technique.SDRT,)))
    path = tmp_path / "analysis.json"
    path.write_bytes(serialize_analysis(analysis))
    reloaded = load(path.read_bytes())
    assert isinstance(reloaded, AggregateAnalysis)
    assert isinstance(reloaded.preparation, MachinePreparation)
    semantic = reloaded.preparation.preparation
    inventory = ContentInventory(source=semantic.source, source_contract=semantic.source_contract,
        items=semantic.inventory, empty_submitted_content=PreparationWarning.EMPTY_SUBMITTED_CONTENT in semantic.warnings)
    result = link_inventory(inventory, ConceptIndex.load())
    record = next(item for item in mention_records(result) if item.mention.quote == "Adobe Analytics")
    joined = native_locations(record, reloaded)
    assert any(item["technique"] == "sdrt" and item["native_quote"] == text for item in joined)
    assert all(item["join"] == "shared_inventory_item" for item in joined)
