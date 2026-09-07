"""Captured token groups must agree with the exact boundaries returned to callers."""

from pathlib import Path
from typing import cast

import pytest

from rdam.rst.contracts.document import RstDocument, TextSpan
from rdam.rst.contracts.trace import PredictorAnalysisTrace
from rdam.rst.parser import Parser
from rdam.ingest.contracts.analysis import AnchorTargetKind, ParserAnalysisResult


@pytest.mark.slow
@pytest.mark.parametrize("release_id", ("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def test_captured_tokens_follow_caller_supplied_source_groups(release_id: str) -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", release_id, device="cpu",
    )
    edus = ("Alpha beta", "gamma delta.")
    text = " ".join(edus)
    boundaries = (
        TextSpan(start=0, end=len(edus[0]), text=edus[0]),
        TextSpan(start=len(edus[0]) + 1, end=len(text), text=edus[1]),
    )
    trace = cast(PredictorAnalysisTrace, parser.predictor.analyse_with_evidence(
        text, edus=edus, sentence_boundaries=boundaries, paragraph_boundaries=boundaries,
    ))
    assert trace.sentence_boundaries == trace.paragraph_boundaries == boundaries
    assert {token.sentence_id for token in trace.tokens} == {1, 2}
    assert {token.paragraph_id for token in trace.tokens} == {1, 2}
    for token in trace.tokens:
        assert token.sentence_id is not None
        assert token.paragraph_id is not None
        for group_id in (token.sentence_id, token.paragraph_id):
            group = boundaries[group_id - 1]
            assert group.start <= token.start < token.end <= group.end
            assert text[token.start:token.end] == token.text


@pytest.mark.slow
@pytest.mark.parametrize("release_id", ("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
def test_word_crossing_edus_preserves_each_exact_anchor_extent(release_id: str) -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", release_id, device="cpu",
    )
    text = "Dvořák left. However, cafe\u0301 patrons stayed—because it rained."
    result = parser.analyse_document(RstDocument.from_text(text))
    document = result.analysed_document
    token = next(token for token in document.tokens if token.text == "stayed—because")
    members = tuple(edu for edu in document.edus if token.token_id in edu.token_ids)
    assert len(members) == 2
    boundary = members[0].character_range.end
    assert boundary == members[1].character_range.start
    assert token.character_range.start < boundary < token.character_range.end
    node_anchors = {
        anchor.target_id: anchor for anchor in result.semantic.anchors
        if anchor.target_kind is AnchorTargetKind.NODE
    }
    for edu in members:
        node = next(node for node in result.analysis.nodes if node.char_span == (
            edu.character_range.start, edu.character_range.end,
        ))
        assert node_anchors[str(node.node_id)].edu_ids == (edu.edu_id,)
        assert token.token_id in node_anchors[str(node.node_id)].token_ids
    restored = ParserAnalysisResult.model_validate_json(result.model_dump_json())
    assert restored.analysed_document == document
    assert restored.semantic.anchors == result.semantic.anchors
    assert {mapping.edu_id for mapping in restored.analysed_document.mappings if mapping.token_id == token.token_id} == {
        edu.edu_id for edu in members
    }
