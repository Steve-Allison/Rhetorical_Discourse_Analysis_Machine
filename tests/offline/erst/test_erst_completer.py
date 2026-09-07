"""Unit tests for eRST graph completion and candidate filtering."""

from rdam.rst.contracts import (
    DocumentToken,
    Edu,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
)
from workbench.erst.completer import ErstCompleter


def test_lexical_hits_do_not_authorize_secondary_edges() -> None:
    document = RstDocument.from_tokens_and_edus(
        text="First. However second.",
        tokens=(
            DocumentToken(token_id=0, text="First.", start=0, end=6),
            DocumentToken(token_id=1, text="However", start=7, end=14),
            DocumentToken(token_id=2, text="second.", start=15, end=22),
        ),
        edus=(),
        document_id="doc-test",
    )
    analysis = RstAnalysis(
        document_id="doc-test",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(
            RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 6), text="First."),
            RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(7, 22), text="However second."),
            RstNode(
                node_id=3,
                kind=NodeKindEnum.ROOT,
                edu_span=(1, 2),
                char_span=(0, 22),
                text="First. However second.",
            ),
        ),
        primary_edges=(
            PrimaryRelationEdge(
                edge_id="p-3-1",
                parent_id=3,
                child_id=1,
                relation_raw="span",
                relation_concept="span",
                nuclearity=NuclearityPatternEnum.NS,
            ),
            PrimaryRelationEdge(
                edge_id="p-3-2",
                parent_id=3,
                child_id=2,
                relation_raw="adversative-contrast",
                relation_concept="Contrast",
                nuclearity=NuclearityPatternEnum.NS,
            ),
        ),
    )
    completer = ErstCompleter()
    signals = tuple(completer.detect_lexical_signals(document, analysis))
    candidates = completer.generate_secondary_candidates(document, analysis, signals)
    assert signals
    assert all(not signal.sufficient and signal.confidence is None for signal in signals)
    assert candidates == ()


def test_lexical_signal_detection() -> None:
    text = "She studied hard. However , she failed ."
    tokens = (
        DocumentToken(token_id=0, text="She", start=0, end=3),
        DocumentToken(token_id=1, text="studied", start=4, end=11),
        DocumentToken(token_id=2, text="hard", start=12, end=16),
        DocumentToken(token_id=3, text=".", start=16, end=17),
        DocumentToken(token_id=4, text="However", start=18, end=25),
        DocumentToken(token_id=5, text=",", start=26, end=27),
        DocumentToken(token_id=6, text="she", start=28, end=31),
        DocumentToken(token_id=7, text="failed", start=32, end=38),
        DocumentToken(token_id=8, text=".", start=39, end=40),
    )
    edus = (
        Edu(edu_id=1, text="She studied hard.", start=0, end=17, token_ids=(0, 1, 2, 3)),
        Edu(edu_id=2, text="However , she failed .", start=18, end=40, token_ids=(4, 5, 6, 7, 8)),
    )
    doc = RstDocument.from_tokens_and_edus(text=text, tokens=tokens, edus=edus, document_id="doc-sig")

    nodes = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 17), text="She studied hard."),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(18, 40), text="However , she failed ."),
        RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, 40), text=text),
    )
    primary_edges = (
        PrimaryRelationEdge(
            edge_id="e0",
            parent_id=3,
            child_id=1,
            relation_raw="span",
            relation_concept="span",
            nuclearity=NuclearityPatternEnum.NS,
        ),
        PrimaryRelationEdge(
            edge_id="e1",
            parent_id=3,
            child_id=2,
            relation_raw="Contrast",
            relation_concept="Contrast",
            nuclearity=NuclearityPatternEnum.NS,
        ),
    )
    analysis = RstAnalysis(
        document_id="doc-sig",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=primary_edges,
    )

    completer = ErstCompleter()
    completed = completer.complete_graph(doc, analysis)

    assert completed.formalism == OutputFormalismEnum.ERST_GRAPH
    assert len(completed.signals) == 1
    assert completed.signals[0].signal_type == "dm"
    assert completed.signals[0].signal_subtype == "discourse_marker"
    assert completed.signals[0].token_ids == (4,)
