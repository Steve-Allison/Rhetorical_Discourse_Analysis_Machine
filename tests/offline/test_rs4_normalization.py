"""Gold normalization preserves annotated attachments and source coordinates."""

from pathlib import Path

import pytest

from workbench.erst.rs4 import RS4Document, RS4Group, RS4Reader, RS4Segment, RS4Writer
from workbench.evaluation.rst.normalization import binarize_rs4
from workbench.evaluation.rst.parseval import BracketSpan, StandardParsevalScorer


def test_multinuclear_group_associates_right() -> None:
    source = RS4Document(
        relations={"joint-list": "multinuc"},
        segments=tuple(RS4Segment(i, str(i), parent=10, relname="joint-list") for i in range(1, 4)),
        groups=(RS4Group(10, "multinuc"),),
    )
    _, analysis = binarize_rs4(source, document_id="joint")
    assert StandardParsevalScorer().extract_spans_from_analysis(analysis) == {
        BracketSpan(2, 3, "NN", "joint-list"), BracketSpan(1, 3, "NN", "joint-list"),
    }


@pytest.mark.parametrize("parent_is_edu", [False, True])
def test_satellites_on_both_sides_preserve_the_nucleus(parent_is_edu: bool) -> None:
    parent = 2 if parent_is_edu else 10
    source = RS4Document(
        relations={"concession": "rst", "cause": "rst"},
        segments=(RS4Segment(1, "a", parent, "concession"),
                  RS4Segment(2, "b", None if parent_is_edu else parent),
                  RS4Segment(3, "c", parent, "cause")),
        groups=() if parent_is_edu else (RS4Group(10, "span"),),
    )
    _, analysis = binarize_rs4(source, document_id="satellites")
    assert StandardParsevalScorer().extract_spans_from_analysis(analysis) == {
        BracketSpan(2, 3, "NS", "cause"), BracketSpan(1, 3, "SN", "concession"),
    }


def test_right_satellites_do_not_create_a_satellite_only_attachment() -> None:
    source = RS4Document(
        relations={"concession": "rst", "cause": "rst"},
        segments=(RS4Segment(1, "a", 10), RS4Segment(2, "b", 10, "concession"),
                  RS4Segment(3, "c", 10, "cause")), groups=(RS4Group(10, "span"),),
    )
    _, analysis = binarize_rs4(source, document_id="right-satellites")
    assert StandardParsevalScorer().extract_spans_from_analysis(analysis) == {
        BracketSpan(1, 2, "NS", "concession"), BracketSpan(1, 3, "NS", "cause"),
    }


def test_unary_structural_group_collapses_without_inventing_a_relation() -> None:
    source = RS4Document(segments=(RS4Segment(1, "a", 10),), groups=(RS4Group(10, "span"),))
    document, analysis = binarize_rs4(source, document_id="unary")
    assert document.text == "a"
    assert len(analysis.nodes) == 1
    assert not StandardParsevalScorer().extract_spans_from_analysis(analysis)


@pytest.mark.parametrize("source,message", [
    (RS4Document(segments=(RS4Segment(1, "a"), RS4Segment(1, "b"))), "unique node IDs"),
    (RS4Document(segments=(RS4Segment(1, "a", 99),)), "missing parent"),
    (RS4Document(segments=(RS4Segment(1, "a"), RS4Segment(2, "b"))), "exactly one root"),
    (RS4Document(segments=(RS4Segment(1, "a", 10, "unknown"),),
                 groups=(RS4Group(10, "span"),)), "absent from header"),
])
def test_invalid_annotations_are_rejected(source: RS4Document, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        binarize_rs4(source, document_id="invalid")


@pytest.mark.parametrize("path", sorted((Path(__file__).parents[1] / "fixtures" / "gum").glob("*.rs4")),
                         ids=lambda path: path.stem)
def test_local_gum_projection_preserves_edus_source_and_annotations(path: Path) -> None:
    raw = path.read_bytes()
    source = RS4Reader.read_file(path)
    snapshot = RS4Writer.to_string(source)
    document, analysis = binarize_rs4(source, document_id=path.stem)
    brackets = StandardParsevalScorer().extract_spans_from_analysis(analysis)
    assert len(brackets) == len(source.segments) - 1
    assert document.edus is not None
    assert [edu.text for edu in document.edus] == [segment.text for segment in source.segments]
    assert all(document.text[node.char_span[0]:node.char_span[1]] == node.text for node in analysis.nodes)
    assert all(bracket.relation in source.relations for bracket in brackets)
    assert RS4Writer.to_string(source) == snapshot
    assert path.read_bytes() == raw
