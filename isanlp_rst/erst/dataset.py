"""Dataset extraction, structural feature computation, and pairwise collation for eRST secondary edges."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import torch
from torch.utils.data import Dataset

from isanlp_rst.contracts.analysis import RstAnalysis, RstNode
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.enums import NodeKindEnum
from isanlp_rst.erst.converter import rs4_to_document_and_analysis
from isanlp_rst.erst.rs4 import RS4Reader


@dataclass(frozen=True, slots=True)
class SecondaryEdgeCandidate:
    """A candidate pairwise link between source node u and target node v."""

    source_id: int
    target_id: int
    source_text: str
    target_text: str
    source_char_span: tuple[int, int]
    target_char_span: tuple[int, int]
    structural_features: tuple[float, ...]
    is_gold_edge: bool
    gold_relation: str | None = None
    gold_concept: str | None = None


# 18 canonical coarse concepts in central.lock.yaml
COARSE_CONCEPTS: tuple[str, ...] = (
    "Attribution",
    "Background",
    "Cause",
    "Comparison",
    "Condition",
    "Contrast",
    "Elaboration",
    "Enablement",
    "Evaluation",
    "Explanation",
    "Joint",
    "Manner-Means",
    "Same-unit",
    "Summary",
    "Temporal",
    "Textual-organization",
    "Topic-Change",
    "Topic-Comment",
)
CONCEPT_TO_IDX: dict[str, int] = {c: i for i, c in enumerate(COARSE_CONCEPTS)}


def compute_structural_features(
    u: RstNode,
    v: RstNode,
    primary_graph: nx.DiGraph,
    doc_text: str,
) -> tuple[float, ...]:
    """Compute rich structural, topological, and lexical distance features for pair (u, v)."""
    # 1. Token / Character distance (log-scaled with direction sign)
    char_dist = v.char_span[0] - u.char_span[0]
    sign_dist = 1.0 if char_dist >= 0 else -1.0
    log_char_dist = sign_dist * math.log1p(abs(char_dist))

    # 2. EDU index distance
    edu_dist = float(v.edu_span[0] - u.edu_span[0])

    # 3. Primary tree shortest undirected path hop count
    undirected = primary_graph.to_undirected()
    try:
        hop_dist = float(nx.shortest_path_length(undirected, source=u.node_id, target=v.node_id))
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        hop_dist = 20.0

    # 4. Spans length log-ratio
    len_u = max(1, u.char_span[1] - u.char_span[0])
    len_v = max(1, v.char_span[1] - v.char_span[0])
    log_len_ratio = math.log(len_u / len_v)

    # 5. Node kind one-hot encodings (EDU vs SPAN vs ROOT)
    u_is_edu = 1.0 if u.kind == NodeKindEnum.EDU else 0.0
    v_is_edu = 1.0 if v.kind == NodeKindEnum.EDU else 0.0

    # 6. Discourse connective presence in source span u
    u_lower = u.text[:40].lower()
    has_contrast = 1.0 if any(w in u_lower for w in ("however", "although", "but", "while", "whereas")) else 0.0
    has_cause = 1.0 if any(w in u_lower for w in ("because", "since", "as a result", "therefore", "thus")) else 0.0
    has_condition = 1.0 if any(w in u_lower for w in ("if", "unless", "provided", "assuming")) else 0.0

    return (
        log_char_dist,
        edu_dist,
        hop_dist,
        log_len_ratio,
        u_is_edu,
        v_is_edu,
        has_contrast,
        has_cause,
        has_condition,
    )


def extract_eRST_candidates_from_document(
    document: RstDocument,
    analysis: RstAnalysis,
    negative_ratio: float = 4.0,
) -> list[SecondaryEdgeCandidate]:
    """Extract positive gold secondary edges and pruned non-ancestor negative candidates."""
    if not analysis.nodes:
        return []

    # 1. Build primary tree directed graph
    primary_graph = nx.DiGraph()
    for n in analysis.nodes:
        primary_graph.add_node(n.node_id)
    for edge in analysis.primary_edges:
        primary_graph.add_edge(edge.parent_id, edge.child_id)

    # 2. Build map of gold secondary edges: (source_id, target_id) -> edge
    gold_edges: dict[tuple[int, int], Any] = {}
    for se in analysis.secondary_edges:
        gold_edges[(se.source_id, se.target_id)] = se

    node_map = {n.node_id: n for n in analysis.nodes}
    candidates: list[SecondaryEdgeCandidate] = []
    positive_count = 0

    # 3. Extract positive candidates
    for (src_id, tgt_id), se in gold_edges.items():
        u = node_map.get(src_id)
        v = node_map.get(tgt_id)
        if u is not None and v is not None:
            features = compute_structural_features(u, v, primary_graph, document.text)
            candidates.append(
                SecondaryEdgeCandidate(
                    source_id=u.node_id,
                    target_id=v.node_id,
                    source_text=u.text,
                    target_text=v.text,
                    source_char_span=u.char_span,
                    target_char_span=v.char_span,
                    structural_features=features,
                    is_gold_edge=True,
                    gold_relation=se.relation_raw,
                    gold_concept=se.relation_concept,
                )
            )
            positive_count += 1

    # 4. Generate negative candidate pairs (Ancestry-Pruned)
    # GUM eRST rule: A secondary edge cannot link direct ancestors/descendants in primary tree
    negative_candidates: list[SecondaryEdgeCandidate] = []
    nodes = list(analysis.nodes)

    for u in nodes:
        # Find ancestors and descendants of u in primary tree
        descendants = nx.descendants(primary_graph, u.node_id) if u.node_id in primary_graph else set()
        ancestors = nx.ancestors(primary_graph, u.node_id) if u.node_id in primary_graph else set()
        invalid_targets = descendants | ancestors | {u.node_id}

        for v in nodes:
            if v.node_id in invalid_targets:
                continue
            if (u.node_id, v.node_id) in gold_edges:
                continue

            features = compute_structural_features(u, v, primary_graph, document.text)
            negative_candidates.append(
                SecondaryEdgeCandidate(
                    source_id=u.node_id,
                    target_id=v.node_id,
                    source_text=u.text,
                    target_text=v.text,
                    source_char_span=u.char_span,
                    target_char_span=v.char_span,
                    structural_features=features,
                    is_gold_edge=False,
                    gold_relation=None,
                    gold_concept=None,
                )
            )

    # Subsample negatives to maintain target ratio (or keep all for comprehensive evaluation)
    max_negs = int(max(positive_count * negative_ratio, 20))
    if len(negative_candidates) > max_negs:
        # Sort negatives by proximity/hop distance so model learns hard negatives
        negative_candidates.sort(key=lambda c: c.structural_features[2])  # hop_dist
        negative_candidates = negative_candidates[:max_negs]

    candidates.extend(negative_candidates)
    return candidates


def load_gum_erst_corpus(data_dir: Path | str) -> list[SecondaryEdgeCandidate]:
    """Load all .rs4 files in directory and extract eRST training candidates."""
    path = Path(data_dir)
    if not path.exists():
        return []

    all_candidates: list[SecondaryEdgeCandidate] = []
    rs4_files = list(path.glob("**/*.rs4"))

    for rs4_file in rs4_files:
        try:
            rs4_doc = RS4Reader.read_file(rs4_file)
            doc, analysis = rs4_to_document_and_analysis(rs4_doc, document_id=rs4_file.stem)
            cands = extract_eRST_candidates_from_document(doc, analysis)
            all_candidates.extend(cands)
        except (OSError, ValueError, RuntimeError, KeyError):
            # Skip malformed files gracefully
            continue

    return all_candidates


class GUMSecondaryEdgeDataset(Dataset):
    """PyTorch Dataset for fine-tuning NeuralSecondaryEdgeScorer with boundary-aware subwords."""

    def __init__(
        self,
        candidates: Sequence[SecondaryEdgeCandidate],
        tokenizer: Any,
        max_length: int = 128,
    ) -> None:
        self.candidates = list(candidates)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.candidates)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        cand = self.candidates[idx]

        # Tokenize source span and target span
        src_enc = self.tokenizer(
            cand.source_text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        tgt_enc = self.tokenizer(
            cand.target_text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        edge_label = 1.0 if cand.is_gold_edge else 0.0
        rel_label = CONCEPT_TO_IDX.get(cand.gold_concept or "", -100) if cand.is_gold_edge else -100

        return {
            "src_input_ids": src_enc["input_ids"].squeeze(0),
            "src_attention_mask": src_enc["attention_mask"].squeeze(0),
            "tgt_input_ids": tgt_enc["input_ids"].squeeze(0),
            "tgt_attention_mask": tgt_enc["attention_mask"].squeeze(0),
            "struct_features": torch.tensor(cand.structural_features, dtype=torch.float),
            "edge_label": torch.tensor(edge_label, dtype=torch.float),
            "rel_label": torch.tensor(rel_label, dtype=torch.long),
        }
