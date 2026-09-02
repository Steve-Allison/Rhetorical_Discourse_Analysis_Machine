"""Integration tests for ModernBERT parser facade integration."""

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts import OutputFormalismEnum, RstAnalysis, RstDocument
from rdam.rst.parser import Parser


def test_parser_modernbert_family_resolution() -> None:
    """Verify Parser resolves modernbert family and versions cleanly."""
    parser = Parser(family="modernbert", device="cpu")
    assert parser.family == "modernbert"
    assert parser.predictor is not None
    assert parser.predictor._device.type == "cpu"


def test_parser_modernbert_parse_tree() -> None:
    """Verify parser.parse_tree returns a valid hierarchical DiscourseUnit."""
    parser = Parser(family="modernbert", device="cpu")
    text = (
        "ModernBERT utilizes rotary position embeddings and FlashAttention. "
        "Because of this architecture, it achieves superior discourse parsing quality."
    )
    root = parser.parse_tree(text)
    assert isinstance(root, DiscourseUnit)
    assert root.text == text
    assert root.nuclearity in ("N", "S", "NS", "SN", "NN")
    assert root.left is not None
    assert root.right is not None


def test_parser_modernbert_parse_document() -> None:
    """Verify parser.parse_document returns a valid RstAnalysis."""
    parser = Parser(family="modernbert", device="cpu")
    text = (
        "Primary claims establish the thesis of the argument. "
        "Furthermore, supporting evidence reinforces the nuclearity of the claim."
    )
    doc = RstDocument.from_text(text, document_id="doc_modernbert_test")
    analysis = parser.parse_document(doc, output="rst_tree")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "doc_modernbert_test"
    assert analysis.formalism == OutputFormalismEnum.RST_TREE
    assert len(analysis.nodes) > 0
    assert len(analysis.primary_edges) > 0


def test_parser_modernbert_from_edus() -> None:
    """Verify parser.from_edus parses pre-segmented EDUs."""
    parser = Parser(family="modernbert", device="cpu")
    edus = [
        "First elementary discourse unit.",
        "Second elementary discourse unit elaborating the first.",
        "Third concluding unit.",
    ]
    res = parser.from_edus(edus)
    assert "rst" in res
    assert len(res["rst"]) == 1
    assert isinstance(res["rst"][0], DiscourseUnit)
