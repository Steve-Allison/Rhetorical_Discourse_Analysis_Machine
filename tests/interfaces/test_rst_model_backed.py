"""Real CPU parity using published RST weights and a configured native eRST bundle."""

from pathlib import Path
import subprocess
import sys

import pytest

from rdam import (
    AggregateAnalysis, AggregateRequest, FormalismChoice, NativeTechniqueResult,
    ResultOutcome, Technique, canonical_json_bytes, load, production_machine, serialize, serialize_request,
)
from rdam.configuration import LocalRstModel, MachineConfig, RstSettings
from rdam.ingest import load_contract
from rdam.ingest.contracts.analysis import AnalysedOutcome, CacheStatus
from rdam.ingest.contracts.inference import ErstDecision, OutputFormalism
from rdam.rst.erst.checkpoint import resolve_default_erst_checkpoint, validate_erst_checkpoint_bundle
from rdam.serialization import serialize_config
from tests.interfaces.test_http import assert_json, running_server

pytestmark = pytest.mark.slow


def assert_actual_cpu_result(aggregate: AggregateAnalysis, formalism: OutputFormalism) -> NativeTechniqueResult:
    assert aggregate.requested_techniques == (Technique.RST,)
    assert aggregate.status == "complete"
    outcome = aggregate.outcome_for(Technique.RST)
    assert isinstance(outcome, ResultOutcome), aggregate.model_dump_json()
    native = outcome.result
    assert native.technique is (Technique.RST if formalism is OutputFormalism.RST_TREE else Technique.ERST)
    assert native.formalism_id == formalism.value
    assert native.provenance.model_identity == "gumrrg-eb1d5745f3a1"
    produced = load_contract(canonical_json_bytes(native.payload))
    assert isinstance(produced, AnalysedOutcome)
    assert produced.execution.device == "cpu"
    assert produced.execution.cache_status is CacheStatus.BYPASS
    parsed = produced.semantic.parser_result
    assert parsed is not None
    assert parsed.loaded_component_receipts
    assert parsed.analysis.nodes and parsed.analysis.primary_edges
    assert parsed.analysis.formalism.value == formalism.value
    assert produced.semantic.primary_inference is not None
    assert produced.semantic.validation is not None and produced.semantic.validation.passed
    completion = produced.semantic.erst_completion
    if formalism is OutputFormalism.ERST_GRAPH:
        assert completion is not None
        assert parsed.semantic.erst_completion == completion
        assert completion.scorer_identity.state == "immutable_release"
        assert completion.calibration_identity.state == "immutable_release"
        assert completion.relation_inventory_identity.state == "immutable_release"
        assert completion.decode_receipt.input_count == len(completion.candidate_decisions)
        accepted_edges = {
            candidate.secondary_edge_id for candidate in completion.candidate_decisions
            if candidate.decision is ErstDecision.ACCEPTED
        }
        assert accepted_edges == {edge.edge_id for edge in parsed.analysis.secondary_edges}
        assert completion.decode_receipt.accepted_count == len(parsed.analysis.secondary_edges)
        assert {signal.signal_id for signal in completion.signals} <= {
            signal.signal_id for signal in parsed.analysis.signals
        }
    else:
        assert completion is None
    return native


@pytest.mark.parametrize("formalism", (OutputFormalism.RST_TREE, OutputFormalism.ERST_GRAPH))
def test_published_cpu_rst_has_python_cli_http_successful_inference_parity(
    tmp_path: Path, formalism: OutputFormalism,
) -> None:
    checkpoint = None
    if formalism is OutputFormalism.ERST_GRAPH:
        checkpoint = resolve_default_erst_checkpoint()
        if checkpoint is None:
            pytest.skip("native eRST resolver found no real completion bundle; successful eRST parity is unverified")
        validate_erst_checkpoint_bundle(checkpoint)
    config = MachineConfig(rst=RstSettings(
        model=LocalRstModel(store=Path.home() / ".cache/isanlp_rst/model-releases", release_id="gumrrg-eb1d5745f3a1"),
        device="cpu",
        erst_checkpoint=checkpoint,
    ))
    path = tmp_path / "configuration.json"
    path.write_bytes(serialize_config(config))
    request = AggregateRequest.for_text(
        "Because it rained, the match stopped. The crowd left.", (Technique.RST,),
        source_name="published-cpu-rst-parity",
        formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=formalism.value),),
    )
    body = serialize_request(request)
    machine = production_machine(config=config)
    expected = machine.analyse(request)
    expected_native = assert_actual_cpu_result(expected, formalism)

    cli = subprocess.run(
        [sys.executable, "-m", "rdam", "analyse", "--request", "-", "--config", str(path)],
        input=body, capture_output=True, check=False, timeout=180,
    )
    assert cli.returncode == 0, cli.stderr
    assert b"Traceback" not in cli.stderr
    cli_result = load(cli.stdout)
    assert isinstance(cli_result, AggregateAnalysis)
    assert cli.stdout == serialize(cli_result) + b"\n"

    with running_server(machine) as server:
        http = server.post("/v1/analyse", body)
    assert_json(http, 200)
    http_result = load(http.body)
    assert isinstance(http_result, AggregateAnalysis)
    assert http.body == serialize(http_result)

    for actual in (cli_result, http_result):
        native = assert_actual_cpu_result(actual, formalism)
        assert native.execution_fields == expected_native.execution_fields
        # The validated native digest binds every payload field except its declared
        # execution paths; the aggregate digest also binds all source/run context.
        assert native.semantic_digest == expected_native.semantic_digest
        assert actual.semantic_digest == expected.semantic_digest
        assert actual.preparation == expected.preparation
        assert actual.configurations == expected.configurations
        assert actual.reading_guide == expected.reading_guide
