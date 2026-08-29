"""Unit tests for DiscourseMarkerPrimer and relation classification refinement."""

import pytest

from isanlp_rst.contracts import (
    DocumentToken,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from isanlp_rst.english.relations.primer import DiscourseMarkerPrimer
from isanlp_rst.parser import Parser


def test_primer_cue_matching() -> None:
    primer = DiscourseMarkerPrimer()

    # Exact start
    match1 = primer.find_cue_in_text("However, the experiment failed.")
    assert match1 is not None
    rule1, start1, end1 = match1
    assert rule1.cue == "however"
    assert rule1.coarse_concept == "Contrast"
    assert start1 == 0
    assert end1 == 7

    # Multi-word connective
    match2 = primer.find_cue_in_text("As a result, production halted.")
    assert match2 is not None
    rule2, start2, end2 = match2
    assert rule2.cue == "as a result"
    assert rule2.coarse_concept == "Cause"

    # Leading whitespace and punctuation
    match3 = primer.find_cue_in_text("  ; in contrast to prior findings")
    assert match3 is not None
    rule3, start3, end3 = match3
    assert rule3.cue == "in contrast"
    assert rule3.coarse_concept == "Contrast"

    # No connective
    match4 = primer.find_cue_in_text("The sky is blue today.")
    assert match4 is None


def test_primer_primes_low_confidence_and_generic_edges() -> None:
    primer = DiscourseMarkerPrimer()

    doc = RstDocument(
        document_id="doc_primer",
        text="The system was fast. However, it used excessive memory.",
        tokens=(
            DocumentToken(token_id=0, text="The", start=0, end=3),
            DocumentToken(token_id=1, text="system", start=4, end=10),
            DocumentToken(token_id=2, text="was", start=11, end=14),
            DocumentToken(token_id=3, text="fast.", start=15, end=20),
            DocumentToken(token_id=4, text="However,", start=21, end=29),
            DocumentToken(token_id=5, text="it", start=30, end=32),
            DocumentToken(token_id=6, text="used", start=33, end=37),
            DocumentToken(token_id=7, text="excessive", start=38, end=47),
            DocumentToken(token_id=8, text="memory.", start=48, end=55),
        ),
        edus=None,
    )

    # Initial analysis with a generic 'Elaboration' relation predicted by neural baseline
    initial_analysis = RstAnalysis(
        document_id="doc_primer",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 20), text="The system was fast."),
            RstNode(
                node_id=2,
                kind=NodeKindEnum.EDU,
                edu_span=(2, 2),
                char_span=(21, 55),
                text="However, it used excessive memory.",
            ),
            RstNode(
                node_id=3,
                kind=NodeKindEnum.ROOT,
                edu_span=(1, 2),
                char_span=(0, 55),
                text="The system was fast. However, it used excessive memory.",
            ),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="e1",
                parent_id=3,
                child_id=2,
                relation_raw="elaboration-additional",
                relation_concept="Elaboration",
                nuclearity=NuclearityPatternEnum.NS,
                confidence=0.55,
            ),
        ),
    )

    primed = primer.prime_analysis(initial_analysis, doc)

    # Assert relation was refined to Contrast
    assert len(primed.primary_edges) == 1
    edge = primed.primary_edges[0]
    assert edge.relation_concept == "Contrast"
    assert edge.relation_raw == "contrast"
    assert edge.calibrated is True
    assert edge.confidence == 0.88

    # Assert signal was created and anchored to token 4 ("However,")
    assert len(primed.signals) == 1
    sig = primed.signals[0]
    assert sig.signal_type == "dm"
    assert sig.signal_subtype == "dm"
    assert sig.edge_id == "e1"
    assert 4 in sig.token_ids


def test_primer_respects_high_confidence_predictions() -> None:
    primer = DiscourseMarkerPrimer()

    doc = RstDocument.from_text("Statement A. However, Statement B.", document_id="doc_high_conf")

    initial_analysis = RstAnalysis(
        document_id="doc_high_conf",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 12), text="Statement A."),
            RstNode(
                node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(13, 34), text="However, Statement B."
            ),
            RstNode(
                node_id=3,
                kind=NodeKindEnum.ROOT,
                edu_span=(1, 2),
                char_span=(0, 34),
                text="Statement A. However, Statement B.",
            ),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="e1",
                parent_id=3,
                child_id=2,
                relation_raw="custom_domain_relation",
                relation_concept="CustomDomain",
                nuclearity=NuclearityPatternEnum.NS,
                confidence=0.98,  # Overwhelmingly high confidence model prediction
            ),
        ),
    )

    # With min_model_confidence_to_override=0.90, confidence 0.98 is NOT overridden
    primed = primer.prime_analysis(initial_analysis, doc, min_model_confidence_to_override=0.90)
    assert primed.primary_edges[0].relation_concept == "CustomDomain"


@pytest.mark.slow
def test_parser_parse_document_with_marker_priming() -> None:
    parser = Parser(family="modernbert", device="cpu")
    doc = RstDocument.from_text(
        "The algorithm ran efficiently. Because the dataset was pre-cached, latency stayed low."
    )

    analysis = parser.parse_document(doc, prime_markers=True)

    assert analysis.document_id == doc.document_id
    assert len(analysis.nodes) >= 2
    # Check that at least one edge has Cause or Explanation or Contrast relation
    concepts = {e.relation_concept for e in analysis.primary_edges}
    assert any(c in {"Cause", "Explanation", "Contrast", "Elaboration"} for c in concepts)
