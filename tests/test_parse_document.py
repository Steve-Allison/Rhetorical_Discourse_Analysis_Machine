"""Unit tests for Parser.parse_document integration."""

from isanlp.annotation_rst import DiscourseUnit
import pytest

from isanlp_rst import (
    OutputFormalismEnum,
    Parser,
    RstAnalysis,
    RstDocument,
)


class DummyPredictor:
    def __init__(self) -> None:
        self.model_dir = "dummy_model"

    def parse_rst(self, text: str) -> dict[str, list[DiscourseUnit]]:
        leaf1 = DiscourseUnit(id=1, text="First sentence.", start=0, end=15, relation="span", nuclearity="")
        leaf2 = DiscourseUnit(id=2, text="Second sentence.", start=16, end=32, relation="elaboration", nuclearity="NS")
        root = DiscourseUnit(id=3, left=leaf1, right=leaf2, start=0, end=32, relation="elaboration", nuclearity="NS")
        return {"rst": [root]}

    def parse_from_edus(self, edus: list[str]) -> dict[str, list[DiscourseUnit]]:
        return self.parse_rst(" ".join(edus))


def test_parse_document_from_text(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = Parser.__new__(Parser)
    parser.predictor = DummyPredictor()  # type: ignore[assignment]
    parser.hf_model_version = "gumrrg"

    doc = RstDocument.from_text("First sentence. Second sentence.", document_id="doc-test-1")
    analysis = parser.parse_document(doc, output="rst_tree")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "doc-test-1"
    assert analysis.formalism == OutputFormalismEnum.RST_TREE
    assert len(analysis.nodes) == 3
    assert len(analysis.primary_edges) == 2
    assert analysis.timing.total_ms >= 0.0
    assert analysis.provenance.model_id == "gumrrg"


def test_parse_document_from_edus(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = Parser.__new__(Parser)
    parser.predictor = DummyPredictor()  # type: ignore[assignment]
    parser.hf_model_version = "rstdt"

    doc = RstDocument.from_edus(["First sentence.", "Second sentence."], document_id="doc-test-2")
    analysis = parser.parse_document(doc, output="erst_graph")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "doc-test-2"
    assert analysis.formalism == OutputFormalismEnum.ERST_GRAPH
    assert len(analysis.nodes) == 3
