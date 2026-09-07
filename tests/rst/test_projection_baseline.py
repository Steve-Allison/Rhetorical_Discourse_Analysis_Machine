"""Preserve historical model choices while repairing unsupported exported evidence."""

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from rdam import ProviderRequest, SourceIdentity, canonical_json_bytes, AggregateRequest, Machine, Technique, ExecutionPolicy
from rdam.rst.provider import RstProvider
from rdam.rst.parser import Parser
from rdam.ingest.identity import semantic_sha256
from rdam.ingest.historical import load_historical_contract
from rdam.ingest.contracts.graph import StoredRstGraph
from rdam.ingest.contracts.analysis import AnalysedDocument, AnalysedToken
from rdam.rst.contracts.analysis import RstNode
from tests.integration.test_production_smoke import STORE
from tools.production_boundary.rst_baseline import DifferenceClass, TEXT, diff_records


@pytest.mark.slow
def test_real_rst_projection_preserves_model_choices_and_repairs_evidence() -> None:
    release_id = "gumrrg-eb1d5745f3a1"
    if not (STORE / release_id).is_dir():
        pytest.skip("the recorded Feature 017 baseline release is not installed")
    provider = RstProvider(store=STORE, release_id=release_id, device="cpu")
    result = provider.analyse(ProviderRequest(
        source=SourceIdentity.from_text(TEXT, source_name="baseline.txt"),
        text=TEXT,
        structured_input=None,
    ))
    baseline = Path("specs/017-universal-source-pipeline/evidence/baseline-dmrst-current/analyse-text.json")
    baseline_bytes = baseline.read_bytes()
    historical = load_historical_contract(baseline_bytes)
    before = historical.payload["semantic"]["parser_result"]["semantic"]
    actual_bytes = canonical_json_bytes(result.payload)
    after = json.loads(actual_bytes)["semantic"]["parser_result"]["semantic"]

    # Scores and lexical overrides are intentionally different, not equivalent.
    differences = diff_records(baseline_bytes, actual_bytes)
    assert any(item.classification is DifferenceClass.ANALYTICAL for item in differences)
    assert before["primary_inference"]["refinements"]
    assert after["primary_inference"]["refinements"] == []

    assert before["analysed_document"]["text"] == after["analysed_document"]["text"]
    restored_document = AnalysedDocument.model_validate_json(json.dumps(after["analysed_document"]))
    assert before["analysed_document"]["edus"] == [
        edu.model_dump(mode="json", exclude={"character_range"}) for edu in restored_document.edus
    ]
    assert TypeAdapter(tuple[AnalysedToken, ...]).validate_json(
        json.dumps(before["analysed_document"]["tokens"]),
    ) == restored_document.tokens
    historical_nodes = TypeAdapter(tuple[RstNode, ...]).validate_json(json.dumps(before["analysis"]["nodes"]))
    restored_graph = StoredRstGraph.model_validate_json(json.dumps(after["analysis"])).resolve(
        after["analysed_document"]["text"],
    )
    assert historical_nodes == restored_graph.nodes
    old_model = before["composite_identity"]["primary_parser"]
    new_model = after["composite_identity"]["primary_parser"]
    assert {key: value for key, value in old_model.items() if key != "capacity_identity"} == {
        key: value for key, value in new_model.items() if key != "capacity_identity"
    }
    assert old_model["capacity_identity"] != new_model["capacity_identity"]
    assert new_model["capacity_identity"]["hex_digest"] == semantic_sha256(Parser.declared_analysis_capacity())
    assert Parser.declared_analysis_capacity().maximum is None

    old_decisions = before["primary_inference"]["structure_decisions"]
    new_decisions = after["primary_inference"]["structure_decisions"]
    assert len(old_decisions) == len(new_decisions) > 0
    old_by_node = {tuple(decision["node_ids"]): decision for decision in old_decisions}
    new_by_node = {tuple(decision["node_ids"]): decision for decision in new_decisions}
    assert len(old_by_node) == len(old_decisions)
    assert len(new_by_node) == len(new_decisions)
    assert old_by_node.keys() == new_by_node.keys()
    for node_ids, old in old_by_node.items():
        new = new_by_node[node_ids]
        for field in ("node_ids", "primary_edge_ids", "analysed_start", "analysed_end", "selected_split", "nuclearity"):
            assert old[field] == new[field], field
        assert old["relation"]["raw_label"] == new["relation"]["raw_label"]
        assert new["joint"] is not None

    old_edges = before["analysis"]["primary_edges"]
    new_edges = after["analysis"]["primary_edges"]
    assert [(edge["edge_id"], edge["parent_id"], edge["child_id"]) for edge in old_edges] == [
        (edge["edge_id"], edge["parent_id"], edge["child_id"]) for edge in new_edges
    ]
    assert all(not edge["calibrated"] for edge in new_edges)
    assert after["analysis"]["signals"]
    assert all(signal["token_ids"] and signal["confidence"] is None for signal in after["analysis"]["signals"])
    assert baseline.read_bytes() == baseline_bytes


@pytest.mark.slow
def test_real_rst_aggregate_semantics_do_not_include_execution_timing() -> None:
    provider = RstProvider(store=STORE, release_id="gumrrg-eb1d5745f3a1", device="cpu")
    request = AggregateRequest.for_text(TEXT, (Technique.RST,))
    first = Machine([provider], execution_policy=ExecutionPolicy(max_workers=1)).analyse(request)
    second = Machine([provider], execution_policy=ExecutionPolicy(max_workers=4)).analyse(request)
    assert first.semantic_digest == second.semantic_digest
