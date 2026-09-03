"""Transformer-based neural Elementary Discourse Unit (EDU) segmenter."""

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from torch import Tensor

from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer, PreTrainedModel

from rdam.rst._torch_runtime import resolve_device, resolve_dtype, torch
from rdam.rst.contracts.document import DocumentToken, Edu


@dataclass(frozen=True, slots=True)
class SegmentationResult:
    """Result of neural EDU segmentation containing aligned tokens and EDUs."""

    text: str
    tokens: tuple[DocumentToken, ...]
    edus: tuple[Edu, ...]


class InvalidSegmenterCheckpointError(ValueError):
    """Raised when a path is not a complete, trained EDU-segmentation checkpoint."""


class SegmenterInputLimitError(ValueError):
    """The exact segmentation substrate exceeds the configured model context."""


class TransformerEduSegmenter:
    """State-of-the-art Transformer token-classification segmenter for RST discourse parsing.

    Predicts EDU start boundaries (B-EDU) on subwords and projects them back
    to exact character spans with zero coordinate drift.
    """

    def __init__(
        self,
        model_name_or_path: str,
        model_revision: str | None = None,
        device: str | torch.device = "auto",
        torch_dtype: str | torch.dtype = "auto",
        max_length: int = 512,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.model_revision = model_revision
        self.max_length = max_length

        self.device = resolve_device(device)
        self.dtype = resolve_dtype(self.device, torch_dtype)

        revision_kwargs = {"revision": model_revision} if model_revision is not None else {}

        # 3. Validate and load a complete, trained token-classification checkpoint.
        config: Any = cast(Any, AutoConfig).from_pretrained(self.model_name_or_path, **revision_kwargs)
        architectures = tuple(config.architectures or ())
        if not any(name.endswith("ForTokenClassification") for name in architectures):
            raise InvalidSegmenterCheckpointError(
                f"{self.model_name_or_path!r} is a base model, not a trained token-classification checkpoint"
            )
        expected_labels = {0: "I-EDU", 1: "B-EDU"}
        if config.num_labels != 2 or config.id2label != expected_labels:
            raise InvalidSegmenterCheckpointError("EDU segmenter config must declare exactly {0: 'I-EDU', 1: 'B-EDU'}")

        self.tokenizer: Any = cast(Any, AutoTokenizer).from_pretrained(
            self.model_name_or_path,
            use_fast=True,
            **revision_kwargs,
        )
        if not self.tokenizer.is_fast:
            raise InvalidSegmenterCheckpointError("EDU segmentation requires a native fast tokenizer artifact")

        loaded: object = cast(Any, AutoModelForTokenClassification).from_pretrained(
            self.model_name_or_path,
            config=config,
            dtype=self.dtype,
            use_safetensors=True,
            output_loading_info=True,
            **revision_kwargs,
        )
        if not isinstance(loaded, tuple):
            raise InvalidSegmenterCheckpointError("Transformers did not return checkpoint loading evidence")
        loaded_tuple = cast(tuple[object, ...], loaded)
        if len(loaded_tuple) != 2:
            raise InvalidSegmenterCheckpointError("Transformers did not return checkpoint loading evidence")
        model, raw_loading_info = loaded_tuple
        if not isinstance(model, PreTrainedModel) or not isinstance(raw_loading_info, dict):
            raise InvalidSegmenterCheckpointError("Transformers returned malformed checkpoint loading evidence")
        loading_info = cast(dict[str, object], raw_loading_info)
        defects = {
            key: tuple(cast(list[object], value))
            for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")
            if (value := loading_info.get(key))
        }
        if defects:
            raise InvalidSegmenterCheckpointError(f"segmenter checkpoint is incomplete: {defects}")
        self.model = cast(PreTrainedModel, torch.nn.Module.to(model, device=self.device))
        self.model.eval()

    @torch.inference_mode()
    def segment(self, text: str) -> tuple[Edu, ...]:
        """Segment raw text into a sequence of typed Edu records."""
        if not text.strip():
            return ()

        # Split text by paragraphs or lines to keep sequences comfortably within context length
        paragraphs: list[tuple[int, int, str]] = []
        pos = 0
        lines = text.splitlines(keepends=True)
        for line in lines:
            start_pos = pos
            end_pos = pos + len(line)
            if line.strip():
                paragraphs.append((start_pos, end_pos, line))
            pos = end_pos

        if not paragraphs:
            paragraphs = [(0, len(text), text)]

        all_edus: list[Edu] = []
        global_edu_id = 1

        for p_start, _p_end, p_text in paragraphs:
            encoding = cast(
                dict[str, Tensor],
                self.tokenizer(
                p_text,
                truncation=False,
                return_offsets_mapping=True,
                return_tensors="pt",
                ),
            )

            input_ids = encoding["input_ids"].to(self.device)
            attention_mask = encoding["attention_mask"].to(self.device)
            offset_mapping = cast(NDArray[np.int64], encoding["offset_mapping"][0].cpu().numpy())
            context_limit = _segmenter_context_limit(
                self.model,
                self.tokenizer,
                self.max_length,
            )
            if input_ids.shape[1] > context_limit:
                raise SegmenterInputLimitError(
                    f"exact segmenter input has {input_ids.shape[1]} tokens; limit is {context_limit}"
                )
            _validate_offset_coverage(p_text, offset_mapping)

            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits[0]  # (seq_len, 2)
            preds = cast(NDArray[np.int64], torch.argmax(logits, dim=-1).cpu().numpy())

            # Extract subword boundary offsets
            edu_start_offsets: list[int] = [0]

            for idx, (sub_start, sub_end) in enumerate(offset_mapping):
                if sub_start == sub_end or attention_mask[0, idx] == 0:
                    continue  # Special token
                if idx > 0 and preds[idx] == 1:
                    # B-EDU predicted: ensure it is not in the middle of a token and points to non-whitespace
                    s_int = int(sub_start)
                    if s_int < len(p_text) and not p_text[s_int].isspace():
                        # Check that previous character is whitespace or punctuation
                        prev_char = p_text[s_int - 1] if s_int > 0 else " "
                        if (prev_char.isspace() or prev_char in ",.;:!?-—\"'()[]{}") and s_int not in edu_start_offsets:
                            edu_start_offsets.append(s_int)

            edu_start_offsets = sorted(set(edu_start_offsets))

            # Build EDUs for this paragraph
            for i, s_offset in enumerate(edu_start_offsets):
                e_offset = edu_start_offsets[i + 1] if i + 1 < len(edu_start_offsets) else len(p_text)
                raw_edu_slice = p_text[s_offset:e_offset]
                if not raw_edu_slice.strip():
                    continue

                abs_start = p_start + s_offset
                abs_end = p_start + e_offset

                # Trim leading/trailing whitespace while adjusting absolute character offsets
                l_strip_len = len(raw_edu_slice) - len(raw_edu_slice.lstrip())
                r_strip_len = len(raw_edu_slice) - len(raw_edu_slice.rstrip())

                trimmed_start = abs_start + l_strip_len
                trimmed_end = abs_end - r_strip_len

                if trimmed_end > trimmed_start:
                    all_edus.append(
                        Edu(
                            edu_id=global_edu_id,
                            text=text[trimmed_start:trimmed_end],
                            start=trimmed_start,
                            end=trimmed_end,
                        )
                    )
                    global_edu_id += 1

        return tuple(all_edus)

    def segment_with_tokens(self, text: str) -> SegmentationResult:
        """Segment raw text into aligned DocumentToken and Edu records."""
        edus = self.segment(text)

        # Extract word tokens with regex
        import re

        tokens: list[DocumentToken] = []
        for tok_id, match in enumerate(re.finditer(r"\S+", text)):
            tokens.append(
                DocumentToken(
                    token_id=tok_id,
                    text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
            )

        return SegmentationResult(
            text=text,
            tokens=tuple(tokens),
            edus=edus,
        )


def _segmenter_context_limit(
    model: PreTrainedModel,
    tokenizer: Any,
    configured_limit: int,
) -> int:
    model_limit = getattr(model.config, "max_position_embeddings", None)
    tokenizer_limit = getattr(tokenizer, "model_max_length", None)
    candidates = [
        value
        for value in (configured_limit, model_limit, tokenizer_limit)
        if isinstance(value, int) and 1 < value < 1_000_000
    ]
    if not candidates:
        raise InvalidSegmenterCheckpointError("EDU segmenter has no finite declared context limit")
    return min(candidates)


def _validate_offset_coverage(text: str, offsets: Any) -> None:
    covered = [False] * len(text)
    for raw_start, raw_end in offsets:
        start = int(raw_start)
        end = int(raw_end)
        if start < 0 or end < start or end > len(text):
            raise ValueError("segmenter tokenizer returned an invalid character offset")
        for index in range(start, end):
            covered[index] = True
    missing = next(
        (index for index, character in enumerate(text) if not character.isspace() and not covered[index]),
        None,
    )
    if missing is not None:
        raise ValueError(f"segmenter tokenizer offsets omit non-whitespace input at character {missing}")


__all__ = [
    "InvalidSegmenterCheckpointError",
    "SegmentationResult",
    "SegmenterInputLimitError",
    "TransformerEduSegmenter",
]
