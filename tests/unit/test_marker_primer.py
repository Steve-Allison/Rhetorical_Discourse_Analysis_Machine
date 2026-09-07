"""Marker candidates preserve predictions and carry no invented probabilities."""

from pathlib import Path

import pytest

from rdam.rst.contracts import (
    DocumentToken,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from rdam.rst.english.relations.primer import DiscourseMarkerPrimer
from rdam.rst.parser import Parser


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
    assert "As a result, production halted."[start2:end2].lower() == rule2.cue

    # Leading whitespace and punctuation
    match3 = primer.find_cue_in_text("  ; in contrast to prior findings")
    assert match3 is not None
    rule3, start3, end3 = match3
    assert rule3.cue == "in contrast"
    assert rule3.coarse_concept == "Contrast"
    assert "  ; in contrast to prior findings"[start3:end3] == rule3.cue

    # No connective
    match4 = primer.find_cue_in_text("The sky is blue today.")
    assert match4 is None


def test_unicode_case_matching_keeps_original_character_coordinates() -> None:
    text = "İ. However, this follows."
    match = DiscourseMarkerPrimer().find_cue_in_text(text)
    assert match is not None
    assert text[match[1] : match[2]] == "However"
    assert match[1] == text.index("However")


def test_nested_constituents_do_not_multiply_a_cue_or_rewrite_span_links() -> None:
    text = "A. However B. C."
    document = RstDocument.from_text(text, document_id="nested")
    nodes = (
        RstNode(1, NodeKindEnum.EDU, (1, 1), (0, 2), text[:2]),
        RstNode(2, NodeKindEnum.EDU, (2, 2), (3, 13), text[3:13]),
        RstNode(3, NodeKindEnum.EDU, (3, 3), (14, 16), text[14:16]),
        RstNode(4, NodeKindEnum.ROOT, (1, 2), (0, 13), text[:13]),
        RstNode(5, NodeKindEnum.ROOT, (1, 3), (0, 16), text),
    )
    edges = (
        PrimaryRelationEdge("e1", 4, 1, "span", "span", NuclearityPatternEnum.NS),
        PrimaryRelationEdge("e2", 4, 2, "elaboration", "elaboration", NuclearityPatternEnum.NS),
        PrimaryRelationEdge("e3", 5, 4, "span", "span", NuclearityPatternEnum.NS),
        PrimaryRelationEdge("e4", 5, 3, "cause", "cause", NuclearityPatternEnum.NS),
    )
    analysis = RstAnalysis("nested", OutputFormalismEnum.RST_TREE, nodes, edges)
    primer = DiscourseMarkerPrimer()
    primed = primer.prime_analysis(analysis, document)
    assert primed.primary_edges == edges
    assert len(primed.signals) == 1
    signal = primed.signals[0]
    assert signal.char_spans == ((3, 10),)
    assert signal.edge_id == "e2"
    assert signal.attachment_candidates == ("e2",)
    assert signal.attachment_basis == "smallest_enclosing_constituent"
    assert primer.prime_analysis(primed, document) == primed


def test_repeated_lexical_occurrences_survive_without_invented_attachments() -> None:
    text = "However A. However B."
    document = RstDocument.from_text(text, document_id="unattached")
    analysis = RstAnalysis("unattached", OutputFormalismEnum.RST_TREE, (), ())
    primed = DiscourseMarkerPrimer().prime_analysis(analysis, document)
    assert [signal.char_spans for signal in primed.signals] == [((0, 7),), ((11, 18),)]
    assert all(signal.edge_id is None and not signal.attachment_candidates for signal in primed.signals)


def test_primer_preserves_low_confidence_and_generic_edges() -> None:
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

    assert primed.primary_edges == initial_analysis.primary_edges
    assert primed.nodes == initial_analysis.nodes

    # Assert signal was created and anchored to token 4 ("However,")
    assert len(primed.signals) == 1
    sig = primed.signals[0]
    assert sig.signal_type == "dm"
    assert sig.signal_subtype == "lexical_candidate"
    assert sig.confidence is None
    assert not sig.sufficient
    assert sig.attachment_candidates == ("e1",)
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

    primed = primer.prime_analysis(initial_analysis, doc)
    assert primed.primary_edges[0].relation_concept == "CustomDomain"


@pytest.mark.slow
def test_parser_parse_document_with_marker_priming() -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", "gumrrg-eb1d5745f3a1", device="cpu"
    )
    doc = RstDocument.from_text(
        "The algorithm ran efficiently. Because the dataset was pre-cached, latency stayed low."
    )

    analysis = parser.parse_document(doc, prime_markers=True)

    assert analysis.document_id == doc.document_id
    assert len(analysis.nodes) >= 2
    unprimed = parser.parse_document(doc, prime_markers=False)
    assert analysis.primary_edges == unprimed.primary_edges
    assert analysis.signals
    assert all(signal.confidence is None and not signal.sufficient for signal in analysis.signals)
    assert all(signal.token_ids for signal in analysis.signals)
