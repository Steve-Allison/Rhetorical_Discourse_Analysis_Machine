"""The ingest capability report is the machine's source-form authority."""

import ast
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from rdam import AggregateRequest, Machine, Technique, ResultOutcome
from rdam.toulmin import ToulminProvider
from rdam.ingest import describe_capabilities
from rdam.ingest.contracts.capabilities import Availability
from rdam.ingest.contracts.source import SourceForm
from rdam.ingest.contracts.failure import ProductionIngestError, LifecycleStage
from tests.ingest.test_inventory_completeness import source_case


@pytest.mark.parametrize("form", tuple(SourceForm))
def test_available_form_enters_machine(form: SourceForm, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    artifact, expected = source_case(form)
    payload = artifact.raw_bytes or json.dumps(artifact.edus).encode()
    request = AggregateRequest.for_bytes(payload, form, artifact.source_name, (Technique.TOULMIN,))
    provider = ToulminProvider()

    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"layouts": []})])

    with provider._built().agent.override(model=FunctionModel(respond)):
        result = Machine([provider]).analyse(request)
    assert isinstance(result.outcome_for(Technique.TOULMIN), ResultOutcome)
    assert result.preparation is not None
    assert {item.item_id for item in result.preparation.inventory.items} == expected


def test_malformed_form_fails_typed_at_classification() -> None:
    request = AggregateRequest.for_bytes(b"{}", SourceForm.DOCLING_JSON, "invalid.json", (Technique.RST,))
    with pytest.raises(ProductionIngestError) as raised:
        Machine().analyse(request)
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION


def test_unavailable_form_fails_typed_before_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    def installed_version(distribution: str) -> str:
        if distribution == "docling-core":
            raise PackageNotFoundError(distribution)
        return version(distribution)

    monkeypatch.setattr("rdam.ingest.contracts.capabilities.version", installed_version)
    monkeypatch.setitem(sys.modules, "docling_core.types.doc", None)
    capability = next(item for item in describe_capabilities().semantic.source_forms
                      if item.source_form is SourceForm.DOCLING_JSON)
    assert capability.availability is Availability.UNAVAILABLE
    artifact, _ = source_case(SourceForm.DOCLING_JSON)
    assert artifact.raw_bytes is not None
    request = AggregateRequest.for_bytes(artifact.raw_bytes, SourceForm.DOCLING_JSON, artifact.source_name, (Technique.RST,))
    with pytest.raises(ProductionIngestError) as raised:
        Machine().analyse(request)
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION
    assert "docling-core" in str(raised.value.failure)


def test_machine_has_no_second_source_form_registry() -> None:
    tree = ast.parse(Path("rdam/machine.py").read_text())
    assert not any(
        isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "SourceForm"
        for node in ast.walk(tree)
    )
    assert {item.source_form for item in describe_capabilities().semantic.source_forms} == set(SourceForm)
