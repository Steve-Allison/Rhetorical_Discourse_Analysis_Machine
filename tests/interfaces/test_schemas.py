"""Advertised schemas validate actual emitted bytes, not invented native outputs.

LLM cases replace only the external model response. Native providers, source
validation, derived fields, preparation, interpretation, and serialization run.
"""

from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Literal

from jsonschema import Draft202012Validator
from jsonschema.protocols import Validator
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import (
    AggregateAnalysis, AggregateRequest, AvailableCapability, FormalismChoice,
    Machine, PreparationRequest, ProviderRequest,
    ResultOutcome, SourceIdentity, StructuredInput, Technique,
    UpstreamResultReference, ViewRequest, canonical_json_bytes, load,
    select_analysis, serialize, serialize_preparation_request, serialize_request,
    serialize_view_request,
)
from rdam._strict import JsonValue
from rdam.dung import DungProvider
from rdam.ibis import IbisProvider
from rdam.pdtb import PdtbProvider
from rdam.rst.provider import ERST_GRAPH, RST_TREE, RstProvider
from rdam.sdrt import SdrtProvider
from rdam.serialization import schema, schema_models
from rdam.toulmin import ToulminProvider
from rdam.walton import WaltonProvider

type SchemaMode = Literal["validation", "serialization"]

HISTORICAL = Path(__file__).parent / "fixtures" / "historical"
MODEL = "openai:gpt-5.6-sol"
SOURCE = "Dark clouds are visible. Rain is likely. Dark clouds often precede rain."


def _validator(name: str, mode: SchemaMode) -> Validator:
    document = schema(name, mode=mode)
    Draft202012Validator.check_schema(document)
    return Draft202012Validator(document)


def _validate(name: str, payload: bytes, mode: SchemaMode) -> None:
    _validator(name, mode).validate(json.loads(payload))


def _proposing(proposal: Mapping[str, JsonValue]) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        del messages
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=dict(proposal))])
    return FunctionModel(respond)


def _proposal(technique: Technique, minimal: bool) -> tuple[str, Mapping[str, JsonValue]]:
    evidence_start = SOURCE.index("Dark clouds often precede rain.")
    if technique is Technique.PDTB:
        return "Rain so traffic", {"relations": [] if minimal else [{
            "relation_id": "r1", "relation_type": "Explicit",
            "arg1": {"spans": [{"start": 0, "end": 4, "text": "Rain"}]},
            "arg2": {"spans": [{"start": 8, "end": 15, "text": "traffic"}]},
            "senses": ["Contingency.Cause.Result"],
            "connective_spans": [{"start": 5, "end": 7, "text": "so"}],
        }]}
    if technique is Technique.SDRT:
        return ("One." if minimal else "One. Two."), {
            "edus": [{"unit_id": "e1", "text": "One.", "start": 0, "end": 4}] + (
                [] if minimal else [{"unit_id": "e2", "text": "Two.", "start": 5, "end": 9}]),
            "relations": [] if minimal else [{"relation_id": "r1", "source_id": "e1", "target_id": "e2",
                                              "label": "Narration", "structural_type": "coordinating"}],
        }
    if technique is Technique.TOULMIN:
        return SOURCE, {"layouts": [] if minimal else [{
            "claim": "Rain is likely.", "grounds": ["Dark clouds are visible."],
            "warrant": "Dark clouds often precede rain.", "warrant_origin": "explicit",
            "warrant_evidence": [{"start": evidence_start, "end": len(SOURCE), "text": SOURCE[evidence_start:]}],
            "warrant_origin_reason": None, "qualifier": "likely",
        }]}
    assert technique is Technique.WALTON
    return SOURCE, {"instances": [] if minimal else [{
        "scheme_id": "sign", "conclusion": "Rain is likely.",
        "premises": {"finding": "Dark clouds are visible.", "indicated": "Rain is likely."},
        "critical_questions": [
            {"index": 0, "status": "addressed", "note": "The passage gives the general sign relation.",
             "evidence": [{"start": evidence_start, "end": len(SOURCE), "text": SOURCE[evidence_start:]}]},
            {"index": 1, "status": "not_assessable", "reason": "insufficient_context"},
        ],
    }]}


@pytest.mark.parametrize("mode", ("validation", "serialization"))
@pytest.mark.parametrize("name", tuple(schema_models()))
def test_every_registered_schema_is_valid_draft_2020_12(name: str, mode: SchemaMode) -> None:
    document = schema(name, mode=mode)
    Draft202012Validator.check_schema(document)
    assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert str(document["$id"]).endswith(f"/{mode}.schema.json")


@pytest.mark.parametrize("mode", ("validation", "serialization"))
@pytest.mark.parametrize("technique", (Technique.DUNG, Technique.IBIS))
@pytest.mark.parametrize("derived", (False, True))
def test_structural_provider_payloads_match_advertised_outputs(
    mode: SchemaMode, technique: Technique, derived: bool,
) -> None:
    provider = DungProvider() if technique is Technique.DUNG else IbisProvider()
    payload: Mapping[str, JsonValue] = (
        {"arguments": ["a"], "attacks": [["a", "a"]]} if technique is Technique.DUNG else
        {"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}], "links": []}
    )
    source = SourceIdentity.from_bytes(canonical_json_bytes(payload), media_type="application/json")
    supplied = provider.analyse(ProviderRequest(source=source, text=None, structured_input=payload))
    assert supplied.semantic_digest is not None
    reference = UpstreamResultReference(technique=technique, result_identity=supplied.semantic_digest)
    result = provider.analyse(ProviderRequest(
        source=source, text=None, structured_input=payload, derived_from=reference if derived else None,
    ))
    _validate(f"{technique.value}-result", canonical_json_bytes(result.payload), mode)
    _validate("native-result", serialize(result), mode)
    output = schema_models()[f"{technique.value}-result"].model_validate_json(canonical_json_bytes(result.payload))
    assert canonical_json_bytes(output) == canonical_json_bytes(result.payload)


@pytest.mark.parametrize("mode", ("validation", "serialization"))
@pytest.mark.parametrize("technique", (Technique.PDTB, Technique.SDRT, Technique.TOULMIN, Technique.WALTON))
@pytest.mark.parametrize("minimal", (False, True))
def test_llm_provider_outputs_and_current_records_match_schemas(
    monkeypatch: pytest.MonkeyPatch, mode: SchemaMode, technique: Technique, minimal: bool,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    provider = {Technique.PDTB: PdtbProvider, Technique.SDRT: SdrtProvider,
                Technique.TOULMIN: ToulminProvider, Technique.WALTON: WaltonProvider}[technique](model=MODEL)
    machine = Machine((provider,))
    text, proposal = _proposal(technique, minimal)
    request = AggregateRequest.for_text(text, (technique,))
    preparation_request = PreparationRequest.for_text(text, (technique,))
    @asynccontextmanager
    async def external_model(model: str, *, timeout_seconds: float) -> AsyncGenerator[FunctionModel]:
        assert model == MODEL
        assert timeout_seconds > 0
        yield _proposing(proposal)

    monkeypatch.setattr("rdam._llm._model_without_implicit_retries", external_model)
    aggregate = machine.analyse(request)
    assert aggregate.status == "complete"
    outcome = aggregate.outcome_for(technique)
    assert isinstance(outcome, ResultOutcome)
    native = outcome.result
    _validate(f"{technique.value}-result", canonical_json_bytes(native.payload), mode)
    output = schema_models()[f"{technique.value}-result"].model_validate_json(canonical_json_bytes(native.payload))
    assert canonical_json_bytes(output) == canonical_json_bytes(native.payload)
    _validate("native-result", serialize(native), mode)
    _validate("aggregate", serialize(aggregate), mode)
    _validate("request", serialize_request(request), mode)
    _validate("preparation-request", serialize_preparation_request(preparation_request), mode)
    assert aggregate.preparation is not None
    _validate("preparation", serialize(aggregate.preparation), mode)
    view = select_analysis(aggregate, techniques=(technique,))
    _validate("analysis-view", serialize(view), mode)
    _validate("view-request", serialize_view_request(ViewRequest(analysis=aggregate, techniques=(technique,))), mode)
    _validate("capabilities", serialize(machine.capabilities()), mode)


@pytest.mark.parametrize("mode", ("validation", "serialization"))
@pytest.mark.parametrize("name", ("aggregate-v1", "toulmin-v1", "walton-omitted-v1", "walton-partial-v1"))
def test_saved_historical_records_match_their_advertised_schemas(name: str, mode: SchemaMode) -> None:
    payload = (HISTORICAL / f"{name}.json").read_bytes().removesuffix(b"\n")
    record = load(payload)
    assert serialize(record) == payload
    _validate("aggregate-v1" if name == "aggregate-v1" else "native-result-v1", payload, mode)
    document = json.loads(payload)
    native_records = [item["result"] for item in document["outcomes"]] if name == "aggregate-v1" else [document]
    for native in native_records:
        _validate(f"{native['technique']}-result-v1", canonical_json_bytes(native["payload"]), mode)


@pytest.mark.parametrize("mode", ("validation", "serialization"))
@pytest.mark.parametrize("state", ("complete", "partial", "unsuccessful", "unavailable"))
def test_aggregate_and_selected_view_schemas_cover_every_outcome_kind(state: str, mode: SchemaMode) -> None:
    if state == "unavailable":
        request = AggregateRequest.for_text("No supplied framework.", (Technique.DUNG, Technique.IBIS))
    else:
        request = AggregateRequest.for_structured((
            StructuredInput(technique=Technique.DUNG, payload={
                "arguments": ["a"], "attacks": [] if state == "complete" else [["a", "missing"]],
            }),
            StructuredInput(technique=Technique.IBIS, payload={
                "nodes": [{"id": "q", "kind": "invalid" if state == "unsuccessful" else "issue", "text": "Why?"}],
                "links": [],
            }),
        ))
    aggregate = Machine((DungProvider(), IbisProvider())).analyse(request)
    assert aggregate.status == ("unsuccessful" if state == "unavailable" else state)
    if state == "unavailable":
        assert all(outcome.kind == "unavailable" for outcome in aggregate.outcomes)
    _validate("request", serialize_request(request), mode)
    _validate("aggregate", serialize(aggregate), mode)
    selection = (Technique.IBIS,)
    _validate("analysis-view", serialize(select_analysis(aggregate, techniques=selection)), mode)
    _validate("view-request", serialize_view_request(ViewRequest(analysis=aggregate, techniques=selection)), mode)


@pytest.fixture(scope="module")
def real_rst_aggregate() -> AggregateAnalysis:
    machine = Machine((RstProvider(device="cpu"),))
    aggregate = machine.analyse(AggregateRequest.for_text(
        "The cat sat on the mat. It was a black cat. The mat was red.", (Technique.RST,),
        formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=RST_TREE),),
    ))
    assert aggregate.status == "complete"
    return aggregate


@pytest.mark.slow
@pytest.mark.parametrize("mode", ("validation", "serialization"))
def test_real_rst_output_matches_schema(real_rst_aggregate: AggregateAnalysis, mode: SchemaMode) -> None:
    outcome = real_rst_aggregate.outcome_for(Technique.RST)
    assert isinstance(outcome, ResultOutcome)
    _validate("rst-result", canonical_json_bytes(outcome.result.payload), mode)
    _validate("aggregate", serialize(real_rst_aggregate), mode)


@pytest.mark.slow
@pytest.mark.parametrize("mode", ("validation", "serialization"))
def test_erst_schema_does_not_accept_an_rst_tree(real_rst_aggregate: AggregateAnalysis, mode: SchemaMode) -> None:
    outcome = real_rst_aggregate.outcome_for(Technique.RST)
    assert isinstance(outcome, ResultOutcome)
    payload = canonical_json_bytes(outcome.result.payload)
    with pytest.raises(ValueError):
        schema_models()["erst-result"].model_validate_json(payload)
    assert not _validator("erst-result", mode).is_valid(json.loads(payload))


@pytest.mark.slow
@pytest.mark.parametrize("mode", ("validation", "serialization"))
def test_real_erst_output_matches_schema_when_checkpoint_is_available(mode: SchemaMode) -> None:
    provider = RstProvider(device="cpu")
    formalism = provider.declaration.formalism(ERST_GRAPH)
    assert formalism is not None
    if not isinstance(formalism.capability, AvailableCapability):
        pytest.skip("a validated eRST checkpoint is not available in this checkout")
    aggregate = Machine((provider,)).analyse(AggregateRequest.for_text(
        "The cat sat on the mat. It was a black cat.", (Technique.RST,),
        formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=ERST_GRAPH),),
    ))
    outcome = aggregate.outcome_for(Technique.RST)
    assert isinstance(outcome, ResultOutcome)
    _validate("erst-result", canonical_json_bytes(outcome.result.payload), mode)
