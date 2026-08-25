"""Single complete, signal-sufficient eRST secondary-edge candidate generator."""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import islice
import math

import networkx as nx
from pydantic import BaseModel, ConfigDict

from isanlp_rst.contracts.analysis import DiscourseSignal, RstAnalysis, RstNode
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.enums import NodeKindEnum


class RelationCompatibilityProfile(BaseModel):
    """Training-derived raw-relation compatibility indexed by signal type/subtype."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_revision: str
    inventory_digest: str
    by_signal: dict[str, tuple[str, ...]]


class CandidateMode(StrEnum):
    """Pipeline stage requesting the canonical candidate space."""

    TRAIN = "train"
    DEVELOPMENT = "development"
    TEST = "test"
    TEST2 = "test2"
    INFERENCE = "inference"


@dataclass(frozen=True, slots=True)
class SecondaryEdgeCandidate:
    """Complete evidence for one ordered primary-tree node pair."""

    document_id: str
    source_id: int
    target_id: int
    source_text: str
    target_text: str
    source_char_span: tuple[int, int]
    target_char_span: tuple[int, int]
    structural_features: tuple[float, ...]
    is_gold_edge: bool = field(compare=False)
    gold_relation: str | None = field(default=None, compare=False)
    gold_concept: str | None = field(default=None, compare=False)
    signal_ids: tuple[str, ...] = ()
    signal_types: tuple[str, ...] = ()
    signal_subtypes: tuple[str, ...] = ()
    compatible_relations: tuple[str, ...] = ()
    source_head_id: int = -1
    target_head_id: int = -1
    source_head_text: str = ""
    target_head_text: str = ""
    source_sentence_ids: tuple[int, ...] = ()
    target_sentence_ids: tuple[int, ...] = ()
    direction: str = "overlap"
    edu_distance: int = 0
    existing_primary_relation: str | None = None
    existing_primary_direction: str | None = None
    primary_path: tuple[str, ...] = ()


def compute_structural_features(
    source: RstNode,
    target: RstNode,
    primary_graph: nx.DiGraph,
    doc_text: str,
    *,
    hop_distance: int | None = None,
) -> tuple[float, ...]:
    """Compute deterministic distance, topology, kind, and lexical features."""

    del doc_text
    char_distance = target.char_span[0] - source.char_span[0]
    signed_log_distance = (1.0 if char_distance >= 0 else -1.0) * math.log1p(abs(char_distance))
    edu_distance = float(target.edu_span[0] - source.edu_span[0])
    if hop_distance is None:
        try:
            resolved_hop_distance = float(
                nx.shortest_path_length(
                    primary_graph.to_undirected(),
                    source.node_id,
                    target.node_id,
                )
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            resolved_hop_distance = math.inf
    else:
        resolved_hop_distance = float(hop_distance)
    source_length = max(1, source.char_span[1] - source.char_span[0])
    target_length = max(1, target.char_span[1] - target.char_span[0])
    source_prefix = source.text[:80].casefold()
    return (
        signed_log_distance,
        edu_distance,
        resolved_hop_distance,
        math.log(source_length / target_length),
        1.0 if source.kind == NodeKindEnum.EDU else 0.0,
        1.0 if target.kind == NodeKindEnum.EDU else 0.0,
        1.0 if any(word in source_prefix for word in ("however", "although", "but", "whereas")) else 0.0,
        1.0 if any(word in source_prefix for word in ("because", "therefore", "thus", "as a result")) else 0.0,
        1.0 if any(word in source_prefix for word in ("if", "unless", "otherwise")) else 0.0,
    )


def _overlaps(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def _signal_applies(signal: DiscourseSignal, node: RstNode, document: RstDocument) -> bool:
    if not signal.sufficient:
        return False
    if signal.char_spans and any(_overlaps(span, node.char_span) for span in signal.char_spans):
        return True
    if signal.token_ids:
        node_tokens = {
            token.token_id
            for token in document.tokens
            if node.char_span[0] <= token.start and token.end <= node.char_span[1]
        }
        return bool(node_tokens.intersection(signal.token_ids))
    return not signal.char_spans


def _sentence_ids(document: RstDocument, node: RstNode) -> tuple[int, ...]:
    token_sentence_ids = {
        token.sentence_id
        for token in document.tokens
        if token.sentence_id is not None and _overlaps((token.start, token.end), node.char_span)
    }
    if token_sentence_ids:
        return tuple(sorted(token_sentence_ids))
    return tuple(
        index
        for index, boundary in enumerate(document.sentence_boundaries)
        if _overlaps((boundary.start, boundary.end), node.char_span)
    )


def _node_heads(
    nodes: tuple[RstNode, ...],
    analysis: RstAnalysis,
) -> dict[int, int]:
    node_by_id = {node.node_id: node for node in nodes}
    children: dict[int, list[tuple[int, str]]] = {}
    for edge in analysis.primary_edges:
        children.setdefault(edge.parent_id, []).append((edge.child_id, edge.relation_raw))
    edu_nodes = tuple(node for node in nodes if node.kind == NodeKindEnum.EDU)
    memo: dict[int, int] = {}

    def resolve(node_id: int, visiting: frozenset[int] = frozenset()) -> int:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            raise ValueError(f"primary graph cycle prevents head resolution at node {node_id}")
        node = node_by_id[node_id]
        if node.kind == NodeKindEnum.EDU:
            memo[node_id] = node_id
            return node_id
        node_children = children.get(node_id, [])
        nucleus_children = [child_id for child_id, relation in node_children if relation.casefold() == "span"]
        choices = nucleus_children or [child_id for child_id, _ in node_children]
        if choices:
            chosen = min(choices, key=lambda child_id: (node_by_id[child_id].edu_span[0], child_id))
            head = resolve(chosen, visiting | {node_id})
        else:
            covered = [
                edu
                for edu in edu_nodes
                if node.edu_span[0] <= edu.edu_span[0] and edu.edu_span[1] <= node.edu_span[1]
            ]
            head = min(covered, key=lambda edu: (edu.edu_span[0], edu.node_id)).node_id if covered else node_id
        memo[node_id] = head
        return head

    return {node.node_id: resolve(node.node_id) for node in nodes}


def _primary_path(
    node_path: list[int],
    relation_by_pair: Mapping[tuple[int, int], str],
) -> tuple[str, ...]:
    steps: list[str] = []
    for left, right in zip(node_path, node_path[1:], strict=False):
        if (left, right) in relation_by_pair:
            steps.append(f">{relation_by_pair[(left, right)]}")
        else:
            steps.append(f"<{relation_by_pair[(right, left)]}")
    return tuple(steps)


def _pair_direction(source: RstNode, target: RstNode) -> str:
    if source.char_span[1] <= target.char_span[0]:
        return "forward"
    if target.char_span[1] <= source.char_span[0]:
        return "backward"
    return "overlap"


def iter_secondary_edge_candidates(
    document: RstDocument,
    analysis: RstAnalysis,
    *,
    signals: tuple[DiscourseSignal, ...] | None = None,
    compatibility: RelationCompatibilityProfile | None = None,
    mode: CandidateMode = CandidateMode.INFERENCE,
) -> Iterator[SecondaryEdgeCandidate]:
    """Yield every signal-sufficient ordered pair; mode cannot alter membership."""

    del mode
    nodes = tuple(sorted(analysis.nodes, key=lambda node: (node.edu_span[0], node.edu_span[1], node.node_id)))
    if len(nodes) < 2:
        return
    available_signals = tuple(signal for signal in (signals if signals is not None else analysis.signals) if signal.sufficient)
    if not available_signals:
        return

    graph = nx.DiGraph()
    graph.add_nodes_from(node.node_id for node in nodes)
    relation_by_pair = {(edge.parent_id, edge.child_id): edge.relation_raw for edge in analysis.primary_edges}
    graph.add_edges_from(relation_by_pair)
    undirected_graph = graph.to_undirected()
    node_by_id = {node.node_id: node for node in nodes}
    head_by_node = _node_heads(nodes, analysis)
    sentence_ids_by_node = {node.node_id: _sentence_ids(document, node) for node in nodes}
    signals_by_node = {
        node.node_id: tuple(
            signal for signal in available_signals if _signal_applies(signal, node, document)
        )
        for node in nodes
    }
    gold_by_pair = {(edge.source_id, edge.target_id): edge for edge in analysis.secondary_edges}
    for source in nodes:
        paths_from_source = nx.single_source_shortest_path(undirected_graph, source.node_id)
        for target in nodes:
            if source.node_id == target.node_id:
                continue
            applicable_signal_ids = {
                signal.signal_id
                for signal in (*signals_by_node[source.node_id], *signals_by_node[target.node_id])
            }
            pair_signals = tuple(
                signal for signal in available_signals if signal.signal_id in applicable_signal_ids
            )
            if not pair_signals:
                continue
            node_path = paths_from_source.get(target.node_id)
            if node_path is None:
                raise ValueError(
                    f"primary tree is disconnected between nodes {source.node_id} and {target.node_id}"
                )
            compatible_relations: list[str] = []
            for signal in pair_signals:
                learned = (
                    compatibility.by_signal.get(f"{signal.signal_type}:{signal.signal_subtype}", ())
                    if compatibility is not None
                    else ()
                )
                for relation in (*signal.compatible_relations, *learned):
                    if relation not in compatible_relations:
                        compatible_relations.append(relation)
            source_head = node_by_id[head_by_node[source.node_id]]
            target_head = node_by_id[head_by_node[target.node_id]]
            direct_relation = relation_by_pair.get((source.node_id, target.node_id))
            direct_direction: str | None = "source_to_target" if direct_relation is not None else None
            if direct_relation is None:
                direct_relation = relation_by_pair.get((target.node_id, source.node_id))
                if direct_relation is not None:
                    direct_direction = "target_to_source"
            gold = gold_by_pair.get((source.node_id, target.node_id))
            yield SecondaryEdgeCandidate(
                document_id=document.document_id,
                source_id=source.node_id,
                target_id=target.node_id,
                source_text=source.text,
                target_text=target.text,
                source_char_span=source.char_span,
                target_char_span=target.char_span,
                structural_features=compute_structural_features(
                    source,
                    target,
                    graph,
                    document.text,
                    hop_distance=len(node_path) - 1,
                ),
                is_gold_edge=gold is not None,
                gold_relation=gold.relation_raw if gold is not None else None,
                gold_concept=gold.relation_concept if gold is not None else None,
                signal_ids=tuple(signal.signal_id for signal in pair_signals),
                signal_types=tuple(signal.signal_type for signal in pair_signals),
                signal_subtypes=tuple(signal.signal_subtype for signal in pair_signals),
                compatible_relations=tuple(compatible_relations),
                source_head_id=source_head.node_id,
                target_head_id=target_head.node_id,
                source_head_text=source_head.text,
                target_head_text=target_head.text,
                source_sentence_ids=sentence_ids_by_node[source.node_id],
                target_sentence_ids=sentence_ids_by_node[target.node_id],
                direction=_pair_direction(source, target),
                edu_distance=target.edu_span[0] - source.edu_span[0],
                existing_primary_relation=direct_relation,
                existing_primary_direction=direct_direction,
                primary_path=_primary_path(node_path, relation_by_pair),
            )


def generate_secondary_edge_candidates(
    document: RstDocument,
    analysis: RstAnalysis,
    *,
    signals: tuple[DiscourseSignal, ...] | None = None,
    compatibility: RelationCompatibilityProfile | None = None,
    mode: CandidateMode = CandidateMode.INFERENCE,
) -> tuple[SecondaryEdgeCandidate, ...]:
    """Materialize the canonical iterator for consumers that require random access."""

    return tuple(
        iter_secondary_edge_candidates(
            document,
            analysis,
            signals=signals,
            compatibility=compatibility,
            mode=mode,
        )
    )


def iter_candidate_batches(
    candidates: Iterable[SecondaryEdgeCandidate],
    *,
    batch_size: int,
) -> Iterator[tuple[SecondaryEdgeCandidate, ...]]:
    """Stream all candidates in bounded batches without truncating membership."""

    if batch_size < 1:
        raise ValueError("candidate batch size must be at least one")
    iterator = iter(candidates)
    while batch := tuple(islice(iterator, batch_size)):
        yield batch


__all__ = [
    "CandidateMode",
    "RelationCompatibilityProfile",
    "SecondaryEdgeCandidate",
    "compute_structural_features",
    "generate_secondary_edge_candidates",
    "iter_candidate_batches",
    "iter_secondary_edge_candidates",
]
