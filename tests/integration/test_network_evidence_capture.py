"""Published CPU models must expose scores without changing decoded outputs."""

from pathlib import Path

import pytest
import torch

from rdam.rst.inference_evidence import NetworkStructureDecision
from rdam.rst.parser import Parser
from rdam.rst.annotation_rst import DiscourseUnit, Exporter
from rdam.rst.dmrst_parser.predictor import PredictorDMRST
from rdam.rst.universal_parser.predictor import PredictorUniRST


@pytest.mark.slow
@pytest.mark.parametrize("release_id", ("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def test_network_capture_preserves_real_decoding(release_id: str) -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases",
        release_id,
        device="cpu",
    )
    predictor = parser.predictor
    texts = ("It rained. The match stopped. The crowd left.", "Birds sing.")
    input_ids = predictor.tokenizer(list(texts), add_special_tokens=False)["input_ids"]
    arguments = dict(
        input_sentence=input_ids,
        input_sent_breaks=None,
        input_entity_ids=None,
        input_entity_position_ids=None,
        input_edu_breaks=[[] for _ in texts],
        label_index=[[] for _ in texts],
        parsing_index=[[] for _ in texts],
        generate_tree=True,
        use_pred_segmentation=True,
    )
    if parser.family == "unirst":
        arguments["dataset_index"] = [predictor.relinventory_idx for _ in texts]
    captured: list[list[NetworkStructureDecision]] = []
    with torch.inference_mode():
        ordinary = predictor.model.testing_loss(**arguments)
        observed = predictor.model.testing_loss(**arguments, decision_traces=captured)
    assert ordinary[2:] == observed[2:]
    assert len(captured) == len(texts)
    assert [len(decisions) for decisions in captured] == [len(edus) - 1 for edus in observed[4]]
    assert [decision.selected_class for decisions in captured for decision in decisions] == observed[3][1]
    decisions = [decision for document in captured for decision in document]
    assert decisions
    for decision in decisions:
        probabilities = torch.tensor(decision.joint_log_probabilities).exp()
        torch.testing.assert_close(probabilities.sum(), torch.tensor(1.0))
        # The evidence contains the trained classifier's full joint inventory.
        assert all(label.rpartition("_")[2].upper() in {"NS", "SN", "NN"} for label in decision.joint_labels)
        assert len(set(decision.joint_log_probabilities)) > 2


@pytest.mark.slow
@pytest.mark.parametrize("release_id", ("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def test_predictor_retains_per_document_evidence(release_id: str) -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases",
        release_id,
        device="cpu",
    )
    predictor = parser.predictor
    assert isinstance(predictor, (PredictorDMRST, PredictorUniRST))
    texts = ("Hi", "It rained. The match stopped. The crowd left.", "Goodbye")
    ordinary = predictor.parse_rst_batch(texts)
    captured = predictor.parse_rst_batch(texts, capture_evidence=True)
    exporter = Exporter()
    for text, original, observed in zip(texts, ordinary, captured, strict=True):
        assert "network_decisions" not in original
        assert original["analysis_tokens"] == observed["analysis_tokens"]
        assert original["analysis_tokens"]
        assert all(text[token.start:token.end] == token.text for token in original["analysis_tokens"])
        original_tree = original["rst"][0]
        observed_tree = observed["rst"][0]
        assert isinstance(original_tree, DiscourseUnit)
        assert isinstance(observed_tree, DiscourseUnit)
        assert exporter.make_body(original_tree) == exporter.make_body(observed_tree)
    assert captured[0]["network_decisions"] == captured[2]["network_decisions"] == ()
    assert captured[1]["network_decisions"]

    edus = ("It rained.", "The match stopped.", "The crowd left.")
    predefined = predictor.parse_from_edus(edus, capture_evidence=True)
    assert all(
        " ".join(edus)[token.start:token.end] == token.text for token in predefined["analysis_tokens"]
    )
    decisions = predefined["network_decisions"]
    assert len(decisions) == len(edus) - 1
    assert all(isinstance(decision, NetworkStructureDecision) for decision in decisions)
    assert {(decision.start, decision.end) for decision in decisions} >= {(0, len(edus) - 1)}
    assert predictor.parse_from_edus(["Hello"], capture_evidence=True)["network_decisions"] == ()
    if isinstance(predictor, PredictorUniRST):
        custom = predictor.parse_rst("It rained.", tokens=["It", "rained", "."], capture_evidence=True)
        assert "network_decisions" in custom
        assert [(token.text, token.start, token.end) for token in custom["analysis_tokens"]] == [
            ("It", 0, 2), ("rained", 3, 9), (".", 9, 10),
        ]
