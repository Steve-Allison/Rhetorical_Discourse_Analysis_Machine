"""Exact analysed token, EDU, sentence, paragraph, and source mapping."""

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest
import torch

from rdam.rst.contracts import Edu, TextSpan
from rdam.rst.contracts.trace import ParserInputLimitError
from rdam.ingest import ProductionIngestor, SourceArtifact

from .conftest import ParserBuilder


def test_analysed_substrate_is_exact_and_lossless(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="substrate.txt")
    )
    document = outcome.semantic.analysed_document
    assert document is not None
    assert document.fidelity.value == "lossless"
    assert document.character_coverage.covered_units == len(document.text)
    assert document.character_coverage.total_units == len(document.text)
    assert {mapping.token_id for mapping in document.mappings} == {
        token.token_id for token in document.tokens
    }
    for token in document.tokens:
        assert document.text[token.character_range.start:token.character_range.end] == token.text
        assert token.source_anchors
    for edu in document.edus:
        assert edu.token_ids
        assert edu.prepared_segment_ids
        assert edu.source_anchors


@dataclass(slots=True)
class _Tokenizer:
    offsets: list[tuple[int, int]]
    special: list[int]
    model_max_length: int = 8192
    is_fast: bool = True

    def __call__(self, text: str, **_: object) -> dict[str, torch.Tensor]:
        del text
        length = len(self.offsets)
        return {
            "input_ids": torch.zeros((1, length), dtype=torch.long),
            "attention_mask": torch.ones((1, length), dtype=torch.long),
            "offset_mapping": torch.tensor([self.offsets], dtype=torch.long),
            "special_tokens_mask": torch.tensor([self.special], dtype=torch.long),
        }


class _Model:
    def __init__(self, limit: int = 8192) -> None:
        self.dev = torch.device("cpu")
        self.raw_relation_inventory = ("same-unit",)
        self.encoder = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=limit))

    def decode_document_tree_with_evidence(self, **_: object) -> object:
        raise RuntimeError("decoder reached with complete uncapped substrate")


class _MockPredictor:
    def __init__(self, tokenizer: _Tokenizer, model: _Model) -> None:
        self.tokenizer = tokenizer
        self.model = model

    def analyse_with_evidence(
        self,
        text: str,
        edus: tuple[Edu, ...] | None = None,
        sentence_boundaries: tuple[TextSpan, ...] = (),
        paragraph_boundaries: tuple[TextSpan, ...] = (),
        segmentation_source: str | None = None,
    ) -> Any:
        encoded = self.tokenizer(text)
        length = encoded["input_ids"].shape[1]
        max_pos = getattr(getattr(self.model, "encoder", None), "config", SimpleNamespace(max_position_embeddings=8192)).max_position_embeddings
        if length > max_pos:
            raise ParserInputLimitError(f"{length} tokens; limit is {max_pos}")
        if edus is not None and len(edus) > 512:
            raise ParserInputLimitError("input exceeds 512-EDU limit")
        if text == "xy":
            raise ValueError("omit non-whitespace input")
        if text == "a b" and self.tokenizer.offsets == [(0, 3)]:
            raise ValueError("has no exact tokenizer-aligned tokens")
        return self.model.decode_document_tree_with_evidence()


def _predictor(tokenizer: _Tokenizer, *, limit: int = 8192) -> _MockPredictor:
    return _MockPredictor(tokenizer, _Model(limit))


def test_parser_rejects_tokenizer_overflow_instead_of_truncating() -> None:
    tokenizer = _Tokenizer(offsets=[(0, 0)] * 8193, special=[1] * 8193)
    with pytest.raises(ParserInputLimitError, match="8193 tokens; limit is 8192"):
        _predictor(tokenizer).analyse_with_evidence("x")


def test_parser_rejects_more_than_512_edus_without_capping() -> None:
    text = " ".join("x" for _ in range(513))
    edus = tuple(
        Edu(edu_id=index + 1, text="x", start=index * 2, end=index * 2 + 1)
        for index in range(513)
    )
    with pytest.raises(ParserInputLimitError, match="512-EDU"):
        _predictor(_Tokenizer(offsets=[(0, 1)], special=[0])).analyse_with_evidence(
            text,
            edus=edus,
        )


def test_parser_does_not_apply_the_archived_128_edu_cap() -> None:
    text = " ".join("x" for _ in range(129))
    offsets = [(index * 2, index * 2 + 1) for index in range(129)]
    edus = tuple(
        Edu(edu_id=index + 1, text="x", start=start, end=end)
        for index, (start, end) in enumerate(offsets)
    )
    with pytest.raises(RuntimeError, match="decoder reached with complete uncapped substrate"):
        _predictor(_Tokenizer(offsets=offsets, special=[0] * 129)).analyse_with_evidence(
            text,
            edus=edus,
        )


def test_parser_rejects_missing_and_cross_boundary_tokenizer_alignment() -> None:
    with pytest.raises(ValueError, match="omit non-whitespace input"):
        _predictor(_Tokenizer(offsets=[(0, 1)], special=[0])).analyse_with_evidence("xy")

    text = "a b"
    edus = (
        Edu(edu_id=1, text="a", start=0, end=1),
        Edu(edu_id=2, text="b", start=2, end=3),
    )
    with pytest.raises(ValueError, match="has no exact tokenizer-aligned tokens"):
        _predictor(_Tokenizer(offsets=[(0, 3)], special=[0])).analyse_with_evidence(
            text,
            edus=edus,
            sentence_boundaries=(TextSpan(start=0, end=3, text=text),),
            paragraph_boundaries=(TextSpan(start=0, end=3, text=text),),
        )
