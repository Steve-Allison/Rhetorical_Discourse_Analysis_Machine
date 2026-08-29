"""Synthetic formal-conformance matrix for eRST secondary-edge decoding."""

import pytest

from isanlp_rst.contracts import (
    DecodeRejectionReason,
    ErstDecoderConfig,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
)
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate
from isanlp_rst.erst.decoder import ErstSecondaryEdgeDecoder


def _analysis() -> RstAnalysis:
    nodes = tuple(
        RstNode(
            node_id=node_id,
            kind=NodeKindEnum.ROOT if node_id == 5 else NodeKindEnum.EDU,
            edu_span=(1, 4) if node_id == 5 else (node_id, node_id),
            char_span=(0, 39) if node_id == 5 else ((node_id - 1) * 10, node_id * 10 - 1),
            text="root" if node_id == 5 else f"node {node_id}",
        )
        for node_id in range(1, 6)
    )
    primary_edges = tuple(
        PrimaryRelationEdge(
            edge_id=f"p-5-{child_id}",
            parent_id=5,
            child_id=child_id,
            relation_raw="span" if child_id == 1 else "elaboration-additional",
            relation_concept="Elaboration",
            nuclearity=NuclearityPatternEnum.NS,
        )
        for child_id in range(1, 5)
    )
    return RstAnalysis(
        document_id="formal-conformance",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=primary_edges,
    )


def _candidate(
    source_id: int,
    target_id: int,
    *,
    signal_ids: tuple[str, ...] = ("sig-valid",),
) -> SecondaryEdgeCandidate:
    return SecondaryEdgeCandidate(
        document_id="formal-conformance",
        source_id=source_id,
        target_id=target_id,
        source_text=f"node {source_id}",
        target_text=f"node {target_id}",
        source_char_span=(0, 1),
        target_char_span=(2, 3),
        structural_features=(0.0,) * 9,
        is_gold_edge=False,
        signal_ids=signal_ids,
    )


def _decoder() -> ErstSecondaryEdgeDecoder:
    return ErstSecondaryEdgeDecoder(
        ErstDecoderConfig(
            edge_threshold=0.5,
            raw_relation_inventory=("adversative-contrast",),
        ),
        ontology_adapter=lambda raw: "Contrast" if raw == "adversative-contrast" else raw,
    )


@pytest.mark.parametrize(
    "pairs",
    [
        ((1, 2), (2, 1)),  # cyclic
        ((1, 3), (2, 4)),  # crossing/non-projective
        ((1, 2), (1, 3), (1, 4)),  # concurrent and unrestricted out-degree
        ((4, 1),),  # reverse direction
        ((5, 1), (1, 5)),  # direct primary overlap and reverse
    ],
)
def test_formally_permitted_graph_shapes_are_accepted(
    pairs: tuple[tuple[int, int], ...],
) -> None:
    candidates = tuple(_candidate(source, target) for source, target in pairs)
    decoded = _decoder().decode_with_receipt(
        _analysis(),
        candidates,
        [0.9] * len(candidates),
        [[1.0]] * len(candidates),
        sufficient_signal_ids={"sig-valid"},
    )
    assert {(edge.source_id, edge.target_id) for edge in decoded.edges} == set(pairs)
    assert all(edge.relation_raw == "adversative-contrast" for edge in decoded.edges)
    assert all(edge.relation_concept == "Contrast" for edge in decoded.edges)
    assert decoded.receipt.accepted_count == len(pairs)
    assert sum(decoded.receipt.formal_rejections.values()) == 0


def test_only_four_formal_constraints_reject_above_threshold_candidates() -> None:
    candidates = (
        _candidate(1, 1),
        _candidate(1, 99),
        _candidate(2, 3, signal_ids=()),
        _candidate(1, 2),
        _candidate(1, 2),
        _candidate(3, 4),
    )
    decoded = _decoder().decode_with_receipt(
        _analysis(),
        candidates,
        [0.9, 0.9, 0.9, 0.9, 0.8, 0.1],
        [[1.0]] * len(candidates),
        sufficient_signal_ids={"sig-valid"},
        streamed_batch_count=2,
    )
    assert {(edge.source_id, edge.target_id) for edge in decoded.edges} == {(1, 2)}
    assert decoded.receipt.below_threshold_count == 1
    assert decoded.receipt.formal_rejections == {
        DecodeRejectionReason.INSUFFICIENT_SIGNAL: 1,
        DecodeRejectionReason.SELF_LOOP: 1,
        DecodeRejectionReason.INVENTED_NODE: 1,
        DecodeRejectionReason.DUPLICATE_DIRECTED_PAIR: 1,
    }
    assert decoded.receipt.candidate_count == 6
    assert decoded.receipt.streamed_batch_count == 2


def test_signal_id_must_be_in_the_validated_sufficient_set() -> None:
    decoded = _decoder().decode_with_receipt(
        _analysis(),
        (_candidate(1, 2, signal_ids=("sig-unvalidated",)),),
        (0.9,),
        ((1.0,),),
        sufficient_signal_ids={"sig-valid"},
    )
    assert decoded.edges == ()
    assert decoded.receipt.formal_rejections[DecodeRejectionReason.INSUFFICIENT_SIGNAL] == 1


def test_invalid_score_shapes_and_values_fail_instead_of_disappearing() -> None:
    decoder = _decoder()
    analysis = _analysis()
    candidate = _candidate(1, 2)
    with pytest.raises(ValueError, match="counts must match"):
        decoder.decode_with_receipt(
            analysis,
            (candidate,),
            (),
            ((1.0,),),
            sufficient_signal_ids={"sig-valid"},
        )
    with pytest.raises(ValueError, match="inventory"):
        decoder.decode_with_receipt(
            analysis,
            (candidate,),
            (0.9,),
            ((1.0, 2.0),),
            sufficient_signal_ids={"sig-valid"},
        )
