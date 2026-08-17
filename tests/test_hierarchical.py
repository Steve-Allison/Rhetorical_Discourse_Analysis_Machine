"""Unit and integration tests for Two-Stage Macro/Micro hierarchical parsing and tree stitching."""

import pytest

from isanlp_rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
    TextSpan,
)
from isanlp_rst.hierarchical.stitcher import HierarchicalSectionStitcher
from isanlp_rst.parser import Parser


def test_detect_sections_double_newline() -> None:
    text = "Paragraph one is here.\n\nParagraph two follows.\n\n\nParagraph three ends."
    doc = RstDocument.from_text(text, document_id="doc_multi")

    # We can pass dummy parser since we only test detect_sections
    stitcher = HierarchicalSectionStitcher(parser=None)  # type: ignore[arg-type]
    sections = stitcher.detect_sections(doc)

    assert len(sections) == 3
    assert sections[0].text == "Paragraph one is here."
    assert sections[1].text == "Paragraph two follows."
    assert sections[2].text == "Paragraph three ends."
    assert sections[0].char_span == (0, 22)


def test_detect_sections_custom_boundaries() -> None:
    text = "# Section 1\nContent A\n# Section 2\nContent B"
    doc = RstDocument.from_text(text, document_id="doc_custom")

    custom_bounds = [
        TextSpan(start=0, end=21, text="# Section 1\nContent A"),
        TextSpan(start=22, end=len(text), text="# Section 2\nContent B"),
    ]

    stitcher = HierarchicalSectionStitcher(parser=None)  # type: ignore[arg-type]
    sections = stitcher.detect_sections(doc, custom_boundaries=custom_bounds)

    assert len(sections) == 2
    assert "Section 1" in sections[0].text
    assert "Section 2" in sections[1].text


def test_stitch_trees_synthetic() -> None:
    text = "Sentence one. Sentence two. Sentence three. Sentence four."
    doc = RstDocument.from_text(text, document_id="doc_synth")

    stitcher = HierarchicalSectionStitcher(parser=None)  # type: ignore[arg-type]
    sections = [
        stitcher.detect_sections(RstDocument.from_text("Sentence one. Sentence two.", document_id="s1"))[0],
        stitcher.detect_sections(RstDocument.from_text("Sentence three. Sentence four.", document_id="s2"))[0],
    ]
    # Update char spans to reflect global coordinates
    sections[0] = type(sections[0])(
        section_id=0,
        char_span=(0, 27),
        text="Sentence one. Sentence two.",
        tokens=(),
        edus=None,
    )
    sections[1] = type(sections[1])(
        section_id=1,
        char_span=(28, 58),
        text="Sentence three. Sentence four.",
        tokens=(),
        edus=None,
    )

    # Micro analysis 1: 2 EDUs joined into Root 3
    ana1 = RstAnalysis(
        document_id="s1",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 13), text="Sentence one."),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(14, 27), text="Sentence two."),
            RstNode(
                node_id=3,
                kind=NodeKindEnum.ROOT,
                edu_span=(1, 2),
                char_span=(0, 27),
                text="Sentence one. Sentence two.",
            ),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="e1",
                parent_id=3,
                child_id=1,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
            PrimaryRelationEdge(
                edge_id="e2",
                parent_id=3,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Elaboration",
                relation_concept="Elaboration",
            ),
        ),
    )

    # Micro analysis 2: 2 EDUs joined into Root 3
    ana2 = RstAnalysis(
        document_id="s2",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 15), text="Sentence three."),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(16, 30), text="Sentence four."),
            RstNode(
                node_id=3,
                kind=NodeKindEnum.ROOT,
                edu_span=(1, 2),
                char_span=(0, 30),
                text="Sentence three. Sentence four.",
            ),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="e1",
                parent_id=3,
                child_id=1,
                nuclearity=NuclearityPatternEnum.NN,
                relation_raw="Joint",
                relation_concept="Joint",
            ),
            PrimaryRelationEdge(
                edge_id="e2",
                parent_id=3,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NN,
                relation_raw="Joint",
                relation_concept="Joint",
            ),
        ),
    )

    # Macro analysis: joins Section 1 and Section 2
    macro_ana = RstAnalysis(
        document_id="macro",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 10), text="Sec1"),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(11, 20), text="Sec2"),
            RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, 20), text="Sec1 Sec2"),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="me1",
                parent_id=3,
                child_id=1,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Contrast",
                relation_concept="Contrast",
            ),
            PrimaryRelationEdge(
                edge_id="me2",
                parent_id=3,
                child_id=2,
                nuclearity=NuclearityPatternEnum.NS,
                relation_raw="Contrast",
                relation_concept="Contrast",
            ),
        ),
    )

    stitched = stitcher.stitch_trees(
        parent_document=doc,
        sections=sections,
        micro_analyses=[ana1, ana2],
        macro_analysis=macro_ana,
        output_formalism=OutputFormalismEnum.RST_TREE,
        total_timing_ms=50.0,
    )

    # Verifications:
    # 4 EDUs + 2 micro roots + 1 macro root = 7 nodes
    assert len(stitched.nodes) == 7
    # 4 micro edges + 2 macro edges = 6 primary edges
    assert len(stitched.primary_edges) == 6

    root = stitched.root_node
    assert root is not None
    assert root.edu_span == (1, 4)
    assert root.char_span == (0, 58)

    # Check global EDU spans
    edu_nodes = [n for n in stitched.nodes if n.kind == NodeKindEnum.EDU]
    assert len(edu_nodes) == 4
    assert [n.edu_span for n in edu_nodes] == [(1, 1), (2, 2), (3, 3), (4, 4)]


@pytest.fixture(scope="module")
def parser_cpu() -> Parser:
    return Parser(hf_model_version="gumrrg", device="cpu")


@pytest.mark.slow
def test_hierarchical_parser_e2e(parser_cpu: Parser) -> None:
    text = (
        "The project started in spring.\n"
        "It aimed to improve performance.\n\n"
        "However, unexpected obstacles occurred.\n"
        "Several experiments failed initially.\n\n"
        "Finally, the team resolved all issues.\n"
        "The system reached high accuracy."
    )
    doc = RstDocument.from_text(text, document_id="doc_e2e_hierarchical")

    analysis = parser_cpu.parse_hierarchical(doc)

    assert analysis.document_id == "doc_e2e_hierarchical"
    assert len(analysis.nodes) > 6
    assert len(analysis.primary_edges) >= 5

    root = analysis.root_node
    assert root is not None
    assert root.char_span == (0, len(text))
    assert root.edu_span[0] == 1
    assert root.edu_span[1] >= 4


@pytest.mark.slow
def test_hierarchical_single_section_delegates(parser_cpu: Parser) -> None:
    text = "Short text with only one paragraph."
    doc = RstDocument.from_text(text, document_id="doc_single")

    analysis = parser_cpu.parse_hierarchical(doc)
    assert analysis.document_id == "doc_single"
    assert len(analysis.nodes) >= 1
