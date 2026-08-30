"""Atomic deterministic recombination of complete parser-unit results."""

from dataclasses import replace
from uuid import uuid4

from isanlp_rst.contracts import (
    DiscourseSignal,
    NodeKindEnum,
    NuclearityPatternEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
    TimingRecord,
)
from isanlp_rst.ingest.contracts.analysis import (
    AnalysedDocument,
    AnalysedEdu,
    AnalysedToken,
    LocalToGlobalMapping,
    ParserAnalysisExecutionEvidence,
    ParserAnalysisResult,
    ParserAnalysisSemanticEvidence,
    PreparedRange,
    RecombinationReceipt,
    StitchingDecision,
    TokenMapping,
    UnitExecutionReceipt,
)
from isanlp_rst.ingest.contracts.base import CoverageUnit, ExactCoverage, SemanticVersion, Sha256Identity
from isanlp_rst.ingest.contracts.inference import (
    ConfidenceKind,
    MappingStatus,
    PrimaryInferenceEvidence,
    PrimaryStructureDecisionEvidence,
    RefinementRecord,
    RelationInterpretation,
    ScoreValue,
)
from isanlp_rst.ingest.contracts.preparation import AnalysisPlan
from isanlp_rst.ingest.contracts.source import TextSpanAnchor
from isanlp_rst.ingest.identity import semantic_sha256
from isanlp_rst.ingest.parser_result import (
    _analysis_anchors,
    _component_digest,
    build_validation_receipt,
    validate_parser_analysis_result,
)


def recombine_parser_results(
    *,
    document_id: str,
    text: str,
    plan: AnalysisPlan,
    unit_ranges: tuple[tuple[int, int], ...],
    results: tuple[ParserAnalysisResult, ...],
) -> ParserAnalysisResult:
    """Recombine complete successful units or fail without returning partial output."""

    if len(results) < 2 or len(results) != len(plan.units) or len(results) != len(unit_ranges):
        raise ValueError("subdivided recombination requires one complete result per plan unit")
    policy = results[0].semantic.policy
    composite = results[0].semantic.composite_identity
    loaded = results[0].semantic.loaded_components
    if any(
        result.semantic.policy != policy
        or result.semantic.composite_identity != composite
        or result.semantic.loaded_components != loaded
        for result in results[1:]
    ):
        raise ValueError("analysis units used different policies or component identities")
    if any(result.semantic.erst_completion is not None for result in results):
        raise ValueError("eRST completion must run after primary-unit recombination")

    all_tokens: list[AnalysedToken] = []
    all_edus: list[AnalysedEdu] = []
    all_mappings: list[TokenMapping] = []
    all_nodes: list[RstNode] = []
    all_edges: list[PrimaryRelationEdge] = []
    all_signals: list[DiscourseSignal] = []
    segmentation = []
    structures: list[PrimaryStructureDecisionEvidence] = []
    refinements: list[RefinementRecord] = []
    node_receipts: list[LocalToGlobalMapping] = []
    edge_receipts: list[LocalToGlobalMapping] = []
    segment_receipts: list[LocalToGlobalMapping] = []
    unit_roots: list[int] = []
    token_order = 0
    edu_order = 0
    next_node_id = 1
    for unit_index, (result, (offset, unit_end)) in enumerate(
        zip(results, unit_ranges, strict=True)
    ):
        local = result.semantic
        if local.analysed_document.text != text[offset:unit_end]:
            raise ValueError("analysis-unit text does not match its declared prepared range")
        prefix = f"unit:{unit_index:04d}"
        token_ids = {
            token.token_id: f"{prefix}:{token.token_id}"
            for token in local.analysed_document.tokens
        }
        signal_token_ids = {
            int(token.token_id.rsplit(":", 1)[-1]): token_order + index
            for index, token in enumerate(local.analysed_document.tokens)
        }
        edu_ids = {
            edu.edu_id: f"{prefix}:{edu.edu_id}"
            for edu in local.analysed_document.edus
        }
        node_ids = {
            node.node_id: next_node_id + index
            for index, node in enumerate(local.analysis.nodes)
        }
        next_node_id += len(node_ids)
        edge_ids = {
            edge.edge_id: f"{prefix}:{edge.edge_id}"
            for edge in local.analysis.primary_edges
        }
        signal_ids = {
            signal.signal_id: f"{prefix}:{signal.signal_id}"
            for signal in local.analysis.signals
        }

        for token in local.analysed_document.tokens:
            all_tokens.append(
                token.model_copy(
                    update={
                        "token_id": token_ids[token.token_id],
                        "order": token_order,
                        "character_range": PreparedRange(
                            start=token.character_range.start + offset,
                            end=token.character_range.end + offset,
                        ),
                        "source_anchors": (
                            _document_anchor(
                                document_id,
                                token.character_range.start + offset,
                                token.character_range.end + offset,
                                text,
                            ),
                        ),
                        "sentence_id": f"{prefix}:{token.sentence_id}",
                        "paragraph_id": f"{prefix}:{token.paragraph_id}",
                    }
                )
            )
            token_order += 1
        for edu in local.analysed_document.edus:
            mapped_tokens = tuple(token_ids[token_id] for token_id in edu.token_ids)
            anchors = tuple(
                token.source_anchors[0]
                for token in all_tokens
                if token.token_id in mapped_tokens
            )
            all_edus.append(
                edu.model_copy(
                    update={
                        "edu_id": edu_ids[edu.edu_id],
                        "order": edu_order,
                        "token_ids": mapped_tokens,
                        "sentence_id": f"{prefix}:{edu.sentence_id}",
                        "paragraph_id": f"{prefix}:{edu.paragraph_id}",
                        "prepared_segment_ids": (f"document:segment:{unit_index:04d}",),
                        "source_anchors": anchors,
                    }
                )
            )
            edu_order += 1
        all_mappings.extend(
            TokenMapping(
                token_id=token_ids[mapping.token_id],
                edu_id=edu_ids[mapping.edu_id],
                sentence_id=f"{prefix}:{mapping.sentence_id}",
                paragraph_id=f"{prefix}:{mapping.paragraph_id}",
            )
            for mapping in local.analysed_document.mappings
        )
        for node in local.analysis.nodes:
            all_nodes.append(
                replace(
                    node,
                    node_id=node_ids[node.node_id],
                    edu_span=(
                        node.edu_span[0] + edu_order - len(local.analysed_document.edus),
                        node.edu_span[1] + edu_order - len(local.analysed_document.edus),
                    ),
                    char_span=(node.char_span[0] + offset, node.char_span[1] + offset),
                )
            )
            node_receipts.append(
                LocalToGlobalMapping(
                    unit_id=plan.units[unit_index].unit_id,
                    local_id=str(node.node_id),
                    global_id=str(node_ids[node.node_id]),
                )
            )
        for edge in local.analysis.primary_edges:
            all_edges.append(
                replace(
                    edge,
                    edge_id=edge_ids[edge.edge_id],
                    parent_id=node_ids[edge.parent_id],
                    child_id=node_ids[edge.child_id],
                )
            )
            edge_receipts.append(
                LocalToGlobalMapping(
                    unit_id=plan.units[unit_index].unit_id,
                    local_id=edge.edge_id,
                    global_id=edge_ids[edge.edge_id],
                )
            )
        all_signals.extend(
            signal.model_copy(
                update={
                    "signal_id": signal_ids[signal.signal_id],
                    "edge_id": (
                        edge_ids[signal.edge_id]
                        if signal.edge_id is not None and signal.edge_id in edge_ids
                        else signal.edge_id
                    ),
                    "token_ids": tuple(signal_token_ids[token_id] for token_id in signal.token_ids),
                    "char_spans": tuple(
                        (start + offset, end + offset) for start, end in signal.char_spans
                    ),
                }
            )
            for signal in local.analysis.signals
        )
        segmentation.extend(
            decision.model_copy(
                update={
                    "decision_id": f"{prefix}:{decision.decision_id}",
                    "boundary_id": f"{prefix}:{decision.boundary_id}",
                    "token_ids": tuple(token_ids[token_id] for token_id in decision.token_ids),
                    "resulting_edu_ids": tuple(
                        edu_ids[edu_id] for edu_id in decision.resulting_edu_ids
                    ),
                }
            )
            for decision in local.primary_inference.segmentation_decisions
        )
        structures.extend(
            decision.model_copy(
                update={
                    "decision_id": f"{prefix}:{decision.decision_id}",
                    "node_ids": tuple(node_ids[node_id] for node_id in decision.node_ids),
                    "primary_edge_ids": tuple(
                        edge_ids[edge_id] for edge_id in decision.primary_edge_ids
                    ),
                    "analysed_start": decision.analysed_start + offset,
                    "analysed_end": decision.analysed_end + offset,
                }
            )
            for decision in local.primary_inference.structure_decisions
        )
        refinements.extend(
            refinement.__class__.model_validate(
                {
                    **refinement.model_dump(exclude={"semantic_digest"}),
                    "refinement_id": f"{prefix}:{refinement.refinement_id}",
                    "trigger_signal_ids": tuple(
                        signal_ids[signal_id] for signal_id in refinement.trigger_signal_ids
                    ),
                    "trigger_anchors": tuple(
                        _shift_anchor(anchor, offset, document_id, text)
                        for anchor in refinement.trigger_anchors
                    ),
                    "graph_element_ids": tuple(
                        edge_ids.get(element_id, element_id)
                        for element_id in refinement.graph_element_ids
                    ),
                }
            )
            for refinement in local.primary_inference.refinements
        )
        child_ids = {edge.child_id for edge in local.analysis.primary_edges}
        roots = [node.node_id for node in local.analysis.nodes if node.node_id not in child_ids]
        if len(roots) != 1:
            raise ValueError("analysis unit does not contain exactly one primary root")
        unit_roots.append(node_ids[roots[0]])
        segment_receipts.append(
            LocalToGlobalMapping(
                unit_id=plan.units[unit_index].unit_id,
                local_id="document:segment:0000",
                global_id=f"document:segment:{unit_index:04d}",
            )
        )

    stitch_node_id = next_node_id
    all_nodes.append(
        RstNode(
            node_id=stitch_node_id,
            kind=NodeKindEnum.MULTINUCLEAR_GROUP,
            edu_span=(1, len(all_edus)),
            char_span=(0, len(text)),
            text=text,
        )
    )
    stitch_edges = tuple(
        PrimaryRelationEdge(
            edge_id=f"recombine:edge:{index:04d}",
            parent_id=stitch_node_id,
            child_id=root_id,
            relation_raw="same-unit",
            relation_concept="same-unit",
            nuclearity=NuclearityPatternEnum.NN,
            confidence=None,
            calibrated=False,
        )
        for index, root_id in enumerate(unit_roots)
    )
    all_edges.extend(stitch_edges)
    recombination_identity = Sha256Identity(
        hex_digest=semantic_sha256(
            {
                "policy": "multinuclear_unit_root_v1",
                "version": "2.0.0",
                "plan": plan.semantic_digest,
            }
        )
    )
    relation_inventory_identity = _component_digest(composite.relation_inventory)
    structures.append(
        PrimaryStructureDecisionEvidence(
            decision_id="recombine:decision:0000",
            node_ids=(stitch_node_id,),
            primary_edge_ids=tuple(edge.edge_id for edge in stitch_edges),
            analysed_start=0,
            analysed_end=len(text),
            selected_split=None,
            nuclearity="NN",
            relation=RelationInterpretation(
                raw_label="same-unit",
                relation_scheme="deterministic_recombination",
                inventory_identity=relation_inventory_identity,
                selected_ontology_concept="same-unit",
                mapping_status=MappingStatus.IDENTITY_ONLY,
            ),
            confidence=ScoreValue(
                value=1.0,
                confidence_kind=ConfidenceKind.DETERMINISTIC,
                minimum=1.0,
                maximum=1.0,
                producing_component_identity=recombination_identity,
            ),
            producing_component_identity=recombination_identity,
        )
    )
    analysis = RstAnalysis(
        document_id=document_id,
        formalism=results[0].analysis.formalism,
        nodes=tuple(all_nodes),
        primary_edges=tuple(all_edges),
        secondary_edges=(),
        signals=tuple(all_signals),
        provenance=results[0].analysis.provenance,
        timing=TimingRecord(
            parsing_ms=sum(result.analysis.timing.parsing_ms for result in results),
            total_ms=sum(result.analysis.timing.total_ms for result in results),
        ),
    )
    analysed = AnalysedDocument(
        text=text,
        tokens=tuple(all_tokens),
        edus=tuple(all_edus),
        mappings=tuple(all_mappings),
        sentence_boundaries=tuple(
            PreparedRange(start=boundary.start + offset, end=boundary.end + offset)
            for result, (offset, _) in zip(results, unit_ranges, strict=True)
            for boundary in result.analysed_document.sentence_boundaries
        ),
        paragraph_boundaries=tuple(
            PreparedRange(start=boundary.start + offset, end=boundary.end + offset)
            for result, (offset, _) in zip(results, unit_ranges, strict=True)
            for boundary in result.analysed_document.paragraph_boundaries
        ),
        structural_boundary_ids=tuple(
            f"unit:{index:04d}" for index in range(len(results))
        ),
        prepared_segment_ids=tuple(
            f"document:segment:{index:04d}" for index in range(len(results))
        ),
        source_anchors=(_document_anchor(document_id, 0, len(text), text),),
        transformations=(),
        fidelity=results[0].analysed_document.fidelity,
        character_coverage=ExactCoverage(
            covered_units=len(text),
            total_units=len(text),
            unit=CoverageUnit.CHARACTERS,
        ),
        token_coverage=ExactCoverage(
            covered_units=len(all_tokens),
            total_units=len(all_tokens),
            unit=CoverageUnit.ITEMS,
        ),
        edu_coverage=ExactCoverage(
            covered_units=len(all_edus),
            total_units=len(all_edus),
            unit=CoverageUnit.ITEMS,
        ),
    )
    primary = PrimaryInferenceEvidence(
        segmentation_decisions=tuple(segmentation),
        structure_decisions=tuple(structures),
        refinements=tuple(refinements),
    )
    anchors = _analysis_anchors(
        analysis,
        analysed,
        primary,
        document_identity=document_id,
    )
    receipt = RecombinationReceipt(
        unit_identities=tuple(
            Sha256Identity(hex_digest=semantic_sha256(unit)) for unit in plan.units
        ),
        local_result_identities=tuple(
            _required_identity(result) for result in results
        ),
        segment_mappings=tuple(segment_receipts),
        node_mappings=tuple(node_receipts),
        edge_mappings=tuple(edge_receipts),
        boundary_inputs=tuple(
            f"{link.predecessor_unit_id}->{link.successor_unit_id}"
            for link in plan.recombination.links
        ),
        nuclear_spine_inputs=tuple(str(root) for root in unit_roots),
        stitching_decisions=(
            StitchingDecision(
                decision_id="recombine:decision:0000",
                predecessor_unit_id=plan.units[0].unit_id,
                successor_unit_id=plan.units[-1].unit_id,
                relation="same-unit",
                nuclearity="NN",
            ),
        ),
        warnings=(),
        policy="multinuclear_unit_root_v1",
        policy_version=SemanticVersion(root="2.0.0"),
        unit_durations_ms=tuple(result.execution.duration_ms for result in results),
    )
    validation = build_validation_receipt(
        analysis,
        analysed,
        primary,
        None,
        anchors,
        policy=policy,
        composite=composite,
        recombination=receipt,
    )
    combined = ParserAnalysisResult(
        semantic=ParserAnalysisSemanticEvidence(
            policy=policy,
            analysed_document=analysed,
            analysis=analysis,
            anchors=anchors,
            primary_inference=primary,
            erst_completion=None,
            composite_identity=composite,
            loaded_components=loaded,
            recombination=receipt,
            validation=validation,
        ),
        execution=ParserAnalysisExecutionEvidence(
            execution_id=str(uuid4()),
            duration_ms=sum(result.execution.duration_ms for result in results),
            device=results[0].execution.device,
            unit_executions=tuple(
                UnitExecutionReceipt(
                    unit_id=plan.units[index].unit_id,
                    duration_ms=result.execution.duration_ms,
                    device=result.execution.device,
                )
                for index, result in enumerate(results)
            ),
        ),
    )
    validate_parser_analysis_result(combined)
    return combined


def _document_anchor(
    document_id: str,
    start: int,
    end: int,
    text: str,
) -> TextSpanAnchor:
    return TextSpanAnchor(
        artifact_identity=document_id,
        start=start,
        end=end,
        quote=text[start:end],
    )


def _shift_anchor(
    anchor: object,
    offset: int,
    document_id: str,
    text: str,
) -> object:
    if isinstance(anchor, TextSpanAnchor):
        return _document_anchor(document_id, anchor.start + offset, anchor.end + offset, text)
    return anchor


def _required_identity(result: ParserAnalysisResult) -> Sha256Identity:
    if result.semantic_digest is None:
        raise ValueError("analysis unit has no semantic identity")
    return result.semantic_digest


__all__ = ["recombine_parser_results"]
