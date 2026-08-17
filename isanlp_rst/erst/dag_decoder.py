"""Constrained Acyclic DAG Graph Decoder for eRST secondary discourse edges."""

from collections import defaultdict
from dataclasses import dataclass

import networkx as nx

from isanlp_rst.contracts.analysis import RstAnalysis, SecondaryRelationEdge
from isanlp_rst.erst.dataset import COARSE_CONCEPTS, SecondaryEdgeCandidate


@dataclass(frozen=True, slots=True)
class ScoredEdgeCandidate:
    """A scored secondary edge candidate with existence probability and best relation."""

    source_id: int
    target_id: int
    edge_prob: float
    best_concept: str
    best_concept_prob: float
    joint_score: float


class AcyclicDagDecoder:
    """Greedy Tarjan-verified Acyclic DAG Decoder.

    Selects high-scoring candidate secondary edges while strictly guaranteeing:
    1. 100% DAG acyclicity (no circular rhetorical dependencies).
    2. Zero self-loops (u != v).
    3. Maximum node in-degree and out-degree constraints.
    """

    def __init__(
        self,
        min_confidence_threshold: float = 0.50,
        max_in_degree: int = 2,
        max_out_degree: int = 2,
    ) -> None:
        self.min_confidence = min_confidence_threshold
        self.max_in_degree = max_in_degree
        self.max_out_degree = max_out_degree

    def decode(
        self,
        analysis: RstAnalysis,
        candidates: list[SecondaryEdgeCandidate],
        edge_probs: list[float],
        rel_logits: list[list[float]],
    ) -> tuple[SecondaryRelationEdge, ...]:
        """Decode scored candidate pairs into a validated, cycle-free tuple of SecondaryRelationEdges."""
        if not candidates or not analysis.nodes:
            return ()

        # 1. Initialize directed graph with primary tree edges
        dag = nx.DiGraph()
        for node in analysis.nodes:
            dag.add_node(node.node_id)
        for p_edge in analysis.primary_edges:
            dag.add_edge(p_edge.parent_id, p_edge.child_id)

        # 2. Score and rank candidate edges
        import numpy as np

        scored_candidates: list[ScoredEdgeCandidate] = []
        for cand, e_prob, r_log in zip(candidates, edge_probs, rel_logits, strict=True):
            if e_prob < self.min_confidence:
                continue

            if not r_log:
                continue

            # Softmax over relation logits
            exp_logs = np.exp(np.array(r_log) - np.max(r_log))
            r_probs = exp_logs / np.sum(exp_logs)

            best_idx = int(np.argmax(r_probs))
            best_concept = COARSE_CONCEPTS[best_idx] if best_idx < len(COARSE_CONCEPTS) else "Elaboration"
            best_concept_prob = float(r_probs[best_idx])
            joint_score = float(e_prob * best_concept_prob)

            scored_candidates.append(
                ScoredEdgeCandidate(
                    source_id=cand.source_id,
                    target_id=cand.target_id,
                    edge_prob=float(e_prob),
                    best_concept=best_concept,
                    best_concept_prob=best_concept_prob,
                    joint_score=joint_score,
                )
            )

        # 3. Sort candidates descending by joint score
        scored_candidates.sort(key=lambda sc: sc.joint_score, reverse=True)

        # 4. Greedy insertion with acyclicity and degree verification
        accepted_edges: list[SecondaryRelationEdge] = []
        sec_in_degree: dict[int, int] = defaultdict(int)
        sec_out_degree: dict[int, int] = defaultdict(int)
        edge_counter = 1

        for sc in scored_candidates:
            u = sc.source_id
            v = sc.target_id

            if u == v:
                continue
            if sec_in_degree[v] >= self.max_in_degree:
                continue
            if sec_out_degree[u] >= self.max_out_degree:
                continue

            # Test adding edge (u, v) into DAG
            dag.add_edge(u, v)
            if nx.is_directed_acyclic_graph(dag):
                # Valid edge: accept!
                sec_out_degree[u] += 1
                sec_in_degree[v] += 1
                accepted_edges.append(
                    SecondaryRelationEdge(
                        edge_id=f"se_{edge_counter}",
                        source_id=u,
                        target_id=v,
                        relation_raw=sc.best_concept.lower(),
                        relation_concept=sc.best_concept,
                        confidence=sc.edge_prob,
                        calibrated=True,
                    )
                )
                edge_counter += 1
            else:
                # Cycle detected: rollback!
                dag.remove_edge(u, v)

        return tuple(accepted_edges)
