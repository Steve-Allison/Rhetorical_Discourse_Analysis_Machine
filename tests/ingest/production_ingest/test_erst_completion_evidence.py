"""Decision-complete eRST candidate, signal, calibration, and decoder evidence."""

import pytest
from pydantic import ValidationError

from isanlp_rst.ingest import SemanticVersion, Sha256Identity
from isanlp_rst.ingest.contracts.inference import (
    ConfidenceKind,
    ErstCandidateDecision,
    ErstCompletionEvidence,
    ErstDecision,
    ErstDecodeReceipt,
    MappingStatus,
    MutableComponentIdentity,
    NamedCount,
    RelationInterpretation,
    ScoreValue,
    SupportingSignalEvidence,
)
from isanlp_rst.ingest.contracts.source import TextSpanAnchor


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
