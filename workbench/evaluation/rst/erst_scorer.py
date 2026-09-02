"""Offline paper-defined eRST and discourse-signal evaluation."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from rdam.rst.contracts.analysis import DiscourseSignal, RstAnalysis

ERST_SCORER_AUTHORITY = "https://aclanthology.org/2025.cl-1.3.pdf#page=30"
EndpointYield: TypeAlias = tuple[int, int]
UnorderedSpanKey: TypeAlias = tuple[EndpointYield, EndpointYield]
DirectedSpanKey: TypeAlias = tuple[EndpointYield, EndpointYield]


@dataclass(frozen=True, slots=True)
class SecondaryEdgeMetrics:
    """Official secondary-edge Parseval precision, recall, F1, and counts."""

    span_precision: float
    span_recall: float
    span_f1: float

    direction_precision: float
    direction_recall: float
    direction_f1: float

    relation_precision: float
    relation_recall: float
    relation_f1: float

    full_precision: float
    full_recall: float
    full_f1: float

    gold_count: int
    pred_count: int
    matched_span: int
    matched_direction: int
    matched_relation: int
    matched_full: int


@dataclass(frozen=True, slots=True)
class SignalMetrics:
    """Evaluation metrics for discourse signals and token anchoring."""

    detection_precision: float
    detection_recall: float
    detection_f1: float

    type_precision: float
    type_recall: float
    type_f1: float

    subtype_precision: float
    subtype_recall: float
    subtype_f1: float

    token_precision: float
    token_recall: float
    token_f1: float

    gold_signals_count: int
    pred_signals_count: int
    matched_detection: int
    matched_type: int
    matched_subtype: int


def _calc_prf(matched: int | float, pred_count: int | float, gold_count: int | float) -> tuple[float, float, float]:
    p = matched / pred_count if pred_count > 0 else (1.0 if gold_count == 0 else 0.0)
    r = matched / gold_count if gold_count > 0 else (1.0 if pred_count == 0 else 0.0)
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return p, r, f1


class ErstScorer:
    """Score eRST graphs using the paper's secondary-edge Parseval definition.

    Node identifiers are serialization-local and therefore never participate in official
    matching. Each secondary endpoint is represented by the one-based inclusive EDU yield
    of its primary-tree node. Span compares the unordered endpoint pair, direction compares
    the ordered pair, Relation compares unordered endpoints plus the raw relation, and Full
    compares ordered endpoints plus the raw relation.
    """

    @staticmethod
    def _secondary_counters(
        analysis: RstAnalysis,
        *,
        ignore_case: bool,
    ) -> tuple[
        Counter[UnorderedSpanKey],
        Counter[DirectedSpanKey],
        Counter[tuple[UnorderedSpanKey, str]],
        Counter[tuple[DirectedSpanKey, str]],
    ]:
        node_yields = {node.node_id: node.edu_span for node in analysis.nodes}
        span: Counter[UnorderedSpanKey] = Counter()
        direction: Counter[DirectedSpanKey] = Counter()
        relation: Counter[tuple[UnorderedSpanKey, str]] = Counter()
        full: Counter[tuple[DirectedSpanKey, str]] = Counter()

        for edge in analysis.secondary_edges:
            try:
                source_yield = node_yields[edge.source_id]
                target_yield = node_yields[edge.target_id]
            except KeyError as error:
                raise ValueError(
                    f"secondary edge {edge.edge_id!r} references a node absent from the analysis"
                ) from error
            unordered: UnorderedSpanKey = (
                (source_yield, target_yield)
                if source_yield <= target_yield
                else (target_yield, source_yield)
            )
            directed = (source_yield, target_yield)
            raw_relation = edge.relation_raw.strip()
            if not raw_relation:
                raise ValueError(f"secondary edge {edge.edge_id!r} has an empty raw relation")
            if ignore_case:
                raw_relation = raw_relation.casefold()
            span[unordered] += 1
            direction[directed] += 1
            relation[(unordered, raw_relation)] += 1
            full[(directed, raw_relation)] += 1
        return span, direction, relation, full

    @staticmethod
    def _intersection_count[K](gold: Counter[K], pred: Counter[K]) -> int:
        return sum((gold & pred).values())

    @staticmethod
    def _secondary_metrics_from_counts(
        *,
        gold_count: int,
        pred_count: int,
        matched_span: int,
        matched_direction: int,
        matched_relation: int,
        matched_full: int,
    ) -> SecondaryEdgeMetrics:
        span_p, span_r, span_f1 = _calc_prf(matched_span, pred_count, gold_count)
        dir_p, dir_r, dir_f1 = _calc_prf(matched_direction, pred_count, gold_count)
        rel_p, rel_r, rel_f1 = _calc_prf(matched_relation, pred_count, gold_count)
        full_p, full_r, full_f1 = _calc_prf(matched_full, pred_count, gold_count)
        return SecondaryEdgeMetrics(
            span_precision=span_p,
            span_recall=span_r,
            span_f1=span_f1,
            direction_precision=dir_p,
            direction_recall=dir_r,
            direction_f1=dir_f1,
            relation_precision=rel_p,
            relation_recall=rel_r,
            relation_f1=rel_f1,
            full_precision=full_p,
            full_recall=full_r,
            full_f1=full_f1,
            gold_count=gold_count,
            pred_count=pred_count,
            matched_span=matched_span,
            matched_direction=matched_direction,
            matched_relation=matched_relation,
            matched_full=matched_full,
        )

    def score_secondary_edges(
        self,
        gold: RstAnalysis,
        pred: RstAnalysis,
        ignore_case: bool = True,
    ) -> SecondaryEdgeMetrics:
        """Score secondary edges by terminal EDU yields, never local node IDs."""

        if gold.document_id != pred.document_id:
            raise ValueError(
                "gold and predicted analyses must identify the same document: "
                f"{gold.document_id!r} != {pred.document_id!r}"
            )
        gold_span, gold_direction, gold_relation, gold_full = self._secondary_counters(
            gold,
            ignore_case=ignore_case,
        )
        pred_span, pred_direction, pred_relation, pred_full = self._secondary_counters(
            pred,
            ignore_case=ignore_case,
        )
        gold_count = len(gold.secondary_edges)
        pred_count = len(pred.secondary_edges)
        matched_span = self._intersection_count(gold_span, pred_span)
        matched_direction = self._intersection_count(gold_direction, pred_direction)
        matched_relation = self._intersection_count(gold_relation, pred_relation)
        matched_full = self._intersection_count(gold_full, pred_full)

        return self._secondary_metrics_from_counts(
            gold_count=gold_count,
            pred_count=pred_count,
            matched_span=matched_span,
            matched_direction=matched_direction,
            matched_relation=matched_relation,
            matched_full=matched_full,
        )

    def score_secondary_corpus(
        self,
        gold_analyses: Sequence[RstAnalysis],
        pred_analyses: Sequence[RstAnalysis],
        *,
        ignore_case: bool = True,
    ) -> SecondaryEdgeMetrics:
        """Micro-average paper-defined secondary Parseval over complete documents."""

        if len(gold_analyses) != len(pred_analyses):
            raise ValueError(
                "gold and predicted eRST corpora must contain the same number of documents"
            )
        document_metrics = tuple(
            self.score_secondary_edges(gold, pred, ignore_case=ignore_case)
            for gold, pred in zip(gold_analyses, pred_analyses, strict=True)
        )
        return self._secondary_metrics_from_counts(
            gold_count=sum(metric.gold_count for metric in document_metrics),
            pred_count=sum(metric.pred_count for metric in document_metrics),
            matched_span=sum(metric.matched_span for metric in document_metrics),
            matched_direction=sum(metric.matched_direction for metric in document_metrics),
            matched_relation=sum(metric.matched_relation for metric in document_metrics),
            matched_full=sum(metric.matched_full for metric in document_metrics),
        )

    def score_signals(
        self,
        gold_signals: Sequence[DiscourseSignal],
        pred_signals: Sequence[DiscourseSignal],
    ) -> SignalMetrics:
        """Score predicted discourse signals and token anchors."""
        gold_count = len(gold_signals)
        pred_count = len(pred_signals)

        # Index gold signals by edge_id
        gold_by_edge: dict[str | None, list[DiscourseSignal]] = {}
        total_gold_tokens = 0
        for g in gold_signals:
            gold_by_edge.setdefault(g.edge_id, []).append(g)
            total_gold_tokens += len(g.token_ids)

        total_pred_tokens = sum(len(p.token_ids) for p in pred_signals)
        total_matched_tokens = 0

        matched_detection = 0
        matched_type = 0
        matched_subtype = 0

        for p in pred_signals:
            candidates = gold_by_edge.get(p.edge_id, [])
            if candidates:
                matched_detection += 1
                if any(c.signal_type.lower() == p.signal_type.lower() for c in candidates):
                    matched_type += 1
                if any(
                    c.signal_type.lower() == p.signal_type.lower()
                    and c.signal_subtype.lower() == p.signal_subtype.lower()
                    for c in candidates
                ):
                    matched_subtype += 1

                # Token anchor overlap against matching candidates
                p_tokens = set(p.token_ids)
                best_token_overlap = 0
                for c in candidates:
                    overlap = len(p_tokens.intersection(set(c.token_ids)))
                    if overlap > best_token_overlap:
                        best_token_overlap = overlap
                total_matched_tokens += best_token_overlap

        det_p, det_r, det_f1 = _calc_prf(matched_detection, pred_count, gold_count)
        typ_p, typ_r, typ_f1 = _calc_prf(matched_type, pred_count, gold_count)
        sub_p, sub_r, sub_f1 = _calc_prf(matched_subtype, pred_count, gold_count)
        tok_p, tok_r, tok_f1 = _calc_prf(total_matched_tokens, total_pred_tokens, total_gold_tokens)

        return SignalMetrics(
            detection_precision=det_p,
            detection_recall=det_r,
            detection_f1=det_f1,
            type_precision=typ_p,
            type_recall=typ_r,
            type_f1=typ_f1,
            subtype_precision=sub_p,
            subtype_recall=sub_r,
            subtype_f1=sub_f1,
            token_precision=tok_p,
            token_recall=tok_r,
            token_f1=tok_f1,
            gold_signals_count=gold_count,
            pred_signals_count=pred_count,
            matched_detection=matched_detection,
            matched_type=matched_type,
            matched_subtype=matched_subtype,
        )

    def score_analysis(
        self,
        gold: RstAnalysis,
        pred: RstAnalysis,
    ) -> tuple[SecondaryEdgeMetrics, SignalMetrics]:
        """Score secondary edges and signals from complete RstAnalysis objects."""
        sec_metrics = self.score_secondary_edges(gold, pred)
        sig_metrics = self.score_signals(gold.signals, pred.signals)
        return sec_metrics, sig_metrics
