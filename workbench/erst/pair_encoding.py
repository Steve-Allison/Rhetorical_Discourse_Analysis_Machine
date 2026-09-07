"""Runtime tensor encoding for complete eRST secondary-edge candidates."""

from collections.abc import Sequence
from typing import Any

import torch
from torch.utils.data import Dataset

from workbench.erst.candidates import SecondaryEdgeCandidate


class SecondaryEdgeInferenceDataset(Dataset[dict[str, torch.Tensor]]):
    """Encode complete candidate spans and pad only to the actual batch width.

    An explicit token budget is a rejection boundary, never permission to silently
    truncate source evidence. Without a budget, the encoder's own supported input
    shape remains authoritative; this dataset does not invent a numerical limit.
    """

    def __init__(
        self,
        candidates: Sequence[SecondaryEdgeCandidate],
        tokenizer: Any,
        max_length: int | None = None,
    ) -> None:
        if not candidates:
            raise ValueError("secondary-edge inference requires at least one candidate")
        if not getattr(tokenizer, "is_fast", False):
            raise ValueError("secondary-edge inference requires a verified fast tokenizer")
        if max_length is not None and (type(max_length) is not int or max_length < 1):
            raise ValueError("an explicit token budget must be a positive integer")
        self.candidates = tuple(candidates)
        texts = [candidate.source_text for candidate in candidates] + [candidate.target_text for candidate in candidates]
        encoded = tokenizer(
            texts, padding=True, truncation=False, return_tensors="pt",
            return_special_tokens_mask=True, return_offsets_mapping=True,
        )
        self.encoded: dict[str, torch.Tensor] = {}
        for key in ("input_ids", "attention_mask", "special_tokens_mask", "offset_mapping"):
            value = encoded[key]
            if not isinstance(value, torch.Tensor):
                raise ValueError(f"candidate tokenizer did not return tensor {key}")
            self.encoded[key] = value
        if max_length is not None and self.encoded["input_ids"].shape[1] > max_length:
            raise ValueError("complete candidate span exceeds the explicit token budget")

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        if not 0 <= index < len(self.candidates):
            raise IndexError("secondary-edge candidate index is out of range")
        result = {
            f"{side}_{key}": values[index + offset]
            for side, offset in (("src", 0), ("tgt", len(self.candidates)))
            for key, values in self.encoded.items()
        }
        result["struct_features"] = torch.tensor(self.candidates[index].structural_features, dtype=torch.float)
        return result


__all__ = ["SecondaryEdgeInferenceDataset"]
