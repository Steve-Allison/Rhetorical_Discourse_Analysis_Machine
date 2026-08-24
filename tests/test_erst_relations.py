"""Train-derived raw relation inventory and dataset label tests."""

from pathlib import Path
from typing import Any

import torch

from isanlp_rst.contracts.analysis import RstAnalysis, SecondaryRelationEdge
from isanlp_rst.contracts.enums import OutputFormalismEnum
from isanlp_rst.contracts.erst import RawRelationInventory
from isanlp_rst.contracts.serialization import analysis_from_json, to_json
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate
from isanlp_rst.erst.dataset import GUMSecondaryEdgeDataset
from isanlp_rst.erst.relations import build_raw_relation_inventory, resolve_gum_relation_concept

_TRACKED_INVENTORY = (
    Path(__file__).resolve().parents[1] / "config" / "erst" / "gum-v12.1.0-raw-relations.json"
)


class _FastTokenizerDouble:
    is_fast = True

    def __call__(self, text: str, **options: Any) -> dict[str, torch.Tensor]:
        del text
        assert options["return_special_tokens_mask"] is True
        assert options["return_offsets_mapping"] is True
        return {
            "input_ids": torch.tensor([[101, 10, 102, 0]]),
            "attention_mask": torch.tensor([[1, 1, 1, 0]]),
            "special_tokens_mask": torch.tensor([[1, 0, 1, 1]]),
            "offset_mapping": torch.tensor([[[0, 0], [0, 4], [0, 0], [0, 0]]]),
        }


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
        tokenizer=_FastTokenizerDouble(),
        raw_relation_inventory=("elaboration-additional", "adversative-contrast"),
    )
    item = dataset[0]
    assert item["rel_label"].item() == 1
    assert tuple(item["src_special_tokens_mask"].tolist()) == (1, 0, 1, 1)
    assert tuple(tuple(pair) for pair in item["src_offset_mapping"].tolist()) == (
        (0, 0),
        (0, 4),
        (0, 0),
        (0, 0),
    )


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
