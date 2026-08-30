"""Unit tests for Parser.parse_document integration."""

from isanlp_rst.annotation_rst import DiscourseUnit
import pytest

from isanlp_rst import (
    ErstCapabilityError,
    OutputFormalismEnum,
    Parser,
    RstAnalysis,
    RstDocument,
)
from isanlp_rst.erst.converter import du_to_analysis


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
    object.__setattr__(parser, "predictor", DummyPredictor())
    parser.hf_model_version = "gumrrg"

    doc = RstDocument.from_text("First sentence. Second sentence.", document_id="doc-test-1")
    expected = du_to_analysis(
        DummyPredictor().parse_rst(doc.text)["rst"][0],
        document_id=doc.document_id,
    )

    class _Semantic:
        analysis = expected

    class _Result:
        semantic = _Semantic()

    monkeypatch.setattr(parser, "analyse_document", lambda *_args, **_kwargs: _Result())
    analysis = parser.parse_document(doc, output="rst_tree")

    assert isinstance(analysis, RstAnalysis)
    assert analysis.document_id == "doc-test-1"
    assert analysis.formalism == OutputFormalismEnum.RST_TREE
    assert len(analysis.nodes) == 3
    assert len(analysis.primary_edges) == 2
    assert analysis == expected


def test_parse_document_from_edus_requires_validated_erst_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = Parser.__new__(Parser)
    object.__setattr__(parser, "predictor", DummyPredictor())
    parser.hf_model_version = "rstdt"
    parser.segmenter = None
    parser.erst_checkpoint = None

    doc = RstDocument.from_edus(["First sentence.", "Second sentence."], document_id="doc-test-2")
    with pytest.raises(ErstCapabilityError, match="validated completion bundle"):
        parser.parse_document(doc, output="erst_graph")


def test_du_to_analysis_nuclearity_and_relations() -> None:
    from isanlp_rst.contracts import NuclearityPatternEnum
    from isanlp_rst.erst.converter import du_to_analysis
    from workbench.evaluation.rst import SoftParsevalScorer

    # 1. NS relation: left is Nucleus (span), right is Satellite (elaboration)
    l1 = DiscourseUnit(id=1, text="Nucleus clause.", start=0, end=15, relation="span")
    r1 = DiscourseUnit(id=2, text="Satellite clause.", start=16, end=33, relation="elaboration")
    root_ns = DiscourseUnit(id=3, left=l1, right=r1, start=0, end=33, relation="elaboration", nuclearity="NS")

    ana_ns = du_to_analysis(root_ns, document_id="doc-ns")
    assert len(ana_ns.nodes) == 3
    assert len(ana_ns.primary_edges) == 2
    # Left edge connects root to left child with relation 'span'
    left_edge = next(e for e in ana_ns.primary_edges if e.child_id == 1)
    right_edge = next(e for e in ana_ns.primary_edges if e.child_id == 2)
    assert left_edge.relation_raw == "span"
    assert right_edge.relation_raw == "elaboration"
    assert left_edge.nuclearity == NuclearityPatternEnum.NS
    assert right_edge.nuclearity == NuclearityPatternEnum.NS

    # 2. SN relation: left is Satellite (condition), right is Nucleus (span)
    l2 = DiscourseUnit(id=1, text="If condition.", start=0, end=13, relation="condition")
    r2 = DiscourseUnit(id=2, text="Main clause.", start=14, end=26, relation="span")
    root_sn = DiscourseUnit(id=3, left=l2, right=r2, start=0, end=26, relation="condition", nuclearity="SN")

    ana_sn = du_to_analysis(root_sn, document_id="doc-sn")
    left_edge_sn = next(e for e in ana_sn.primary_edges if e.child_id == 1)
    right_edge_sn = next(e for e in ana_sn.primary_edges if e.child_id == 2)
    assert left_edge_sn.relation_raw == "condition"
    assert right_edge_sn.relation_raw == "span"
    assert left_edge_sn.nuclearity == NuclearityPatternEnum.SN
    assert right_edge_sn.nuclearity == NuclearityPatternEnum.SN

    # 3. NN relation: both left and right are Nuclei (joint)
    l3 = DiscourseUnit(id=1, text="First point.", start=0, end=12, relation="joint")
    r3 = DiscourseUnit(id=2, text="Second point.", start=13, end=26, relation="joint")
    root_nn = DiscourseUnit(id=3, left=l3, right=r3, start=0, end=26, relation="joint", nuclearity="NN")

    ana_nn = du_to_analysis(root_nn, document_id="doc-nn")
    left_edge_nn = next(e for e in ana_nn.primary_edges if e.child_id == 1)
    right_edge_nn = next(e for e in ana_nn.primary_edges if e.child_id == 2)
    assert left_edge_nn.relation_raw == "joint"
    assert right_edge_nn.relation_raw == "joint"
    assert left_edge_nn.nuclearity == NuclearityPatternEnum.NN
    assert right_edge_nn.nuclearity == NuclearityPatternEnum.NN

    # Evaluation remains available through the canonical offline workbench.
    scorer = SoftParsevalScorer()
    assert scorer is not None
