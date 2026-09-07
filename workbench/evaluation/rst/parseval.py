"""Offline Standard-Parseval and RST-Parseval evaluation implementation."""

from collections import Counter, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts.analysis import PrimaryRelationEdge, RstAnalysis, RstNode
from rdam.rst.contracts.enums import NodeKindEnum, NuclearityPatternEnum


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


def _exact_match_counts(
    gold: Sequence[tuple[int, int, str, str]],
    predicted: Sequence[tuple[int, int, str, str]],
) -> tuple[int, int, int, int]:
    """Intersect bracket multisets independently for each evaluation criterion.

    A gold occurrence can earn credit only once within a metric. Projecting to
    unlabeled coordinates must preserve multiplicity, including unary brackets
    with the same yield. Label criteria have their own one-to-one matches.
    """
    span = (Counter((s, e) for s, e, _, _ in gold)
            & Counter((s, e) for s, e, _, _ in predicted)).total()
    nuclearity = (Counter((s, e, n) for s, e, n, _ in gold)
                  & Counter((s, e, n) for s, e, n, _ in predicted)).total()
    relation = (Counter((s, e, r) for s, e, _, r in gold)
                & Counter((s, e, r) for s, e, _, r in predicted)).total()
    full = (Counter(gold) & Counter(predicted)).total()
    return span, nuclearity, relation, full


def maximum_match_count(candidates: Sequence[Sequence[int]]) -> int:
    """Count a maximum bipartite matching using iterative augmenting paths.

    Rows identify predicted occurrences; entries identify eligible gold
    occurrences. Iterative traversal avoids a recursion limit on long trees.
    """
    gold_matches: dict[int, int] = {}
    predicted_matches: dict[int, int] = {}
    for root in range(len(candidates)):
        pending = deque([root])
        visited = {root}
        predecessor: dict[int, int] = {}
        free_gold: int | None = None
        while pending and free_gold is None:
            predicted = pending.popleft()
            for gold in candidates[predicted]:
                if gold in predecessor:
                    continue
                predecessor[gold] = predicted
                owner = gold_matches.get(gold)
                if owner is None:
                    free_gold = gold
                    break
                if owner not in visited:
                    visited.add(owner)
                    pending.append(owner)
        while free_gold is not None:
            predicted = predecessor[free_gold]
            previous_gold = predicted_matches.get(predicted)
            gold_matches[free_gold] = predicted
            predicted_matches[predicted] = free_gold
            free_gold = previous_gold
    return len(gold_matches)


def _overlap_match_counts(
    gold: Sequence[CharBracketSpan], predicted: Sequence[CharBracketSpan], min_iou: float,
) -> tuple[int, int, int, int]:
    """Maximize one-to-one credit separately for each metric's constraints."""
    span_candidates: list[list[int]] = []
    nuclearity_candidates: list[list[int]] = []
    relation_candidates: list[list[int]] = []
    full_candidates: list[list[int]] = []
    for prediction in predicted:
        spans: list[int] = []
        nuclearities: list[int] = []
        relations: list[int] = []
        full: list[int] = []
        for index, reference in enumerate(gold):
            overlap = compute_span_iou(
                prediction.start_char, prediction.end_char, reference.start_char, reference.end_char,
            )
            if overlap < min_iou:
                continue
            spans.append(index)
            same_nuclearity = prediction.nuclearity.upper() == reference.nuclearity.upper()
            same_relation = prediction.relation == reference.relation
            if same_nuclearity:
                nuclearities.append(index)
            if same_relation:
                relations.append(index)
            if same_nuclearity and same_relation:
                full.append(index)
        span_candidates.append(spans)
        nuclearity_candidates.append(nuclearities)
        relation_candidates.append(relations)
        full_candidates.append(full)
    return (
        maximum_match_count(span_candidates), maximum_match_count(nuclearity_candidates),
        maximum_match_count(relation_candidates), maximum_match_count(full_candidates),
    )


def _binary_attachments(analysis: RstAnalysis) -> tuple[int | None, list[tuple[RstNode, str, str]]]:
    """Validate binary topology and recover each parent's native attachment.

    RS4 graphs with EDU parents or non-binary groups must be normalized first;
    interpreting their incoming labels as binary attachment patterns is invalid.
    """
    nodes = {node.node_id: node for node in analysis.nodes}
    if len(nodes) != len(analysis.nodes):
        raise ValueError("Evaluation tree contains duplicate node IDs")
    children: dict[int, list[PrimaryRelationEdge]] = {}
    parents: set[int] = set()
    for edge in analysis.primary_edges:
        if edge.parent_id not in nodes or edge.child_id not in nodes:
            raise ValueError("Evaluation edge references a missing node")
        if edge.child_id in parents:
            raise ValueError("Evaluation tree has repeated incoming edges")
        parents.add(edge.child_id)
        children.setdefault(edge.parent_id, []).append(edge)
    if not nodes:
        return None, []
    roots = nodes.keys() - parents
    if len(roots) != 1:
        raise ValueError("Evaluation tree must have exactly one root")
    root_id = next(iter(roots))
    visited: set[int] = set()
    pending = [root_id]
    attachments: list[tuple[RstNode, str, str]] = []
    leaves: list[int] = []
    while pending:
        node_id = pending.pop()
        if node_id in visited:
            raise ValueError("Evaluation tree contains a cycle")
        visited.add(node_id)
        node = nodes[node_id]
        outgoing = children.get(node_id, [])
        if node.kind == NodeKindEnum.EDU:
            if outgoing or node.edu_span[0] != node.edu_span[1]:
                raise ValueError("Evaluation EDU must be a leaf with a singleton EDU span")
            leaves.append(node.edu_span[0])
            continue
        if len(outgoing) != 2:
            raise ValueError("Evaluation requires binary attachments; normalize non-binary annotations first")
        left_edge, right_edge = sorted(outgoing, key=lambda edge: nodes[edge.child_id].edu_span)
        left, right = nodes[left_edge.child_id], nodes[right_edge.child_id]
        if (left.edu_span[0] != node.edu_span[0] or right.edu_span[1] != node.edu_span[1]
                or left.edu_span[1] + 1 != right.edu_span[0]):
            raise ValueError("Attachment child EDU spans must partition the parent")
        if (left.char_span[0] != node.char_span[0] or right.char_span[1] != node.char_span[1]
                or left.char_span[1] > right.char_span[0]):
            raise ValueError("Attachment child character spans must be ordered within the parent")
        pattern = left_edge.nuclearity.value
        if pattern != right_edge.nuclearity.value:
            raise ValueError("Binary attachment edges disagree on nuclearity")
        left_rel, right_rel = left_edge.relation_raw.strip(), right_edge.relation_raw.strip()
        if pattern == "NS" and left_rel == "span" and right_rel and right_rel != "span":
            relation = right_rel
        elif pattern == "SN" and right_rel == "span" and left_rel and left_rel != "span":
            relation = left_rel
        elif pattern == "NN" and left_rel == right_rel and left_rel and left_rel != "span":
            relation = left_rel
        else:
            raise ValueError("Binary attachment relation labels disagree with its nuclearity")
        attachments.append((node, pattern, relation))
        pending.extend((right.node_id, left.node_id))
    if visited != nodes.keys():
        raise ValueError("Evaluation tree contains disconnected nodes")
    if sorted(leaves) != list(range(1, len(leaves) + 1)):
        raise ValueError("Evaluation EDUs must form a consecutive one-based sequence")
    return root_id, attachments


def rst_parseval_spans(analysis: RstAnalysis) -> set[BracketSpan]:
    """Marcu-style brackets: incoming N/S labels, leaves included, root excluded.

    This projection evaluates the supplied binary tree. Non-binary annotations
    must be normalized explicitly before invoking it.
    """
    _, attachments = _binary_attachments(analysis)
    nodes = {node.node_id: node for node in analysis.nodes}
    child_edges: dict[int, list[PrimaryRelationEdge]] = {}
    for edge in analysis.primary_edges:
        child_edges.setdefault(edge.parent_id, []).append(edge)
    brackets: set[BracketSpan] = set()
    for parent, pattern, _ in attachments:
        outgoing = sorted(child_edges[parent.node_id], key=lambda edge: nodes[edge.child_id].edu_span)
        for edge, role in zip(outgoing, pattern, strict=True):
            child = nodes[edge.child_id]
            brackets.add(BracketSpan(child.edu_span[0], child.edu_span[1], role, edge.relation_raw))
    return brackets


class StandardParsevalScorer:
    """Score labelled binary attachment decisions using native relation labels.

    Defaults include every internal attachment, including the root, and exclude
    leaves: n-1 decisions for n EDUs, as in Morey et al. (2017), section 4.
    Explicit root exclusion or leaf inclusion produces a custom diagnostic;
    it does not reproduce Marcu's RST-Parseval encoding.
    """

    def __init__(
        self,
        include_leaves: bool = False,
        include_root: bool = True,
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
        """Recover labels from outgoing binary edges, independent of node IDs."""
        root_id, attachments = _binary_attachments(analysis)
        spans = {
            BracketSpan(node.edu_span[0], node.edu_span[1], pattern, self.normalize_label(relation))
            for node, pattern, relation in attachments
            if self.include_root or node.node_id != root_id
        }
        if self.include_leaves:
            spans.update(
                BracketSpan(node.edu_span[0], node.edu_span[1], "", "")
                for node in analysis.nodes if node.kind == NodeKindEnum.EDU
            )
        return spans

    def extract_spans_from_du(self, unit: DiscourseUnit) -> set[BracketSpan]:
        """Read attachment labels from the internal nodes that own them.

        DiscourseUnit stores a binary attachment's relation and NS/SN/NN
        pattern on its parent, not on its children. Leaves carry no attachment
        labels. Root inclusion remains controlled by the caller's convention.
        """
        spans: set[BracketSpan] = set()
        pending: list[tuple[DiscourseUnit, bool]] = [(unit, False)]
        visited: set[int] = set()
        yields: dict[int, tuple[int, int]] = {}
        next_edu = 1
        while pending:
            node, exiting = pending.pop()
            identity = id(node)
            if not exiting:
                if identity in visited:
                    raise ValueError("DiscourseUnit must be a tree without cycles or shared children")
                visited.add(identity)
                left, right = node.left, node.right
                if left is None and right is None:
                    yields[identity] = (next_edu, next_edu)
                    if self.include_leaves:
                        spans.add(BracketSpan(next_edu, next_edu, "", ""))
                    next_edu += 1
                    continue
                if left is None or right is None:
                    raise ValueError("A binary attachment must have both children")
                pending.extend(((node, True), (right, False), (left, False)))
                continue
            left, right = node.left, node.right
            if left is None or right is None:
                raise ValueError("A binary attachment must have both children")
            start, _ = yields[id(left)]
            _, end = yields[id(right)]
            yields[identity] = (start, end)
            nuclearity = node.nuclearity.upper()
            if nuclearity not in NuclearityPatternEnum:
                raise ValueError(f"Attachment has invalid nuclearity: {node.nuclearity!r}")
            relation = self.normalize_label(node.relation)
            if not relation or relation == "span":
                raise ValueError("Attachment must carry a rhetorical relation, not a structural span label")
            if node is not unit or self.include_root:
                spans.add(BracketSpan(start, end, nuclearity, relation))
        return spans

    def score_span_sets(self, gold_spans: set[BracketSpan], pred_spans: set[BracketSpan]) -> ParsevalMetrics:
        """Compare two sets of bracket spans."""
        gold_count = len(gold_spans)
        pred_count = len(pred_spans)

        matched_span, matched_nuclearity, matched_relation, matched_full = _exact_match_counts(
            [(g.start_edu, g.end_edu, g.nuclearity.upper(), g.relation) for g in gold_spans],
            [(p.start_edu, p.end_edu, p.nuclearity.upper(), p.relation) for p in pred_spans],
        )

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
        gold: RstAnalysis | DiscourseUnit,
        pred: RstAnalysis | DiscourseUnit,
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
        gold_items: Sequence[RstAnalysis | DiscourseUnit],
        pred_items: Sequence[RstAnalysis | DiscourseUnit],
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
    - Each metric maximizes one-to-one matches satisfying its overlap and label constraints;
      scores are independent of input order. This is a local overlap diagnostic,
      not an assertion of equivalence to a published Parseval benchmark.
    - Excludes single-EDU leaves (node.kind == EDU) by default.
    - Includes the root attachment by default, as with EDU-coordinate Parseval.
    """

    def __init__(
        self,
        include_leaves: bool = False,
        include_root: bool = True,
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
        """Use the same native attachment decisions as EDU-coordinate Parseval."""
        root_id, attachments = _binary_attachments(analysis)
        spans = [
            CharBracketSpan(node.char_span[0], node.char_span[1], pattern, self.normalize_label(relation))
            for node, pattern, relation in attachments
            if self.include_root or node.node_id != root_id
        ]
        if self.include_leaves:
            spans.extend(
                CharBracketSpan(node.char_span[0], node.char_span[1], "", "")
                for node in analysis.nodes if node.kind == NodeKindEnum.EDU
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
            matched_span, matched_nuclearity, matched_relation, matched_full = _exact_match_counts(
                [(g.start_char, g.end_char, g.nuclearity.upper(), g.relation) for g in gold_list],
                [(p.start_char, p.end_char, p.nuclearity.upper(), p.relation) for p in pred_list],
            )
        else:
            matched_span, matched_nuclearity, matched_relation, matched_full = _overlap_match_counts(
                gold_list, pred_list, self.min_iou,
            )

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
