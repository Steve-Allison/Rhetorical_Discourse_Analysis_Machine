"""Cross-field production inventory, preparation, analysis, and evidence validation."""

from isanlp_rst.contracts import RstAnalysis
from isanlp_rst.contracts.enums import NodeKindEnum
from isanlp_rst.ingest.contracts.analysis import (
    AnalysedDocument,
    AnalysisAnchor,
    AnalysisPolicy,
    AnchorTargetKind,
    CheckClassification,
    CheckOutcome,
    FidelityClass,
    ParserAnalysisResult,
    RecombinationReceipt,
    ValidationCheckReceipt,
    ValidationReceipt,
)
from isanlp_rst.ingest.contracts.base import CoverageUnit, ExactCoverage
from isanlp_rst.ingest.contracts.inference import (
    CompositeAnalysisIdentity,
    ErstCompletionEvidence,
    ImmutableComponentIdentity,
    PrimaryInferenceEvidence,
)
from isanlp_rst.ingest.contracts.source import (
    ContentInventoryItem,
    DispositionDecision,
    RedactedContentRepresentation,
)
from isanlp_rst.ingest.contracts.preparation import (
    AnalysisPlanStatus,
    PlanningPolicy,
    PreparationOutcome,
    PreparationPolicy,
    PreparedRstDocument,
    TransformationRecord,
)
from isanlp_rst.ingest.identity import (
    parser_result_semantic_identity,
    preparation_semantic_identity,
    semantic_sha256,
)


def build_analysis_validation_receipt(
    analysis: RstAnalysis,
    analysed: AnalysedDocument,
    primary: PrimaryInferenceEvidence,
    erst: ErstCompletionEvidence | None,
    anchors: tuple[AnalysisAnchor, ...],
    *,
    policy: AnalysisPolicy,
    composite: CompositeAnalysisIdentity,
    recombination: RecombinationReceipt | None,
) -> ValidationReceipt:
    """Validate every required analysis invariant and return its stable receipt."""

    validators = {
        "source_substrate_identity": lambda: _validate_analysed_document(analysed),
        "primary_tree": lambda: _validate_primary_tree(analysis),
        "erst_formal_rules": lambda: _validate_erst(analysis, erst),
        "decision_evidence": lambda: _validate_decisions(analysis, primary, erst),
        "analysis_anchors": lambda: _validate_anchors(analysis, analysed, anchors),
        "component_identity": lambda: _validate_composite(composite),
        "semantic_identity": lambda: None,
    }
    checks: list[ValidationCheckReceipt] = []
    for check_id in policy.validation.required_checks:
        validator = validators.get(check_id)
        if validator is None:
            raise ValueError(f"validation policy names unsupported required check {check_id!r}")
        validator()
        checks.append(
            ValidationCheckReceipt(
                check_id=check_id,
                classification=CheckClassification.REQUIRED,
                outcome=CheckOutcome.PASSED,
                checked_count=_analysis_checked_count(check_id, analysis, anchors, primary),
                affected_ids=(),
            )
        )
    for check_id in policy.validation.advisory_checks:
        checks.append(
            ValidationCheckReceipt(
                check_id=check_id,
                classification=CheckClassification.ADVISORY,
                outcome=CheckOutcome.NOT_APPLICABLE,
                checked_count=0,
                affected_ids=(),
                code="advisory_not_configured",
            )
        )
    graph_count = len(analysis.nodes) + len(analysis.primary_edges) + len(analysis.secondary_edges)
    evidence_count = len(primary.segmentation_decisions) + len(primary.structure_decisions)
    if erst is not None:
        evidence_count += len(erst.candidate_decisions)
    if recombination is not None:
        _validate_recombination(recombination)
    return ValidationReceipt(
        policy_version=policy.validation.policy_version,
        checks=tuple(checks),
        passed=True,
        graph_coverage=ExactCoverage(covered_units=graph_count, total_units=graph_count, unit=CoverageUnit.ITEMS),
        anchor_coverage=ExactCoverage(covered_units=len(anchors), total_units=len(anchors), unit=CoverageUnit.ANCHORS),
        evidence_coverage=ExactCoverage(covered_units=evidence_count, total_units=evidence_count, unit=CoverageUnit.ITEMS),
        warnings=(),
    )


def validate_parser_analysis_result(result: ParserAnalysisResult) -> None:
    """Recompute and revalidate every public parser-result semantic handoff."""

    semantic = result.semantic
    rebuilt = build_analysis_validation_receipt(
        semantic.analysis,
        semantic.analysed_document,
        semantic.primary_inference,
        semantic.erst_completion,
        semantic.anchors,
        policy=semantic.policy,
        composite=semantic.composite_identity,
        recombination=semantic.recombination,
    )
    if rebuilt != semantic.validation:
        raise ValueError("parser result validation receipt does not reproduce")
    immutable_components = tuple(
        component
        for component in (
            semantic.composite_identity.primary_parser,
            semantic.composite_identity.segmenter,
            semantic.composite_identity.marker_refiner,
            semantic.composite_identity.erst_detector,
            semantic.composite_identity.erst_scorer,
            semantic.composite_identity.erst_decoder,
            semantic.composite_identity.calibration,
            semantic.composite_identity.relation_inventory,
            semantic.composite_identity.ontology_mapping,
        )
        if isinstance(component, ImmutableComponentIdentity)
    )
    receipt_by_component = {receipt.component: receipt for receipt in semantic.loaded_components}
    if len(receipt_by_component) != len(semantic.loaded_components):
        raise ValueError("loaded component receipts contain duplicate component identities")
    if set(receipt_by_component) != {component.component for component in immutable_components}:
        raise ValueError("loaded component receipts do not match immutable participating components")
    for component in immutable_components:
        receipt = receipt_by_component[component.component]
        if (
            receipt.declared_identity.hex_digest != semantic_sha256(component)
            or receipt.resolved_member_identities != component.files
            or receipt.verified is not True
        ):
            raise ValueError("loaded component receipt does not reproduce its declared identity")
    expected = parser_result_semantic_identity(result)
    if result.semantic_digest is None or result.semantic_digest.hex_digest != expected:
        raise ValueError("parser result semantic identity does not reproduce")


def _validate_analysed_document(document: AnalysedDocument) -> None:
    if document.fidelity is not FidelityClass.LOSSLESS:
        raise ValueError("production analysed document is not lossless")
    token_ids = {token.token_id for token in document.tokens}
    edu_ids = {edu.edu_id for edu in document.edus}
    if len(token_ids) != len(document.tokens) or len(edu_ids) != len(document.edus):
        raise ValueError("analysed token or EDU identity is duplicated")
    if {mapping.token_id for mapping in document.mappings} != token_ids:
        raise ValueError("token mappings do not cover every analysed token")
    if any(mapping.edu_id not in edu_ids for mapping in document.mappings):
        raise ValueError("token mapping references an absent EDU")
    for token in document.tokens:
        if document.text[token.character_range.start:token.character_range.end] != token.text:
            raise ValueError("analysed token cannot be reconstructed from exact offsets")
    if document.character_coverage.covered_units != len(document.text):
        raise ValueError("analysed character coverage is incomplete")


def _validate_primary_tree(analysis: RstAnalysis) -> None:
    node_ids = {node.node_id for node in analysis.nodes}
    if len(node_ids) != len(analysis.nodes) or not node_ids:
        raise ValueError("primary graph requires unique nodes")
    children: dict[int, list[int]] = {}
    child_ids: set[int] = set()
    edge_ids: set[str] = set()
    for edge in analysis.primary_edges:
        if edge.edge_id in edge_ids or edge.parent_id not in node_ids or edge.child_id not in node_ids:
            raise ValueError("primary edge identity or endpoint is invalid")
        if edge.parent_id == edge.child_id or not edge.relation_raw or not edge.relation_concept:
            raise ValueError("primary edge is a self-loop or lacks relation semantics")
        if edge.child_id in child_ids:
            raise ValueError("primary graph node has multiple parents")
        edge_ids.add(edge.edge_id)
        child_ids.add(edge.child_id)
        children.setdefault(edge.parent_id, []).append(edge.child_id)
    roots = node_ids - child_ids
    if len(roots) != 1 or len(analysis.primary_edges) != len(node_ids) - 1:
        raise ValueError("primary graph is not a single rooted tree")
    visited: set[int] = set()
    active: set[int] = set()

    def visit(node_id: int) -> None:
        if node_id in active:
            raise ValueError("primary graph contains a cycle")
        if node_id in visited:
            return
        active.add(node_id)
        for child_id in children.get(node_id, ()):
            visit(child_id)
        active.remove(node_id)
        visited.add(node_id)

    visit(next(iter(roots)))
    if visited != node_ids:
        raise ValueError("primary graph is disconnected")


def _validate_erst(analysis: RstAnalysis, evidence: ErstCompletionEvidence | None) -> None:
    if evidence is None:
        if analysis.secondary_edges:
            raise ValueError("secondary edges exist without eRST completion evidence")
        return
    node_ids = {node.node_id for node in analysis.nodes}
    sufficient = {signal.signal_id for signal in analysis.signals if signal.sufficient}
    decisions = {decision.secondary_edge_id: decision for decision in evidence.candidate_decisions if decision.secondary_edge_id}
    seen: set[tuple[int, int]] = set()
    for edge in analysis.secondary_edges:
        pair = (edge.source_id, edge.target_id)
        decision = decisions.get(edge.edge_id)
        if edge.source_id == edge.target_id or edge.source_id not in node_ids or edge.target_id not in node_ids:
            raise ValueError("secondary edge violates endpoint constraints")
        if pair in seen:
            raise ValueError("secondary edge duplicates a directed pair")
        if decision is None or not set(decision.supporting_signal_ids) & sufficient:
            raise ValueError("secondary edge lacks sufficient supporting signal evidence")
        seen.add(pair)


def _validate_decisions(analysis: RstAnalysis, primary: PrimaryInferenceEvidence, erst: ErstCompletionEvidence | None) -> None:
    node_ids = {node.node_id for node in analysis.nodes}
    edge_ids = {edge.edge_id for edge in analysis.primary_edges}
    linked_nodes = {node_id for decision in primary.structure_decisions for node_id in decision.node_ids}
    linked_edges = {edge_id for decision in primary.structure_decisions for edge_id in decision.primary_edge_ids}
    non_edu_nodes = {node.node_id for node in analysis.nodes if node.kind is not NodeKindEnum.EDU}
    if linked_nodes != non_edu_nodes or linked_edges != edge_ids:
        raise ValueError("primary decisions do not cover every created non-EDU node and edge")
    if any(node_id not in node_ids for node_id in linked_nodes):
        raise ValueError("primary decision references an absent node")
    for refinement in primary.refinements:
        if not refinement.trigger_signal_ids or not set(refinement.graph_element_ids) <= edge_ids:
            raise ValueError("refinement lacks trigger evidence or graph linkage")
    if erst is not None:
        candidate_ids = {decision.candidate_id for decision in erst.candidate_decisions}
        if tuple(decision.candidate_id for decision in erst.candidate_decisions) != erst.decode_receipt.candidate_decision_ids:
            raise ValueError("eRST decoder receipt order differs from candidate decisions")
        for signal in erst.signals:
            if not signal.candidate_ids or not set(signal.candidate_ids) <= candidate_ids:
                raise ValueError("eRST signal is orphaned or references an absent candidate")


def _validate_anchors(analysis: RstAnalysis, analysed: AnalysedDocument, anchors: tuple[AnalysisAnchor, ...]) -> None:
    expected: set[tuple[str, AnchorTargetKind]] = {(str(node.node_id), AnchorTargetKind.NODE) for node in analysis.nodes}
    expected.update((edge.edge_id, AnchorTargetKind.PRIMARY_EDGE) for edge in analysis.primary_edges)
    expected.update((edge.edge_id, AnchorTargetKind.SECONDARY_EDGE) for edge in analysis.secondary_edges)
    actual = {(anchor.target_id, anchor.target_kind) for anchor in anchors}
    if not expected <= actual:
        raise ValueError("analysis anchors do not cover every graph element")
    token_ids = {token.token_id for token in analysed.tokens}
    edu_ids = {edu.edu_id for edu in analysed.edus}
    for anchor in anchors:
        if not set(anchor.token_ids) <= token_ids or not set(anchor.edu_ids) <= edu_ids:
            raise ValueError("analysis anchor references an absent analysed token or EDU")
        if not anchor.source_anchors:
            raise ValueError("analysis anchor lacks source reconstruction anchors")


def _validate_composite(composite: CompositeAnalysisIdentity) -> None:
    expected = semantic_sha256(composite.model_dump(exclude={"semantic_digest"}))
    if composite.semantic_digest is None or composite.semantic_digest.hex_digest != expected:
        raise ValueError("composite component identity does not reproduce")


def _validate_recombination(receipt: RecombinationReceipt) -> None:
    if len(receipt.unit_identities) != len(receipt.local_result_identities):
        raise ValueError("recombination local-result identities do not cover every unit")
    if len(receipt.unit_identities) != len(receipt.unit_durations_ms):
        raise ValueError("recombination timings do not cover every unit")
    if len({mapping.global_id for mapping in receipt.node_mappings}) != len(receipt.node_mappings):
        raise ValueError("recombination node mappings are not one-to-one")
    if len({mapping.global_id for mapping in receipt.edge_mappings}) != len(receipt.edge_mappings):
        raise ValueError("recombination edge mappings are not one-to-one")


def _analysis_checked_count(check_id: str, analysis: RstAnalysis, anchors: tuple[AnalysisAnchor, ...], primary: PrimaryInferenceEvidence) -> int:
    return {
        "source_substrate_identity": len(primary.segmentation_decisions),
        "primary_tree": len(analysis.nodes) + len(analysis.primary_edges),
        "erst_formal_rules": len(analysis.secondary_edges),
        "decision_evidence": len(primary.structure_decisions) + len(primary.refinements),
        "analysis_anchors": len(anchors),
        "component_identity": 9,
        "semantic_identity": 1,
    }[check_id]


def validate_inventory(inventory: tuple[ContentInventoryItem, ...]) -> None:
    """Reject incomplete links, duplicate cycles, or inaccessible retained content."""

    by_id = {item.item_id: item for item in inventory}
    if len(by_id) != len(inventory):
        raise ValueError("inventory item identities must be unique")
    for item in inventory:
        if item.parent_id is not None:
            parent = by_id.get(item.parent_id)
            if parent is None or item.item_id not in parent.child_ids:
                raise ValueError(f"inventory parent link is not reciprocal: {item.item_id}")
        for child_id in item.child_ids:
            child = by_id.get(child_id)
            if child is None or child.parent_id != item.item_id:
                raise ValueError(f"inventory child link is not reciprocal: {child_id}")
        for relationship in item.relationships:
            if (
                relationship.target_kind == "inventory_item"
                and relationship.target_identity not in by_id
            ):
                raise ValueError(
                    f"inventory relationship target does not exist: {relationship.target_identity}"
                )
        if item.disposition.retained and isinstance(
            item.representation,
            RedactedContentRepresentation,
        ):
            raise ValueError("normal retained inventory cannot replace accessible content with a digest")
        if item.disposition.decision is DispositionDecision.DUPLICATE:
            _validate_duplicate_chain(item.item_id, by_id)


def validate_preparation_outcome(outcome: PreparationOutcome) -> None:
    """Fail closed unless every exposed preparation reference and identity agrees."""

    semantic = outcome.semantic
    prepared = semantic.prepared_document
    inventory = semantic.inventory
    validate_inventory(inventory)
    if semantic.source != prepared.source:
        raise ValueError("preparation source summary and prepared source differ")

    _revalidate(semantic.preparation_policy, PreparationPolicy)
    _revalidate(semantic.planning_policy, PlanningPolicy)
    _revalidate(prepared, PreparedRstDocument)
    for transformation in semantic.transformations:
        _revalidate(transformation, TransformationRecord)

    primary_count = sum(
        item.disposition.decision is DispositionDecision.PRIMARY for item in inventory
    )
    retained_count = sum(item.disposition.retained for item in inventory)
    _require_exact_coverage(
        semantic.inventory_coverage.covered_units,
        semantic.inventory_coverage.total_units,
        len(inventory),
        "inventory",
    )
    _require_exact_coverage(
        semantic.primary_coverage.covered_units,
        semantic.primary_coverage.total_units,
        primary_count,
        "primary",
    )
    _require_exact_coverage(
        semantic.retained_coverage.covered_units,
        semantic.retained_coverage.total_units,
        retained_count,
        "retained",
    )
    mapped = sum(segment.prepared_range.length for segment in prepared.segments)
    _require_exact_coverage(
        semantic.mapping_coverage.covered_units,
        semantic.mapping_coverage.total_units,
        len(prepared.text),
        "mapping",
    )
    if mapped != len(prepared.text):
        raise ValueError("prepared mapping does not cover every output character")

    item_by_id = {item.item_id: item for item in inventory}
    segment_by_id = {segment.segment_id: segment for segment in prepared.segments}
    transformation_by_id = {
        transformation.transformation_id: transformation
        for transformation in semantic.transformations
    }
    boundary_by_id = {
        boundary.boundary_id: boundary for boundary in prepared.structural_boundaries
    }
    if len(segment_by_id) != len(prepared.segments):
        raise ValueError("prepared segment identities must be unique")
    if len(transformation_by_id) != len(semantic.transformations):
        raise ValueError("transformation identities must be unique")
    if len(boundary_by_id) != len(prepared.structural_boundaries):
        raise ValueError("structural boundary identities must be unique")

    for item in inventory:
        if any(anchor.artifact_identity != semantic.source.source_id for anchor in item.anchors):
            raise ValueError(f"inventory item {item.item_id!r} has a foreign source anchor")

    for segment in prepared.segments:
        if any(item_id not in item_by_id for item_id in segment.contributing_item_ids):
            raise ValueError(f"segment {segment.segment_id!r} references an absent inventory item")
        if any(anchor.artifact_identity != semantic.source.source_id for anchor in segment.source_anchors):
            raise ValueError(f"segment {segment.segment_id!r} has a foreign source anchor")
        if segment.structural_boundary_id not in boundary_by_id and segment.structural_boundary_id is not None:
            raise ValueError(f"segment {segment.segment_id!r} has an absent structural boundary")
        if any(value not in transformation_by_id for value in segment.transformation_ids):
            raise ValueError(f"segment {segment.segment_id!r} has an absent transformation")

    for transformation in semantic.transformations:
        if any(item_id not in item_by_id for item_id in transformation.input_item_ids):
            raise ValueError(f"transformation {transformation.transformation_id!r} has an absent input")
        if any(segment_id not in segment_by_id for segment_id in transformation.output_segment_ids):
            raise ValueError(f"transformation {transformation.transformation_id!r} has an absent output")
        for segment_id in transformation.output_segment_ids:
            if transformation.transformation_id not in segment_by_id[segment_id].transformation_ids:
                raise ValueError("transformation-to-segment link is not reciprocal")
        for item_id in transformation.input_item_ids:
            if transformation.transformation_id not in item_by_id[item_id].disposition.transformation_ids:
                raise ValueError("transformation-to-inventory link is not reciprocal")

    for boundary in prepared.structural_boundaries:
        if any(item_id not in item_by_id for item_id in boundary.source_item_ids):
            raise ValueError(f"boundary {boundary.boundary_id!r} has an absent inventory source")
        if boundary.parent_boundary_id is not None:
            parent = boundary_by_id.get(boundary.parent_boundary_id)
            if parent is None or boundary.boundary_id not in parent.child_boundary_ids:
                raise ValueError("structural boundary parent link is not reciprocal")
        for child_id in boundary.child_boundary_ids:
            child = boundary_by_id.get(child_id)
            if child is None or child.parent_boundary_id != boundary.boundary_id:
                raise ValueError("structural boundary child link is not reciprocal")

    _validate_analysis_plan(outcome)
    expected_identity = preparation_semantic_identity(outcome)
    if outcome.semantic_digest is None or outcome.semantic_digest.hex_digest != expected_identity:
        raise ValueError("preparation outcome semantic digest mismatch")


def _validate_analysis_plan(outcome: PreparationOutcome) -> None:
    plan = outcome.semantic.analysis_plan
    _revalidate(plan, type(plan))
    segments = outcome.semantic.prepared_document.segments
    if plan.status is AnalysisPlanStatus.NOT_PLANNED:
        if plan.units or plan.recombination.links:
            raise ValueError("not-planned analysis cannot contain units or recombination links")
        return
    covered_orders: list[int] = []
    for expected_order, unit in enumerate(plan.units):
        if unit.order != expected_order:
            raise ValueError("analysis units are not in canonical order")
        covered_orders.extend(range(unit.first_segment_order, unit.last_segment_order + 1))
        expected_predecessor = plan.units[expected_order - 1].unit_id if expected_order else None
        expected_successor = (
            plan.units[expected_order + 1].unit_id
            if expected_order + 1 < len(plan.units)
            else None
        )
        if unit.predecessor_id != expected_predecessor or unit.successor_id != expected_successor:
            raise ValueError("analysis-unit chain is incomplete")
    if covered_orders != list(range(len(segments))):
        raise ValueError("analysis units must cover every prepared segment exactly once")
    expected_links = tuple(
        (left.unit_id, right.unit_id, right.first_segment_order)
        for left, right in zip(plan.units, plan.units[1:], strict=False)
    )
    actual_links = tuple(
        (link.predecessor_unit_id, link.successor_unit_id, link.boundary_segment_order)
        for link in plan.recombination.links
    )
    if actual_links != expected_links:
        raise ValueError("analysis recombination links do not match the unit chain")


def _require_exact_coverage(covered: int, total: int, expected: int, label: str) -> None:
    if covered != expected or total != expected:
        raise ValueError(f"{label} coverage is not exact")


def _revalidate(value: object, model_type: type[object]) -> None:
    validator = getattr(model_type, "model_validate", None)
    dumper = getattr(value, "model_dump", None)
    if not callable(validator) or not callable(dumper):
        raise TypeError("preparation validation received a non-contract value")
    validator(dumper())


def _validate_duplicate_chain(
    item_id: str,
    by_id: dict[str, ContentInventoryItem],
) -> None:
    seen: set[str] = set()
    current = by_id[item_id]
    while current.disposition.duplicate_of is not None:
        if current.item_id in seen:
            raise ValueError(f"duplicate disposition cycle includes {current.item_id}")
        seen.add(current.item_id)
        target = by_id.get(current.disposition.duplicate_of)
        if target is None:
            raise ValueError(
                f"duplicate canonical target does not exist: {current.disposition.duplicate_of}"
            )
        current = target
    if current.disposition.decision is DispositionDecision.DUPLICATE:
        raise ValueError("duplicate chain does not resolve to a canonical item")


__all__ = [
    "build_analysis_validation_receipt",
    "validate_inventory",
    "validate_parser_analysis_result",
    "validate_preparation_outcome",
]
