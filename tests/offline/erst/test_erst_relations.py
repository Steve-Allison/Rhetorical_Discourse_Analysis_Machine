"""Train-derived raw relation inventory and dataset label tests."""

from pathlib import Path
import torch
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from tokenizers.processors import TemplateProcessing
from transformers import PreTrainedTokenizerFast

from rdam.rst.contracts.analysis import RstAnalysis, SecondaryRelationEdge
from rdam.rst.contracts.enums import OutputFormalismEnum
from workbench.erst.contracts import RawRelationInventory
from rdam.rst.contracts.serialization import analysis_from_json, to_json
from workbench.erst.candidates import SecondaryEdgeCandidate
from workbench.erst.relations import resolve_gum_relation_concept
from workbench.corpus.erst.relations import build_raw_relation_inventory
from workbench.training.erst.dataset import GUMSecondaryEdgeDataset

_TRACKED_INVENTORY = (
    Path(__file__).resolve().parents[3] / "config" / "erst" / "gum-v12.1.0-raw-relations.json"
)


def _local_tokenizer() -> PreTrainedTokenizerFast:
    vocabulary = {"[PAD]": 0, "[UNK]": 1, "[CLS]": 2, "[SEP]": 3, "left": 4, "right": 5}
    backend = Tokenizer(WordLevel(vocab=vocabulary, unk_token="[UNK]"))
    backend.pre_tokenizer = Whitespace()
    backend.post_processor = TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=(("[CLS]", 2), ("[SEP]", 3)),
    )
    return PreTrainedTokenizerFast(
        tokenizer_object=backend, unk_token="[UNK]", pad_token="[PAD]", cls_token="[CLS]", sep_token="[SEP]",
    )


def test_tracked_train_inventory_is_hash_valid_and_raw_to_concept_complete() -> None:
    inventory = RawRelationInventory.model_validate_json(_TRACKED_INVENTORY.read_text(encoding="utf-8"))
    assert inventory.partition.value == "train"
    assert len(inventory.labels) == 27
    assert inventory.edge_count == 1082
    assert inventory.inventory_sha256 == "574e4aa2c1739adca7a4b90aa62158f99783c4946000c5ef1be57c7e923fa3ce"
    assert inventory.concept_by_raw["adversative-contrast"] == "Contrast"
    assert inventory.concept_by_raw["mode-means"] == "Manner-Means"


def test_inventory_builder_uses_raw_labels_and_canonical_concepts() -> None:
    inventory = build_raw_relation_inventory(
        {"elaboration-additional": 2, "adversative-contrast": 1},
        corpus_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
        source_fingerprint="a" * 64,
    )
    assert inventory.labels == ("adversative-contrast", "elaboration-additional")
    assert inventory.concept_by_raw == {
        "adversative-contrast": "Contrast",
        "elaboration-additional": "Elaboration",
    }
    assert resolve_gum_relation_concept("adversative-contrast") == "Contrast"


def test_dataset_classifies_positive_edges_by_raw_train_label() -> None:
    candidate = SecondaryEdgeCandidate(
        document_id="raw-label-test",
        source_id=1,
        target_id=2,
        source_text="left",
        target_text="right",
        source_char_span=(0, 4),
        target_char_span=(5, 10),
        structural_features=(0.0,) * 9,
        is_gold_edge=True,
        gold_relation="adversative-contrast",
        gold_concept="Contrast",
        signal_ids=("sig",),
    )
    dataset = GUMSecondaryEdgeDataset(
        (candidate,),
        tokenizer=_local_tokenizer(),
        raw_relation_inventory=("elaboration-additional", "adversative-contrast"),
    )
    item = dataset[0]
    assert item["rel_label"].item() == 1
    assert item["src_special_tokens_mask"].equal(torch.tensor([1, 0, 1]))
    assert item["src_input_ids"].equal(torch.tensor([2, 4, 3]))
    assert item["tgt_input_ids"].equal(torch.tensor([2, 5, 3]))
    assert item["src_offset_mapping"].equal(torch.tensor([[0, 0], [0, 4], [0, 0]]))
    assert item["tgt_offset_mapping"].equal(torch.tensor([[0, 0], [0, 5], [0, 0]]))


def test_raw_relation_and_ontology_concept_survive_analysis_json_round_trip() -> None:
    analysis = RstAnalysis(
        document_id="raw-relation-round-trip",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(),
        primary_edges=(),
        secondary_edges=(
            SecondaryRelationEdge(
                edge_id="secondary-1-2",
                source_id=1,
                target_id=2,
                relation_raw="adversative-contrast",
                relation_concept="Contrast",
                confidence=0.91,
                calibrated=True,
            ),
        ),
    )

    restored = analysis_from_json(to_json(analysis))

    assert restored.secondary_edges[0].relation_raw == "adversative-contrast"
    assert restored.secondary_edges[0].relation_concept == "Contrast"
