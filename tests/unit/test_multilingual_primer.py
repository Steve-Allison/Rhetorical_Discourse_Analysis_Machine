"""Unit tests for multilingual discourse marker priming and cue detection."""

from rdam.rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from rdam.rst.relations.primer import DiscourseMarkerPrimer


def test_multilingual_marker_cue_detection():
    # Russian
    ru_primer = DiscourseMarkerPrimer(language="ru")
    cue_ru = ru_primer.find_cue_in_text("Однако это не помогло.")
    assert cue_ru is not None
    assert cue_ru[0].coarse_concept == "Contrast"
    assert cue_ru[0].cue == "однако"

    # Spanish
    es_primer = DiscourseMarkerPrimer(language="es")
    cue_es = es_primer.find_cue_in_text("Sin embargo, todo cambió.")
    assert cue_es is not None
    assert cue_es[0].coarse_concept == "Contrast"
    assert cue_es[0].cue == "sin embargo"

    # German
    de_primer = DiscourseMarkerPrimer(language="de")
    cue_de = de_primer.find_cue_in_text("Deshalb ist es wichtig.")
    assert cue_de is not None
    assert cue_de[0].coarse_concept == "Cause"
    assert cue_de[0].cue == "deshalb"

    # French
    fr_primer = DiscourseMarkerPrimer(language="fr")
    cue_fr = fr_primer.find_cue_in_text("Cependant, il faut attendre.")
    assert cue_fr is not None
    assert cue_fr[0].coarse_concept == "Contrast"
    assert cue_fr[0].cue == "cependant"

    # Chinese
    zh_primer = DiscourseMarkerPrimer(language="zh")
    cue_zh = zh_primer.find_cue_in_text("但是情况改变了。")
    assert cue_zh is not None
    assert cue_zh[0].coarse_concept == "Contrast"
    assert cue_zh[0].cue == "但是"


def test_multilingual_prime_analysis():
    doc = RstDocument(
        document_id="ru_doc",
        text="Первое предложение. Однако второе предложение продолжается.",
        language="ru",
    )
    node1 = RstNode(
        node_id=1,
        kind=NodeKindEnum.EDU,
        edu_span=(1, 1),
        char_span=(0, 19),
        text="Первое предложение.",
    )
    node2 = RstNode(
        node_id=2,
        kind=NodeKindEnum.EDU,
        edu_span=(2, 2),
        char_span=(21, 60),
        text="Однако второе предложение продолжается.",
    )
    root = RstNode(
        node_id=3,
        kind=NodeKindEnum.ROOT,
        edu_span=(1, 2),
        char_span=(0, 60),
        text=doc.text,
    )
    edge = PrimaryRelationEdge(
        edge_id="e1",
        parent_id=3,
        child_id=2,
        relation_raw="elaboration",
        relation_concept="Elaboration",
        nuclearity=NuclearityPatternEnum.NS,
        confidence=0.60,
    )
    analysis = RstAnalysis(
        document_id="ru_doc",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(node1, node2, root),
        primary_edges=(edge,),
    )

    primer = DiscourseMarkerPrimer()
    primed = primer.prime_analysis(analysis, doc)

    assert len(primed.signals) == 1
    assert primed.signals[0].signal_type == "dm"
    assert primed.primary_edges[0].relation_concept == "Contrast"
    assert primed.primary_edges[0].calibrated is True
