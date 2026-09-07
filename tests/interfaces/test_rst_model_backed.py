"""Real CPU parity using published RST weights."""

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
from rdam.ingest.contracts.inference import OutputFormalism
from workbench.erst.converter import rs4_to_document_and_analysis
from workbench.erst.rs4 import RS4Reader
from rdam.serialization import serialize_config
from rdam.summary import summarise
from tests.interfaces.test_http import assert_json, running_server

pytestmark = pytest.mark.slow

GUM_REAL_DOCUMENT = Path(__file__).resolve().parents[1] / "fixtures/gum/GUM_bio_dvorak.rs4"


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
    assert produced.semantic.erst_completion is None
    return native


@pytest.mark.parametrize("formalism", (OutputFormalism.RST_TREE,))
def test_published_cpu_rst_has_python_cli_http_successful_inference_parity(
    tmp_path: Path, formalism: OutputFormalism,
) -> None:
    config = MachineConfig(rst=RstSettings(
        model=LocalRstModel(store=Path.home() / ".cache/isanlp_rst/model-releases", release_id="gumrrg-eb1d5745f3a1"),
        device="cpu",
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


def test_real_gum_document_produces_a_complete_ai_ready_rst_report() -> None:
    rs4 = RS4Reader().read_file(GUM_REAL_DOCUMENT)
    gold_document, _gold_analysis = rs4_to_document_and_analysis(rs4, document_id="GUM_bio_dvorak")
    assert gold_document.edus is not None
    assert len(gold_document.edus) == 71

    config = MachineConfig(rst=RstSettings(
        model=LocalRstModel(
            store=Path.home() / ".cache/isanlp_rst/model-releases",
            release_id="gumrrg-eb1d5745f3a1",
        ),
        device="cpu",
    ))
    request = AggregateRequest.for_text(
        gold_document.text,
        (Technique.RST,),
        source_name="GUM_bio_dvorak",
        formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=OutputFormalism.RST_TREE.value),),
    )
    aggregate = production_machine(config=config).analyse(request)
    native = assert_actual_cpu_result(aggregate, OutputFormalism.RST_TREE)
    produced = load_contract(canonical_json_bytes(native.payload))
    assert isinstance(produced, AnalysedOutcome)
    assert produced.semantic.analysed_document is not None
    assert produced.semantic.analysed_document.text == gold_document.text
    assert produced.semantic.validation is not None and produced.semantic.validation.passed

    assert produced.semantic.primary_inference is not None
    assert produced.semantic.primary_inference.refinements == ()
    assert produced.semantic.analysis is not None
    markers = tuple(signal for signal in produced.semantic.analysis.signals if signal.detector.detector_id == "isanlp_rst.marker_primer")
    assert markers
    assert len({signal.char_spans for signal in markers}) == len(markers)
    anchors = {anchor.target_id: anchor for anchor in produced.semantic.anchors}
    for signal in markers:
        assert signal.token_ids and signal.confidence is None and not signal.sufficient
        assert tuple(f"token:{token_id:06d}" for token_id in signal.token_ids) == anchors[signal.signal_id].token_ids

    guide = aggregate.reading_guide.entries[0].descriptor
    assert guide is not None
    guidance = " ".join(
        (
            guide.purpose,
            *(section.meaning for section in guide.sections),
            *guide.evidence_rules,
            *guide.limitations,
        )
    ).lower()
    assert "proposition-scale" in guidance
    assert "recursive salience" in guidance
    assert "relation labels as hypotheses" in guidance
    assert "must not be promoted to argument structure" in guidance

    encoded = serialize(aggregate)
    assert serialize(load(encoded)) == encoded
    summary = summarise(aggregate)
    assert "rst: result; formalism=rst_tree; provider=rdam.rst/gumrrg" in summary
