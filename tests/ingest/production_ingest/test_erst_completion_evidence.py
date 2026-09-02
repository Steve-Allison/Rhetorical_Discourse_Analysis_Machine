"""Decision-complete eRST candidate, signal, calibration, and decoder evidence."""

import pytest
from pydantic import ValidationError

from rdam.rst.contracts.analysis import DiscourseSignal, RstAnalysis, RstNode, SignalDetectorProvenance
from rdam.rst.contracts.enums import NodeKindEnum, OutputFormalismEnum, SignalDetectionMethod
from rdam.rst.contracts.erst import ErstDecoderConfig
from rdam.rst.english.erst.completer import ErstCompletionTrace
from rdam.rst.erst.candidates import SecondaryEdgeCandidate
from rdam.rst.erst.decoder import ErstSecondaryEdgeDecoder
from rdam.rst.ingest import SemanticVersion, Sha256Identity
from rdam.rst.ingest.contracts.inference import (
    ComponentFileIdentity,
    CompositeAnalysisIdentity,
    ConfidenceKind,
    ErstCandidateDecision,
    ErstCompletionEvidence,
    ErstDecision,
    ErstDecodeReceipt,
    ImmutableComponentIdentity,
    MappingStatus,
    MutableComponentIdentity,
    NamedCount,
    NotUsedComponentIdentity,
    RelationInterpretation,
    ScoreValue,
    SupportingSignalEvidence,
)
from rdam.rst.ingest.contracts.source import TextSpanAnchor
from rdam.rst.ingest.parser_result import (
    _decision_basis,
    _erst_evidence,
    _packaged_component,
    _segmentation_source_from_composite,
)


def test_erst_completion_preserves_accepted_and_rejected_candidate_account() -> None:
    component = MutableComponentIdentity(
        component="erst_scorer",
        provider_type="fixture",
        reason="test double",
    )
    component_digest = Sha256Identity(hex_digest="a" * 64)
    signal = SupportingSignalEvidence(
        signal_id="signal:1",
        signal_type="dm:dm",
        anchors=(
            TextSpanAnchor(
                artifact_identity="document",
                start=0,
                end=7,
                quote="because",
            ),
        ),
        candidate_ids=("candidate:1", "candidate:2"),
        edge_ids=("secondary:1",),
    )
    decisions = (
        _candidate("candidate:1", 1, 2, ErstDecision.ACCEPTED, component_digest, "secondary:1"),
        _candidate("candidate:2", 2, 1, ErstDecision.REJECTED_SCORE, component_digest, None),
    )
    receipt = ErstDecodeReceipt(
        policy="four_formal_erst_constraints",
        policy_version=SemanticVersion(root="2.0.0"),
        candidate_decision_ids=("candidate:1", "candidate:2"),
        input_count=2,
        accepted_count=1,
        rejected_count=1,
        constraint_checks=(NamedCount(name="no_self_loop", count=2),),
        rejection_reasons=(NamedCount(name="rejected_score", count=1),),
        ordering_identity=Sha256Identity(hex_digest="b" * 64),
        warnings=(),
    )
    evidence = ErstCompletionEvidence(
        signals=(signal,),
        candidate_decisions=decisions,
        decode_receipt=receipt,
        scorer_identity=component,
        calibration_identity=component.model_copy(update={"component": "calibration"}),
        relation_inventory_identity=component.model_copy(update={"component": "relation_inventory"}),
    )
    assert evidence.semantic_digest is not None
    assert evidence.candidate_decisions[0].secondary_edge_id == "secondary:1"
    assert evidence.candidate_decisions[1].secondary_edge_id is None

    orphan = signal.model_copy(update={"candidate_ids": ("absent",)})
    with pytest.raises(ValidationError, match="absent candidate"):
        ErstCompletionEvidence.model_validate(
            {
                **evidence.model_dump(exclude={"semantic_digest"}),
                "signals": (orphan,),
            }
        )


def test_constraint_checks_and_orphan_signals_reflect_decoder_reality() -> None:
    """Checked-counts follow the decoder's short-circuit; orphan signals are filtered."""

    nodes = (
        RstNode(node_id=1, kind=NodeKindEnum.EDU, edu_span=(1, 1), char_span=(0, 8), text="Because "),
        RstNode(node_id=2, kind=NodeKindEnum.EDU, edu_span=(2, 2), char_span=(8, 16), text="we left,"),
        RstNode(node_id=3, kind=NodeKindEnum.EDU, edu_span=(3, 3), char_span=(16, 24), text="we rest."),
    )
    analysis = RstAnalysis(
        document_id="doc",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=(),
    )
    provenance = SignalDetectorProvenance(
        detector_id="fixture-detector",
        detector_version="1.0.0",
        method=SignalDetectionMethod.RULE,
    )
    signals = (
        _signal("sig_1", provenance, char_spans=((0, 7),), sufficient=True),
        _signal("sig_2", provenance, char_spans=((8, 10),), sufficient=False),
        _signal("sig_3", provenance, char_spans=((11, 15),), sufficient=True),
    )
    candidates = (
        _secondary_candidate(1, 2, ("sig_1",)),
        _secondary_candidate(2, 1, ("sig_2",)),
        _secondary_candidate(1, 3, ("sig_1",)),
        _secondary_candidate(3, 2, ("sig_1",)),
    )
    decoder = ErstSecondaryEdgeDecoder(
        ErstDecoderConfig(edge_threshold=0.5, raw_relation_inventory=("causal-cause",))
    )
    decoded = decoder.decode_with_receipt(
        analysis,
        candidates,
        (0.9, 0.9, 0.2, 0.9),
        ((0.0,), (0.0,), (0.0,), (0.0,)),
        sufficient_signal_ids={"sig_1", "sig_3"},
        streamed_batch_count=1,
    )
    trace = ErstCompletionTrace(
        analysis=analysis,
        signals=signals,
        candidates=candidates,
        edge_probabilities=(0.9, 0.9, 0.2, 0.9),
        relation_logits=((0.0,), (0.0,), (0.0,), (0.0,)),
        decoded=decoded,
    )
    evidence = _erst_evidence(trace, _fixture_composite(), document_identity="doc")

    # Decoder disposition of the four candidates: (1, 2) and (3, 2) accepted,
    # (2, 1) insufficient signal, (1, 3) below threshold. Constraints after
    # the threshold gate are checked only on surviving candidates.
    assert evidence.decode_receipt.constraint_checks == (
        NamedCount(name="sufficient_signal", count=3),
        NamedCount(name="no_self_loop", count=2),
        NamedCount(name="existing_endpoints", count=2),
        NamedCount(name="unique_directed_pair", count=2),
    )
    assert evidence.decode_receipt.accepted_count == 2
    accepted = [
        decision for decision in evidence.candidate_decisions if decision.decision is ErstDecision.ACCEPTED
    ]
    assert sorted(decision.secondary_edge_id for decision in accepted if decision.secondary_edge_id) == [
        "se_pred_1_2",
        "se_pred_3_2",
    ]
    assert {signal.signal_id for signal in evidence.signals} == {"sig_1", "sig_2"}
    assert all(signal.candidate_ids for signal in evidence.signals)
    assert evidence.decode_receipt.warnings == ("orphan_signals_without_candidates:1",)


def test_segmentation_source_recovery_from_composite_identity() -> None:
    presegmented = NotUsedComponentIdentity(
        component="segmenter",
        reason="input supplied exact presegmented EDUs",
    )
    assert _segmentation_source_from_composite(presegmented) == "presegmented"

    packaged, _ = _packaged_component("segmenter", ("dmrst_parser/predictor.py",))
    assert _segmentation_source_from_composite(packaged) == "deterministic_sentence_boundary_v1"

    mutable_model = MutableComponentIdentity(
        component="segmenter",
        provider_type="FixtureSegmenter",
        reason="segmenter was not loaded from an immutable local model release",
    )
    assert _segmentation_source_from_composite(mutable_model) == "model"

    released_model = ImmutableComponentIdentity(
        component="segmenter",
        release_id="segmenter-release",
        manifest_identity=Sha256Identity(hex_digest="c" * 64),
        architecture="transformer_segmenter",
        files=(
            ComponentFileIdentity(
                path="model.safetensors",
                role="weights",
                size_bytes=1,
                identity=Sha256Identity(hex_digest="d" * 64),
            ),
        ),
    )
    assert _segmentation_source_from_composite(released_model) == "model"


def test_decision_basis_preserves_model_segmentation() -> None:
    assert _decision_basis("presegmented") == "presegmented"
    assert _decision_basis("model") == "model"
    assert _decision_basis("deterministic_sentence_boundary_v1") == "deterministic_rule"


def _signal(
    signal_id: str,
    provenance: SignalDetectorProvenance,
    *,
    char_spans: tuple[tuple[int, int], ...],
    sufficient: bool,
) -> DiscourseSignal:
    return DiscourseSignal(
        signal_id=signal_id,
        edge_id=None,
        signal_type="dm",
        signal_subtype="discourse_marker",
        char_spans=char_spans,
        compatible_relations=("causal-cause",),
        detector=provenance,
        sufficient=sufficient,
    )


def _secondary_candidate(source: int, target: int, signal_ids: tuple[str, ...]) -> SecondaryEdgeCandidate:
    return SecondaryEdgeCandidate(
        document_id="doc",
        source_id=source,
        target_id=target,
        source_text="source",
        target_text="target",
        source_char_span=(0, 8),
        target_char_span=(8, 16),
        structural_features=(0.0,),
        is_gold_edge=False,
        signal_ids=signal_ids,
    )


def _fixture_composite() -> CompositeAnalysisIdentity:
    def not_used(component: str) -> NotUsedComponentIdentity:
        return NotUsedComponentIdentity(component=component, reason="test double")

    return CompositeAnalysisIdentity(
        primary_parser=MutableComponentIdentity(
            component="primary_parser",
            provider_type="fixture",
            reason="test double",
        ),
        segmenter=not_used("segmenter"),
        marker_refiner=not_used("marker_refiner"),
        erst_detector=not_used("erst_detector"),
        erst_scorer=not_used("erst_scorer"),
        erst_decoder=not_used("erst_decoder"),
        calibration=not_used("calibration"),
        relation_inventory=not_used("relation_inventory"),
        ontology_mapping=not_used("ontology_mapping"),
    )


def _candidate(
    candidate_id: str,
    source: int,
    target: int,
    decision: ErstDecision,
    component: Sha256Identity,
    edge_id: str | None,
) -> ErstCandidateDecision:
    probability = ScoreValue(
        value=0.9,
        confidence_kind=ConfidenceKind.PROBABILITY,
        minimum=0.0,
        maximum=1.0,
        producing_component_identity=component,
    )
    return ErstCandidateDecision(
        candidate_id=candidate_id,
        source_node_id=source,
        target_node_id=target,
        supporting_signal_ids=("signal:1",),
        edge_probability=probability,
        relation=RelationInterpretation(
            raw_label="cause",
            relation_scheme="gum_erst",
            inventory_identity=component,
            selected_ontology_concept="cause",
            mapping_status=MappingStatus.IDENTITY_ONLY,
        ),
        relation_probability=probability,
        joint_selection_score=probability.model_copy(update={"value": 0.81}),
        calibration_identity=component,
        decision=decision,
        decoder_order=0 if source == 1 else 1,
        secondary_edge_id=edge_id,
    )
