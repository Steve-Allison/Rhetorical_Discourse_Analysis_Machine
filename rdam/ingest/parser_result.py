"""Construction of evidence-complete parser-owned production results."""

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from rdam.rst._provenance import resolve_package_version
from rdam.rst._version import PACKAGE_NAME
from rdam.rst.contracts import DocumentToken, RstAnalysis, RstDocument
from rdam.ingest.contracts.analysis import (
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
    UnitExecutionReceipt,
)
from rdam.ingest.contracts.base import CoverageUnit, ExactCoverage, SemanticVersion, Sha256Identity
from rdam.ingest.contracts.inference import (
    ComponentFileIdentity,
    ComponentIdentity,
    CompositeAnalysisIdentity,
    ConfidenceKind,
    EvidenceDetailPolicy,
    ImmutableComponentIdentity,
    LabelledScore,
    JointRelationNuclearityEvidence,
    LoadedComponentReceipt,
    MappingStatus,
    MutableComponentIdentity,
    NormalizedDistribution,
    NotUsedComponentIdentity,
    OutputFormalism,
    PrimaryInferenceEvidence,
    PrimaryStructureDecisionEvidence,
    RefinementRecord,
    RelationInterpretation,
    ScoreValue,
    SegmentationDecisionEvidence,
)
from rdam.ingest.contracts.source import TextSpanAnchor
from rdam.ingest.identity import semantic_sha256, sha256_file
from rdam.ingest.validation import (
    build_analysis_validation_receipt as build_validation_receipt,
    validate_parser_analysis_result,
)
from rdam.rst.contracts.trace import PredictorAnalysisTrace
from rdam.ingest.vocabulary import capture_runtime_vocabulary


@dataclass(frozen=True, slots=True)
class _AnchorIndex:
    tokens: tuple[AnalysedToken, ...]
    starts: tuple[int, ...]
    ends: tuple[int, ...]
    edu_ids: tuple[str, ...]
    edu_starts: tuple[int, ...]
    edu_ends: tuple[int, ...]

    @classmethod
    def build(cls, analysed: AnalysedDocument) -> _AnchorIndex:
        return cls(
            tokens=analysed.tokens,
            starts=tuple(token.character_range.start for token in analysed.tokens),
            ends=tuple(token.character_range.end for token in analysed.tokens),
            edu_ids=tuple(edu.edu_id for edu in analysed.edus),
            edu_starts=tuple(edu.character_range.start for edu in analysed.edus),
            edu_ends=tuple(edu.character_range.end for edu in analysed.edus),
        )

    def overlapping_range(self, start: int, end: int) -> tuple[str, ...]:
        first = bisect_right(self.ends, start)
        stop = bisect_left(self.starts, end)
        return tuple(token.token_id for token in self.tokens[first:stop])

    def overlapping(self, spans: Sequence[tuple[int, int]]) -> tuple[str, ...]:
        indexes: set[int] = set()
        for start, end in spans:
            first = bisect_right(self.ends, start)
            stop = bisect_left(self.starts, end)
            indexes.update(range(first, stop))
        return tuple(self.tokens[index].token_id for index in sorted(indexes))

    def edus_overlapping(self, spans: Sequence[tuple[int, int]]) -> tuple[str, ...]:
        indexes: set[int] = set()
        for start, end in spans:
            indexes.update(range(bisect_right(self.edu_ends, start), bisect_left(self.edu_starts, end)))
        return tuple(self.edu_ids[index] for index in sorted(indexes))


def build_parser_analysis_result(
    parser: Any,
    document: RstDocument,
    trace: PredictorAnalysisTrace,
    *,
    policy: AnalysisPolicy,
    model_analysis: RstAnalysis,
    final_analysis: RstAnalysis,
    duration_ms: float,
) -> ParserAnalysisResult:
    """Build the canonical parser result from exact backend handoff evidence."""

    composite, loaded = _composite_identity(parser, trace.segmentation_source, policy)
    analysed_document = _analysed_document(document, trace)
    component_digest = component_digest_for(composite.primary_parser)
    relation_inventory_identity = Sha256Identity(hex_digest=semantic_sha256(tuple(trace.relation_inventory)))
    primary = _primary_evidence(
        trace,
        model_analysis,
        final_analysis,
        policy,
        component_digest=component_digest,
        segmenter_component_digest=component_digest_for(composite.segmenter),
        relation_inventory_identity=relation_inventory_identity,
        marker_component_digest=component_digest_for(composite.marker_refiner),
        document_identity=document.document_id,
    )
    primary = PrimaryInferenceEvidence.model_validate({
        **primary.model_dump(),
        "relation_vocabulary": capture_runtime_vocabulary(parser.predictor, trace.relation_inventory),
    })
    validation = build_validation_receipt(
        final_analysis,
        analysed_document,
        primary,
        None,
        None,
        policy=policy,
        composite=composite,
        recombination=None,
    )
    result = ParserAnalysisResult(
        semantic=ParserAnalysisSemanticEvidence(
            policy=policy,
            analysed_document=analysed_document,
            analysis=final_analysis,
            primary_inference=primary,
            erst_completion=None,
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
    trace_tokens = {token.token_id: token for token in trace.tokens}
    edu_ids = {edu.edu_id: f"edu:{edu.edu_id:06d}" for edu in trace.edus}
    tokens = tuple(
        AnalysedToken(
            token_id=token_ids[token.token_id],
            order=order,
            text=token.text,
            character_range=PreparedRange(start=token.start, end=token.end),
            source_anchors=(_span_anchor(document.document_id, token.start, token.end, document.text),),
            sentence_id=f"sentence:{_membership(trace_tokens, (token.token_id,), 'sentence_id'):04d}",
            paragraph_id=f"paragraph:{_membership(trace_tokens, (token.token_id,), 'paragraph_id'):04d}",
        )
        for order, token in enumerate(trace.tokens)
    )
    edus = tuple(
        AnalysedEdu(
            edu_id=edu_ids[edu.edu_id],
            order=order,
            text=edu.text,
            character_range=PreparedRange(start=edu.start, end=edu.end),
            token_ids=tuple(token_ids[token_id] for token_id in edu.token_ids),
            sentence_id=f"sentence:{_membership(trace_tokens, edu.token_ids, 'sentence_id'):04d}",
            paragraph_id=f"paragraph:{_membership(trace_tokens, edu.token_ids, 'paragraph_id'):04d}",
            prepared_segment_ids=("document:segment:0000",),
            source_anchors=(_span_anchor(document.document_id, edu.start, edu.end, document.text),),
        )
        for order, edu in enumerate(trace.edus)
    )

    return AnalysedDocument(
        text=document.text,
        tokens=tokens,
        edus=edus,
        sentence_boundaries=tuple(
            PreparedRange(start=boundary.start, end=boundary.end) for boundary in trace.sentence_boundaries
        ),
        paragraph_boundaries=tuple(
            PreparedRange(start=boundary.start, end=boundary.end) for boundary in trace.paragraph_boundaries
        ),
        structural_boundary_ids=tuple(f"paragraph:{index:04d}" for index, _ in enumerate(trace.paragraph_boundaries, start=1)),
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
            decision_basis=segmentation_decision_basis(trace.segmentation_source),
            confidence=None,
            distribution=None,
            scores_unavailable_reason=(
                "presegmented_input" if trace.segmentation_source == "presegmented"
                else "not_captured_by_backend" if trace.segmentation_source == "model"
                else "deterministic_boundary_rule"
            ),
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
        node = nodes_by_span.get((decision.start + 1, decision.end + 1))
        if node is None:
            raise ValueError(f"decoded span {(decision.start, decision.end)} has no final graph node")
        raw_relation, _, nuclearity = decision.joint_labels[decision.selected_class].rpartition("_")
        nuclearity = nuclearity.upper()
        joint_weights = _exponential_weights(decision.joint_log_probabilities)
        joint_total = math.fsum(joint_weights)
        relation_labels = trace.relation_inventory
        relations = tuple(label.rpartition("_")[0] for label in decision.joint_labels)
        nuclearities = tuple(label.rpartition("_")[2].upper() for label in decision.joint_labels)
        relation_probabilities = tuple(
            math.fsum(value for label, value in zip(relations, joint_weights, strict=True) if label == relation)
            / joint_total
            for relation in relation_labels
        )
        nuclearity_probabilities = tuple(
            math.fsum(value for label, value in zip(nuclearities, joint_weights, strict=True) if label == pattern)
            / joint_total
            for pattern in ("NS", "SN", "NN")
        )
        split_distribution = (
            _distribution(
                tuple(str(value) for value in range(decision.start, decision.end)),
                decision.split_log_probabilities,
                component_digest,
            )
            if decision.split_log_probabilities is not None
            else None
        )
        relation_distribution = _probability_distribution(relation_labels, relation_probabilities, component_digest)
        nuclearity_distribution = _probability_distribution(
            ("NS", "SN", "NN"), nuclearity_probabilities, component_digest
        )
        selected_relation_probability = relation_probabilities[_relation_index(relation_labels, raw_relation)]
        confidence = math.exp(decision.joint_log_probabilities[decision.selected_class])
        structures.append(
            PrimaryStructureDecisionEvidence(
                decision_id=f"primary:{index:06d}",
                node_ids=(node.node_id,),
                primary_edge_ids=tuple(edges_by_parent.get(node.node_id, ())),
                analysed_start=node.char_span[0],
                analysed_end=node.char_span[1],
                selected_split=decision.split,
                nuclearity=nuclearity,
                relation=interpret_native_relation(
                    policy=policy,
                    raw_label=raw_relation,
                    relation_scheme="provider_native",
                    inventory_identity=relation_inventory_identity,
                    confidence=_probability_score(
                        selected_relation_probability,
                        component_digest,
                    ),
                ),
                confidence=_probability_score(confidence, component_digest),
                confidence_basis="joint_relation_nuclearity_given_selected_split",
                joint=JointRelationNuclearityEvidence(
                    labels=decision.joint_labels,
                    log_probabilities=tuple(
                        value if math.isfinite(value) else None for value in decision.joint_log_probabilities
                    ),
                    selected_class=decision.selected_class,
                ),
                split_basis=(
                    "bottom_up_transitions"
                    if decision.transitions
                    else "pointer"
                    if decision.split_log_probabilities is not None
                    else "forced_two_edu"
                ),
                transitions=decision.transitions,
                split_entropy=(
                    _entropy_score(decision.split_log_probabilities, component_digest)
                    if decision.split_log_probabilities is not None
                    else None
                ),
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


def interpret_native_relation(
    *,
    policy: AnalysisPolicy,
    raw_label: str,
    relation_scheme: str,
    inventory_identity: Sha256Identity,
    confidence: ScoreValue | None = None,
) -> RelationInterpretation:
    """Apply the requested mapping policy without inventing a canonical crosswalk."""
    mode = policy.relation_interpretation.ontology_mapping
    status = {
        "disabled": MappingStatus.NOT_MAPPED,
        "identity_only": MappingStatus.IDENTITY_ONLY,
        "provider_mapping": MappingStatus.NOT_AVAILABLE,
    }[mode]
    reason = {
        "disabled": "ontology_mapping_disabled",
        "identity_only": None,
        "provider_mapping": "authoritative_crosswalk_unavailable",
    }[mode]
    return RelationInterpretation(
        raw_label=raw_label,
        relation_scheme=relation_scheme,
        inventory_identity=inventory_identity,
        selected_ontology_concept=raw_label if status is MappingStatus.IDENTITY_ONLY else None,
        mapping_status=status,
        mapping_reason=reason,
        confidence=confidence,
    )


def analysis_anchors(
    analysis: RstAnalysis,
    analysed: AnalysedDocument,
    primary: PrimaryInferenceEvidence,
    *,
    document_identity: str,
) -> tuple[AnalysisAnchor, ...]:
    index = _AnchorIndex.build(analysed)
    anchors: list[AnalysisAnchor] = [
        AnalysisAnchor(
            target_id=edu.edu_id,
            target_kind=AnchorTargetKind.EDU,
            token_ids=edu.token_ids,
            edu_ids=(edu.edu_id,),
            prepared_segment_ids=edu.prepared_segment_ids,
            source_anchors=edu.source_anchors,
        )
        for edu in analysed.edus
    ]
    anchors.extend(_node_anchor(node, analysed, index, document_identity=document_identity) for node in analysis.nodes)
    node_by_id = {node.node_id: node for node in analysis.nodes}
    anchors.extend(
        _edge_anchor(
            edge.edge_id,
            AnchorTargetKind.PRIMARY_EDGE,
            node_by_id[edge.parent_id],
            node_by_id[edge.child_id],
            analysed,
            index,
            document_identity=document_identity,
        )
        for edge in analysis.primary_edges
    )
    anchors.extend(
        _edge_anchor(
            edge.edge_id,
            AnchorTargetKind.SECONDARY_EDGE,
            node_by_id[edge.source_id],
            node_by_id[edge.target_id],
            analysed,
            index,
            document_identity=document_identity,
        )
        for edge in analysis.secondary_edges
    )
    edu_by_id = {edu.edu_id: edu for edu in analysed.edus}
    for decision in (*primary.segmentation_decisions, *primary.structure_decisions):
        token_ids = (
            decision.token_ids
            if isinstance(decision, SegmentationDecisionEvidence)
            else index.overlapping_range(decision.analysed_start, decision.analysed_end)
        )
        edu_ids = (
            decision.resulting_edu_ids if isinstance(decision, SegmentationDecisionEvidence)
            else index.edus_overlapping(((decision.analysed_start, decision.analysed_end),))
        )
        source_anchors = tuple(anchor for edu_id in edu_ids for anchor in edu_by_id[edu_id].source_anchors)
        anchors.append(
            AnalysisAnchor(
                target_id=decision.decision_id,
                target_kind=AnchorTargetKind.DECISION,
                token_ids=token_ids,
                edu_ids=edu_ids,
                prepared_segment_ids=tuple(
                    dict.fromkeys(segment for edu_id in edu_ids for segment in edu_by_id[edu_id].prepared_segment_ids)
                ),
                source_anchors=source_anchors,
            )
        )
    for signal in analysis.signals:
        tokens = index.overlapping(signal.char_spans)
        edu_ids = index.edus_overlapping(signal.char_spans)
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
    index: _AnchorIndex,
    *,
    document_identity: str,
) -> AnalysisAnchor:
    tokens = index.overlapping_range(*node.char_span)
    edus = index.edus_overlapping((node.char_span,))
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
    index: _AnchorIndex,
    *,
    document_identity: str,
) -> AnalysisAnchor:
    source = _endpoint(source_node, analysed, index, document_identity=document_identity)
    target = _endpoint(target_node, analysed, index, document_identity=document_identity)
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
    index: _AnchorIndex,
    *,
    document_identity: str,
) -> EndpointAnchor:
    tokens = index.overlapping_range(*node.char_span)
    edus = index.edus_overlapping((node.char_span,))
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
    if policy.output_formalism is not OutputFormalism.RST_TREE:
        raise ValueError("production component discovery supports rst_tree only")
    if policy.relation_interpretation.relation_scheme != "provider_native":
        raise ValueError("RST analysis supports only the provider_native relation scheme")
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
        if segmenter_runtime is not None:
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
            segmenter, receipt = packaged_component_identity(
                "segmenter",
                ("dmrst_parser/predictor.py",),
            )
            loaded.append(receipt)
    else:
        segmenter, receipt = packaged_component_identity(
            "segmenter",
            ("dmrst_parser/predictor.py",),
        )
        loaded.append(receipt)
    if policy.marker_refinement.value == "disabled":
        marker: ComponentIdentity = NotUsedComponentIdentity(
            component="marker_refiner",
            reason="analysis policy disabled marker refinement",
        )
    else:
        marker, receipt = packaged_component_identity(
            "marker_refiner",
            ("relations/primer.py", "relations/multilingual_markers.py"),
        )
        loaded.append(receipt)

    ontology: ComponentIdentity = NotUsedComponentIdentity(
        component="ontology_mapping",
        reason="provider-native relation identity policy does not invoke ontology mapping",
    )
    detector = NotUsedComponentIdentity(component="erst_detector", reason="RST tree requested")
    scorer = NotUsedComponentIdentity(component="erst_scorer", reason="RST tree requested")
    decoder = NotUsedComponentIdentity(component="erst_decoder", reason="RST tree requested")
    calibration = NotUsedComponentIdentity(component="calibration", reason="RST tree requested")
    if release is None:
        relation_inventory, receipt = packaged_component_identity(
            "relation_inventory",
            ("dmrst_parser/predictor.py",),
        )
    else:
        relation_inventory, receipt = _released_runtime_component(
            "relation_inventory",
            parser.predictor,
            release,
            selected_roles=("relation_inventory", "relation-inventory"),
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


def packaged_component_identity(
    component: str,
    relative_paths: Sequence[str],
) -> tuple[ImmutableComponentIdentity, LoadedComponentReceipt]:
    package_root = Path(__file__).resolve().parents[1] / "rst"
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
        release_id=f"{PACKAGE_NAME}-{resolve_package_version()}",
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


def _loaded_receipt(identity: ImmutableComponentIdentity) -> LoadedComponentReceipt:
    return LoadedComponentReceipt(
        component=identity.component,
        declared_identity=component_digest_for(identity),
        resolved_member_identities=identity.files,
        verified=True,
    )


def component_digest_for(component: ComponentIdentity) -> Sha256Identity:
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


def _membership(
    tokens: Mapping[int, DocumentToken], token_ids: Sequence[int], field: Literal["sentence_id", "paragraph_id"],
) -> int:
    """Identify the first overlapping token's actual group, without a fallback."""
    if not token_ids or token_ids[0] not in tokens:
        raise ValueError("source group membership requires an identified input token")
    value = getattr(tokens[token_ids[0]], field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"input token has no valid {field} source group")
    return value


def _exponential_weights(logits: Sequence[float]) -> tuple[float, ...]:
    """Keep unnormalized mass so a marginal cannot exceed its total by rounding."""
    if not logits or any(math.isnan(value) or value == math.inf for value in logits) or max(logits) == -math.inf:
        raise ValueError("provider scores must contain a finite value and no NaN or positive infinity")
    maximum = max(logits)
    return tuple(math.exp(value - maximum) for value in logits)


def _softmax(logits: Sequence[float]) -> tuple[float, ...]:
    values = _exponential_weights(logits)
    total = math.fsum(values)
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


def _probability_distribution(
    labels: Sequence[str],
    probabilities: Sequence[float],
    component_identity: Sha256Identity,
) -> NormalizedDistribution:
    return NormalizedDistribution(
        entries=tuple(
            LabelledScore(label=label, score=_probability_score(value, component_identity))
            for label, value in zip(labels, probabilities, strict=True)
        )
    )


def _relation_index(inventory: Sequence[str], relation: str) -> int:
    try:
        return inventory.index(relation)
    except ValueError:
        rel_lower = relation.lower()
        for idx, item in enumerate(inventory):
            if item.lower() == rel_lower:
                return idx
        raise ValueError(f"selected relation {relation!r} is absent from parser inventory") from None


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


def segmentation_decision_basis(
    segmentation_source: str,
) -> Literal["model", "presegmented", "deterministic_rule"]:
    if segmentation_source == "presegmented":
        return "presegmented"
    if segmentation_source == "model":
        return "model"
    return "deterministic_rule"


def segmentation_source_from_composite(segmenter: ComponentIdentity) -> str:
    """Recover the primary run's segmentation source from its recorded identity.

    ``_composite_identity`` builds the segmenter identity from exactly three
    sources: presegmented input records a not-used identity, the packaged
    deterministic segmenter records the ``packaged_deterministic_component``
    architecture, and every other identity is a configured segmentation model.
    """

    if isinstance(segmenter, NotUsedComponentIdentity):
        return "presegmented"
    if (
        isinstance(segmenter, ImmutableComponentIdentity)
        and segmenter.architecture == "packaged_deterministic_component"
    ):
        return "deterministic_sentence_boundary_v1"
    return "model"


__all__ = [
    "analysis_anchors",
    "build_parser_analysis_result",
    "build_validation_receipt",
    "component_digest_for",
    "describe_analysis_components",
    "interpret_native_relation",
    "packaged_component_identity",
    "segmentation_decision_basis",
    "segmentation_source_from_composite",
    "validate_parser_analysis_result",
]
