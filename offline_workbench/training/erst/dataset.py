"""Offline labels layered on the canonical production pair encoder."""

from collections.abc import Sequence
from typing import Any

import torch

from isanlp_rst.contracts.analysis import RstAnalysis
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate, generate_secondary_edge_candidates
from isanlp_rst.erst.pair_encoding import SecondaryEdgeInferenceDataset


class GUMSecondaryEdgeDataset(SecondaryEdgeInferenceDataset):
    """Add train-derived edge and relation targets to runtime encodings."""

    def __init__(
        self,
        candidates: Sequence[SecondaryEdgeCandidate],
        tokenizer: Any,
        max_length: int = 128,
        raw_relation_inventory: Sequence[str] | None = None,
    ) -> None:
        super().__init__(candidates, tokenizer, max_length)
        if raw_relation_inventory is None:
            raise ValueError("dataset requires an explicit train-derived raw relation inventory")
        self.raw_relation_inventory = tuple(raw_relation_inventory)
        if not self.raw_relation_inventory or len(self.raw_relation_inventory) != len(set(self.raw_relation_inventory)):
            raise ValueError("dataset raw relation inventory must be non-empty and unique")
        self.relation_to_index = {relation: index for index, relation in enumerate(self.raw_relation_inventory)}

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        encoded = super().__getitem__(index)
        candidate = self.candidates[index]
        edge_label = 1.0 if candidate.is_gold_edge else 0.0
        if candidate.is_gold_edge:
            if candidate.gold_relation is None:
                raise ValueError("positive candidate is missing a raw relation label")
            try:
                relation_label = self.relation_to_index[candidate.gold_relation]
            except KeyError as error:
                raise ValueError(f"gold raw relation is absent from the train-derived inventory: {candidate.gold_relation}") from error
        else:
            relation_label = -100
        return encoded | {
            "edge_label": torch.tensor(edge_label, dtype=torch.float),
            "rel_label": torch.tensor(relation_label, dtype=torch.long),
        }


def extract_eRST_candidates_from_document(document: RstDocument, analysis: RstAnalysis) -> list[SecondaryEdgeCandidate]:
    """Return the complete canonical candidate sequence for offline fitting."""

    return list(generate_secondary_edge_candidates(document, analysis))


__all__ = ["GUMSecondaryEdgeDataset", "extract_eRST_candidates_from_document"]
