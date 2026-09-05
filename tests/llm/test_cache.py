"""Machine cache integration with a real structured analyst at the external-model seam."""

from pathlib import Path

from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import (AggregateRequest, AvailableCapability, ExecutionPolicy, FormalismDeclaration,
                  Machine, NativeTechniqueResult, ProviderDeclaration, ProviderProvenance, ProviderRequest,
                  SemanticVersion, Technique, semantic_sha256, technique_curie)
from rdam._llm import StructuredAnalyst
from rdam.toulmin.argument import ToulminAnalysis
from rdam.toulmin.provider import ToulminProvider
from rdam.contracts import ProviderConfiguration
from tests.machine.conftest import fixture_descriptor


class AnalystProvider:
    """A complete test provider with immutable fixture code provenance, not a patched production provider."""

    def __init__(self) -> None:
        self.analyst = StructuredAnalyst(output_type=ToulminAnalysis, instructions="Return layouts.", model="openai:gpt-5.6-sol")
        version = SemanticVersion(root="1.0.0")
        capability = AvailableCapability(provider_id="test/analyst", contract_version=version)
        self.declaration = ProviderDeclaration(
            provider_id=capability.provider_id, technique=Technique.TOULMIN,
            technique_curie=technique_curie(Technique.TOULMIN), contract_version=version,
            formalisms=(FormalismDeclaration(formalism_id="toulmin_layout", technique=Technique.TOULMIN,
                                             technique_curie=technique_curie(Technique.TOULMIN), capability=capability),),
            provenance=ProviderProvenance(package="tests.llm.test_cache", version="1.0.0",
                                          source_revision=semantic_sha256(Path(__file__).read_text()),
                                          model_identity=self.analyst.model, licence="test fixture"),
            capability=capability, requires_structured_input=False,
            content_requirement=ToulminProvider().content_requirement,
            configuration=ProviderConfiguration(settings={"model": self.analyst.model}, cache_eligible=True,
                cache_reason="fixed_external_model_fixture"),
            interpretations=(fixture_descriptor("toulmin_layout", Technique.TOULMIN, version),),
        )

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        assert request.projection is not None
        extraction = self.analyst.extract(request.projection.prepared_document.text)
        return NativeTechniqueResult(
            technique=Technique.TOULMIN, formalism_id="toulmin_layout", provider_id=self.declaration.provider_id,
            provider_contract_version=self.declaration.contract_version, source=request.source,
            payload=extraction.structure.to_payload(), provenance=self.declaration.provenance,
        )


@pytest.mark.parametrize("damage", (None, "corrupt", "truncated", "contract_stale"))
def test_hit_makes_no_model_request_and_damaged_entries_reanalyse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damage: str | None,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    calls = 0

    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"layouts": []})])

    provider = AnalystProvider()
    machine = Machine([provider], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
    request = AggregateRequest.for_text("The result follows from the evidence.", (Technique.TOULMIN,))
    with provider.analyst.agent.override(model=FunctionModel(respond)):
        first = machine.analyse(request)
    if damage is None:
        second = machine.analyse(request)  # No override: any accidental model request is forbidden.
        assert second == first and calls == 1
    else:
        entry = next(tmp_path.glob("*.json"))
        payload = entry.read_bytes()
        entry.write_bytes(b"garbage" if damage == "corrupt" else payload[:len(payload)//2] if damage == "truncated"
                          else payload.replace(b'"contract_version":"2.0.0"', b'"contract_version":"9.0.0"', 1))
        with pytest.warns(RuntimeWarning, match="discarded corrupt"), provider.analyst.agent.override(model=FunctionModel(respond)):
            assert machine.analyse(request) == first
        assert calls == 2


def test_no_cache_directory_means_no_persistence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.chdir(tmp_path)
    provider = AnalystProvider()
    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"layouts": []})])
    with provider.analyst.agent.override(model=FunctionModel(respond)):
        Machine([provider]).analyse(AggregateRequest.for_text("Evidence.", (Technique.TOULMIN,)))
    assert tuple(tmp_path.iterdir()) == ()


@pytest.mark.parametrize("element", ("source", "projection", "provider", "contract", "model", "instructions"))
def test_each_identity_change_causes_one_real_cache_miss(
    element: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    calls = 0

    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"layouts": []})])

    provider = AnalystProvider()
    machine = Machine([provider], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
    request = AggregateRequest.for_text("Evidence supports the claim.", (Technique.TOULMIN,))
    with provider.analyst.agent.override(model=FunctionModel(respond)):
        first = machine.analyse(request)
        assert machine.analyse(request) == first
        assert calls == 1
        declaration = provider.declaration.model_dump()
        if element == "source":
            request = AggregateRequest.for_text("Different evidence supports the claim.", (Technique.TOULMIN,))
        elif element == "projection":
            requirement = declaration["content_requirement"]
            requirement.pop("semantic_digest")
            requirement["normalization"] = "unicode_nfc"
        elif element == "provider":
            declaration["provider_id"] = "test/changed-provider"
            declaration["capability"]["provider_id"] = declaration["provider_id"]
            for formalism in declaration["formalisms"]:
                formalism["capability"]["provider_id"] = declaration["provider_id"]
        elif element == "contract":
            declaration["contract_version"] = "2.0.0"
            declaration["capability"]["contract_version"] = "2.0.0"
            for formalism in declaration["formalisms"]:
                formalism["capability"]["contract_version"] = "2.0.0"
            declaration["interpretations"] = (fixture_descriptor("toulmin_layout", Technique.TOULMIN,
                SemanticVersion(root="2.0.0")).model_dump(),)
        elif element == "model":
            declaration["provenance"]["model_identity"] = "fixture/changed-model"
        else:
            declaration["instructions_identity"] = {"algorithm": "sha256", "hex_digest": semantic_sha256("Changed instructions.")}
        provider.declaration = ProviderDeclaration.model_validate(declaration)
        second = machine.analyse(request)
        assert calls == 2
        assert machine.analyse(request) == second
        assert calls == 2
    assert len(tuple(tmp_path.glob("*.json"))) == 2
