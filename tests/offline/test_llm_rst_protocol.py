"""LLM comparison rejects malformed trees without inventing replacement parses."""

from hashlib import sha256
import json
from pathlib import Path

import pytest

from rdam.rst.contracts import OutputFormalismEnum, RstAnalysis, RstDocument
from workbench.evaluation.rst.llm_evaluation import decode_tree, score_generation
from workbench.evaluation.rst.llm_generation import JsonTreePrefix
from workbench.evaluation.rst.parseval import StandardParsevalScorer
from workbench.evaluation.rst.regression import evaluation_source_identities


INVENTORY = ("cause_SN", "joint_NN", "elaboration_NS")


def test_streaming_check_preserves_valid_output_at_every_chunk_boundary() -> None:
    response = ' [[1,3,1,"cause_SN"], [2,3,2,"joint_NN"]] \n'
    for boundary in range(len(response) + 1):
        prefix = JsonTreePrefix(3, INVENTORY)
        assert prefix.feed(response[:boundary]) is None
        assert prefix.feed(response[boundary:]) is None
        assert prefix.state == "closed"
    prefix = JsonTreePrefix(3, INVENTORY)
    for character in response:
        assert prefix.feed(character) is None
    assert prefix.state == "closed"


@pytest.mark.parametrize("response", (
    '```json', '[]', '[[1,3,1,"invented_SN"]',
    '[[true,3,1,"cause_SN"]', '[[1,3,1,"cause_SN"],[1,3,2,"joint_NN"]',
    '[[1,3,1,"cause_SN"],]',
    '[[1,3,1,"cause_SN"],[2,3,2,"joint_NN"]] extra',
))
def test_streaming_check_rejects_irrecoverable_prefixes(response: str) -> None:
    assert JsonTreePrefix(3, INVENTORY).feed(response) is not None


def test_incomplete_prefix_is_neither_rejected_nor_accepted() -> None:
    prefix = JsonTreePrefix(3, INVENTORY)
    assert prefix.feed('[[1,3,1,"cause') is None
    assert prefix.state != "closed"


@pytest.mark.parametrize("changed_field", ("fixture_sha256", "split"))
def test_scoring_rejects_response_provenance_substitution(tmp_path: Path, changed_field: str) -> None:
    # Invalid fixture bytes prove identity rejection happens before parsing/scoring.
    source = b"not a parsed evaluation fixture"
    (tmp_path / "example.rs4").write_bytes(source)
    manifest = b"{}"
    (tmp_path / "upstream-manifest.json").write_bytes(manifest)
    job = {"fixture_sha256": sha256(source).hexdigest(), "split": "test", "prompt": "source only"}
    jobs = {"evaluation_sources": evaluation_source_identities(),
            "upstream_manifest_sha256": sha256(manifest).hexdigest(),
            "joint_inventory": INVENTORY, "documents": {"example": job}}
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps(jobs))
    response = {**job, "prompt_sha256": sha256(job["prompt"].encode()).hexdigest()}
    response[changed_field] = "substituted"
    responses_path = tmp_path / "responses.json"
    responses_path.write_text(json.dumps({"status": "complete", "jobs_sha256": sha256(jobs_path.read_bytes()).hexdigest(),
                                          "documents": {"example": response}}))
    output = tmp_path / "result.json"
    with pytest.raises(ValueError, match="response fixture or split identity differs"):
        score_generation(tmp_path, jobs_path, responses_path, output)
    assert not output.exists()


def test_scoring_rejects_changed_evaluation_implementation(tmp_path: Path) -> None:
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps({"evaluation_sources": {}}))
    output = tmp_path / "result.json"
    with pytest.raises(ValueError, match="evaluation implementation changed"):
        score_generation(tmp_path, jobs_path, tmp_path / "absent-responses.json", output)
    assert not output.exists()


def test_protocol_reconstructs_exact_source_and_binary_nuclearity() -> None:
    document = RstDocument.from_edus(["It rained.", "The match stopped.", "The crowd left."], document_id="synthetic")
    prediction = decode_tree(document, [[1, 3, 1, "cause_SN"], [2, 3, 2, "joint_NN"]], INVENTORY)
    assert len(prediction.nodes) == 5
    assert len(prediction.primary_edges) == 4
    assert all(node.text == document.text[slice(*node.char_span)] for node in prediction.nodes)
    score = StandardParsevalScorer().score(prediction, prediction)
    assert score.matched_full == score.gold_spans_count == score.pred_spans_count == 2
    root = next(node for node in prediction.nodes if node.edu_span == (1, 3))
    edges = [edge for edge in prediction.primary_edges if edge.parent_id == root.node_id]
    assert [edge.relation_raw for edge in edges] == ["cause", "span"]
    assert all(edge.nuclearity.value == "SN" for edge in edges)


@pytest.mark.parametrize("response", (
    {}, [], [[1, 3, 1, "cause_SN"]],
    [[1, 3, 1, "cause_SN"], [1, 3, 2, "joint_NN"]],
    [[1, 3, 1, "cause_SN"], [1, 2, 1, "joint_NN"]],
    [[1, 3, 3, "cause_SN"], [2, 3, 2, "joint_NN"]],
    [[True, 3, 1, "cause_SN"], [2, 3, 2, "joint_NN"]],
    [[1, 3, 1, "invented_SN"], [2, 3, 2, "joint_NN"]],
    [[1, 3, 1, "cause_SN", "extra"], [2, 3, 2, "joint_NN"]],
))
def test_invalid_response_never_becomes_a_repaired_tree(response: object) -> None:
    document = RstDocument.from_edus(["One.", "Two.", "Three."], document_id="synthetic")
    with pytest.raises(ValueError):
        decode_tree(document, response, INVENTORY)


def test_missing_prediction_keeps_every_gold_attachment_in_denominator() -> None:
    document = RstDocument.from_edus(["One.", "Two.", "Three."], document_id="synthetic")
    gold = decode_tree(document, [[1, 3, 1, "cause_SN"], [2, 3, 2, "joint_NN"]], INVENTORY)
    empty = RstAnalysis(document_id=document.document_id, formalism=OutputFormalismEnum.RST_TREE, nodes=(), primary_edges=())
    score = StandardParsevalScorer().score(gold, empty)
    assert score.gold_spans_count == 2
    assert score.pred_spans_count == score.matched_full == 0


def test_single_edu_requires_no_invented_attachment() -> None:
    document = RstDocument.from_edus(["Only one."], document_id="synthetic")
    prediction = decode_tree(document, [], INVENTORY)
    assert len(prediction.nodes) == 1
    assert prediction.primary_edges == ()
