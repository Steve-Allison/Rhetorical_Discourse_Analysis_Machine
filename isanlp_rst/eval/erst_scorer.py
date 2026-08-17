"""Evaluation scorers for eRST secondary edges and discourse signals."""

from collections.abc import Sequence
from dataclasses import dataclass

from isanlp_rst.contracts.analysis import DiscourseSignal, RstAnalysis, SecondaryRelationEdge


@dataclass(frozen=True, slots=True)
class SecondaryEdgeMetrics:
    """Evaluation metrics for directed secondary discourse relations."""

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
    p = float(matched / pred_count) if pred_count > 0 else (1.0 if gold_count == 0 else 0.0)
    r = float(matched / gold_count) if gold_count > 0 else (1.0 if pred_count == 0 else 0.0)
    f1 = float(2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return p, r, f1


class ErstScorer:
    """Scores eRST graphs including secondary edges and discourse signals."""

    def score_secondary_edges(
        self,
        gold_edges: Sequence[SecondaryRelationEdge],
        pred_edges: Sequence[SecondaryRelationEdge],
        ignore_case: bool = True,
    ) -> SecondaryEdgeMetrics:
        """Score predicted secondary edges against gold secondary edges."""
        gold_count = len(gold_edges)
        pred_count = len(pred_edges)

        gold_map: dict[tuple[int, int], list[str]] = {}
        for g in gold_edges:
            rel = g.relation_concept or g.relation_raw
            if ignore_case:
                rel = rel.lower().strip()
            gold_map.setdefault((g.source_id, g.target_id), []).append(rel)

        matched_direction = 0
        matched_relation = 0
        matched_full = 0

        for p in pred_edges:
            p_rel = p.relation_concept or p.relation_raw
            if ignore_case:
                p_rel = p_rel.lower().strip()

            candidates = gold_map.get((p.source_id, p.target_id), [])
            if candidates:
                matched_direction += 1
                if any(c == p_rel for c in candidates):
                    matched_relation += 1
                    matched_full += 1

        dir_p, dir_r, dir_f1 = _calc_prf(matched_direction, pred_count, gold_count)
        rel_p, rel_r, rel_f1 = _calc_prf(matched_relation, pred_count, gold_count)
        full_p, full_r, full_f1 = _calc_prf(matched_full, pred_count, gold_count)

        return SecondaryEdgeMetrics(
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
            matched_direction=matched_direction,
            matched_relation=matched_relation,
            matched_full=matched_full,
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
        gold_by_edge: dict[str, list[DiscourseSignal]] = {}
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
        sec_metrics = self.score_secondary_edges(gold.secondary_edges, pred.secondary_edges)
        sig_metrics = self.score_signals(gold.signals, pred.signals)
        return sec_metrics, sig_metrics
