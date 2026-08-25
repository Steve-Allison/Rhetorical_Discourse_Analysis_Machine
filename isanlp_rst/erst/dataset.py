"""Dataset collation over the single complete eRST candidate generator."""

from collections.abc import Sequence
from typing import Any

import torch
from torch.utils.data import Dataset

from isanlp_rst.contracts.analysis import RstAnalysis
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.erst.candidates import (
    SecondaryEdgeCandidate,
    compute_structural_features,
    generate_secondary_edge_candidates,
)


COARSE_CONCEPTS: tuple[str, ...] = (
    "Attribution",
    "Background",
    "Cause",
    "Comparison",
    "Condition",
    "Contrast",
    "Elaboration",
    "Enablement",
    "Evaluation",
    "Explanation",
    "Joint",
    "Manner-Means",
    "Same-unit",
    "Summary",
    "Temporal",
    "Textual-organization",
    "Topic-Change",
    "Topic-Comment",
)
def extract_eRST_candidates_from_document(
    document: RstDocument,
    analysis: RstAnalysis,
) -> list[SecondaryEdgeCandidate]:
    """Compatibility wrapper over the canonical complete generator."""

    return list(generate_secondary_edge_candidates(document, analysis))


class GUMSecondaryEdgeDataset(Dataset):
    """PyTorch dataset for pairwise eRST scoring."""

    def __init__(
        self,
        candidates: Sequence[SecondaryEdgeCandidate],
        tokenizer: Any,
        max_length: int = 128,
        raw_relation_inventory: Sequence[str] | None = None,
    ) -> None:
        if not candidates:
            raise ValueError("secondary-edge dataset requires at least one candidate")
        if not getattr(tokenizer, "is_fast", False):
            raise ValueError("secondary-edge dataset requires a verified fast tokenizer")
        self.candidates = tuple(candidates)
        self.tokenizer = tokenizer
        self.max_length = max_length
        if raw_relation_inventory is None:
            raise ValueError("dataset requires an explicit train-derived raw relation inventory")
        self.raw_relation_inventory = tuple(raw_relation_inventory)
        if not self.raw_relation_inventory or len(self.raw_relation_inventory) != len(
            set(self.raw_relation_inventory)
        ):
            raise ValueError("dataset raw relation inventory must be non-empty and unique")
        self.relation_to_index = {
            relation: index for index, relation in enumerate(self.raw_relation_inventory)
        }

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        candidate = self.candidates[idx]
        source_encoding = self.tokenizer(
            candidate.source_text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            return_special_tokens_mask=True,
            return_offsets_mapping=True,
        )
        target_encoding = self.tokenizer(
            candidate.target_text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            return_special_tokens_mask=True,
            return_offsets_mapping=True,
        )
        edge_label = 1.0 if candidate.is_gold_edge else 0.0
        if candidate.is_gold_edge:
            if candidate.gold_relation is None:
                raise ValueError("positive candidate is missing a raw relation label")
            try:
                relation_label = self.relation_to_index[candidate.gold_relation]
            except KeyError as error:
                raise ValueError(
                    f"gold raw relation is absent from the train-derived inventory: {candidate.gold_relation}"
                ) from error
        else:
            relation_label = -100
        return {
            "src_input_ids": source_encoding["input_ids"].squeeze(0),
            "src_attention_mask": source_encoding["attention_mask"].squeeze(0),
            "src_special_tokens_mask": source_encoding["special_tokens_mask"].squeeze(0),
            "src_offset_mapping": source_encoding["offset_mapping"].squeeze(0),
            "tgt_input_ids": target_encoding["input_ids"].squeeze(0),
            "tgt_attention_mask": target_encoding["attention_mask"].squeeze(0),
            "tgt_special_tokens_mask": target_encoding["special_tokens_mask"].squeeze(0),
            "tgt_offset_mapping": target_encoding["offset_mapping"].squeeze(0),
            "struct_features": torch.tensor(candidate.structural_features, dtype=torch.float),
            "edge_label": torch.tensor(edge_label, dtype=torch.float),
            "rel_label": torch.tensor(relation_label, dtype=torch.long),
        }


__all__ = [
    "COARSE_CONCEPTS",
    "GUMSecondaryEdgeDataset",
    "SecondaryEdgeCandidate",
    "compute_structural_features",
    "extract_eRST_candidates_from_document",
]
