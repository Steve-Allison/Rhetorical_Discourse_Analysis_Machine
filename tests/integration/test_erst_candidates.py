"""Formal completeness and identity tests for the shared eRST candidate generator."""

from dataclasses import replace

from isanlp_rst.contracts import (
    DiscourseSignal,
    DocumentToken,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
    SecondaryRelationEdge,
    SignalDetectionMethod,
    SignalDetectorProvenance,
)
from isanlp_rst.erst.candidates import (
    CandidateMode,
    generate_secondary_edge_candidates,
    iter_candidate_batches,
    iter_secondary_edge_candidates,
)


def _document() -> RstDocument:
    return RstDocument.from_tokens_and_edus(
        text="However first. Second.",
        tokens=(
            DocumentToken(token_id=10, text="However", start=0, end=7, sentence_id=0),
            DocumentToken(token_id=20, text="first.", start=8, end=14, sentence_id=0),
            DocumentToken(token_id=30, text="Second.", start=15, end=22, sentence_id=1),
        ),
        edus=(),
        document_id="candidate-doc",
    )


def _signal(*, sufficient: bool = True) -> DiscourseSignal:
    return DiscourseSignal(
        signal_id="sig-1",
        edge_id=None,
        signal_type="dm",
        signal_subtype="discourse_marker",
        token_ids=(10,),
        char_spans=((0, 7),),
        compatible_relations=("adversative-contrast",),
        detector=SignalDetectorProvenance(
            detector_id="candidate-test",
            detector_version="1.0.0",
            method=SignalDetectionMethod.RULE,
        ),
        confidence=0.9,
        sufficient=sufficient,
    )


def _analysis(*, with_gold: bool = False, signal: DiscourseSignal | None = None) -> RstAnalysis:
    nodes = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 14), text="However first."),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(15, 22), text="Second."),
        RstNode(node_id=3, kind=NodeKindEnum.ROOT, edu_span=(1, 2), char_span=(0, 22), text="However first. Second."),
    )
    primary = (
        PrimaryRelationEdge(
            edge_id="p-1",
            parent_id=3,
            child_id=1,
            relation_raw="span",
            relation_concept="span",
            nuclearity=NuclearityPatternEnum.NS,
        ),
        PrimaryRelationEdge(
            edge_id="p-2",
            parent_id=3,
            child_id=2,
            relation_raw="elaboration-additional",
            relation_concept="Elaboration",
            nuclearity=NuclearityPatternEnum.NS,
        ),
    )
    secondary = (
        SecondaryRelationEdge(
            edge_id="s-1",
            source_id=1,
            target_id=2,
            relation_raw="adversative-contrast",
            relation_concept="Contrast",
        ),
    ) if with_gold else ()
    return RstAnalysis(
        document_id="candidate-doc",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=nodes,
        primary_edges=primary,
        secondary_edges=secondary,
        signals=(signal or _signal(),),
    )


def test_complete_ordered_pair_space_includes_primary_overlap_and_both_directions() -> None:
    candidates = generate_secondary_edge_candidates(_document(), _analysis())
    pairs = {(candidate.source_id, candidate.target_id) for candidate in candidates}
    assert pairs == {(1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2)}
    assert (3, 1) in pairs and (1, 3) in pairs
    assert all(candidate.signal_ids == ("sig-1",) for candidate in candidates)


def test_gold_edges_annotate_but_never_change_candidate_membership() -> None:
    without_gold = generate_secondary_edge_candidates(_document(), _analysis(with_gold=False))
    with_gold = generate_secondary_edge_candidates(_document(), _analysis(with_gold=True))
    without_identity = tuple(
        (candidate.source_id, candidate.target_id, candidate.signal_ids) for candidate in without_gold
    )
    with_identity = tuple(
        (candidate.source_id, candidate.target_id, candidate.signal_ids) for candidate in with_gold
    )
    assert without_identity == with_identity
    assert without_gold == with_gold
    gold = next(candidate for candidate in with_gold if (candidate.source_id, candidate.target_id) == (1, 2))
    assert gold.is_gold_edge
    assert gold.gold_relation == "adversative-contrast"


def test_candidate_identity_includes_document_but_excludes_gold_annotations() -> None:
    candidate = generate_secondary_edge_candidates(_document(), _analysis(with_gold=True))[0]
    assert candidate.document_id == "candidate-doc"
    assert candidate == replace(
        candidate,
        is_gold_edge=not candidate.is_gold_edge,
        gold_relation="different-raw-label",
        gold_concept="DifferentConcept",
    )
    assert candidate != replace(candidate, document_id="different-document")


def test_candidate_features_include_heads_context_direction_and_primary_relation() -> None:
    candidates = generate_secondary_edge_candidates(_document(), _analysis())
    forward = next(candidate for candidate in candidates if (candidate.source_id, candidate.target_id) == (1, 2))
    reverse_primary = next(candidate for candidate in candidates if (candidate.source_id, candidate.target_id) == (1, 3))
    assert forward.direction == "forward"
    assert forward.edu_distance == 1
    assert forward.source_head_id == 1
    assert forward.target_head_id == 2
    assert forward.source_sentence_ids == (0,)
    assert forward.target_sentence_ids == (1,)
    assert forward.compatible_relations == ("adversative-contrast",)
    assert reverse_primary.existing_primary_relation == "span"
    assert reverse_primary.existing_primary_direction == "target_to_source"


def test_missing_or_insufficient_signal_produces_no_candidate() -> None:
    analysis = _analysis()
    assert generate_secondary_edge_candidates(_document(), replace(analysis, signals=())) == ()
    assert generate_secondary_edge_candidates(
        _document(),
        replace(analysis, signals=(_signal(sufficient=False),)),
    ) == ()


def test_candidate_identity_is_identical_in_every_pipeline_mode() -> None:
    identities_by_mode = {
        mode: tuple(
            (candidate.source_id, candidate.target_id, candidate.signal_ids)
            for candidate in iter_secondary_edge_candidates(_document(), _analysis(), mode=mode)
        )
        for mode in CandidateMode
    }
    first = next(iter(identities_by_mode.values()))
    assert first
    assert all(identities == first for identities in identities_by_mode.values())


def test_batched_candidate_stream_is_complete_and_untruncated() -> None:
    expected = generate_secondary_edge_candidates(_document(), _analysis())
    batches = tuple(
        iter_candidate_batches(
            iter_secondary_edge_candidates(_document(), _analysis()),
            batch_size=2,
        )
    )
    assert all(0 < len(batch) <= 2 for batch in batches)
    assert tuple(candidate for batch in batches for candidate in batch) == expected
