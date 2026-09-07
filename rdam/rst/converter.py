"""Convert primary discourse trees to the shared typed analysis contract."""

from typing import Any
from rdam.rst.contracts import RstNode, PrimaryRelationEdge, RstAnalysis, ProvenanceRecord, NodeKindEnum, NuclearityPatternEnum, OutputFormalismEnum


def du_to_analysis(unit: Any, document_id: str = "doc") -> RstAnalysis:
    """Convert an isanlp.annotation_rst.DiscourseUnit tree into a typed RstAnalysis."""
    nodes: list[RstNode] = []
    primary_edges: list[PrimaryRelationEdge] = []

    def count_leaves(node: Any) -> int:
        if node is None:
            return 0
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        if left is None and right is None:
            return 1
        return count_leaves(left) + count_leaves(right)

    total_leaves = max(count_leaves(unit), 1)
    next_internal_id = total_leaves + 1
    curr_edu = 1

    def walk(node: Any) -> int:
        nonlocal curr_edu, next_internal_id
        node_id = getattr(node, "id", None)
        left = getattr(node, "left", None)
        right = getattr(node, "right", None)
        text = str(getattr(node, "text", "") or "")
        start_char = int(getattr(node, "start", 0) or 0)
        end_char = int(getattr(node, "end", len(text)) or len(text))
        proba = getattr(node, "proba", None)
        confidence = float(proba) if proba is not None else None

        if left is None and right is None:
            edu_idx = curr_edu
            curr_edu += 1
            assigned_id = int(node_id) if node_id is not None else edu_idx
            nodes.append(
                RstNode(
                    node_id=assigned_id,
                    kind=NodeKindEnum.EDU,
                    edu_span=(edu_idx, edu_idx),
                    char_span=(start_char, end_char),
                    text=text,
                    confidence=confidence,
                )
            )
            return assigned_id

        # Internal node
        node_rel = str(getattr(node, "relation", "") or "span")
        node_nuc = str(getattr(node, "nuclearity", "") or "NS")

        # Recurse children
        start_edu = curr_edu
        left_id = walk(left) if left is not None else None
        right_id = walk(right) if right is not None else None
        end_edu = max(curr_edu - 1, start_edu)

        if node_id is not None:
            assigned_id = int(node_id)
        else:
            assigned_id = next_internal_id
            next_internal_id += 1

        kind = NodeKindEnum.MULTINUCLEAR_GROUP if node_nuc == "NN" else NodeKindEnum.SPAN

        nodes.append(
            RstNode(
                node_id=assigned_id,
                kind=kind,
                edu_span=(start_edu, end_edu),
                char_span=(start_char, end_char),
                text=text,
                confidence=confidence,
            )
        )

        if left_id is not None:
            # NS: left is Nucleus (span), right is Satellite (node_rel)
            # SN: left is Satellite (node_rel), right is Nucleus (span)
            # NN: left is Nucleus (node_rel), right is Nucleus (node_rel)
            left_rel = "span" if node_nuc == "NS" else node_rel
            primary_edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{assigned_id}_{left_id}",
                    parent_id=assigned_id,
                    child_id=left_id,
                    relation_raw=left_rel,
                    relation_concept=left_rel,
                    nuclearity=NuclearityPatternEnum(node_nuc)
                    if node_nuc in NuclearityPatternEnum
                    else NuclearityPatternEnum.NS,
                )
            )

        if right_id is not None:
            right_rel = "span" if node_nuc == "SN" else node_rel
            primary_edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{assigned_id}_{right_id}",
                    parent_id=assigned_id,
                    child_id=right_id,
                    relation_raw=right_rel,
                    relation_concept=right_rel,
                    nuclearity=NuclearityPatternEnum(node_nuc)
                    if node_nuc in NuclearityPatternEnum
                    else NuclearityPatternEnum.NS,
                )
            )

        return assigned_id

    walk(unit)

    return RstAnalysis(
        document_id=document_id,
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=tuple(nodes),
        primary_edges=tuple(primary_edges),
        provenance=ProvenanceRecord(producer="du_converter"),
    )
