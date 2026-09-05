"""Exact transport parity over real preparation and native deterministic providers.

These checks make no live-model quality claim. RST/eRST inference and source
grounding by the four LLM techniques require their separate model-backed checks.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from typing import cast
from unittest.mock import patch

from openai.resources.responses import AsyncResponses
from openai.types.responses import Response
from pydantic_ai import models
import pytest

from rdam import (
    AggregateRequest, FailedOutcome, FormalismChoice, Machine, PreparationRequest, ResultOutcome,
    StructuredInput, Technique, UnavailableOutcome, ViewRequest, production_machine,
    select_analysis, serialize, serialize_preparation_request, serialize_request,
    serialize_view_request, summarise,
)
from rdam.configuration import LlmSettings, LocalRstModel, MachineConfig, RstSettings
from rdam.contracts import outcome_technique
from rdam.frameworks import BOUNDARY_TECHNIQUES
from rdam.ingest.contracts.source import SourceForm
from rdam.serialization import serialize_config
from rdam._strict import JsonValue
from tests.ingest.test_inventory_completeness import source_case
from tests.interfaces.test_cli import run_cli
from tests.interfaces.test_http import assert_json, running_server
from tests.pdtb.test_provider import TEXT as PDTB_SOURCE, VALID_ANALYSIS
from tests.sdrt.test_provider import TEXT as SDRT_SOURCE, VALID_GRAPH
from tests.toulmin.test_provider import SOURCE_TEXT as TOULMIN_SOURCE, VALID_LAYOUT
from tests.walton.test_provider import SOURCE_TEXT as WALTON_SOURCE, VALID_INSTANCE


@pytest.fixture
def configured_machine(tmp_path: Path) -> tuple[Machine, Path]:
    config = MachineConfig(
        llm=LlmSettings(model="openai:parity-unused"),
        rst=RstSettings(model=LocalRstModel(store=tmp_path / "no-models", release_id="absent")),
    )
    path = tmp_path / "configuration.json"
    path.write_bytes(serialize_config(config))
    return production_machine(config=config), path


@pytest.mark.parametrize("form", tuple(SourceForm))
def test_every_source_form_and_boundary_preparation_has_exact_three_interface_parity(
    form: SourceForm, configured_machine: tuple[Machine, Path],
) -> None:
    machine, config = configured_machine
    artifact, expected_inventory = source_case(form)
    if artifact.edus is not None:
        request = PreparationRequest.for_edus(artifact.edus, BOUNDARY_TECHNIQUES, source_name=artifact.source_name)
    else:
        assert artifact.raw_bytes is not None
        request = PreparationRequest.for_bytes(artifact.raw_bytes, form, artifact.source_name, BOUNDARY_TECHNIQUES)
    expected = machine.prepare(request)
    assert {item.item_id for item in expected.preparation.inventory} == expected_inventory
    assert tuple(binding.technique for binding in expected.bindings) == BOUNDARY_TECHNIQUES
    assert expected.preparation.source.source_form is form
    body = serialize_preparation_request(request)
    cli = run_cli("prepare", "--request", "-", "--config", str(config), input_bytes=body)
    assert cli.returncode == 0 and cli.stderr == b""
    assert cli.stdout == serialize(expected) + b"\n"
    with running_server(machine) as server:
        http = server.post("/v1/prepare", body)
    assert_json(http, 200)
    assert http.body == serialize(expected)


def test_all_seven_production_declarations_have_exact_discovery_parity(configured_machine: tuple[Machine, Path]) -> None:
    machine, config = configured_machine
    expected = machine.capabilities()
    assert tuple(item.technique for item in expected.techniques) == BOUNDARY_TECHNIQUES
    cli = run_cli("capabilities", "--config", str(config))
    assert cli.returncode == 0 and cli.stderr == b""
    assert cli.stdout == serialize(expected) + b"\n"
    with running_server(machine) as server:
        http = server.request("GET", "/v1/capabilities")
    assert_json(http, 200)
    assert http.body == serialize(expected)


@pytest.mark.parametrize("mixed", (False, True))
@pytest.mark.parametrize("dung_state", ("valid", "malformed", "missing"))
def test_real_native_analysis_view_and_summary_agree_across_all_interfaces(
    mixed: bool, dung_state: str, configured_machine: tuple[Machine, Path], tmp_path: Path,
) -> None:
    machine, config = configured_machine
    structures = [StructuredInput(technique=Technique.IBIS,
        payload={"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}], "links": []})]
    if dung_state != "missing":
        structures.append(StructuredInput(technique=Technique.DUNG,
            payload={"arguments": ["a"], "attacks": [["a", "missing" if dung_state == "malformed" else "a"]]}))
    techniques = (Technique.IBIS, Technique.DUNG)
    if mixed:
        source = PreparationRequest.for_text("Éva asks why. No prose-derived structures are authorised.")
        request = AggregateRequest(source=source.source, text=source.text, source_artifact=source.source_artifact,
                                   techniques=techniques, structured_inputs=tuple(structures))
    else:
        request = AggregateRequest.for_structured(tuple(structures), techniques=techniques)
    expected = machine.analyse(request)
    assert tuple(outcome_technique(outcome) for outcome in expected.outcomes) == techniques
    assert isinstance(expected.outcome_for(Technique.IBIS), ResultOutcome)
    dung = expected.outcome_for(Technique.DUNG)
    if dung_state == "valid":
        assert isinstance(dung, ResultOutcome)
    elif dung_state == "malformed":
        assert isinstance(dung, FailedOutcome)
    else:
        assert isinstance(dung, UnavailableOutcome)
    status = 0 if dung_state == "valid" else 3
    assert expected.status == ("complete" if status == 0 else "partial")
    body = serialize_request(request)
    cli = run_cli("analyse", "--request", "-", "--config", str(config), input_bytes=body)
    assert cli.returncode == status and cli.stderr == b""
    saved_bytes = serialize(expected)
    assert cli.stdout == saved_bytes + b"\n"
    saved = tmp_path / "analysis.json"
    saved.write_bytes(saved_bytes)
    view = select_analysis(expected, techniques=(Technique.DUNG, Technique.IBIS))
    view_cli = run_cli("view", str(saved), "--techniques", "dung,ibis")
    assert view_cli.returncode == 0 and view_cli.stderr == b""
    assert view_cli.stdout == serialize(view) + b"\n"
    summary = (summarise(expected) + "\n").encode("utf-8")
    summary_cli = run_cli("summary", str(saved))
    assert summary_cli.returncode == 0 and summary_cli.stderr == b""
    assert summary_cli.stdout == summary
    with running_server(machine) as server:
        http = server.post("/v1/analyse", body)
        view_http = server.post("/v1/view", serialize_view_request(ViewRequest(analysis=expected, techniques=(Technique.DUNG, Technique.IBIS))))
        summary_http = server.post("/v1/summary", saved_bytes)
    assert_json(http, 200)
    assert http.body == saved_bytes
    assert_json(view_http, 200)
    assert view_http.body == serialize(view)
    assert summary_http.status == 200 and summary_http.body == summary


def model_case(technique: Technique) -> tuple[str, dict[str, JsonValue]]:
    """Reuse the native suites' authored proposals; they are not model-quality evidence."""
    cases: dict[Technique, tuple[str, object]] = {
        Technique.PDTB: (PDTB_SOURCE, VALID_ANALYSIS),
        Technique.SDRT: (SDRT_SOURCE, VALID_GRAPH),
        Technique.TOULMIN: (TOULMIN_SOURCE, {"layouts": [VALID_LAYOUT]}),
        Technique.WALTON: (WALTON_SOURCE, {"instances": [VALID_INSTANCE]}),
    }
    source, proposal = cases[technique]
    return source, cast(dict[str, JsonValue], proposal)


@contextmanager
def fixed_model_responses() -> Generator[list[Technique]]:
    """Substitute only the external Responses call, leaving provider and schema execution real."""
    calls: list[Technique] = []

    async def create_response(_client: object, **options: object) -> Response:
        model = options["model"]
        assert isinstance(model, str) and model.startswith("parity-")
        technique = Technique(model.removeprefix("parity-"))
        _, proposal = model_case(technique)
        tools = options["tools"]
        assert isinstance(tools, list)
        declared_tools = cast(list[object], tools)
        assert len(declared_tools) == 1
        tool = cast(Mapping[str, object], declared_tools[0])
        assert tool["type"] == "function" and isinstance(tool["name"], str)
        assert options["input"], "the external model must receive the actual source"
        calls.append(technique)
        return Response.model_validate({
            "id": "resp_parity", "object": "response", "created_at": 0, "status": "completed",
            "model": model, "parallel_tool_calls": False, "tool_choice": "auto", "tools": [],
            "output": [{"type": "function_call", "id": "fc_parity", "call_id": "call_parity",
                        "status": "completed", "name": tool["name"], "arguments": json.dumps(proposal)}],
        })

    with patch.object(AsyncResponses, "create", create_response), patch.object(models, "ALLOW_MODEL_REQUESTS", True):
        yield calls


@pytest.mark.parametrize("technique", (Technique.PDTB, Technique.SDRT, Technique.TOULMIN, Technique.WALTON))
@pytest.mark.parametrize("wrong_source", (False, True))
def test_corrected_llm_native_results_and_source_validation_have_exact_transport_parity(
    technique: Technique, wrong_source: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-external-response-only")
    config = MachineConfig(llm=LlmSettings(model=f"openai:parity-{technique.value}", output_retries=0, transport_retries=0))
    path = tmp_path / "configuration.json"
    path.write_bytes(serialize_config(config))
    source, _ = model_case(technique)
    request = AggregateRequest.for_text(("X" + source[1:]) if wrong_source else source, (technique,))
    body = serialize_request(request)
    machine = production_machine(config=config)
    with fixed_model_responses() as calls:
        expected = machine.analyse(request)
        outcome = expected.outcome_for(technique)
        if wrong_source:
            assert isinstance(outcome, FailedOutcome)
            assert outcome.failure.code == "llm_output_failed_validation"
            assert expected.status == "unsuccessful"
        else:
            assert isinstance(outcome, ResultOutcome), expected.model_dump_json()
            assert outcome.result.contract_version == "2.0.0"
            assert outcome.result.source_alignment
            assert expected.status == "complete"
        with running_server(machine) as server:
            http = server.post("/v1/analyse", body)
            view = select_analysis(expected, techniques=(technique,))
            view_http = server.post("/v1/view", serialize_view_request(ViewRequest(analysis=expected, techniques=(technique,))))
        assert calls == [technique, technique]
    assert_json(http, 200)
    assert http.body == serialize(expected)
    assert_json(view_http, 200)
    assert view_http.body == serialize(view)
    saved = tmp_path / "analysis.json"
    saved.write_bytes(serialize(expected))
    view_cli = run_cli("view", str(saved), "--techniques", technique.value)
    assert view_cli.returncode == 0 and view_cli.stderr == b""
    assert view_cli.stdout == serialize(view) + b"\n"
    script = """
import sys
from rdam.cli import main
from tests.interfaces.test_parity import fixed_model_responses
with fixed_model_responses() as calls:
    status = main(sys.argv[1:])
    assert len(calls) == 1, calls
raise SystemExit(status)
"""
    cli = subprocess.run([sys.executable, "-c", script, "analyse", "--request", "-", "--config", str(path)],
                         input=body, capture_output=True, check=False, timeout=30)
    assert cli.returncode == (4 if wrong_source else 0), cli.stderr
    assert cli.stderr == b""
    assert cli.stdout == serialize(expected) + b"\n"


@pytest.mark.parametrize("formalism", ("rst_tree", "erst_graph"))
def test_missing_rst_artifacts_preserve_requested_boundary_and_unavailable_status(
    formalism: str, configured_machine: tuple[Machine, Path],
) -> None:
    machine, config = configured_machine
    request = AggregateRequest.for_text("First. Second.", (Technique.RST,),
        formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=formalism),))
    expected = machine.analyse(request)
    assert expected.requested_techniques == (Technique.RST,)
    assert expected.status == "unsuccessful"
    assert isinstance(expected.outcome_for(Technique.RST), UnavailableOutcome)
    body = serialize_request(request)
    cli = run_cli("analyse", "--request", "-", "--config", str(config), input_bytes=body)
    assert cli.returncode == 4 and cli.stderr == b""
    assert cli.stdout == serialize(expected) + b"\n"
    with running_server(machine) as server:
        http = server.post("/v1/analyse", body)
    assert_json(http, 200)
    assert http.body == serialize(expected)


def test_retained_native_success_never_improves_requested_status(configured_machine: tuple[Machine, Path]) -> None:
    machine, config = configured_machine
    source = "No new structured graph was supplied."
    seed = AggregateRequest.for_text(source, (Technique.IBIS,), structured_inputs=(StructuredInput(
        technique=Technique.IBIS, payload={"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}], "links": []}),))
    retained = machine.analyse(seed).outcome_for(Technique.IBIS)
    assert isinstance(retained, ResultOutcome)
    request = AggregateRequest.for_text(source, (Technique.DUNG,), upstream_results=(retained.result,))
    expected = machine.analyse(request)
    assert expected.status == "unsuccessful"
    assert expected.upstream_results == (retained.result,)
    assert isinstance(expected.outcome_for(Technique.DUNG), UnavailableOutcome)
    body = serialize_request(request)
    cli = run_cli("analyse", "--request", "-", "--config", str(config), input_bytes=body)
    assert cli.returncode == 4 and cli.stderr == b""
    assert cli.stdout == serialize(expected) + b"\n"
    with running_server(machine) as server:
        http = server.post("/v1/analyse", body)
    assert_json(http, 200)
    assert http.body == serialize(expected)
