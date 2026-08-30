"""Construction of evidence-complete parser-owned production results."""

from collections import Counter
from collections.abc import Sequence
import math
from pathlib import Path
from typing import Any
from uuid import uuid4

from isanlp_rst._provenance import resolve_package_version
from isanlp_rst.contracts import RstAnalysis, RstDocument
from isanlp_rst.english.erst.completer import ErstCompletionTrace
from isanlp_rst.ingest.contracts.analysis import (
    AnalysedDocument,
    AnalysedEdu,
    AnalysedToken,
    AnalysisAnchor,
    AnalysisPolicy,
    AnchorTargetKind,
    EndpointAnchor,
    FidelityClass,
    ParserAnalysisExecutionEvidence,
    ParserAnalysisResult,
    ParserAnalysisSemanticEvidence,
    PreparedRange,
    TokenMapping,
    UnitExecutionReceipt,
)
from isanlp_rst.ingest.contracts.base import CoverageUnit, ExactCoverage, SemanticVersion, Sha256Identity
from isanlp_rst.ingest.contracts.inference import (
    ComponentFileIdentity,
    ComponentIdentity,
    CompositeAnalysisIdentity,
    ConfidenceKind,
    ErstCandidateDecision,
    ErstCompletionEvidence,
    ErstDecision,
    ErstDecodeReceipt,
    EvidenceDetailPolicy,
    ImmutableComponentIdentity,
    LabelledScore,
    LoadedComponentReceipt,
    MappingStatus,
    MutableComponentIdentity,
    NamedCount,
    NormalizedDistribution,
    NotUsedComponentIdentity,
    OutputFormalism,
    PrimaryInferenceEvidence,
    PrimaryStructureDecisionEvidence,
    RefinementRecord,
    RelationInterpretation,
    ScoreValue,
    SegmentationDecisionEvidence,
    SupportingSignalEvidence,
)
from isanlp_rst.ingest.contracts.source import TextSpanAnchor
from isanlp_rst.ingest.identity import semantic_sha256, sha256_file
from isanlp_rst.ingest.validation import (
    build_analysis_validation_receipt as build_validation_receipt,
    validate_parser_analysis_result,
)
from isanlp_rst.transformer_parser.predictor import PredictorAnalysisTrace


def build_parser_analysis_result(
    parser: Any,
    document: RstDocument,
    trace: PredictorAnalysisTrace,
    *,
    policy: AnalysisPolicy,
    model_analysis: RstAnalysis,
    final_analysis: RstAnalysis,
    erst_trace: ErstCompletionTrace | None,
    duration_ms: float,
) -> ParserAnalysisResult:
    """Build the canonical parser result from exact backend handoff evidence."""

    composite, loaded = _composite_identity(parser, trace.segmentation_source, policy)
    analysed_document = _analysed_document(document, trace)
    component_digest = _component_digest(composite.primary_parser)
    relation_inventory_identity = Sha256Identity(
        hex_digest=semantic_sha256(tuple(parser.predictor.model.raw_relation_inventory))
    )
    primary = _primary_evidence(
        trace,
        model_analysis,
        final_analysis,
        policy,
        component_digest=component_digest,
        segmenter_component_digest=_component_digest(composite.segmenter),
        relation_inventory_identity=relation_inventory_identity,
        marker_component_digest=_component_digest(composite.marker_refiner),
        document_identity=document.document_id,
    )
    erst = (
        _erst_evidence(
            erst_trace,
            final_analysis,
            policy,
            composite,
            document_identity=document.document_id,
        )
        if erst_trace is not None
        else None
    )
    anchors = _analysis_anchors(
        final_analysis,
        analysed_document,
        primary,
        document_identity=document.document_id,
    )
    validation = build_validation_receipt(
        final_analysis,
        analysed_document,
        primary,
        erst,
        anchors,
        policy=policy,
        composite=composite,
        recombination=None,
    )
    result = ParserAnalysisResult(
        semantic=ParserAnalysisSemanticEvidence(
            policy=policy,
            analysed_document=analysed_document,
            analysis=final_analysis,
            anchors=anchors,
            primary_inference=primary,
            erst_completion=erst,
            composite_identity=composite,
            loaded_components=loaded,
            recombination=None,
            validation=validation,
        ),
        execution=ParserAnalysisExecutionEvidence(
            execution_id=str(uuid4()),
            duration_ms=duration_ms,
            device=str(parser.predictor._device),
            unit_executions=(
                UnitExecutionReceipt(
                    unit_id="unit:0000",
                    duration_ms=duration_ms,
                    device=str(parser.predictor._device),
                ),
            ),
        ),
    )
    validate_parser_analysis_result(result)
    return result


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
    segmentation_source = (
        "presegmented"
        if primary_semantic.composite_identity.segmenter.component == "segmenter"
        and isinstance(primary_semantic.composite_identity.segmenter, NotUsedComponentIdentity)
        else "deterministic_sentence_boundary_v1"
    )
    composite, loaded = _composite_identity(parser, segmentation_source, policy)
    previous_composite = primary_semantic.composite_identity
    if (
        composite.primary_parser != previous_composite.primary_parser
        or composite.segmenter != previous_composite.segmenter
        or composite.marker_refiner != previous_composite.marker_refiner
    ):
        raise ValueError("eRST completion runtime differs from primary-analysis components")
    erst = _erst_evidence(
        erst_trace,
        erst_trace.analysis,
        policy,
        composite,
        document_identity=document.document_id,
    )
    anchors = _analysis_anchors(
        erst_trace.analysis,
        primary_semantic.analysed_document,
        primary_semantic.primary_inference,
        document_identity=document.document_id,
    )
    validation = build_validation_receipt(
        erst_trace.analysis,
        primary_semantic.analysed_document,
        primary_semantic.primary_inference,
        erst,
        anchors,
        policy=policy,
        composite=composite,
        recombination=primary_semantic.recombination,
    )
    result = ParserAnalysisResult(
        semantic=ParserAnalysisSemanticEvidence(
            policy=policy,
            analysed_document=primary_semantic.analysed_document,
            analysis=erst_trace.analysis,
            anchors=anchors,
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


def describe_analysis_components(
    parser: Any,
    *,
    segmentation_source: str,
    policy: AnalysisPolicy,
) -> tuple[CompositeAnalysisIdentity, tuple[LoadedComponentReceipt, ...]]:
    """Describe exact participating runtime components without executing inference."""

    return _composite_identity(parser, segmentation_source, policy)


def _analysed_document(
    document: RstDocument,
    trace: PredictorAnalysisTrace,
) -> AnalysedDocument:
    token_ids = {token.token_id: f"token:{token.token_id:06d}" for token in trace.tokens}
    edu_ids = {edu.edu_id: f"edu:{edu.edu_id:06d}" for edu in trace.edus}
    token_to_edu = {token_id: edu for edu in trace.edus for token_id in edu.token_ids}
    tokens = tuple(
        AnalysedToken(
            token_id=token_ids[token.token_id],
            order=token.token_id,
            text=token.text,
            character_range=PreparedRange(start=token.start, end=token.end),
            source_anchors=(_span_anchor(document.document_id, token.start, token.end, document.text),),
            sentence_id=f"sentence:{token.sentence_id or 0:04d}",
            paragraph_id=f"paragraph:{token.paragraph_id or 0:04d}",
        )
        for token in trace.tokens
    )
    edus = tuple(
        AnalysedEdu(
            edu_id=edu_ids[edu.edu_id],
            order=order,
            text=edu.text,
            token_ids=tuple(token_ids[token_id] for token_id in edu.token_ids),
            sentence_id=f"sentence:{_membership(trace.tokens, edu.token_ids, 'sentence_id'):04d}",
            paragraph_id=f"paragraph:{_membership(trace.tokens, edu.token_ids, 'paragraph_id'):04d}",
            prepared_segment_ids=("document:segment:0000",),
            source_anchors=(_span_anchor(document.document_id, edu.start, edu.end, document.text),),
        )
        for order, edu in enumerate(trace.edus)
    )
    mappings = tuple(
        TokenMapping(
            token_id=token_ids[token.token_id],
            edu_id=edu_ids[token_to_edu[token.token_id].edu_id],
            sentence_id=f"sentence:{token.sentence_id or 0:04d}",
            paragraph_id=f"paragraph:{token.paragraph_id or 0:04d}",
        )
        for token in trace.tokens
    )
    return AnalysedDocument(
        text=document.text,
        tokens=tokens,
        edus=edus,
        mappings=mappings,
        sentence_boundaries=tuple(
            PreparedRange(start=boundary.start, end=boundary.end) for boundary in trace.sentence_boundaries
        ),
        paragraph_boundaries=tuple(
            PreparedRange(start=boundary.start, end=boundary.end) for boundary in trace.paragraph_boundaries
        ),
        structural_boundary_ids=tuple(f"paragraph:{index:04d}" for index, _ in enumerate(trace.paragraph_boundaries)),
        prepared_segment_ids=("document:segment:0000",),
        source_anchors=(_span_anchor(document.document_id, 0, len(document.text), document.text),),
        transformations=(),
        fidelity=FidelityClass.LOSSLESS,
        character_coverage=ExactCoverage(
            covered_units=len(document.text),
            total_units=len(document.text),
            unit=CoverageUnit.CHARACTERS,
        ),
        token_coverage=ExactCoverage(
            covered_units=len(tokens),
            total_units=len(tokens),
            unit=CoverageUnit.ITEMS,
        ),
        edu_coverage=ExactCoverage(
            covered_units=len(edus),
            total_units=len(edus),
            unit=CoverageUnit.ITEMS,
        ),
    )


def _primary_evidence(
    trace: PredictorAnalysisTrace,
    model_analysis: RstAnalysis,
    final_analysis: RstAnalysis,
    policy: AnalysisPolicy,
    *,
    component_digest: Sha256Identity,
    segmenter_component_digest: Sha256Identity,
    relation_inventory_identity: Sha256Identity,
    marker_component_digest: Sha256Identity,
    document_identity: str,
) -> PrimaryInferenceEvidence:
    segmentation = tuple(
        SegmentationDecisionEvidence(
            decision_id=f"segmentation:{edu.edu_id:06d}",
            boundary_id=f"boundary:{edu.start:08d}",
            selected_boundary=True,
            decision_basis=("presegmented" if trace.segmentation_source == "presegmented" else "deterministic_rule"),
            confidence=None,
            distribution=None,
            token_ids=tuple(f"token:{token_id:06d}" for token_id in edu.token_ids),
            resulting_edu_ids=(f"edu:{edu.edu_id:06d}",),
            producing_component_identity=segmenter_component_digest,
        )
        for edu in trace.edus
    )
    nodes_by_span = {node.edu_span: node for node in model_analysis.nodes}
    edges_by_parent: dict[int, list[str]] = {}
    for edge in model_analysis.primary_edges:
        edges_by_parent.setdefault(edge.parent_id, []).append(edge.edge_id)
    structures: list[PrimaryStructureDecisionEvidence] = []
    for index, decision in enumerate(trace.structure_decisions):
        span = decision.span
        node = nodes_by_span.get((span.start + 1, span.end + 1))
        if node is None:
            raise ValueError(f"decoded span {(span.start, span.end)} has no final graph node")
        split_distribution = _distribution(
            tuple(str(value) for value in decision.split_candidates),
            decision.split_logits,
            component_digest,
        )
        nuclearity_distribution = _distribution(
            tuple(parser_label for parser_label in ("NS", "SN", "NN")),
            decision.nuclearity_logits,
            component_digest,
        )
        relation_labels = trace.relation_inventory
        relation_distribution = _distribution(
            relation_labels,
            decision.relation_logits,
            component_digest,
        )
        selected_split_probability = _selected_probability(
            decision.split_candidates,
            decision.split_logits,
            span.split,
        )
        selected_nuclearity_probability = _selected_probability(
            ("NS", "SN", "NN"),
            decision.nuclearity_logits,
            span.nuclearity,
        )
        relation_index = _relation_index(trace.relation_inventory, span.relation)
        selected_relation_probability = _softmax(decision.relation_logits)[relation_index]
        confidence = selected_split_probability * selected_nuclearity_probability * selected_relation_probability
        structures.append(
            PrimaryStructureDecisionEvidence(
                decision_id=f"primary:{index:06d}",
                node_ids=(node.node_id,),
                primary_edge_ids=tuple(edges_by_parent.get(node.node_id, ())),
                analysed_start=node.char_span[0],
                analysed_end=node.char_span[1],
                selected_split=span.split,
                nuclearity=span.nuclearity,
                relation=RelationInterpretation(
                    raw_label=span.relation,
                    relation_scheme="provider_native",
                    inventory_identity=relation_inventory_identity,
                    selected_ontology_concept=span.relation,
                    mapping_status=MappingStatus.IDENTITY_ONLY,
                    confidence=_probability_score(
                        selected_relation_probability,
                        component_digest,
                    ),
                ),
                confidence=_probability_score(confidence, component_digest),
                split_entropy=_entropy_score(decision.split_logits, component_digest),
                split_distribution=(
                    split_distribution
                    if policy.evidence_detail is EvidenceDetailPolicy.NORMALIZED_DISTRIBUTIONS
                    else None
                ),
                relation_distribution=(
                    relation_distribution
                    if policy.evidence_detail is EvidenceDetailPolicy.NORMALIZED_DISTRIBUTIONS
                    else None
                ),
                nuclearity_distribution=(
                    nuclearity_distribution
                    if policy.evidence_detail is EvidenceDetailPolicy.NORMALIZED_DISTRIBUTIONS
                    else None
                ),
                producing_component_identity=component_digest,
            )
        )
    refinements = _refinements(
        model_analysis,
        final_analysis,
        policy,
        marker_component_digest=marker_component_digest,
        document_identity=document_identity,
    )
    return PrimaryInferenceEvidence(
        segmentation_decisions=segmentation,
        structure_decisions=tuple(structures),
        refinements=refinements,
    )


def _refinements(
    before: RstAnalysis,
    after: RstAnalysis,
    policy: AnalysisPolicy,
    *,
    marker_component_digest: Sha256Identity,
    document_identity: str,
) -> tuple[RefinementRecord, ...]:
    before_by_id = {edge.edge_id: edge for edge in before.primary_edges}
    signals_by_edge: dict[str, list[Any]] = {}
    for signal in after.signals:
        if signal.edge_id is not None:
            signals_by_edge.setdefault(signal.edge_id, []).append(signal)
    records: list[RefinementRecord] = []
    for edge in after.primary_edges:
        original = before_by_id.get(edge.edge_id)
        if original is None:
            continue
        dimensions = (
            ("relation_raw", original.relation_raw, edge.relation_raw),
            ("relation_concept", original.relation_concept, edge.relation_concept),
            ("nuclearity", original.nuclearity.value, edge.nuclearity.value),
        )
        for dimension, before_value, after_value in dimensions:
            if before_value == after_value:
                continue
            signals = tuple(signals_by_edge.get(edge.edge_id, ()))
            records.append(
                RefinementRecord(
                    refinement_id=f"refinement:{edge.edge_id}:{dimension}",
                    decision_kind=dimension,
                    before_value=before_value,
                    after_value=after_value,
                    trigger_signal_ids=tuple(signal.signal_id for signal in signals),
                    trigger_anchors=tuple(
                        _span_anchor(document_identity, start, end, "")
                        for signal in signals
                        for start, end in signal.char_spans
                    ),
                    policy_identity=policy.semantic_digest or Sha256Identity(hex_digest=semantic_sha256(policy)),
                    algorithm_version=SemanticVersion(root="2.0.0"),
                    graph_element_ids=(edge.edge_id,),
                    explanation_code="discourse_marker_refinement",
                )
            )
    return tuple(records)


def _erst_evidence(
    trace: ErstCompletionTrace,
    analysis: RstAnalysis,
    policy: AnalysisPolicy,
    composite: CompositeAnalysisIdentity,
    *,
    document_identity: str,
) -> ErstCompletionEvidence:
    scorer_digest = _component_digest(composite.erst_scorer)
    calibration_digest = _component_digest(composite.calibration)
    inventory_digest = _component_digest(composite.relation_inventory)
    relation_labels = tuple(getattr(trace, "relation_inventory", ()))
    if not relation_labels and trace.relation_logits:
        relation_labels = tuple(str(index) for index in range(len(trace.relation_logits[0])))
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
                relation=RelationInterpretation(
                    raw_label=decoded.relation_raw,
                    relation_scheme="gum_erst",
                    inventory_identity=inventory_digest,
                    selected_ontology_concept=decoded.relation_raw,
                    mapping_status=MappingStatus.IDENTITY_ONLY,
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
    signals = tuple(
        SupportingSignalEvidence(
            signal_id=signal.signal_id,
            signal_type=f"{signal.signal_type}:{signal.signal_subtype}",
            anchors=tuple(_span_anchor(document_identity, start, end, "") for start, end in signal.char_spans),
            candidate_ids=tuple(candidate_ids_by_signal.get(signal.signal_id, ())),
            edge_ids=tuple(edge_ids_by_signal.get(signal.signal_id, ())),
        )
        for signal in trace.signals
    )
    rejection_counts = Counter(
        decision.decision.value for decision in decisions if decision.decision is not ErstDecision.ACCEPTED
    )
    decode_receipt = ErstDecodeReceipt(
        policy="four_formal_erst_constraints",
        policy_version=SemanticVersion(root="2.0.0"),
        candidate_decision_ids=tuple(decision.candidate_id for decision in decisions),
        input_count=len(decisions),
        accepted_count=sum(decision.decision is ErstDecision.ACCEPTED for decision in decisions),
        rejected_count=sum(decision.decision is not ErstDecision.ACCEPTED for decision in decisions),
        constraint_checks=tuple(
            NamedCount(name=name, count=len(decisions))
            for name in (
                "sufficient_signal",
                "no_self_loop",
                "existing_endpoints",
                "unique_directed_pair",
            )
        ),
        rejection_reasons=tuple(NamedCount(name=name, count=count) for name, count in sorted(rejection_counts.items())),
        ordering_identity=Sha256Identity(
            hex_digest=semantic_sha256(tuple(decision.candidate_id for decision in decisions))
        ),
        warnings=(),
    )
    return ErstCompletionEvidence(
        signals=signals,
        candidate_decisions=tuple(decisions),
        decode_receipt=decode_receipt,
        scorer_identity=composite.erst_scorer,
        calibration_identity=composite.calibration,
        relation_inventory_identity=composite.relation_inventory,
    )


def _analysis_anchors(
    analysis: RstAnalysis,
    analysed: AnalysedDocument,
    primary: PrimaryInferenceEvidence,
    *,
    document_identity: str,
) -> tuple[AnalysisAnchor, ...]:
    anchors: list[AnalysisAnchor] = []
    for edu in analysed.edus:
        anchors.append(
            AnalysisAnchor(
                target_id=edu.edu_id,
                target_kind=AnchorTargetKind.EDU,
                token_ids=edu.token_ids,
                edu_ids=(edu.edu_id,),
                prepared_segment_ids=edu.prepared_segment_ids,
                source_anchors=edu.source_anchors,
            )
        )
    for node in analysis.nodes:
        anchors.append(_node_anchor(node, analysed, document_identity=document_identity))
    node_by_id = {node.node_id: node for node in analysis.nodes}
    for edge in analysis.primary_edges:
        anchors.append(
            _edge_anchor(
                edge.edge_id,
                AnchorTargetKind.PRIMARY_EDGE,
                node_by_id[edge.parent_id],
                node_by_id[edge.child_id],
                analysed,
                document_identity=document_identity,
            )
        )
    for edge in analysis.secondary_edges:
        anchors.append(
            _edge_anchor(
                edge.edge_id,
                AnchorTargetKind.SECONDARY_EDGE,
                node_by_id[edge.source_id],
                node_by_id[edge.target_id],
                analysed,
                document_identity=document_identity,
            )
        )
    for decision in (*primary.segmentation_decisions, *primary.structure_decisions):
        token_ids = (
            decision.token_ids
            if isinstance(decision, SegmentationDecisionEvidence)
            else tuple(
                token.token_id
                for token in analysed.tokens
                if decision.analysed_start <= token.character_range.start
                and token.character_range.end <= decision.analysed_end
            )
        )
        edu_ids = tuple(edu.edu_id for edu in analysed.edus if set(edu.token_ids) & set(token_ids))
        source_anchors = tuple(
            anchor for edu in analysed.edus if edu.edu_id in edu_ids for anchor in edu.source_anchors
        )
        anchors.append(
            AnalysisAnchor(
                target_id=decision.decision_id,
                target_kind=AnchorTargetKind.DECISION,
                token_ids=token_ids,
                edu_ids=edu_ids,
                prepared_segment_ids=tuple(
                    dict.fromkeys(
                        segment
                        for edu in analysed.edus
                        if edu.edu_id in edu_ids
                        for segment in edu.prepared_segment_ids
                    )
                ),
                source_anchors=source_anchors,
            )
        )
    for signal in analysis.signals:
        tokens = tuple(
            token.token_id
            for token in analysed.tokens
            if any(
                start < token.character_range.end and token.character_range.start < end
                for start, end in signal.char_spans
            )
        )
        edu_ids = tuple(edu.edu_id for edu in analysed.edus if set(edu.token_ids) & set(tokens))
        source_anchors = tuple(
            _span_anchor(document_identity, start, end, analysed.text) for start, end in signal.char_spans
        )
        if not source_anchors:
            raise ValueError(f"supporting signal {signal.signal_id!r} has no character anchors")
        anchors.append(
            AnalysisAnchor(
                target_id=signal.signal_id,
                target_kind=AnchorTargetKind.SUPPORTING_SIGNAL,
                token_ids=tokens,
                edu_ids=edu_ids,
                prepared_segment_ids=("document:segment:0000",),
                source_anchors=source_anchors,
                supporting_signal_ids=(signal.signal_id,),
            )
        )
    return tuple(anchors)


def _node_anchor(
    node: Any,
    analysed: AnalysedDocument,
    *,
    document_identity: str,
) -> AnalysisAnchor:
    tokens = tuple(
        token.token_id
        for token in analysed.tokens
        if node.char_span[0] <= token.character_range.start and token.character_range.end <= node.char_span[1]
    )
    edus = tuple(edu.edu_id for edu in analysed.edus if set(edu.token_ids) & set(tokens))
    return AnalysisAnchor(
        target_id=str(node.node_id),
        target_kind=AnchorTargetKind.NODE,
        token_ids=tokens,
        edu_ids=edus,
        prepared_segment_ids=("document:segment:0000",),
        source_anchors=(_span_anchor(document_identity, node.char_span[0], node.char_span[1], analysed.text),),
    )


def _edge_anchor(
    edge_id: str,
    kind: AnchorTargetKind,
    source_node: Any,
    target_node: Any,
    analysed: AnalysedDocument,
    *,
    document_identity: str,
) -> AnalysisAnchor:
    source = _endpoint(source_node, analysed, document_identity=document_identity)
    target = _endpoint(target_node, analysed, document_identity=document_identity)
    return AnalysisAnchor(
        target_id=edge_id,
        target_kind=kind,
        token_ids=tuple(dict.fromkeys((*source.token_ids, *target.token_ids))),
        edu_ids=tuple(dict.fromkeys((*source.edu_ids, *target.edu_ids))),
        prepared_segment_ids=("document:segment:0000",),
        source_anchors=(*source.source_anchors, *target.source_anchors),
        source_endpoint=source,
        target_endpoint=target,
    )


def _endpoint(
    node: Any,
    analysed: AnalysedDocument,
    *,
    document_identity: str,
) -> EndpointAnchor:
    tokens = tuple(
        token.token_id
        for token in analysed.tokens
        if node.char_span[0] <= token.character_range.start and token.character_range.end <= node.char_span[1]
    )
    edus = tuple(edu.edu_id for edu in analysed.edus if set(edu.token_ids) & set(tokens))
    return EndpointAnchor(
        node_id=node.node_id,
        token_ids=tokens,
        edu_ids=edus,
        prepared_segment_ids=("document:segment:0000",),
        source_anchors=(_span_anchor(document_identity, node.char_span[0], node.char_span[1], analysed.text),),
    )


def _composite_identity(
    parser: Any,
    segmentation_source: str,
    policy: AnalysisPolicy,
) -> tuple[CompositeAnalysisIdentity, tuple[LoadedComponentReceipt, ...]]:
    loaded: list[LoadedComponentReceipt] = []
    release = parser.model_release_identity
    if release is None:
        primary: ComponentIdentity = MutableComponentIdentity(
            component="primary_parser",
            provider_type=type(parser.predictor).__qualname__,
            reason="parser was not loaded from an immutable local model release",
        )
    else:
        runtime_files = tuple(getattr(parser.predictor, "loaded_release_files", ()))
        if runtime_files != release.files:
            raise ValueError("primary parser runtime files contradict the validated release identity")
        files = tuple(
            ComponentFileIdentity(
                path=str(item.path),
                role=item.role,
                size_bytes=item.size_bytes,
                identity=Sha256Identity(hex_digest=item.sha256),
            )
            for item in release.files
        )
        primary = ImmutableComponentIdentity(
            component="primary_parser",
            release_id=release.release_id,
            manifest_identity=Sha256Identity(hex_digest=release.manifest_sha256),
            architecture=release.architecture,
            capacity_identity=Sha256Identity(hex_digest=semantic_sha256(release.capacity)),
            files=files,
        )
        loaded.append(_loaded_receipt(primary))

    if segmentation_source == "presegmented":
        segmenter: ComponentIdentity = NotUsedComponentIdentity(
            component="segmenter",
            reason="input supplied exact presegmented EDUs",
        )
    elif segmentation_source == "model":
        segmenter_runtime = getattr(parser, "segmenter", None)
        if segmenter_runtime is None:
            raise ValueError("model segmentation was declared without a configured segmenter")
        segmenter_release = getattr(segmenter_runtime, "model_release_identity", None)
        if segmenter_release is None:
            segmenter = MutableComponentIdentity(
                component="segmenter",
                provider_type=type(segmenter_runtime).__qualname__,
                reason="segmenter was not loaded from an immutable local model release",
            )
        else:
            segmenter, receipt = _released_runtime_component(
                "segmenter",
                segmenter_runtime,
                segmenter_release,
            )
            loaded.append(receipt)
    else:
        segmenter, receipt = _packaged_component(
            "segmenter",
            ("transformer_parser/predictor.py",),
        )
        loaded.append(receipt)
    if policy.marker_refinement.value == "disabled":
        marker: ComponentIdentity = NotUsedComponentIdentity(
            component="marker_refiner",
            reason="analysis policy disabled marker refinement",
        )
    else:
        marker, receipt = _packaged_component(
            "marker_refiner",
            ("relations/primer.py", "relations/multilingual_markers.py"),
        )
        loaded.append(receipt)

    ontology: ComponentIdentity = NotUsedComponentIdentity(
        component="ontology_mapping",
        reason="provider-native relation identity policy does not invoke ontology mapping",
    )
    if policy.output_formalism is OutputFormalism.ERST_GRAPH:
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
        detector = components["erst_detector"]
        scorer = components["erst_scorer"]
        decoder = components["erst_decoder"]
        calibration = components["calibration"]
        relation_inventory = components["relation_inventory"]
        ontology = components["ontology_mapping"]
    else:
        detector = NotUsedComponentIdentity(component="erst_detector", reason="RST tree requested")
        scorer = NotUsedComponentIdentity(component="erst_scorer", reason="RST tree requested")
        decoder = NotUsedComponentIdentity(component="erst_decoder", reason="RST tree requested")
        calibration = NotUsedComponentIdentity(component="calibration", reason="RST tree requested")
        if release is None:
            relation_inventory, receipt = _packaged_component(
                "relation_inventory",
                ("transformer_parser/predictor.py",),
            )
        else:
            relation_inventory, receipt = _released_runtime_component(
                "relation_inventory",
                parser.predictor,
                release,
                selected_roles=("relation_inventory",),
            )
        loaded.append(receipt)
    composite = CompositeAnalysisIdentity(
        primary_parser=primary,
        segmenter=segmenter,
        marker_refiner=marker,
        erst_detector=detector,
        erst_scorer=scorer,
        erst_decoder=decoder,
        calibration=calibration,
        relation_inventory=relation_inventory,
        ontology_mapping=ontology,
    )
    return composite, tuple(loaded)


def _packaged_component(
    component: str,
    relative_paths: Sequence[str],
) -> tuple[ImmutableComponentIdentity, LoadedComponentReceipt]:
    package_root = Path(__file__).resolve().parents[1]
    files = tuple(
        ComponentFileIdentity(
            path=relative,
            role="provider_code",
            size_bytes=(package_root / relative).stat().st_size,
            identity=Sha256Identity(hex_digest=sha256_file(package_root / relative)),
        )
        for relative in relative_paths
    )
    manifest = Sha256Identity(hex_digest=semantic_sha256(files))
    identity = ImmutableComponentIdentity(
        component=component,
        release_id=f"isanlp_rst-{resolve_package_version()}",
        manifest_identity=manifest,
        architecture="packaged_deterministic_component",
        files=files,
    )
    return identity, _loaded_receipt(identity)


def _released_runtime_component(
    component: str,
    runtime: Any,
    release: Any,
    *,
    selected_roles: tuple[str, ...] | None = None,
) -> tuple[ImmutableComponentIdentity, LoadedComponentReceipt]:
    runtime_files: tuple[Any, ...] = tuple(getattr(runtime, "loaded_release_files", ()))
    if runtime_files != release.files:
        raise ValueError(f"{component} runtime files contradict the validated release identity")
    selected = tuple(item for item in runtime_files if selected_roles is None or item.role in selected_roles)
    if not selected:
        raise ValueError(f"{component} release has no selected runtime files")
    files = tuple(
        ComponentFileIdentity(
            path=str(item.path),
            role=item.role,
            size_bytes=item.size_bytes,
            identity=Sha256Identity(hex_digest=item.sha256),
        )
        for item in selected
    )
    identity = ImmutableComponentIdentity(
        component=component,
        release_id=release.release_id,
        manifest_identity=Sha256Identity(hex_digest=release.manifest_sha256),
        architecture=release.architecture,
        capacity_identity=(
            Sha256Identity(hex_digest=semantic_sha256(release.capacity)) if component == "segmenter" else None
        ),
        files=files,
    )
    return identity, _loaded_receipt(identity)


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


def _loaded_receipt(identity: ImmutableComponentIdentity) -> LoadedComponentReceipt:
    return LoadedComponentReceipt(
        component=identity.component,
        declared_identity=_component_digest(identity),
        resolved_member_identities=identity.files,
        verified=True,
    )


def _component_digest(component: ComponentIdentity) -> Sha256Identity:
    return Sha256Identity(hex_digest=semantic_sha256(component))


def _span_anchor(
    identity: str,
    start: int,
    end: int,
    text: str,
) -> TextSpanAnchor:
    quote = text[start:end] if text and end <= len(text) else None
    return TextSpanAnchor(
        artifact_identity=identity,
        start=start,
        end=end,
        quote=quote,
    )


def _membership(tokens: Sequence[Any], token_ids: Sequence[int], field: str) -> int:
    values = {getattr(token, field) for token in tokens if token.token_id in token_ids}
    if len(values) != 1 or None in values:
        raise ValueError(f"EDU tokens do not have one exact {field}")
    return int(next(iter(values)))


def _softmax(logits: Sequence[float]) -> tuple[float, ...]:
    if not logits or any(not math.isfinite(value) for value in logits):
        raise ValueError("provider logits must be finite and non-empty")
    maximum = max(logits)
    values = tuple(math.exp(value - maximum) for value in logits)
    total = sum(values)
    return tuple(value / total for value in values)


def _distribution(
    labels: Sequence[str],
    logits: Sequence[float],
    component_identity: Sha256Identity,
) -> NormalizedDistribution:
    probabilities = _softmax(logits)
    if len(labels) != len(probabilities):
        raise ValueError("provider label and logit counts differ")
    return NormalizedDistribution(
        entries=tuple(
            LabelledScore(
                label=label,
                score=_probability_score(probability, component_identity),
            )
            for label, probability in zip(labels, probabilities, strict=True)
        )
    )


def _selected_probability(
    labels: Sequence[Any],
    logits: Sequence[float],
    selected: Any,
) -> float:
    try:
        index = tuple(labels).index(selected)
    except ValueError as exc:
        raise ValueError(f"selected provider value {selected!r} is absent from logits") from exc
    return _softmax(logits)[index]


def _relation_index(inventory: Sequence[str], relation: str) -> int:
    try:
        return inventory.index(relation)
    except ValueError as exc:
        raise ValueError(f"selected relation {relation!r} is absent from parser inventory") from exc


def _probability_score(value: float, component_identity: Sha256Identity) -> ScoreValue:
    return ScoreValue(
        value=value,
        confidence_kind=ConfidenceKind.PROBABILITY,
        minimum=0.0,
        maximum=1.0,
        producing_component_identity=component_identity,
    )


def _entropy_score(logits: Sequence[float], component_identity: Sha256Identity) -> ScoreValue:
    probabilities = _softmax(logits)
    entropy = -sum(value * math.log(value) for value in probabilities if value > 0.0)
    return ScoreValue(
        value=entropy,
        confidence_kind=ConfidenceKind.ENTROPY,
        minimum=0.0,
        maximum=math.log(len(probabilities)) if len(probabilities) > 1 else 0.0,
        producing_component_identity=component_identity,
    )


def _candidate_id(candidate: Any) -> str:
    return f"candidate:{candidate.document_id}:{candidate.source_id}:{candidate.target_id}"


__all__ = [
    "build_parser_analysis_result",
    "build_validation_receipt",
    "complete_parser_analysis_result_with_erst",
    "describe_analysis_components",
    "validate_parser_analysis_result",
]
