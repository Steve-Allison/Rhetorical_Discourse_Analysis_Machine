"""Shared semantic projection contracts for every format-native mapper."""

from dataclasses import asdict, dataclass
import json
import math
from typing import Any, Callable

import networkx as nx
import pytest

from isanlp_rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from isanlp_rst.doclang.mapper import flatten_tree as flatten_doclang_tree
from isanlp_rst.doclang.schema import DoclangRstResult
from isanlp_rst.doclang.schema import HarvestSpan as DoclangSpan
from isanlp_rst.docling.mapper import flatten_tree as flatten_docling_tree
from isanlp_rst.docling.schema import DoclingRstResult
from isanlp_rst.docling.schema import HarvestSpan as DoclingSpan
from isanlp_rst.markdown.mapper import flatten_tree as flatten_markdown_tree
from isanlp_rst.markdown.schema import HarvestSpan as MarkdownSpan
from isanlp_rst.markdown.schema import MarkdownRstResult
from isanlp_rst.erst.dataset import compute_structural_features
from isanlp_rst.eval.parseval import StandardParsevalScorer
from isanlp_rst.hierarchical.stitcher import HierarchicalSectionStitcher, SectionSlice


@dataclass
class _Node:
    start: int
    end: int
    left: _Node | None = None
    right: _Node | None = None
    relation: str = ""
    nuclearity: str = ""


def _tree() -> _Node:
    first = _Node(0, 6)
    second = _Node(8, 13)
    third = _Node(15, 21)
    first_pair = _Node(0, 13, first, second, "elaboration", "NS")
    return _Node(0, 21, first_pair, third, "joint", "NN")


SOURCE_TEXT = "Alpha.\n\nBeta.\n\nGamma."


def _docling_projection() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    spans = (
        DoclingSpan("#/texts/0", "Alpha.", 0, 6),
        DoclingSpan("#/texts/1", "Beta.", 8, 13),
        DoclingSpan("#/texts/2", "Gamma.", 15, 21),
    )
    return flatten_docling_tree(_tree(), spans, (), source_text=SOURCE_TEXT)


def _doclang_projection() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    spans = (
        DoclangSpan("/doclang[1]/text[1]", None, "body", "Alpha.", 0, 6),
        DoclangSpan("/doclang[1]/text[2]", None, "body", "Beta.", 8, 13),
        DoclangSpan("/doclang[1]/text[3]", None, "body", "Gamma.", 15, 21),
    )
    return flatten_doclang_tree(_tree(), spans, (), source_text=SOURCE_TEXT)


def _markdown_projection() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    spans = (
        MarkdownSpan("#/blocks/0", "paragraph", "Alpha.", 0, 6, 0, 1),
        MarkdownSpan("#/blocks/1", "paragraph", "Beta.", 8, 13, 2, 3),
        MarkdownSpan("#/blocks/2", "paragraph", "Gamma.", 15, 21, 4, 5),
    )
    return flatten_markdown_tree(_tree(), spans, (), source_text=SOURCE_TEXT)


@pytest.mark.parametrize(
    "project",
    [_docling_projection, _doclang_projection, _markdown_projection],
    ids=["docling", "doclang", "markdown"],
)
def test_nested_tree_has_exact_self_contained_projection(
    project: Callable[[], tuple[tuple[Any, ...], tuple[Any, ...]]],
) -> None:
    relations, edus = project()

    assert [edu.edu_span for edu in edus] == [(1, 1), (2, 2), (3, 3)]
    assert [edu.char_span for edu in edus] == [(0, 6), (8, 13), (15, 21)]
    assert [edu.text for edu in edus] == ["Alpha.", "Beta.", "Gamma."]

    assert [relation.edu_span for relation in relations] == [(1, 3), (1, 2)]
    assert [relation.char_span for relation in relations] == [(0, 21), (0, 13)]
    assert [relation.text for relation in relations] == [SOURCE_TEXT, "Alpha.\n\nBeta."]

    for item in (*relations, *edus):
        payload = json.loads(json.dumps(asdict(item)))
        assert payload["text"] == SOURCE_TEXT[item.char_span[0] : item.char_span[1]]
        assert payload["char_span"] == list(item.char_span)
        assert payload["edu_span"] == list(item.edu_span)


@pytest.mark.parametrize(
    "project",
    [_docling_projection, _doclang_projection, _markdown_projection],
    ids=["docling", "doclang", "markdown"],
)
def test_leaf_ordinals_are_not_preorder_node_ids(
    project: Callable[[], tuple[tuple[Any, ...], tuple[Any, ...]]],
) -> None:
    relations, edus = project()

    assert [edu.id for edu in edus] == [2, 3, 4]
    assert [edu.edu_span for edu in edus] == [(1, 1), (2, 2), (3, 3)]
    assert relations[0].edu_span == (1, 3)


def _format_analyses() -> tuple[Any, ...]:
    docling_relations, docling_edus = _docling_projection()
    doclang_relations, doclang_edus = _doclang_projection()
    markdown_relations, markdown_edus = _markdown_projection()
    common = {
        "tool": "isanlp_rst",
        "tool_version": "4.0.0",
        "source_revision": "0123456789abcdef0123456789abcdef01234567",
        "model_version": "test-model",
        "inventory": "test",
        "source": "sample",
        "source_origin": {},
        "boundaries": (),
    }
    return (
        DoclingRstResult(relations=docling_relations, edus=docling_edus, schema_name="docling", schema_version="1.2", **common).to_format_analysis(),
        DoclangRstResult(relations=doclang_relations, edus=doclang_edus, schema_name="doclang", schema_version="1.1", **common).to_format_analysis(),
        MarkdownRstResult(relations=markdown_relations, edus=markdown_edus, schema_name="markdown", schema_version="1.1", **common).to_format_analysis(),
    )


def test_every_schema_uses_truthful_shared_analysis_conversion() -> None:
    for format_analysis in _format_analyses():
        analysis = format_analysis.document_analysis
        by_id = {node.node_id: node for node in analysis.nodes}
        assert by_id[0].text == SOURCE_TEXT
        assert by_id[0].char_span == (0, 21)
        assert by_id[0].edu_span == (1, 3)
        assert [by_id[node_id].text for node_id in (2, 3, 4)] == ["Alpha.", "Beta.", "Gamma."]
        assert analysis.provenance.software_version == "4.0.0"
        assert all(node.text for node in analysis.nodes)


def test_downstream_parseval_and_structural_features_use_real_projection() -> None:
    scorer = StandardParsevalScorer(include_leaves=True, include_root=True)
    for format_analysis in _format_analyses():
        analysis = format_analysis.document_analysis
        spans = scorer.extract_spans_from_analysis(analysis)
        assert len(spans) == len(analysis.nodes) == 5
        assert {(span.start_edu, span.end_edu) for span in spans} == {
            (1, 1),
            (2, 2),
            (3, 3),
            (1, 2),
            (1, 3),
        }

        primary_graph = nx.DiGraph((edge.parent_id, edge.child_id) for edge in analysis.primary_edges)
        first = analysis.get_node(2)
        third = analysis.get_node(4)
        assert first is not None and third is not None
        features = compute_structural_features(first, third, primary_graph, SOURCE_TEXT)
        assert features[0] == pytest.approx(math.log1p(15))
        assert features[1] == 2.0


def test_hierarchical_stitcher_preserves_projected_text_and_coordinates() -> None:
    micro = _format_analyses()[0].document_analysis
    parent_text = f"{SOURCE_TEXT}\n\n{SOURCE_TEXT}"
    second_start = len(SOURCE_TEXT) + 2
    sections = [
        SectionSlice(0, (0, len(SOURCE_TEXT)), SOURCE_TEXT, (), None),
        SectionSlice(1, (second_start, len(parent_text)), SOURCE_TEXT, (), None),
    ]
    macro = RstAnalysis(
        document_id="macro",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(10, NodeKindEnum.EDU, (1, 1), (0, len(SOURCE_TEXT)), SOURCE_TEXT),
            RstNode(11, NodeKindEnum.EDU, (2, 2), (len(SOURCE_TEXT) + 1, len(parent_text)), SOURCE_TEXT),
            RstNode(12, NodeKindEnum.ROOT, (1, 2), (0, len(parent_text)), parent_text),
        ),
        primary_edges=(
            PrimaryRelationEdge("macro-left", 12, 10, "joint", "joint", NuclearityPatternEnum.NN),
            PrimaryRelationEdge("macro-right", 12, 11, "joint", "joint", NuclearityPatternEnum.NN),
        ),
    )
    stitcher = object.__new__(HierarchicalSectionStitcher)
    stitched = stitcher.stitch_trees(
        parent_document=RstDocument.from_text(parent_text, document_id="parent"),
        sections=sections,
        micro_analyses=[micro, micro],
        macro_analysis=macro,
        output_formalism=OutputFormalismEnum.RST_TREE,
        total_timing_ms=1.0,
    )

    edus = sorted((node for node in stitched.nodes if node.kind is NodeKindEnum.EDU), key=lambda node: node.edu_span)
    assert len(edus) == 6
    assert [node.edu_span for node in edus] == [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6)]
    assert all(parent_text[node.char_span[0] : node.char_span[1]] == node.text for node in stitched.nodes)
