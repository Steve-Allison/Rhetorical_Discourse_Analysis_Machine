"""Runtime tensor encoding for eRST secondary-edge candidates."""

from collections.abc import Sequence
from typing import Any

import torch
from torch.utils.data import Dataset

from rdam.rst.erst.candidates import SecondaryEdgeCandidate


class SecondaryEdgeInferenceDataset(Dataset[dict[str, torch.Tensor]]):
    """Encode candidate pairs for released eRST scorer inference."""

    def __init__(
        self,
        candidates: Sequence[SecondaryEdgeCandidate],
        tokenizer: Any,
        max_length: int = 128,
    ) -> None:
        if not candidates:
            raise ValueError("secondary-edge inference requires at least one candidate")
        if not getattr(tokenizer, "is_fast", False):
            raise ValueError("secondary-edge inference requires a verified fast tokenizer")
        self.candidates = tuple(candidates)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        candidate = self.candidates[index]
        source = self._encode(candidate.source_text)
        target = self._encode(candidate.target_text)
        return {
            "src_input_ids": source["input_ids"].squeeze(0),
            "src_attention_mask": source["attention_mask"].squeeze(0),
            "src_special_tokens_mask": source["special_tokens_mask"].squeeze(0),
            "src_offset_mapping": source["offset_mapping"].squeeze(0),
            "tgt_input_ids": target["input_ids"].squeeze(0),
            "tgt_attention_mask": target["attention_mask"].squeeze(0),
            "tgt_special_tokens_mask": target["special_tokens_mask"].squeeze(0),
            "tgt_offset_mapping": target["offset_mapping"].squeeze(0),
            "struct_features": torch.tensor(candidate.structural_features, dtype=torch.float),
        }

    def _encode(self, text: str) -> dict[str, torch.Tensor]:
        return self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            return_special_tokens_mask=True,
            return_offsets_mapping=True,
        )


__all__ = ["SecondaryEdgeInferenceDataset"]
