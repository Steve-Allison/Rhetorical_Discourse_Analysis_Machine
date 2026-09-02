"""Canonical v2 production source preparation and analysis orchestration."""

from pathlib import Path
from time import perf_counter
from typing import Final, Protocol, runtime_checkable
from uuid import uuid4

from rdam.rst._provenance import resolve_package_version, resolve_source_revision
from rdam.rst.contracts import Edu, RstDocument
from rdam.rst.ingest.contracts.analysis import (
    AnalysedOutcome,
    AnalysisExecutionEvidence,
    AnalysisPolicy,
    AnalysisRequest,
    AnalysisSemanticEvidence,
    AnalysisStatus,
    CacheStatus,
    EmptyPrimaryAnalysisOutcome,
    LossyInputPolicy,
    MarkerRefinementMode,
    ParserAnalysisResult,
    ProductionAnalysisOutcome,
    RelationInterpretationPolicy,
    ValidationPolicy,
)
from rdam.rst.ingest.contracts.base import SemanticVersion, Sha256Identity
from rdam.rst.ingest.contracts.capabilities import ProductionCapabilities
from rdam.rst.ingest.contracts.failure import (
    AcquisitionCompletedEvidence,
    DiagnosticPolicy,
    FailureCategory,
    InferenceCompletedEvidence,
    LifecycleStage,
    MissingDistributionContext,
    PreparationCompletedEvidence,
    ProductionFailure,
    ProductionIngestError,
    Retryability,
    SafeCause,
)
from rdam.rst.ingest.contracts.inference import (
    CompositeAnalysisIdentity,
    EvidenceDetailPolicy,
    InferenceEvidence,
    NotUsedComponentIdentity,
    OutputFormalism,
)
from rdam.rst.ingest.contracts.preparation import (
    AnalysisPlanStatus,
    CapacityUnit,
    ParserCapacity,
    PlanningPolicy,
    PreparationOutcome,
    PreparationPolicy,
    PreparedRstDocument,
    SegmentKind,
)
from rdam.rst.ingest.contracts.source import SourceArtifact, SourceForm
from rdam.rst.ingest.identity import semantic_sha256
from rdam.rst.ingest.capabilities import describe_capabilities
from rdam.rst.ingest.cache import ProductionIngestCache, cache_entry_identity
from rdam.rst.ingest.policy import DEFAULT_PLANNING_POLICY, DEFAULT_PREPARATION_POLICY
from rdam.rst.ingest.prepare import (
    PreparationValidationError,
    SourceClassificationError,
    prepare_source,
)
from rdam.rst.ingest.subdivision import AnalysisPlanningError


DEFAULT_ANALYSIS_POLICY = AnalysisPolicy(
    output_formalism=OutputFormalism.RST_TREE,
    evidence_detail=EvidenceDetailPolicy.DECISION_COMPLETE,
    marker_refinement=MarkerRefinementMode.EVIDENCE_PRESERVING,
    validation=ValidationPolicy(
        policy_version=SemanticVersion(root="2.0.0"),
        required_checks=(
            "source_substrate_identity",
            "primary_tree",
            "erst_formal_rules",
            "analysis_anchors",
            "decision_evidence",
            "component_identity",
            "semantic_identity",
        ),
        advisory_checks=(),
    ),
    relation_interpretation=RelationInterpretationPolicy(
        relation_scheme="provider_native",
        ontology_mapping="disabled",
        policy_version=SemanticVersion(root="2.0.0"),
    ),
    lossy_input=LossyInputPolicy.FORBID,
    policy_version=SemanticVersion(root="2.0.0"),
)


@runtime_checkable
class AnalysisParser(Protocol):
    """Complete parser boundary consumed by production ingest."""

    @property
    def analysis_capacity(self) -> object: ...

    @property
    def model_release_identity(self) -> object | None: ...

    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult: ...


@runtime_checkable
class ErstCompletionParser(Protocol):
    """Optional extension required for document-global subdivided eRST completion."""

    def complete_erst_document(
        self,
        document: RstDocument,
        primary_result: ParserAnalysisResult,
        *,
        analysis_policy: AnalysisPolicy,
    ) -> ParserAnalysisResult: ...


@runtime_checkable
class AnalysisIdentityProvider(Protocol):
    """Model-free exact component identity required for pre-inference cache lookup."""

    def describe_analysis_identity(
        self,
        *,
        analysis_policy: AnalysisPolicy,
        segmentation_source: str,
    ) -> CompositeAnalysisIdentity: ...


class ProductionIngestor:
    """One provider-owned authority for preparation and evidence-complete analysis."""

    def __init__(self, *, parser: AnalysisParser | None = None) -> None:
        self.parser = parser

    def capabilities(self) -> ProductionCapabilities:
        return describe_capabilities(self.parser)

    def prepare(
        self,
        source: SourceArtifact,
        *,
        policy: PreparationPolicy | None = None,
        planning_policy: PlanningPolicy | None = None,
        parser_capacity: ParserCapacity | None = None,
    ) -> PreparationOutcome:
        acquired = AcquisitionCompletedEvidence(source=source.summary())
        try:
            return prepare_source(
                source,
                policy=policy or DEFAULT_PREPARATION_POLICY,
                planning_policy=planning_policy or DEFAULT_PLANNING_POLICY,
                parser_capacity=parser_capacity,
            )
        except ProductionIngestError:
            raise
        except PreparationValidationError as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.VALIDATION,
                category=FailureCategory.VALIDATION_FAILURE,
                code="preparation_validation_failed",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="assembled_preparation_failed_required_validation",
                completed=PreparationCompletedEvidence(preparation=exc.outcome),
                cause=_safe_cause(_root_cause(exc), FailureCategory.VALIDATION_FAILURE),
            )
            raise ProductionIngestError(failure) from exc
        except SourceClassificationError as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.CLASSIFICATION,
                category=FailureCategory.MALFORMED_INPUT,
                code="source_classification_failed",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="source_could_not_be_classified_under_its_declared_contract",
                completed=acquired,
                cause=_safe_cause(_root_cause(exc), FailureCategory.MALFORMED_INPUT),
            )
            raise ProductionIngestError(failure) from exc
        except AnalysisPlanningError as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.PLANNING,
                category=FailureCategory.UNSUPPORTED_INPUT,
                code="analysis_planning_failed",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="source_cannot_be_planned_with_declared_capacity",
                completed=acquired,
                cause=_safe_cause(exc, FailureCategory.UNSUPPORTED_INPUT),
            )
            raise ProductionIngestError(failure) from exc
        except ModuleNotFoundError as exc:
            missing_root = (exc.name or "").split(".")[0]
            if missing_root not in _ADAPTER_IMPORT_ROOTS.get(source.source_form, frozenset()):
                # The missing module is not this source form's optional adapter,
                # so "requires an uninstalled distribution" would be a false
                # claim; classify honestly as an internal failure instead.
                failure = ProductionFailure(
                    failed_stage=LifecycleStage.CLASSIFICATION,
                    category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                    code="source_classification_internal_failure",
                    retryability=Retryability.UNKNOWN,
                    message_template="source_classification_failed_before_a_complete_outcome",
                    completed=acquired,
                    cause=_safe_cause(exc, FailureCategory.INTERNAL_PROCESSING_FAILURE),
                )
                raise ProductionIngestError(failure) from exc
            distribution, extra = _source_requirement(source)
            failure = ProductionFailure(
                failed_stage=LifecycleStage.CLASSIFICATION,
                category=FailureCategory.PROVIDER_UNAVAILABLE,
                code="source_adapter_distribution_unavailable",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="source_form_requires_an_uninstalled_distribution",
                diagnostic_context=(
                    MissingDistributionContext(
                        distributions=(distribution,),
                        required_extra=extra,
                    ),
                ),
                completed=acquired,
                cause=_safe_cause(exc, FailureCategory.PROVIDER_UNAVAILABLE),
            )
            raise ProductionIngestError(failure) from exc
        except UnicodeError as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.CLASSIFICATION,
                category=FailureCategory.MALFORMED_INPUT,
                code="source_classification_failed",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="source_could_not_be_classified_under_its_declared_contract",
                completed=acquired,
                cause=_safe_cause(exc, FailureCategory.MALFORMED_INPUT),
            )
            raise ProductionIngestError(failure) from exc
        except ValueError as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.PREPARATION,
                category=FailureCategory.VALIDATION_FAILURE,
                code="source_preparation_failed",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="source_could_not_be_prepared_under_the_resolved_policy",
                completed=acquired,
                cause=_safe_cause(exc, FailureCategory.VALIDATION_FAILURE),
            )
            raise ProductionIngestError(failure) from exc
        except Exception as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.PREPARATION,
                category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                code="source_preparation_internal_failure",
                retryability=Retryability.UNKNOWN,
                message_template="source_preparation_failed_before_a_complete_outcome",
                completed=acquired,
                cause=_safe_cause(exc, FailureCategory.INTERNAL_PROCESSING_FAILURE),
            )
            raise ProductionIngestError(failure) from exc

    def analyse(
        self,
        source: SourceArtifact,
        *,
        policy: PreparationPolicy | None = None,
        planning_policy: PlanningPolicy | None = None,
        analysis_policy: AnalysisPolicy | None = None,
        cache_directory: Path | None = None,
        diagnostic_policy: DiagnosticPolicy | None = None,
    ) -> ProductionAnalysisOutcome:
        """Analyse atomically or raise one typed completed-stage failure."""

        started = perf_counter()
        parser = self.parser
        try:
            capacity = _parser_capacity(parser.analysis_capacity) if parser is not None else None
        except Exception as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.PLANNING,
                category=FailureCategory.PROVIDER_UNAVAILABLE,
                code="parser_capacity_unavailable",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="parser_did_not_expose_a_valid_declarative_capacity",
                completed=AcquisitionCompletedEvidence(source=source.summary()),
                cause=_safe_cause(exc, FailureCategory.PROVIDER_UNAVAILABLE),
            )
            raise ProductionIngestError(failure) from exc
        preparation = self.prepare(
            source,
            policy=policy,
            planning_policy=planning_policy,
            parser_capacity=capacity,
        )
        resolved_policy = analysis_policy or DEFAULT_ANALYSIS_POLICY
        if not preparation.semantic.prepared_document.text:
            empty = _empty_outcome(
                source,
                preparation,
                resolved_policy,
                started=started,
            )
            return _resolve_empty_cache(empty, cache_directory, started=started)
        if parser is None:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.INFERENCE,
                category=FailureCategory.PROVIDER_UNAVAILABLE,
                code="parser_not_configured",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="non_empty_primary_discourse_requires_parser",
                completed=PreparationCompletedEvidence(preparation=preparation),
            )
            raise ProductionIngestError(failure)
        prepared_document = preparation.semantic.prepared_document
        plan = preparation.semantic.analysis_plan
        request: AnalysisRequest | None = None
        cache: ProductionIngestCache | None = None
        declared_composite: CompositeAnalysisIdentity | None = None
        if cache_directory is not None:
            if not isinstance(parser, AnalysisIdentityProvider):
                failure = ProductionFailure(
                    failed_stage=LifecycleStage.CACHE_RETRIEVAL,
                    category=FailureCategory.PROVIDER_UNAVAILABLE,
                    code="exact_cache_identity_unavailable",
                    retryability=Retryability.NOT_RETRYABLE,
                    message_template="parser_cannot_describe_runtime_identity_before_inference",
                    completed=PreparationCompletedEvidence(preparation=preparation),
                )
                raise ProductionIngestError(failure)
            segmentation_source = (
                "presegmented"
                if source.source_form is SourceForm.EDUS
                else "model"
                if getattr(parser, "segmenter", None) is not None
                else "deterministic_sentence_boundary_v1"
            )
            declared_composite = parser.describe_analysis_identity(
                analysis_policy=resolved_policy,
                segmentation_source=segmentation_source,
            )
            if not declared_composite.durable_cache_eligible:
                failure = ProductionFailure(
                    failed_stage=LifecycleStage.CACHE_RETRIEVAL,
                    category=FailureCategory.PROVIDER_UNAVAILABLE,
                    code="analysis_not_cache_eligible",
                    retryability=Retryability.NOT_RETRYABLE,
                    message_template="participating_components_are_not_immutable",
                    completed=PreparationCompletedEvidence(preparation=preparation),
                )
                raise ProductionIngestError(failure)
            request = _analysis_request(
                source,
                preparation,
                resolved_policy,
                capacity,
                declared_composite,
            )
            request_identity = _required_identity(request.semantic_digest, "analysis request")
            cache = ProductionIngestCache(cache_directory)
            cached = cache.load(request_identity)
            if cached is not None:
                return _with_cache_execution(cached, CacheStatus.HIT, started=started)
        if plan.status is AnalysisPlanStatus.SUBDIVIDED:
            unit_policy = resolved_policy
            if resolved_policy.output_formalism is OutputFormalism.ERST_GRAPH:
                unit_policy = AnalysisPolicy.model_validate(
                    {
                        **resolved_policy.model_dump(exclude={"semantic_digest"}),
                        "output_formalism": OutputFormalism.RST_TREE,
                    }
                )
            unit_ranges = tuple(
                (
                    prepared_document.segments[unit.first_segment_order].prepared_range.start,
                    prepared_document.segments[unit.last_segment_order].prepared_range.end,
                )
                for unit in plan.units
            )
            unit_results = tuple(
                _analyse_parser_unit(
                    parser,
                    _rst_document(
                        prepared_document,
                        source.source_form,
                        document_id=f"{source.source_id}:{plan.units[index].unit_id}",
                        start=start,
                        end=end,
                    ),
                    unit_policy,
                    preparation,
                )
                for index, (start, end) in enumerate(unit_ranges)
            )
            from rdam.rst.ingest.recombination import recombine_parser_results

            try:
                parser_result = recombine_parser_results(
                    document_id=source.source_id,
                    text=prepared_document.text,
                    plan=plan,
                    unit_ranges=unit_ranges,
                    results=unit_results,
                )
            except ProductionIngestError:
                raise
            except Exception as exc:
                failure = ProductionFailure(
                    failed_stage=LifecycleStage.ASSEMBLY,
                    category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                    code="multi_unit_recombination_failed",
                    retryability=Retryability.UNKNOWN,
                    message_template="complete_unit_results_could_not_be_recombined",
                    completed=_inference_completed(preparation, unit_results),
                    cause=_safe_cause(exc, FailureCategory.INTERNAL_PROCESSING_FAILURE),
                )
                raise ProductionIngestError(failure) from exc
            if resolved_policy.output_formalism is OutputFormalism.ERST_GRAPH:
                if not isinstance(parser, ErstCompletionParser):
                    failure = ProductionFailure(
                        failed_stage=LifecycleStage.INFERENCE,
                        category=FailureCategory.PROVIDER_UNAVAILABLE,
                        code="erst_completion_unsupported",
                        retryability=Retryability.NOT_RETRYABLE,
                        message_template="subdivided_erst_requires_document_global_completion_support",
                        completed=PreparationCompletedEvidence(preparation=preparation),
                    )
                    raise ProductionIngestError(failure)
                try:
                    parser_result = parser.complete_erst_document(
                        _rst_document(
                            prepared_document,
                            source.source_form,
                            document_id=source.source_id,
                        ),
                        parser_result,
                        analysis_policy=resolved_policy,
                    )
                except ProductionIngestError:
                    raise
                except Exception as exc:
                    failure = ProductionFailure(
                        failed_stage=LifecycleStage.INFERENCE,
                        category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                        code="document_global_erst_completion_failed",
                        retryability=Retryability.UNKNOWN,
                        message_template="erst_completion_failed_after_primary_recombination",
                        completed=PreparationCompletedEvidence(preparation=preparation),
                        cause=_safe_cause(exc, FailureCategory.INTERNAL_PROCESSING_FAILURE),
                    )
                    raise ProductionIngestError(failure) from exc
        else:
            document = _rst_document(
                prepared_document,
                source.source_form,
                document_id=source.source_id,
            )
            parser_result = _analyse_parser_unit(
                parser,
                document,
                resolved_policy,
                preparation,
            )
        from rdam.rst.ingest.enrichment import enrich_parser_evidence
        from rdam.rst.ingest.validation import build_analysis_validation_receipt

        try:
            analysed_document, anchors = enrich_parser_evidence(preparation, parser_result)
        except Exception as exc:
            # Inference is the last pipeline stage proven complete here; the
            # parser-internal receipt is unit-level evidence, not the pipeline
            # validation stage, so claiming validation-completed would be false.
            failure = ProductionFailure(
                failed_stage=LifecycleStage.ASSEMBLY,
                category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                code="source_evidence_enrichment_failed",
                retryability=Retryability.UNKNOWN,
                message_template="parser_coordinates_could_not_be_mapped_to_source_evidence",
                completed=_inference_completed(preparation, (parser_result,)),
                cause=_safe_cause(exc, FailureCategory.INTERNAL_PROCESSING_FAILURE),
            )
            raise ProductionIngestError(failure) from exc
        try:
            validation = build_analysis_validation_receipt(
                parser_result.semantic.analysis,
                analysed_document,
                parser_result.semantic.primary_inference,
                parser_result.semantic.erst_completion,
                anchors,
                policy=parser_result.semantic.policy,
                composite=parser_result.semantic.composite_identity,
                recombination=parser_result.semantic.recombination,
            )
        except (TypeError, ValueError) as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.VALIDATION,
                category=FailureCategory.VALIDATION_FAILURE,
                code="analysis_validation_failed",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="analysis_evidence_failed_required_validation",
                completed=_inference_completed(preparation, (parser_result,)),
                cause=_safe_cause(exc, FailureCategory.VALIDATION_FAILURE),
            )
            raise ProductionIngestError(failure) from exc
        except Exception as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.VALIDATION,
                category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                code="analysis_validation_internal_failure",
                retryability=Retryability.UNKNOWN,
                message_template="analysis_validation_failed_before_a_verdict",
                completed=_inference_completed(preparation, (parser_result,)),
                cause=_safe_cause(exc, FailureCategory.INTERNAL_PROCESSING_FAILURE),
            )
            raise ProductionIngestError(failure) from exc
        composite_identity = parser_result.semantic.composite_identity
        if declared_composite is not None and declared_composite != composite_identity:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.VALIDATION,
                category=FailureCategory.IDENTITY_CONTRADICTION,
                code="runtime_identity_contradiction",
                retryability=Retryability.NOT_RETRYABLE,
                message_template="declared_and_participating_component_identities_differ",
                completed=_inference_completed(preparation, (parser_result,)),
            )
            raise ProductionIngestError(failure)
        request = request or _analysis_request(
            source,
            preparation,
            parser_result.semantic.policy,
            capacity,
            composite_identity,
        )
        semantic = AnalysisSemanticEvidence(
            preparation=preparation,
            request=request,
            policy=parser_result.semantic.policy,
            analysed_document=analysed_document,
            composite_identity=composite_identity,
            parser_result=parser_result,
            status=AnalysisStatus.ANALYSED,
            analysis=parser_result.semantic.analysis,
            primary_inference=parser_result.semantic.primary_inference,
            erst_completion=parser_result.semantic.erst_completion,
            anchors=anchors,
            recombination=parser_result.semantic.recombination,
            validation=validation,
            cache_request_identity=request.semantic_digest,
        )
        outcome = AnalysedOutcome(
            semantic=semantic,
            execution=AnalysisExecutionEvidence(
                execution_id=str(uuid4()),
                duration_ms=(perf_counter() - started) * 1_000.0,
                device=parser_result.execution.device,
                cache_status=CacheStatus.BYPASS,
                unit_executions=parser_result.execution.unit_executions,
                software_version=resolve_package_version(),
                source_revision=resolve_source_revision(),
            ),
        )
        if cache is None:
            return outcome
        request_identity = _required_identity(request.semantic_digest, "analysis request")
        persisted = _with_cache_execution(outcome, CacheStatus.WRITTEN, started=started)
        cache.store(request_identity, persisted)
        return persisted


def _empty_outcome(
    source: SourceArtifact,
    preparation: PreparationOutcome,
    policy: AnalysisPolicy,
    *,
    started: float,
) -> EmptyPrimaryAnalysisOutcome:
    component = NotUsedComponentIdentity(
        component="all_analysis_components",
        reason="empty_primary_discourse",
    )
    composite = CompositeAnalysisIdentity(
        primary_parser=component,
        segmenter=component.model_copy(update={"component": "segmenter"}),
        marker_refiner=component.model_copy(update={"component": "marker_refiner"}),
        erst_detector=component.model_copy(update={"component": "erst_detector"}),
        erst_scorer=component.model_copy(update={"component": "erst_scorer"}),
        erst_decoder=component.model_copy(update={"component": "erst_decoder"}),
        calibration=component.model_copy(update={"component": "calibration"}),
        relation_inventory=component.model_copy(update={"component": "relation_inventory"}),
        ontology_mapping=component.model_copy(update={"component": "ontology_mapping"}),
    )
    plan_identity = preparation.semantic.analysis_plan.semantic_digest
    preparation_identity = preparation.semantic_digest
    if plan_identity is None or preparation_identity is None:
        raise ValueError("validated preparation identities are absent")
    request = AnalysisRequest(
        source_identity=Sha256Identity(hex_digest=source.source_id),
        preparation_identity=preparation_identity,
        analysis_policy=policy,
        analysis_plan_identity=plan_identity,
        parser_capacity_identity=None,
        composite_analysis_identity=composite,
        pipeline_version=SemanticVersion(root="2.0.0"),
        production_contract_version=SemanticVersion(root="2.0.0"),
    )
    semantic = AnalysisSemanticEvidence(
        preparation=preparation,
        request=request,
        policy=policy,
        analysed_document=None,
        composite_identity=composite,
        parser_result=None,
        status=AnalysisStatus.EMPTY_PRIMARY_DISCOURSE,
        analysis=None,
        primary_inference=None,
        erst_completion=None,
        anchors=(),
        recombination=None,
        validation=None,
        cache_request_identity=_required_identity(request.semantic_digest, "analysis request"),
    )
    return EmptyPrimaryAnalysisOutcome(
        semantic=semantic,
        execution=AnalysisExecutionEvidence(
            execution_id=str(uuid4()),
            duration_ms=(perf_counter() - started) * 1_000.0,
            device="not_used",
            cache_status=CacheStatus.BYPASS,
            unit_executions=(),
            software_version=resolve_package_version(),
            source_revision=resolve_source_revision(),
        ),
    )


def _analysis_request(
    source: SourceArtifact,
    preparation: PreparationOutcome,
    policy: AnalysisPolicy,
    capacity: ParserCapacity | None,
    composite: CompositeAnalysisIdentity,
) -> AnalysisRequest:
    preparation_identity = _required_identity(preparation.semantic_digest, "preparation")
    plan_identity = _required_identity(
        preparation.semantic.analysis_plan.semantic_digest,
        "analysis plan",
    )
    return AnalysisRequest(
        source_identity=Sha256Identity(hex_digest=source.source_id),
        preparation_identity=preparation_identity,
        analysis_policy=policy,
        analysis_plan_identity=plan_identity,
        parser_capacity_identity=(
            Sha256Identity(hex_digest=semantic_sha256(capacity))
            if capacity is not None
            else None
        ),
        composite_analysis_identity=composite,
        pipeline_version=SemanticVersion(root="2.0.0"),
        production_contract_version=SemanticVersion(root="2.0.0"),
    )


def _rst_document(
    prepared: PreparedRstDocument,
    source_form: SourceForm,
    *,
    document_id: str,
    start: int = 0,
    end: int | None = None,
) -> RstDocument:
    resolved_end = len(prepared.text) if end is None else end
    text = prepared.text[start:resolved_end]
    if source_form is not SourceForm.EDUS:
        return RstDocument.from_text(text, document_id=document_id)
    edus = tuple(
        Edu(
            edu_id=index,
            text=segment.text,
            start=segment.prepared_range.start - start,
            end=segment.prepared_range.end - start,
        )
        for index, segment in enumerate(
            (
                item
                for item in prepared.segments
                if item.kind is SegmentKind.SOURCE
                and start <= item.prepared_range.start
                and item.prepared_range.end <= resolved_end
            ),
            start=1,
        )
    )
    if not edus:
        raise ValueError("presegmented source unit contains no complete EDUs")
    return RstDocument(
        document_id=document_id,
        text=text,
        edus=edus,
    )


def _analyse_parser_unit(
    parser: AnalysisParser,
    document: RstDocument,
    policy: AnalysisPolicy,
    preparation: PreparationOutcome,
) -> ParserAnalysisResult:
    from rdam.rst.transformer_parser.predictor import ParserInputLimitError

    try:
        return parser.analyse_document(document, analysis_policy=policy)
    except ProductionIngestError:
        raise
    except Exception as exc:
        if isinstance(exc, ParserInputLimitError):
            category = FailureCategory.UNSUPPORTED_INPUT
            code = "parser_capacity_exceeded"
            retryability = Retryability.NOT_RETRYABLE
            message = "exact_inference_substrate_exceeds_declared_parser_capacity"
        elif isinstance(exc, ValueError):
            category = FailureCategory.VALIDATION_FAILURE
            code = "parser_evidence_invalid"
            retryability = Retryability.NOT_RETRYABLE
            message = "parser_did_not_return_a_valid_canonical_result"
        else:
            category = FailureCategory.INTERNAL_PROCESSING_FAILURE
            code = "parser_execution_failed"
            retryability = Retryability.UNKNOWN
            message = "parser_failed_before_a_complete_result_was_available"
        failure = ProductionFailure(
            failed_stage=LifecycleStage.INFERENCE,
            category=category,
            code=code,
            retryability=retryability,
            message_template=message,
            completed=PreparationCompletedEvidence(preparation=preparation),
            cause=_safe_cause(exc, category),
        )
        raise ProductionIngestError(failure) from exc


def _inference_completed(
    preparation: PreparationOutcome,
    results: tuple[ParserAnalysisResult, ...],
) -> InferenceCompletedEvidence:
    if not results:
        raise ValueError("inference completed evidence requires at least one complete result")
    unit_identities = tuple(
        _required_identity(result.semantic_digest, "parser result") for result in results
    )
    final = results[-1]
    semantic = final.semantic
    return InferenceCompletedEvidence(
        preparation=preparation,
        inference=InferenceEvidence(
            request_identity=Sha256Identity(
                hex_digest=semantic_sha256(
                    {
                        "preparation": preparation.semantic_digest,
                        "policy": semantic.policy,
                        "composite": semantic.composite_identity,
                    }
                )
            ),
            analysed_document_identity=_required_identity(
                semantic.analysed_document.semantic_digest,
                "analysed document",
            ),
            composite_identity=_required_identity(
                semantic.composite_identity.semantic_digest,
                "composite analysis",
            ),
            unit_identities=unit_identities,
            primary_evidence_identity=Sha256Identity(
                hex_digest=semantic_sha256(semantic.primary_inference)
            ),
            erst_evidence_identity=(
                _required_identity(semantic.erst_completion.semantic_digest, "eRST evidence")
                if semantic.erst_completion is not None
                else None
            ),
            output_node_count=sum(len(result.semantic.analysis.nodes) for result in results),
            output_primary_edge_count=sum(
                len(result.semantic.analysis.primary_edges) for result in results
            ),
            output_secondary_edge_count=sum(
                len(result.semantic.analysis.secondary_edges) for result in results
            ),
            completed_unit_count=len(results),
            expected_unit_count=len(results),
        ),
    )


def _safe_cause(exc: Exception, category: FailureCategory) -> SafeCause:
    return SafeCause(
        category=category,
        exception_type=type(exc).__qualname__,
        message_template="underlying_operation_failed",
    )


def _root_cause(exc: Exception) -> Exception:
    cause = exc.__cause__
    return cause if isinstance(cause, Exception) else exc


_ADAPTER_IMPORT_ROOTS: Final = {
    SourceForm.MARKDOWN: frozenset({"markdown_it", "mdit_py_plugins"}),
    SourceForm.DOCLING_JSON: frozenset({"docling_core"}),
    SourceForm.DOCLANG_XML: frozenset({"doclang"}),
    SourceForm.DOCLANG_ARCHIVE: frozenset({"doclang"}),
}


def _source_requirement(source: SourceArtifact) -> tuple[str, str | None]:
    requirement = {
        SourceForm.MARKDOWN: "markdown-it-py",
        SourceForm.DOCLING_JSON: "docling-core",
        SourceForm.DOCLANG_XML: "doclang",
        SourceForm.DOCLANG_ARCHIVE: "doclang",
    }.get(source.source_form)
    return (requirement or "isanlp-rst", "formats" if requirement is not None else None)


def _resolve_empty_cache(
    outcome: EmptyPrimaryAnalysisOutcome,
    cache_directory: Path | None,
    *,
    started: float,
) -> EmptyPrimaryAnalysisOutcome:
    if cache_directory is None:
        return outcome
    request_identity = _required_identity(
        outcome.semantic.request.semantic_digest,
        "analysis request",
    )
    cache = ProductionIngestCache(cache_directory)
    cached = cache.load(request_identity)
    if cached is not None:
        resolved = _with_cache_execution(cached, CacheStatus.HIT, started=started)
        if not isinstance(resolved, EmptyPrimaryAnalysisOutcome):
            raise ValueError("empty-primary request resolved to an analysed cache outcome")
        return resolved
    persisted = _with_cache_execution(outcome, CacheStatus.WRITTEN, started=started)
    if not isinstance(persisted, EmptyPrimaryAnalysisOutcome):
        raise TypeError("empty-primary cache binding changed outcome kind")
    cache.store(request_identity, persisted)
    return persisted


def _with_cache_execution(
    outcome: ProductionAnalysisOutcome,
    status: CacheStatus,
    *,
    started: float,
) -> ProductionAnalysisOutcome:
    request_identity = _required_identity(
        outcome.semantic.request.semantic_digest,
        "analysis request",
    )
    result_identity = _required_identity(outcome.semantic_digest, "analysis outcome")
    execution = outcome.execution.model_copy(
        update={
            "execution_id": str(uuid4()),
            "duration_ms": (perf_counter() - started) * 1_000.0,
            "cache_status": status,
            "cache_entry_identity": cache_entry_identity(request_identity, result_identity),
        }
    )
    return outcome.model_copy(update={"execution": execution})


def _required_identity(
    identity: Sha256Identity | None,
    label: str,
) -> Sha256Identity:
    if identity is None:
        raise ValueError(f"{label} has no semantic identity")
    return identity


def _parser_capacity(value: object) -> ParserCapacity:
    if isinstance(value, ParserCapacity):
        return value
    unit = getattr(value, "unit", None)
    maximum = getattr(value, "maximum", None)
    source = getattr(value, "source", None)
    if not isinstance(unit, str) or not isinstance(maximum, int) or not isinstance(source, str):
        raise TypeError("parser analysis_capacity does not satisfy the public capacity contract")
    return ParserCapacity(
        unit=CapacityUnit(unit),
        maximum=maximum,
        estimation_algorithm="provider_declared",
        estimation_version=SemanticVersion(root="2.0.0"),
        source=source,
    )


__all__ = [
    "AnalysisIdentityProvider",
    "AnalysisParser",
    "DEFAULT_ANALYSIS_POLICY",
    "ErstCompletionParser",
    "ProductionIngestor",
]
