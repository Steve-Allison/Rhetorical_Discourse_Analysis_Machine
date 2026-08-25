"""Canonical production source-ingest orchestration."""

from datetime import UTC, datetime
from pathlib import Path
import resource
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from isanlp_rst.contracts import RstAnalysis, RstDocument, TextSpan
from isanlp_rst.ingest.cache import ProductionIngestCache
from isanlp_rst.ingest.contracts import (
    AnalysisAnchor,
    AnalysisStatus,
    AnalysisUnit,
    CacheStatus,
    ContentInventoryItem,
    Disposition,
    ExecutionReceipt,
    FailureStage,
    PreparationPolicy,
    PreparationReceipt,
    PreparedRange,
    PreparedRstDocument,
    ProductionAnalysisResult,
    ProductionIngestError,
    INGEST_PIPELINE_VERSION,
    SegmentKind,
    SourceArtifact,
    SourceContractIdentity,
    INGEST_SCHEMA_NAME,
    INGEST_SCHEMA_VERSION,
)
from isanlp_rst.ingest.identity import semantic_sha256
from isanlp_rst.ingest.policy import AUTHORED_PROSE_V1, apply_policy
from isanlp_rst.ingest.prepare import prepare_source
from isanlp_rst.ingest.subdivision import build_subdivision_plan
from isanlp_rst.model_loading import ModelReleaseIdentity, ParserCapacity


class AnalysisParser(Protocol):
    """Minimum parser surface required by production ingest."""

    @property
    def analysis_capacity(self) -> ParserCapacity: ...

    @property
    def model_release_identity(self) -> ModelReleaseIdentity | None: ...

    def parse_document(self, document: RstDocument, output: str = "rst_tree") -> RstAnalysis: ...


class ProductionIngestor:
    """One in-process authority for production source preparation and analysis."""

    def __init__(self, *, parser: AnalysisParser | None) -> None:
        self.parser = parser

    def prepare(
        self,
        artifact: SourceArtifact,
        *,
        policy: PreparationPolicy = AUTHORED_PROSE_V1,
    ) -> PreparedRstDocument:
        prepared, _inventory, _dispositions, _contract = _prepare_with_diagnostics(artifact, policy)
        return prepared

    def analyse(
        self,
        artifact: SourceArtifact,
        *,
        policy: PreparationPolicy = AUTHORED_PROSE_V1,
        cache_dir: Path | None = None,
    ) -> ProductionAnalysisResult:
        started_at = datetime.now(UTC)
        run_id = str(uuid4())
        timings: list[tuple[str, float]] = []

        stage_started = perf_counter()
        prepared, inventory, dispositions, contract = _prepare_with_diagnostics(artifact, policy)
        _policy_dispositions, duplicates = apply_policy(inventory, policy)
        timings.append(("prepare", _elapsed_ms(stage_started)))

        parser = self.parser
        capacity = parser.analysis_capacity if parser is not None else ParserCapacity(
            unit="edu_count",
            maximum=512,
            source="isanlp_rst.ingest/empty-only",
        )
        plan = build_subdivision_plan(prepared, capacity)
        model_identity = parser.model_release_identity if parser is not None else None
        model_digest = (
            model_identity.semantic_digest
            if model_identity is not None
            else semantic_sha256(
                {
                    "mutable_parser": (
                        f"{type(parser).__module__}.{type(parser).__qualname__}" if parser is not None else "none"
                    ),
                    "capacity": capacity,
                }
            )
        )
        cache_fingerprint = (
            semantic_sha256(
                {
                    "source": artifact.source_id,
                    "source_contract": contract.semantic_digest,
                    "policy": policy.policy_digest,
                    "prepared": prepared.semantic_digest,
                    "subdivision": plan.semantic_digest,
                    "model": model_digest,
                    "pipeline": INGEST_PIPELINE_VERSION,
                    "result_contract": f"{INGEST_SCHEMA_NAME}/{INGEST_SCHEMA_VERSION}",
                }
            )
            if model_identity is not None
            else None
        )
        warnings = () if model_identity is not None else ("durable_cache_disabled_without_released_model_identity",)

        if cache_fingerprint is not None and cache_dir is not None:
            cached = ProductionIngestCache(cache_dir).load(cache_fingerprint)
            if cached is not None:
                return cached.model_copy(
                    update={
                        "execution_receipt": _execution_receipt(
                            run_id,
                            started_at,
                            CacheStatus.HIT,
                            timings,
                            warnings,
                        )
                    }
                )

        if not prepared.text:
            analysis = None
            analysis_status = AnalysisStatus.EMPTY_PRIMARY_DISCOURSE
        else:
            if parser is None:
                raise ProductionIngestError(
                    stage=FailureStage.ANALYSE,
                    code="parser_required",
                    artifact_id=artifact.source_id,
                    expectation="a configured parser for non-empty primary discourse",
                    detail="ProductionIngestor was constructed without a parser",
                )
            stage_started = perf_counter()
            if len(plan.units) <= 1:
                analysis = _parse_document(parser, prepared.document, artifact.source_id)
            else:
                parse_hierarchical = getattr(parser, "parse_hierarchical", None)
                if parse_hierarchical is None:
                    raise ProductionIngestError(
                        stage=FailureStage.ANALYSE,
                        code="hierarchical_parser_required",
                        artifact_id=artifact.source_id,
                        expectation="a parser implementing parse_hierarchical for subdivided input",
                        detail=f"subdivision produced {len(plan.units)} analysis units",
                    )
                boundaries = tuple(
                    TextSpan(
                        start=unit.output_range.start,
                        end=unit.output_range.end,
                        text=prepared.text[unit.output_range.start : unit.output_range.end],
                    )
                    for unit in plan.units
                )
                try:
                    analysis = parse_hierarchical(
                        prepared.document,
                        custom_boundaries=boundaries,
                        output="rst_tree",
                    )
                except (OSError, RuntimeError, TypeError, ValueError) as exc:
                    raise ProductionIngestError(
                        stage=FailureStage.ANALYSE,
                        code="hierarchical_analysis_failed",
                        artifact_id=artifact.source_id,
                        expectation="one complete coherent RST analysis from every subdivision",
                        detail=f"hierarchical parser failed ({type(exc).__name__})",
                        diagnostic_counts={"analysis_units": len(plan.units)},
                    ) from exc
            timings.append(("analyse", _elapsed_ms(stage_started)))
            analysis_status = AnalysisStatus.ANALYSED

        anchors = _analysis_anchors(analysis, prepared, plan.units)
        target_count = 0 if analysis is None else len(analysis.nodes) + len(analysis.primary_edges) + len(analysis.secondary_edges)
        anchor_coverage = 1.0 if target_count == 0 else len(anchors) / target_count
        primary_count = len(prepared.primary_item_ids)
        mapped_primary = sum(
            any(segment.source_item_id == item_id for segment in prepared.segments)
            for item_id in prepared.primary_item_ids
        )
        receipt = PreparationReceipt(
            source_id=artifact.source_id,
            source_contract_digest=contract.semantic_digest,
            policy_digest=policy.policy_digest,
            preparation_digest=prepared.semantic_digest,
            subdivision_digest=plan.semantic_digest,
            model_digest=model_digest,
            pipeline_version=INGEST_PIPELINE_VERSION,
            inventory_count=len(inventory),
            disposition_count=len(dispositions),
            inventory_coverage=1.0,
            primary_source_coverage=1.0 if primary_count == 0 else mapped_primary / primary_count,
            prepared_text_coverage=1.0,
            analysis_anchor_coverage=anchor_coverage,
            dispositions=dispositions,
            duplicate_findings=duplicates,
            warnings=warnings,
            cache_fingerprint=cache_fingerprint,
        )
        cache_status = CacheStatus.MISS if cache_fingerprint is not None else CacheStatus.DISABLED
        result = ProductionAnalysisResult(
            source=artifact.summary(),
            analysis_status=analysis_status,
            prepared_document=prepared,
            analysis=analysis,
            analysis_anchors=anchors,
            preparation_receipt=receipt,
            execution_receipt=_execution_receipt(run_id, started_at, cache_status, timings, warnings),
        )
        if cache_fingerprint is not None and cache_dir is not None:
            ProductionIngestCache(cache_dir).store(cache_fingerprint, result)
            result = result.model_copy(
                update={
                    "execution_receipt": _execution_receipt(
                        run_id,
                        started_at,
                        CacheStatus.WRITTEN,
                        timings,
                        warnings,
                    )
                }
            )
        return result


def analyse_source(
    artifact: SourceArtifact,
    *,
    parser: AnalysisParser | None,
    policy: PreparationPolicy = AUTHORED_PROSE_V1,
    cache_dir: Path | None = None,
) -> ProductionAnalysisResult:
    """Analyse one materialized source through the canonical production path."""

    return ProductionIngestor(parser=parser).analyse(
        artifact,
        policy=policy,
        cache_dir=cache_dir,
    )


def _prepare_with_diagnostics(
    artifact: SourceArtifact,
    policy: PreparationPolicy,
) -> tuple[
    PreparedRstDocument,
    tuple[ContentInventoryItem, ...],
    tuple[Disposition, ...],
    SourceContractIdentity,
]:
    """Run canonical preparation and convert unsafe partial failures to evidence."""

    try:
        return prepare_source(artifact, policy=policy)
    except ProductionIngestError:
        raise
    except (OSError, SyntaxError, TypeError, UnicodeError, ValueError) as exc:
        raise ProductionIngestError(
            stage=FailureStage.VALIDATE,
            code=f"invalid_{artifact.source_form.value}",
            artifact_id=artifact.source_id,
            expectation="a complete source valid under the current accepted contract",
            detail=f"source validation or inventory failed ({type(exc).__name__})",
        ) from exc


def _parse_document(
    parser: AnalysisParser,
    document: RstDocument,
    artifact_id: str,
) -> RstAnalysis:
    try:
        return parser.parse_document(document, output="rst_tree")
    except ProductionIngestError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ProductionIngestError(
            stage=FailureStage.ANALYSE,
            code="analysis_failed",
            artifact_id=artifact_id,
            expectation="a complete RST analysis over the prepared primary discourse",
            detail=f"parser failed ({type(exc).__name__})",
        ) from exc


def _analysis_anchors(
    analysis: RstAnalysis | None,
    prepared: PreparedRstDocument,
    units: tuple[AnalysisUnit, ...],
) -> tuple[AnalysisAnchor, ...]:
    if analysis is None:
        return ()
    anchors: list[AnalysisAnchor] = []
    node_by_id = {node.node_id: node for node in analysis.nodes}
    for node in analysis.nodes:
        anchor = _anchor_for_range(f"node:{node.node_id}", "node", node.char_span, prepared, units)
        if anchor is not None:
            anchors.append(anchor)
    for edge in (*analysis.primary_edges, *analysis.secondary_edges):
        node_id = getattr(edge, "parent_id", getattr(edge, "source_id", None))
        if not isinstance(node_id, int):
            continue
        node = node_by_id.get(node_id)
        if node is None:
            continue
        anchor = _anchor_for_range(f"edge:{edge.edge_id}", "relation", node.char_span, prepared, units)
        if anchor is not None:
            anchors.append(anchor)
    return tuple(anchors)


def _anchor_for_range(
    analysis_id: str,
    analysis_kind: str,
    char_span: tuple[int, int],
    prepared: PreparedRstDocument,
    units: tuple[AnalysisUnit, ...],
) -> AnalysisAnchor | None:
    start, end = char_span
    if end <= start:
        return None
    prepared_range = PreparedRange(start=start, end=end)
    source_segments = tuple(
        segment
        for segment in prepared.segments
        if segment.kind is SegmentKind.SOURCE
        and segment.prepared_range.start < end
        and start < segment.prepared_range.end
    )
    if not source_segments:
        return None
    touched_units = sum(
        unit.output_range.start < end and start < unit.output_range.end
        for unit in units
    )
    return AnalysisAnchor(
        analysis_id=analysis_id,
        analysis_kind=analysis_kind,
        prepared_ranges=(prepared_range,),
        source_segment_ids=tuple(segment.segment_id for segment in source_segments),
        native_anchors=tuple(anchor for segment in source_segments for anchor in segment.native_anchors),
        origin="macro" if touched_units > 1 else "local",
    )


def _execution_receipt(
    run_id: str,
    started_at: datetime,
    cache_status: CacheStatus,
    timings: list[tuple[str, float]],
    warnings: tuple[str, ...],
) -> ExecutionReceipt:
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_bytes = peak_rss if peak_rss > 10_000_000 else peak_rss * 1_024
    return ExecutionReceipt(
        run_id=run_id,
        started_at=started_at,
        cache_status=cache_status,
        duration_ms=tuple(timings),
        peak_rss_bytes=peak_rss_bytes,
        warnings=warnings,
    )


def _elapsed_ms(started: float) -> float:
    return (perf_counter() - started) * 1_000.0


__all__ = ["AnalysisParser", "ProductionIngestor", "analyse_source"]
