"""Unit tests for eRST graph completion and candidate filtering."""

from isanlp_rst.contracts import (
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
from isanlp_rst.english.erst import CompleterConfig, ErstCompleter


def test_secondary_candidate_generation_bounds() -> None:
    # 5 EDUs in a tree
    nodes = tuple(
        RstNode(node_id=i, kind=NodeKindEnum.EDU, edu_span=(i, i), char_span=(i * 10, (i + 1) * 10), text=f"EDU {i}")
        for i in range(1, 6)
    )
    primary_edges = (
        PrimaryRelationEdge(
            edge_id="e1",
            parent_id=10,
            child_id=1,
            relation_raw="span",
            relation_concept="span",
            nuclearity=NuclearityPatternEnum.NS,
        ),
        PrimaryRelationEdge(
            edge_id="e2",
            parent_id=10,
            child_id=2,
            relation_raw="Elaboration",
            relation_concept="Elaboration",
            nuclearity=NuclearityPatternEnum.NS,
        ),
    )

    analysis = RstAnalysis(
        document_id="doc-test",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=primary_edges,
    )

    completer = ErstCompleter(CompleterConfig(max_edu_distance=2, max_candidates_per_document=10))
    candidates = completer.generate_secondary_candidates(analysis)

    assert len(candidates) > 0
    assert len(candidates) <= 10
    # Verify distance constraint
    for src, tgt in candidates:
        src_node = analysis.get_node(src)
        tgt_node = analysis.get_node(tgt)
        assert src_node is not None and tgt_node is not None
        assert abs(src_node.edu_span[0] - tgt_node.edu_span[0]) <= 2


def test_lexical_signal_detection() -> None:
    text = "She studied hard. However , she failed ."
    tokens = (
        DocumentToken(token_id=0, text="She", start=0, end=3),
        DocumentToken(token_id=1, text="studied", start=4, end=11),
        DocumentToken(token_id=2, text="hard", start=12, end=16),
        DocumentToken(token_id=3, text=".", start=16, end=17),
        DocumentToken(token_id=4, text="However", start=18, end=25),
        DocumentToken(token_id=5, text=",", start=25, end=26),
        DocumentToken(token_id=6, text="she", start=27, end=30),
        DocumentToken(token_id=7, text="failed", start=31, end=37),
        DocumentToken(token_id=8, text=".", start=37, end=38),
    )
    edus = (
        Edu(edu_id=1, text="She studied hard .", start=0, end=17, token_ids=(0, 1, 2, 3)),
        Edu(edu_id=2, text="However , she failed .", start=18, end=38, token_ids=(4, 5, 6, 7, 8)),
    )
    doc = RstDocument.from_tokens_and_edus(text=text, tokens=tokens, edus=edus, document_id="doc-sig")

    nodes = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 17), text="She studied hard ."),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(18, 38), text="However , she failed ."),
        RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, 38), text=text),
    )
    primary_edges = (
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
    assert completed.signals[0].signal_subtype == "dm"
    assert completed.signals[0].token_ids == (4,)
