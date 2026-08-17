"""Pure-Python Standard-Parseval and RST-Parseval evaluation implementation."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from isanlp_rst.contracts.analysis import RstAnalysis
from isanlp_rst.contracts.enums import NodeKindEnum, NuclearityPatternEnum


@dataclass(frozen=True, slots=True)
class BracketSpan:
    """A single span tuple for Parseval comparison: (start_edu, end_edu, nuclearity, relation)."""

    start_edu: int
    end_edu: int
    nuclearity: str  # e.g., "NS", "SN", "NN" or empty for unlabeled
    relation: str  # normalized relation string

    @property
    def is_leaf(self) -> bool:
        return self.start_edu == self.end_edu


@dataclass(frozen=True, slots=True)
class CharBracketSpan:
    """A character-level span tuple for exact or soft Parseval comparison: (start_char, end_char, nuclearity, relation)."""

    start_char: int
    end_char: int
    nuclearity: str  # e.g., "NS", "SN", "NN" or empty for unlabeled
    relation: str  # normalized relation string

    @property
    def length(self) -> int:
        return max(0, self.end_char - self.start_char)


def compute_span_iou(start_a: int, end_a: int, start_b: int, end_b: int) -> float:
    """Compute Intersection-over-Union (IoU) between two coordinate spans."""
    intersection = max(0, min(end_a, end_b) - max(start_a, start_b))
    union = max(end_a, end_b) - min(start_a, start_b)
    if union <= 0:
        return 0.0
    return intersection / union


@dataclass(frozen=True, slots=True)
class ParsevalMetrics:
    """Parseval precision, recall, and F1 across Span, Nuclearity, Relation, and Full."""

    span_precision: float
    span_recall: float
    span_f1: float

    nuclearity_precision: float
    nuclearity_recall: float
    nuclearity_f1: float

    relation_precision: float
    relation_recall: float
    relation_f1: float

    full_precision: float
    full_recall: float
    full_f1: float

    gold_spans_count: int
    pred_spans_count: int
    matched_span: int
    matched_nuclearity: int
    matched_relation: int
    matched_full: int


def _calc_prf(matched: int, pred_count: int, gold_count: int) -> tuple[float, float, float]:
    p = (matched / pred_count) if pred_count > 0 else (1.0 if gold_count == 0 else 0.0)
    r = (matched / gold_count) if gold_count > 0 else (1.0 if pred_count == 0 else 0.0)
    f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
    return p, r, f1


class StandardParsevalScorer:
    """Evaluates discourse trees using Standard-Parseval or RST-Parseval conventions.

    Standard-Parseval / Morey et al. (2017):
    - Excludes single-EDU leaves (start == end) by default.
    - Excludes root span (start == 1, end == N) by default.
    - Nuclearity evaluation: matched span + identical nuclearity pattern (NS/SN/NN).
    - Relation evaluation: matched span + identical relation label.
    - Full evaluation: matched span + identical nuclearity + identical relation label.
    """

    def __init__(
        self,
        include_leaves: bool = False,
        include_root: bool = False,
        label_mapper: Callable[[str], str] | None = None,
        ignore_case: bool = True,
    ) -> None:
        self.include_leaves = include_leaves
        self.include_root = include_root
        self.label_mapper = label_mapper
        self.ignore_case = ignore_case

    def normalize_label(self, label: str) -> str:
        lab = label.strip()
        if self.ignore_case:
            lab = lab.lower()
        if self.label_mapper is not None:
            lab = self.label_mapper(lab)
        return lab

    def extract_spans_from_analysis(self, analysis: RstAnalysis) -> set[BracketSpan]:
        """Extract bracket spans from an RstAnalysis."""
        if not analysis.nodes:
            return set()

        num_edus = max((n.edu_span[1] for n in analysis.nodes), default=0)
        spans: set[BracketSpan] = set()

        # Map child_id to primary edge
        child_to_edge = {edge.child_id: edge for edge in analysis.primary_edges}

        for node in analysis.nodes:
            start, end = node.edu_span
            if not self.include_leaves and start == end:
                continue
            if not self.include_root and start == 1 and end == num_edus and num_edus > 1:
                continue

            edge = child_to_edge.get(node.node_id)
            if edge is not None:
                nuc = edge.nuclearity.value
                rel = self.normalize_label(edge.relation_concept or edge.relation_raw)
            else:
                nuc = NuclearityPatternEnum.NN.value if node.kind == NodeKindEnum.MULTINUCLEAR_GROUP else "ROOT"
                rel = "span"

            spans.add(BracketSpan(start_edu=start, end_edu=end, nuclearity=nuc, relation=rel))

        return spans

    def extract_spans_from_du(self, unit: object) -> set[BracketSpan]:
        """Extract bracket spans from an isanlp.annotation_rst.DiscourseUnit or similar tree."""
        spans: set[BracketSpan] = set()

        # First pass: find total EDUs
        edu_count = 0

        def count_leaves(node: object) -> None:
            nonlocal edu_count
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)
            if left is None and right is None:
                edu_count += 1
                return
            if left is not None:
                count_leaves(left)
            if right is not None:
                count_leaves(right)

        count_leaves(unit)
        total_edus = max(edu_count, 1)

        curr_edu = 1

        def walk(node: object) -> tuple[int, int]:
            nonlocal curr_edu
            left = getattr(node, "left", None)
            right = getattr(node, "right", None)

            if left is None and right is None:
                start = curr_edu
                end = curr_edu
                curr_edu += 1
                if self.include_leaves:
                    spans.add(BracketSpan(start_edu=start, end_edu=end, nuclearity="", relation=""))
                return start, end

            start_l, end_l = walk(left) if left is not None else (curr_edu, curr_edu)
            start_r, end_r = walk(right) if right is not None else (end_l, end_l)
            start = start_l
            end = end_r

            if not self.include_root and start == 1 and end == total_edus and total_edus > 1:
                pass
            else:
                nuc = str(getattr(node, "nuclearity", "") or "")
                raw_rel = str(getattr(node, "relation", "") or "")
                rel = self.normalize_label(raw_rel)
                spans.add(BracketSpan(start_edu=start, end_edu=end, nuclearity=nuc, relation=rel))

            return start, end

        walk(unit)
        return spans

    def score_span_sets(self, gold_spans: set[BracketSpan], pred_spans: set[BracketSpan]) -> ParsevalMetrics:
        """Compare two sets of bracket spans."""
        gold_count = len(gold_spans)
        pred_count = len(pred_spans)

        # Build index for fast lookup by (start, end)
        gold_by_span: dict[tuple[int, int], list[BracketSpan]] = {}
        for g in gold_spans:
            gold_by_span.setdefault((g.start_edu, g.end_edu), []).append(g)

        matched_span = 0
        matched_nuclearity = 0
        matched_relation = 0
        matched_full = 0

        for p in pred_spans:
            candidates = gold_by_span.get((p.start_edu, p.end_edu), [])
            if candidates:
                matched_span += 1
                # Check nuclearity
                if any(c.nuclearity.upper() == p.nuclearity.upper() for c in candidates):
                    matched_nuclearity += 1
                # Check relation
                if any(c.relation == p.relation for c in candidates):
                    matched_relation += 1
                # Check full
                if any(c.nuclearity.upper() == p.nuclearity.upper() and c.relation == p.relation for c in candidates):
                    matched_full += 1

        span_p, span_r, span_f1 = _calc_prf(matched_span, pred_count, gold_count)
        nuc_p, nuc_r, nuc_f1 = _calc_prf(matched_nuclearity, pred_count, gold_count)
        rel_p, rel_r, rel_f1 = _calc_prf(matched_relation, pred_count, gold_count)
        full_p, full_r, full_f1 = _calc_prf(matched_full, pred_count, gold_count)

        return ParsevalMetrics(
            span_precision=span_p,
            span_recall=span_r,
            span_f1=span_f1,
            nuclearity_precision=nuc_p,
            nuclearity_recall=nuc_r,
            nuclearity_f1=nuc_f1,
            relation_precision=rel_p,
            relation_recall=rel_r,
            relation_f1=rel_f1,
            full_precision=full_p,
            full_recall=full_r,
            full_f1=full_f1,
            gold_spans_count=gold_count,
            pred_spans_count=pred_count,
            matched_span=matched_span,
            matched_nuclearity=matched_nuclearity,
            matched_relation=matched_relation,
            matched_full=matched_full,
        )

    def score(
        self,
        gold: RstAnalysis | object,
        pred: RstAnalysis | object,
    ) -> ParsevalMetrics:
        """Score a predicted tree against a gold tree."""
        if isinstance(gold, RstAnalysis):
            gold_spans = self.extract_spans_from_analysis(gold)
        else:
            gold_spans = self.extract_spans_from_du(gold)

        if isinstance(pred, RstAnalysis):
            pred_spans = self.extract_spans_from_analysis(pred)
        else:
            pred_spans = self.extract_spans_from_du(pred)

        return self.score_span_sets(gold_spans, pred_spans)

    def score_corpus(
        self,
        gold_items: Sequence[RstAnalysis | object],
        pred_items: Sequence[RstAnalysis | object],
    ) -> ParsevalMetrics:
        """Micro-averaged Standard-Parseval score over a corpus of documents."""
        if len(gold_items) != len(pred_items):
            raise ValueError(f"Corpus size mismatch: {len(gold_items)} gold vs {len(pred_items)} pred")

        total_gold = 0
        total_pred = 0
        total_matched_span = 0
        total_matched_nuc = 0
        total_matched_rel = 0
        total_matched_full = 0

        for gold, pred in zip(gold_items, pred_items, strict=True):
            m = self.score(gold, pred)
            total_gold += m.gold_spans_count
            total_pred += m.pred_spans_count
            total_matched_span += m.matched_span
            total_matched_nuc += m.matched_nuclearity
            total_matched_rel += m.matched_relation
            total_matched_full += m.matched_full

        span_p, span_r, span_f1 = _calc_prf(total_matched_span, total_pred, total_gold)
        nuc_p, nuc_r, nuc_f1 = _calc_prf(total_matched_nuc, total_pred, total_gold)
        rel_p, rel_r, rel_f1 = _calc_prf(total_matched_rel, total_pred, total_gold)
        full_p, full_r, full_f1 = _calc_prf(total_matched_full, total_pred, total_gold)

        return ParsevalMetrics(
            span_precision=span_p,
            span_recall=span_r,
            span_f1=span_f1,
            nuclearity_precision=nuc_p,
            nuclearity_recall=nuc_r,
            nuclearity_f1=nuc_f1,
            relation_precision=rel_p,
            relation_recall=rel_r,
            relation_f1=rel_f1,
            full_precision=full_p,
            full_recall=full_r,
            full_f1=full_f1,
            gold_spans_count=total_gold,
            pred_spans_count=total_pred,
            matched_span=total_matched_span,
            matched_nuclearity=total_matched_nuc,
            matched_relation=total_matched_rel,
            matched_full=total_matched_full,
        )


class SoftParsevalScorer:
    """Evaluates discourse trees using character-span coordinates and soft IoU overlap tolerance.

    Addresses the integer-index boundary shift artifact of discrete EDU Parseval:
    - Evaluates constituent character spans (char_start, char_end) rather than discrete EDU IDs.
    - When min_iou == 1.0 (default), enforces exact character-boundary equality.
    - When min_iou < 1.0 (e.g. 0.85), permits slight punctuation/boundary shifts via Intersection-over-Union.
    - Excludes single-EDU leaves (node.kind == EDU) by default.
    - Excludes document root span by default.
    """

    def __init__(
        self,
        include_leaves: bool = False,
        include_root: bool = False,
        min_iou: float = 1.0,
        label_mapper: Callable[[str], str] | None = None,
        ignore_case: bool = True,
    ) -> None:
        if not (0.0 < min_iou <= 1.0):
            raise ValueError(f"min_iou must be in (0.0, 1.0], got {min_iou}")
        self.include_leaves = include_leaves
        self.include_root = include_root
        self.min_iou = min_iou
        self.label_mapper = label_mapper
        self.ignore_case = ignore_case

    def normalize_label(self, label: str) -> str:
        lab = label.strip()
        if self.ignore_case:
            lab = lab.lower()
        if self.label_mapper is not None:
            lab = self.label_mapper(lab)
        return lab

    def extract_spans_from_analysis(self, analysis: RstAnalysis) -> list[CharBracketSpan]:
        """Extract character-level bracket spans from an RstAnalysis."""
        if not analysis.nodes:
            return []

        doc_char_span = (0, max((n.char_span[1] for n in analysis.nodes), default=0))
        num_edus = max((n.edu_span[1] for n in analysis.nodes), default=0)
        spans: list[CharBracketSpan] = []

        child_to_edge = {edge.child_id: edge for edge in analysis.primary_edges}

        for node in analysis.nodes:
            if not self.include_leaves and node.kind == NodeKindEnum.EDU:
                continue
            if not self.include_root and node.char_span == doc_char_span and num_edus > 1:
                continue

            edge = child_to_edge.get(node.node_id)
            if edge is not None:
                nuc = edge.nuclearity.value
                rel = self.normalize_label(edge.relation_concept or edge.relation_raw)
            else:
                nuc = NuclearityPatternEnum.NN.value if node.kind == NodeKindEnum.MULTINUCLEAR_GROUP else "ROOT"
                rel = "span"

            spans.append(
                CharBracketSpan(
                    start_char=node.char_span[0],
                    end_char=node.char_span[1],
                    nuclearity=nuc,
                    relation=rel,
                )
            )

        return spans

    def score_span_sets(
        self,
        gold_spans: Sequence[CharBracketSpan] | set[CharBracketSpan],
        pred_spans: Sequence[CharBracketSpan] | set[CharBracketSpan],
    ) -> ParsevalMetrics:
        """Compare two collections of character-level bracket spans."""
        gold_list = list(gold_spans)
        pred_list = list(pred_spans)
        gold_count = len(gold_list)
        pred_count = len(pred_list)

        matched_span = 0
        matched_nuclearity = 0
        matched_relation = 0
        matched_full = 0

        if self.min_iou >= 1.0:
            # Exact character span matching
            gold_by_span: dict[tuple[int, int], list[CharBracketSpan]] = {}
            for g in gold_list:
                gold_by_span.setdefault((g.start_char, g.end_char), []).append(g)

            for p in pred_list:
                candidates = gold_by_span.get((p.start_char, p.end_char), [])
                if candidates:
                    matched_span += 1
                    if any(c.nuclearity.upper() == p.nuclearity.upper() for c in candidates):
                        matched_nuclearity += 1
                    if any(c.relation == p.relation for c in candidates):
                        matched_relation += 1
                    if any(
                        c.nuclearity.upper() == p.nuclearity.upper() and c.relation == p.relation for c in candidates
                    ):
                        matched_full += 1
        else:
            # Soft / IoU-tolerant matching with greedy assignment
            matched_gold_indices: set[int] = set()
            for p in pred_list:
                best_iou = 0.0
                best_g_idx = -1
                for g_idx, g in enumerate(gold_list):
                    if g_idx in matched_gold_indices:
                        continue
                    iou = compute_span_iou(p.start_char, p.end_char, g.start_char, g.end_char)
                    if iou >= self.min_iou and iou > best_iou:
                        best_iou = iou
                        best_g_idx = g_idx

                if best_g_idx >= 0:
                    matched_gold_indices.add(best_g_idx)
                    g_match = gold_list[best_g_idx]
                    matched_span += 1
                    if g_match.nuclearity.upper() == p.nuclearity.upper():
                        matched_nuclearity += 1
                    if g_match.relation == p.relation:
                        matched_relation += 1
                    if g_match.nuclearity.upper() == p.nuclearity.upper() and g_match.relation == p.relation:
                        matched_full += 1

        span_p, span_r, span_f1 = _calc_prf(matched_span, pred_count, gold_count)
        nuc_p, nuc_r, nuc_f1 = _calc_prf(matched_nuclearity, pred_count, gold_count)
        rel_p, rel_r, rel_f1 = _calc_prf(matched_relation, pred_count, gold_count)
        full_p, full_r, full_f1 = _calc_prf(matched_full, pred_count, gold_count)

        return ParsevalMetrics(
            span_precision=span_p,
            span_recall=span_r,
            span_f1=span_f1,
            nuclearity_precision=nuc_p,
            nuclearity_recall=nuc_r,
            nuclearity_f1=nuc_f1,
            relation_precision=rel_p,
            relation_recall=rel_r,
            relation_f1=rel_f1,
            full_precision=full_p,
            full_recall=full_r,
            full_f1=full_f1,
            gold_spans_count=gold_count,
            pred_spans_count=pred_count,
            matched_span=matched_span,
            matched_nuclearity=matched_nuclearity,
            matched_relation=matched_relation,
            matched_full=matched_full,
        )

    def score(
        self,
        gold: RstAnalysis,
        pred: RstAnalysis,
    ) -> ParsevalMetrics:
        """Score a predicted RstAnalysis against a gold RstAnalysis using character spans."""
        gold_spans = self.extract_spans_from_analysis(gold)
        pred_spans = self.extract_spans_from_analysis(pred)
        return self.score_span_sets(gold_spans, pred_spans)

    def score_corpus(
        self,
        gold_items: Sequence[RstAnalysis],
        pred_items: Sequence[RstAnalysis],
    ) -> ParsevalMetrics:
        """Micro-averaged Soft-Parseval score over a corpus of documents."""
        if len(gold_items) != len(pred_items):
            raise ValueError(f"Corpus size mismatch: {len(gold_items)} gold vs {len(pred_items)} pred")

        total_gold = 0
        total_pred = 0
        total_matched_span = 0
        total_matched_nuc = 0
        total_matched_rel = 0
        total_matched_full = 0

        for gold, pred in zip(gold_items, pred_items, strict=True):
            m = self.score(gold, pred)
            total_gold += m.gold_spans_count
            total_pred += m.pred_spans_count
            total_matched_span += m.matched_span
            total_matched_nuc += m.matched_nuclearity
            total_matched_rel += m.matched_relation
            total_matched_full += m.matched_full

        span_p, span_r, span_f1 = _calc_prf(total_matched_span, total_pred, total_gold)
        nuc_p, nuc_r, nuc_f1 = _calc_prf(total_matched_nuc, total_pred, total_gold)
        rel_p, rel_r, rel_f1 = _calc_prf(total_matched_rel, total_pred, total_gold)
        full_p, full_r, full_f1 = _calc_prf(total_matched_full, total_pred, total_gold)

        return ParsevalMetrics(
            span_precision=span_p,
            span_recall=span_r,
            span_f1=span_f1,
            nuclearity_precision=nuc_p,
            nuclearity_recall=nuc_r,
            nuclearity_f1=nuc_f1,
            relation_precision=rel_p,
            relation_recall=rel_r,
            relation_f1=rel_f1,
            full_precision=full_p,
            full_recall=full_r,
            full_f1=full_f1,
            gold_spans_count=total_gold,
            pred_spans_count=total_pred,
            matched_span=total_matched_span,
            matched_nuclearity=total_matched_nuc,
            matched_relation=total_matched_rel,
            matched_full=total_matched_full,
        )
