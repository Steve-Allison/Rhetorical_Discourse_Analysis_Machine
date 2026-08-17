"""Dataset loader and tokenizer collation for EDU discourse segmentation."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset


@dataclass(frozen=True, slots=True)
class SegmentedSentence:
    """A sentence with word tokens, character offsets, and binary EDU start labels."""

    text: str
    tokens: tuple[str, ...]
    token_starts: tuple[int, ...]
    token_ends: tuple[int, ...]
    labels: tuple[int, ...]  # 1: B-EDU (starts an EDU), 0: I-EDU (continuation)


def parse_disrpt_tok_file(file_path: Path | str) -> list[SegmentedSentence]:
    """Parse a DISRPT `.tok` file into a list of SegmentedSentence records."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"DISRPT file not found: {path}")

    sentences: list[SegmentedSentence] = []
    current_tokens: list[str] = []
    current_labels: list[int] = []

    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            if current_tokens:
                # Build sentence
                sent_text = " ".join(current_tokens)
                starts: list[int] = []
                ends: list[int] = []
                pos = 0
                for tok in current_tokens:
                    tok_start = sent_text.find(tok, pos)
                    if tok_start == -1:
                        tok_start = pos
                    tok_end = tok_start + len(tok)
                    starts.append(tok_start)
                    ends.append(tok_end)
                    pos = tok_end + 1

                sentences.append(
                    SegmentedSentence(
                        text=sent_text,
                        tokens=tuple(current_tokens),
                        token_starts=tuple(starts),
                        token_ends=tuple(ends),
                        labels=tuple(current_labels),
                    )
                )
                current_tokens = []
                current_labels = []
            continue

        parts = line.split("\t")
        if len(parts) >= 2:
            tok_text = parts[1]
            seg_col = parts[2] if len(parts) > 2 else "_"
            is_b_edu = 1 if "B-EDU" in seg_col or "Seg=B" in seg_col or len(current_tokens) == 0 else 0
            current_tokens.append(tok_text)
            current_labels.append(is_b_edu)

    if current_tokens:
        sent_text = " ".join(current_tokens)
        starts = []
        ends = []
        pos = 0
        for tok in current_tokens:
            tok_start = sent_text.find(tok, pos)
            if tok_start == -1:
                tok_start = pos
            tok_end = tok_start + len(tok)
            starts.append(tok_start)
            ends.append(tok_end)
            pos = tok_end + 1

        sentences.append(
            SegmentedSentence(
                text=sent_text,
                tokens=tuple(current_tokens),
                token_starts=tuple(starts),
                token_ends=tuple(ends),
                labels=tuple(current_labels),
            )
        )

    return sentences


def parse_rs4_to_sentences(file_path: Path | str) -> list[SegmentedSentence]:
    """Extract segmented sentences from an .rs4 XML file."""
    from isanlp_rst.erst.converter import rs4_to_document_and_analysis
    from isanlp_rst.erst.rs4 import RS4Reader

    rs4 = RS4Reader.read_file(file_path)
    doc, _ = rs4_to_document_and_analysis(rs4)
    if not doc.edus:
        return []

    raw_text = doc.text
    edu_start_chars = {e.start for e in doc.edus}

    # Split document into paragraphs/sentences while tracking character offsets
    sentences: list[SegmentedSentence] = []
    lines = raw_text.splitlines(keepends=True)
    curr_char = 0

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            curr_char += len(line)
            continue

        words: list[str] = []
        starts: list[int] = []
        ends: list[int] = []
        labels: list[int] = []

        import re
        for match in re.finditer(r"\S+", line):
            word = match.group(0)
            abs_start = curr_char + match.start()
            abs_end = curr_char + match.end()

            # Word is B-EDU if its start matches an EDU start or it's the very first word of an EDU
            is_b_edu = 1 if any(abs_start <= s < abs_end or s == abs_start for s in edu_start_chars) else 0
            if not words and not labels:
                is_b_edu = 1  # First word is always start of a unit

            words.append(word)
            starts.append(match.start())
            ends.append(match.end())
            labels.append(is_b_edu)

        if words:
            sentences.append(
                SegmentedSentence(
                    text=line_clean,
                    tokens=tuple(words),
                    token_starts=tuple(starts),
                    token_ends=tuple(ends),
                    labels=tuple(labels),
                )
            )

        curr_char += len(line)

    return sentences


class EduSegmentationDataset(Dataset):
    """PyTorch Dataset for fine-tuning Transformer EDU segmenters with subword alignment."""

    def __init__(
        self,
        sentences: Sequence[SegmentedSentence],
        tokenizer: Any,
        max_length: int = 512,
    ) -> None:
        self.sentences = list(sentences)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.sentences)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        sent = self.sentences[idx]

        # Tokenize with fast offset mappings
        encoding = self.tokenizer(
            sent.text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_offsets_mapping=True,
            return_tensors="pt",
        )

        input_ids = encoding["input_ids"].squeeze(0)
        attention_mask = encoding["attention_mask"].squeeze(0)
        offset_mapping = encoding["offset_mapping"].squeeze(0)

        # Align word-level B-EDU/I-EDU labels to subwords
        labels = torch.full((self.max_length,), fill_value=-100, dtype=torch.long)

        for subword_idx, (sub_start, sub_end) in enumerate(offset_mapping):
            if sub_start == sub_end or attention_mask[subword_idx] == 0:
                continue  # Special token ([CLS], [SEP], [PAD])

            # Find corresponding word token
            sub_s = int(sub_start.item())

            for word_idx, (w_start, w_end) in enumerate(zip(sent.token_starts, sent.token_ends, strict=True)):
                if w_start <= sub_s < w_end:
                    # If this subword is the first subword of the word, assign word's label
                    if sub_s == w_start:
                        labels[subword_idx] = sent.labels[word_idx]
                    else:
                        labels[subword_idx] = 0  # Continuation of word -> I-EDU
                    break

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }
