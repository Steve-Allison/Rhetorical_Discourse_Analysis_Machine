"""Real configured machines preserve requested scope and source evidence."""

from collections import Counter
from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
import socket
import sys
from types import FrameType
from typing import cast

from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam._strict import JsonValue
from rdam.composition import production_machine
from rdam.configuration import ExecutionSettings, LlmSettings, MachineConfig, RstSettings, TechniqueModels
from rdam.contracts import (
    AggregateAnalysis, AggregateRequest, FailedOutcome, MachinePreparation,
    PreparationRequest, ProjectedPreparationBinding, ResultOutcome, StructuredInput,
    StructuredPreparationBinding, UnavailableCapability, UnavailableOutcome,
    UnavailablePreparationBinding, UpstreamResultReference,
)
from rdam.dung import DungProvider
from rdam.frameworks import BOUNDARY_TECHNIQUES, Technique
from rdam.ibis import IbisProvider
from rdam.interpretation import AnalysisView, select_analysis
from rdam.machine import Machine
from rdam.serialization import load, serialize
from rdam.toulmin import ToulminProvider


def _dung(*, malformed: bool = False) -> StructuredInput:
    return StructuredInput(technique=Technique.DUNG, payload={
        "arguments": ["a"], "attacks": [["a", "missing" if malformed else "a"]],
    })


def _ibis(*, derived_from: UpstreamResultReference | None = None) -> StructuredInput:
    return StructuredInput(technique=Technique.IBIS, payload={
        "nodes": [{"id": "issue", "kind": "issue", "text": "Should we proceed?"}], "links": [],
    }, derived_from=derived_from)


def test_configuration_resolves_once_and_reaches_all_actual_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RDAM_LLM_MODEL", "openai:model-at-construction")
    config = MachineConfig(
        llm=LlmSettings(output_retries=0, transport_retries=1, transport_deadline_seconds=4.5),
        technique_models=TechniqueModels(toulmin="anthropic:technique-override"),
        dung_capacity=1,
        rst=RstSettings(device="cpu", relinventory="eng.erst.gum", evidence_detail="normalized_distributions",
                        marker_refinement="disabled"),
    )
    monkeypatch.setenv("RDAM_LLM_MODEL", "openai:changed-after-construction")
    machine = production_machine(config=config)
    assert tuple(machine.providers) == BOUNDARY_TECHNIQUES
    for technique in (Technique.PDTB, Technique.SDRT, Technique.TOULMIN, Technique.WALTON):
        settings = machine.providers[technique].declaration.configuration.settings
        assert settings["model"] == ("anthropic:technique-override" if technique is Technique.TOULMIN
                                     else "openai:model-at-construction")
        assert settings["output_retries"] == 0
        assert settings["transport_retries"] == 1
        assert settings["transport_deadline_seconds"] == 4.5
    rst = machine.providers[Technique.RST].declaration.configuration.settings
    assert rst["device"] == "cpu"
    assert rst["relinventory"] == "eng.erst.gum"
    assert rst["evidence_detail"] == "normalized_distributions"
    assert rst["marker_refinement"] == "disabled"
    policy = rst["analysis_policy"]
    assert isinstance(policy, Mapping)
    assert policy["evidence_detail"] == rst["evidence_detail"]
    assert policy["marker_refinement"] == rst["marker_refinement"]
    request = AggregateRequest.for_structured((StructuredInput(technique=Technique.DUNG, payload={
        "arguments": ["a", "b"], "attacks": [],
    }),))
    outcome = machine.analyse(request).outcome_for(Technique.DUNG)
    assert isinstance(outcome, FailedOutcome)
    assert outcome.failure.code == "framework_exceeds_declared_capacity"


def test_execution_settings_do_not_change_analytical_provider_identities(tmp_path: Path) -> None:
    plain = production_machine(config=MachineConfig(execution=ExecutionSettings(max_workers=1)))
    cached = production_machine(config=MachineConfig(execution=ExecutionSettings(max_workers=3, cache_directory=tmp_path)))
    assert plain.capabilities().configurations == cached.capabilities().configurations
    request = AggregateRequest.for_structured((_dung(), _ibis()))
    assert serialize(plain.analyse(request)) == serialize(cached.analyse(request))


def test_capabilities_are_model_free_and_cover_every_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_network(*_args: object, **_kwargs: object) -> object:
        pytest.fail("capabilities attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden_network)
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    capabilities = production_machine(config=MachineConfig()).capabilities()
    assert tuple(item.technique for item in capabilities.techniques) == BOUNDARY_TECHNIQUES
    assert tuple(item.technique for item in capabilities.configurations) == BOUNDARY_TECHNIQUES
    assert capabilities.model_probe == "not_performed"
    assert capabilities.source_forms
    assert capabilities.contracts
    assert load(serialize(capabilities)) == capabilities


def test_default_preparation_keeps_complete_inventory_without_selecting_projections() -> None:
    machine = production_machine(config=MachineConfig())
    request = PreparationRequest.for_text("First paragraph.\n\nSecond paragraph.", source_name="source")
    prepared = machine.prepare(request)
    assert prepared.source == request.source
    assert prepared.preparation.inventory
    assert prepared.preparation.prepared_document.text == request.text
    assert prepared.projections == ()
    assert prepared.bindings == ()
    assert load(serialize(prepared)) == prepared
    assert serialize(machine.prepare(request)) == serialize(prepared)


def test_preparation_bindings_are_explicit_and_request_ordered(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    machine = Machine((ToulminProvider(model="openai:unconfigured-model"), DungProvider()))
    requested = (Technique.DUNG, Technique.TOULMIN, Technique.IBIS)
    prepared = machine.prepare(PreparationRequest.for_text("Evidence.", requested))
    assert tuple(item.technique for item in prepared.bindings) == requested
    assert isinstance(prepared.bindings[0], StructuredPreparationBinding)
    projected = prepared.bindings[1]
    assert isinstance(projected, ProjectedPreparationBinding)
    assert isinstance(projected.capability, UnavailableCapability)
    assert isinstance(prepared.bindings[2], UnavailablePreparationBinding)
    assert len(prepared.projections) == 1
    assert prepared.projections[0].projection_identity is not None
    assert projected.projection_identity.hex_digest == prepared.projections[0].projection_identity.hex_digest
    assert prepared.receipt().inventory.items == prepared.preparation.inventory


@pytest.mark.parametrize(("malformed", "missing_ibis", "status"), (
    (False, False, "complete"), (False, True, "partial"), (True, True, "unsuccessful"),
))
def test_structured_only_status_counts_exactly_requested_outcomes(malformed: bool, missing_ibis: bool, status: str) -> None:
    inputs = (_dung(malformed=malformed),) if missing_ibis else (_dung(malformed=malformed), _ibis())
    requested = (Technique.IBIS, Technique.DUNG)
    result = Machine((DungProvider(), IbisProvider())).analyse(AggregateRequest.for_structured(inputs, techniques=requested))
    assert result.requested_techniques == requested
    assert result.status == status
    assert result.preparation is None
    assert result.upstream_results == ()
    assert len(result.outcomes) == len(requested)
    assert result.outcome_for(Technique.IBIS) == result.outcomes[0]
    assert result.outcome_for(Technique.DUNG) == result.outcomes[1]
    if missing_ibis:
        assert isinstance(result.outcomes[0], UnavailableOutcome)
    if not malformed:
        dung = result.outcomes[1]
        assert isinstance(dung, ResultOutcome)
        extensions = dung.result.payload["extensions"]
        assert isinstance(extensions, Mapping)
        assert extensions["stable"] == []
    assert load(serialize(result)) == result


@pytest.mark.parametrize("derived", (False, True))
def test_retained_upstream_stays_separate_and_only_explicit_derivation_creates_lineage(derived: bool) -> None:
    machine = Machine((DungProvider(), IbisProvider()))
    first = machine.analyse(AggregateRequest.for_structured((_dung(),)))
    outcome = first.outcomes[0]
    assert isinstance(outcome, ResultOutcome)
    upstream = outcome.result
    assert upstream.semantic_digest is not None
    reference = UpstreamResultReference(technique=Technique.DUNG, result_identity=upstream.semantic_digest)
    request = AggregateRequest.for_structured((_ibis(derived_from=reference if derived else None),), upstream_results=(upstream,))
    result = machine.analyse(request)
    assert result.status == "complete"
    assert result.requested_techniques == (Technique.IBIS,)
    assert len(result.outcomes) == 1
    assert result.outcome_for(Technique.DUNG) is None
    assert result.upstream_results == (upstream,)
    assert serialize(result.upstream_results[0]) == serialize(upstream)
    assert len(result.lineage) == int(derived)
    assert result.preparation is None


def test_retained_success_cannot_upgrade_an_unsuccessful_requested_scope() -> None:
    machine = Machine((DungProvider(), IbisProvider()))
    first = machine.analyse(AggregateRequest.for_structured((_dung(),)))
    outcome = first.outcomes[0]
    assert isinstance(outcome, ResultOutcome)
    request = AggregateRequest(source=first.source, techniques=(Technique.IBIS,), upstream_results=(outcome.result,))
    result = machine.analyse(request)
    assert result.status == "unsuccessful"
    assert len(result.outcomes) == 1
    assert isinstance(result.outcomes[0], UnavailableOutcome)
    assert result.upstream_results == (outcome.result,)
    assert result.outcome_for(Technique.DUNG) is None
    assert result.lineage == ()


@pytest.mark.parametrize("damage", ("source", "projection", "binding"))
def test_preparation_rejects_inconsistent_material_even_with_a_recomputed_outer_digest(damage: str) -> None:
    machine = Machine((ToulminProvider(),))
    prepared = machine.prepare(PreparationRequest.for_text("Evidence.", (Technique.TOULMIN,)))
    other = machine.prepare(PreparationRequest.for_text("Different source.", (Technique.TOULMIN,)))
    fields = prepared.model_dump(exclude={"semantic_digest"})
    if damage == "source":
        fields["source"] = other.source.model_dump()
    elif damage == "projection":
        fields["projections"] = tuple(item.model_dump() for item in other.projections)
    else:
        fields["bindings"][0]["projection_identity"] = {"algorithm": "sha256", "hex_digest": "0" * 64}
    with pytest.raises(ValueError):
        MachinePreparation.model_validate(fields)


@pytest.fixture
def aligned_analysis(monkeypatch: pytest.MonkeyPatch) -> AggregateAnalysis:
    text = "The bridge has cracks. Close the bridge."
    proposal: dict[str, JsonValue] = {"layouts": [{
        "claim": "Close the bridge.", "grounds": ["The bridge has cracks."],
        "warrant": "Structurally damaged bridges require closure.", "warrant_origin": "reconstructed",
        "warrant_evidence": [{"start": 0, "end": 22, "text": "The bridge has cracks."}],
        "warrant_origin_reason": None,
    }]}

    def respond(_messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, proposal)])

    @asynccontextmanager
    async def model_for_test(_model: str, *, timeout_seconds: float) -> AsyncGenerator[FunctionModel]:
        assert timeout_seconds > 0
        yield FunctionModel(respond)

    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr("rdam._llm._model_without_implicit_retries", model_for_test)
    result = Machine((ToulminProvider(),)).analyse(AggregateRequest.for_text(text, (Technique.TOULMIN,)))
    assert isinstance(result.outcomes[0], ResultOutcome)
    assert result.outcomes[0].result.source_alignment
    return result


def test_valid_aligned_analysis_round_trips_with_complete_preparation(aligned_analysis: AggregateAnalysis) -> None:
    assert aligned_analysis.preparation is not None
    assert aligned_analysis.preparation.projections
    assert load(serialize(aligned_analysis)) == aligned_analysis


@pytest.mark.parametrize("damage", ("pointer", "quote", "range", "projection", "contributors", "anchors"))
def test_aggregate_rejects_alignment_lies_despite_recomputed_digests(aligned_analysis: AggregateAnalysis, damage: str) -> None:
    fields = aligned_analysis.model_dump(exclude={"semantic_digest"})
    native = fields["outcomes"][0]["result"]
    native.pop("artifact_digest")
    native.pop("semantic_digest")
    alignment = cast(dict[str, object], native["source_alignment"][0])
    if damage == "pointer":
        alignment["payload_path"] = "/missing"
    elif damage == "quote":
        alignment["quote"] = "x" * len(str(alignment["quote"]))
    elif damage == "range":
        original = cast(dict[str, int], alignment["prepared_range"])
        alignment["prepared_range"] = {"start": original["start"] + 1, "end": original["end"] + 1}
    elif damage == "projection":
        alignment["projection_identity"] = {"algorithm": "sha256", "hex_digest": "0" * 64}
    elif damage == "contributors":
        alignment["contributing_item_ids"] = ("invented-item",)
    else:
        other = Machine((ToulminProvider(),)).prepare(PreparationRequest.for_text("Other source.", (Technique.TOULMIN,)))
        alignment["source_anchors"] = tuple(anchor.model_dump() for anchor in other.projections[0].prepared_document.segments[0].source_anchors)
    with pytest.raises(ValueError):
        AggregateAnalysis.model_validate(fields)


@pytest.mark.parametrize("techniques", ((Technique.TOULMIN,), BOUNDARY_TECHNIQUES))
def test_real_preparation_executes_each_distinct_projection_only_once(techniques: tuple[Technique, ...]) -> None:
    machine = production_machine(config=MachineConfig())
    calls: Counter[str] = Counter()
    observed = {
        ("rdam.ingest.prepare", "inventory_source"),
        ("rdam.ingest.policy", "apply_policy"),
        ("rdam.ingest.projection", "project"),
    }

    def profile(frame: FrameType, event: str, _argument: object) -> None:
        name = frame.f_code.co_name
        if event == "call" and (frame.f_globals.get("__name__"), name) in observed:
            calls[name] += 1

    previous = sys.getprofile()
    try:
        sys.setprofile(profile)
        prepared = machine.prepare(PreparationRequest.for_text("Evidence exists.", techniques))
    finally:
        sys.setprofile(previous)
    assert calls["inventory_source"] == 1
    assert calls["apply_policy"] == 1
    assert calls["project"] == len(prepared.projections)


@pytest.mark.parametrize("damage", ("preparation_source", "missing_configurations"))
def test_saved_view_rejects_inconsistent_context_despite_recomputed_view_digest(damage: str) -> None:
    machine = Machine((DungProvider(),))
    aggregate = machine.analyse(AggregateRequest.for_text(
        "Original source.", (Technique.DUNG,), structured_inputs=(_dung(),),
    ))
    view = select_analysis(aggregate, techniques=(Technique.DUNG,))
    assert load(serialize(view)) == view
    fields = view.model_dump(exclude={"semantic_digest"})
    if damage == "preparation_source":
        other = machine.prepare(PreparationRequest.for_text("Entirely different source."))
        fields["preparation"] = other.model_dump()
    else:
        fields["configurations"] = ()
    with pytest.raises(ValueError):
        inconsistent = AnalysisView.model_validate(fields)
        load(serialize(inconsistent))
