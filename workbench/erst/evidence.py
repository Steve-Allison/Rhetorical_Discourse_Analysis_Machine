"""Experimental eRST evidence assembly; never imported by production."""

from collections import Counter

from collections.abc import Sequence


from typing import Any


from rdam.rst.contracts import RstDocument

from workbench.erst.contracts import DecodeRejectionReason

from workbench.erst.completer import ErstCompletionTrace

from rdam.ingest.contracts.analysis import (
    AnalysisPolicy,
    ParserAnalysisResult,
    ParserAnalysisSemanticEvidence,
)

from rdam.ingest.contracts.base import SemanticVersion, Sha256Identity

from rdam.ingest.contracts.inference import (
    ComponentFileIdentity,
    ComponentIdentity,
    CompositeAnalysisIdentity,
    ErstCandidateDecision,
    ErstCompletionEvidence,
    ErstDecision,
    ErstDecodeReceipt,
    ImmutableComponentIdentity,
    LoadedComponentReceipt,
    NamedCount,
    OutputFormalism,
    SupportingSignalEvidence,
)


from rdam.ingest.identity import semantic_sha256

from rdam.ingest.validation import (
    build_analysis_validation_receipt as build_validation_receipt,
    validate_parser_analysis_result,
)


from rdam.ingest.parser_result import (
    component_digest_for,
    segmentation_source_from_composite,
    _span_anchor,
    _probability_score,
    interpret_native_relation,
    _loaded_receipt,
    describe_analysis_components,
)


def complete_parser_analysis_result_with_erst(
    parser: Any,
    document: RstDocument,
    primary_result: ParserAnalysisResult,
    erst_trace: ErstCompletionTrace,
    *,
    policy: AnalysisPolicy,
) -> ParserAnalysisResult:
    """Complete one validated primary result with document-global eRST evidence."""

    if policy.output_formalism is not OutputFormalism.ERST_GRAPH:
        raise ValueError("document-global eRST completion requires the eRST output formalism")
    primary_semantic = primary_result.semantic
    if primary_semantic.policy.output_formalism is not OutputFormalism.RST_TREE:
        raise ValueError("document-global eRST completion requires an RST primary result")
    segmentation_source = segmentation_source_from_composite(primary_semantic.composite_identity.segmenter)
    composite, loaded = _composite_identity(parser, segmentation_source, policy)
    previous_composite = primary_semantic.composite_identity
    if (
        composite.primary_parser != previous_composite.primary_parser
        or composite.segmenter != previous_composite.segmenter
        or composite.marker_refiner != previous_composite.marker_refiner
    ):
        raise ValueError("eRST completion runtime differs from primary-analysis components")
    erst = build_erst_completion_evidence(
        erst_trace,
        composite,
        policy=policy,
        document_identity=document.document_id,
    )
    validation = build_validation_receipt(
        erst_trace.analysis,
        primary_semantic.analysed_document,
        primary_semantic.primary_inference,
        erst,
        None,
        policy=policy,
        composite=composite,
        recombination=primary_semantic.recombination,
    )
    result = ParserAnalysisResult(
        semantic=ParserAnalysisSemanticEvidence(
            policy=policy,
            analysed_document=primary_semantic.analysed_document,
            analysis=erst_trace.analysis,
            primary_inference=primary_semantic.primary_inference,
            erst_completion=erst,
            composite_identity=composite,
            loaded_components=loaded,
            recombination=primary_semantic.recombination,
            validation=validation,
        ),
        execution=primary_result.execution,
    )
    validate_parser_analysis_result(result)
    return result


def build_erst_completion_evidence(
    trace: ErstCompletionTrace,
    composite: CompositeAnalysisIdentity,
    *,
    policy: AnalysisPolicy,
    document_identity: str,
) -> ErstCompletionEvidence:
    scorer_digest = component_digest_for(composite.erst_scorer)
    calibration_digest = component_digest_for(composite.calibration)
    inventory_digest = component_digest_for(composite.relation_inventory)
    decisions: list[ErstCandidateDecision] = []
    for decoded in trace.decoded.decisions:
        reason = decoded.rejection_reason
        if reason is None:
            decision = ErstDecision.ACCEPTED
        elif reason == "below_threshold":
            decision = ErstDecision.REJECTED_SCORE
        elif reason == "insufficient_signal":
            decision = ErstDecision.REJECTED_INSUFFICIENT_SIGNAL
        else:
            decision = ErstDecision.REJECTED_CONSTRAINT
        decisions.append(
            ErstCandidateDecision(
                candidate_id=_candidate_id(decoded.candidate),
                source_node_id=decoded.candidate.source_id,
                target_node_id=decoded.candidate.target_id,
                supporting_signal_ids=decoded.candidate.signal_ids,
                edge_probability=_probability_score(decoded.edge_probability, scorer_digest),
                relation=interpret_native_relation(
                    policy=policy,
                    raw_label=decoded.relation_raw,
                    relation_scheme="gum_erst",
                    inventory_identity=inventory_digest,
                ),
                relation_probability=_probability_score(
                    decoded.relation_probability,
                    scorer_digest,
                ),
                joint_selection_score=_probability_score(decoded.joint_score, scorer_digest),
                calibration_identity=calibration_digest,
                decision=decision,
                decoder_order=decoded.decoder_order,
                secondary_edge_id=decoded.accepted_edge_id,
            )
        )
    edge_ids_by_signal: dict[str, list[str]] = {}
    candidate_ids_by_signal: dict[str, list[str]] = {}
    for decision in decisions:
        for signal_id in decision.supporting_signal_ids:
            candidate_ids_by_signal.setdefault(signal_id, []).append(decision.candidate_id)
            if decision.secondary_edge_id is not None:
                edge_ids_by_signal.setdefault(signal_id, []).append(decision.secondary_edge_id)
    # Detected signals with no candidate (single-node analyses, unattached
    # triggers) stay in analysis.signals; supporting-signal evidence records
    # only signals that actually support at least one candidate.
    persisted_signals: list[SupportingSignalEvidence] = []
    orphan_signal_count = 0
    for signal in trace.signals:
        signal_candidate_ids = tuple(candidate_ids_by_signal.get(signal.signal_id, ()))
        if not signal_candidate_ids:
            orphan_signal_count += 1
            continue
        persisted_signals.append(
            SupportingSignalEvidence(
                signal_id=signal.signal_id,
                signal_type=f"{signal.signal_type}:{signal.signal_subtype}",
                anchors=tuple(_span_anchor(document_identity, start, end, "") for start, end in signal.char_spans),
                candidate_ids=signal_candidate_ids,
                edge_ids=tuple(edge_ids_by_signal.get(signal.signal_id, ())),
            )
        )
    signals = tuple(persisted_signals)
    rejection_counts = Counter(
        decision.decision.value for decision in decisions if decision.decision is not ErstDecision.ACCEPTED
    )
    # The decoder short-circuits its constraint chain: each constraint is
    # checked only on candidates that survived every earlier check.
    decoder_receipt = trace.decoded.receipt
    checked_sufficient_signal = decoder_receipt.candidate_count - decoder_receipt.below_threshold_count
    checked_no_self_loop = (
        checked_sufficient_signal - decoder_receipt.formal_rejections[DecodeRejectionReason.INSUFFICIENT_SIGNAL]
    )
    checked_existing_endpoints = (
        checked_no_self_loop - decoder_receipt.formal_rejections[DecodeRejectionReason.SELF_LOOP]
    )
    checked_unique_directed_pair = (
        checked_existing_endpoints - decoder_receipt.formal_rejections[DecodeRejectionReason.INVENTED_NODE]
    )
    decode_receipt = ErstDecodeReceipt(
        policy="four_formal_erst_constraints",
        policy_version=SemanticVersion(root="2.0.0"),
        candidate_decision_ids=tuple(decision.candidate_id for decision in decisions),
        input_count=len(decisions),
        accepted_count=sum(decision.decision is ErstDecision.ACCEPTED for decision in decisions),
        rejected_count=sum(decision.decision is not ErstDecision.ACCEPTED for decision in decisions),
        constraint_checks=(
            NamedCount(name="sufficient_signal", count=checked_sufficient_signal),
            NamedCount(name="no_self_loop", count=checked_no_self_loop),
            NamedCount(name="existing_endpoints", count=checked_existing_endpoints),
            NamedCount(name="unique_directed_pair", count=checked_unique_directed_pair),
        ),
        rejection_reasons=tuple(NamedCount(name=name, count=count) for name, count in sorted(rejection_counts.items())),
        ordering_identity=Sha256Identity(
            hex_digest=semantic_sha256(tuple(decision.candidate_id for decision in decisions))
        ),
        warnings=((f"orphan_signals_without_candidates:{orphan_signal_count}",) if orphan_signal_count else ()),
    )
    return ErstCompletionEvidence(
        signals=signals,
        candidate_decisions=tuple(decisions),
        decode_receipt=decode_receipt,
        scorer_identity=composite.erst_scorer,
        calibration_identity=composite.calibration,
        relation_inventory_identity=composite.relation_inventory,
    )


def _checkpoint_component(
    checkpoint: Any,
    component: str,
    roles: Sequence[str],
) -> ImmutableComponentIdentity:
    selected = tuple(item for item in checkpoint.manifest.files if item.role.value in roles)
    if not selected:
        raise ValueError(f"eRST checkpoint has no files for component {component!r}")
    files = tuple(
        ComponentFileIdentity(
            path=item.path,
            role=item.role.value,
            size_bytes=item.size_bytes,
            identity=Sha256Identity(hex_digest=item.sha256),
        )
        for item in selected
    )
    return ImmutableComponentIdentity(
        component=component,
        release_id=f"erst-{checkpoint.manifest.manifest_sha256[:16]}",
        manifest_identity=Sha256Identity(hex_digest=checkpoint.manifest.manifest_sha256),
        architecture=checkpoint.manifest.architecture,
        files=files,
    )


def _candidate_id(candidate: Any) -> str:
    return f"candidate:{candidate.document_id}:{candidate.source_id}:{candidate.target_id}"


def _composite_identity(
    parser: Any, segmentation_source: str, policy: AnalysisPolicy
) -> tuple[CompositeAnalysisIdentity, tuple[LoadedComponentReceipt, ...]]:
    primary_policy = AnalysisPolicy.model_validate(
        {
            **policy.model_dump(exclude={"semantic_digest"}),
            "output_formalism": OutputFormalism.RST_TREE,
        }
    )
    primary, primary_loaded = describe_analysis_components(
        parser, segmentation_source=segmentation_source, policy=primary_policy
    )
    loaded: list[LoadedComponentReceipt] = []
    checkpoint = parser.erst_checkpoint
    if checkpoint is None:
        raise ValueError("eRST policy requires a loaded checkpoint")
    roles = {
        "erst_scorer": ("scorer_state", "scorer_config", "encoder_config", "tokenizer"),
        "erst_detector": ("signal_config",),
        "erst_decoder": ("decoder_config",),
        "calibration": ("calibration",),
        "relation_inventory": ("relation_inventory",),
        "ontology_mapping": ("ontology_mapping",),
    }
    components: dict[str, ComponentIdentity] = {}
    for component, selected_roles in roles.items():
        identity = _checkpoint_component(checkpoint, component, selected_roles)
        components[component] = identity
        loaded.append(_loaded_receipt(identity))
    replaced = set(components)
    composite = CompositeAnalysisIdentity.model_validate(
        {
            **primary.model_dump(exclude={"semantic_digest"}),
            **{name: identity.model_dump() for name, identity in components.items()},
        }
    )
    return composite, (*tuple(item for item in primary_loaded if item.component not in replaced), *loaded)
