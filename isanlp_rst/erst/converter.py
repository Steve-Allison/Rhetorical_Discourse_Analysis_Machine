"""Conversion utilities between RS4 DOM, DiscourseUnit, and typed contracts."""

from collections.abc import Mapping, Sequence
from typing import Any

from isanlp_rst.contracts.analysis import (
    DiscourseSignal,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
    SecondaryRelationEdge,
    TimingRecord,
)
from isanlp_rst.contracts.document import DocumentToken, Edu, ProvenanceRecord, RstDocument
from isanlp_rst.contracts.enums import (
    AnnotationStatusEnum,
    InputFidelityEnum,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
)
from isanlp_rst.erst.rs4 import RS4Document, RS4Group, RS4SecEdge, RS4Segment, RS4Signal


def rs4_to_document_and_analysis(
    rs4: RS4Document,
    document_id: str = "doc",
) -> tuple[RstDocument, RstAnalysis]:
    """Convert an RS4Document into an RstDocument and an RstAnalysis."""
    # 1. Build text and EDUs
    constructed_parts: list[str] = []
    edus: list[Edu] = []
    tokens: list[DocumentToken] = []
    curr_char = 0
    token_counter = 0

    seg_id_to_edu_id: dict[int, int] = {}
    for idx, seg in enumerate(rs4.segments):
        if idx > 0:
            constructed_parts.append(" ")
            curr_char += 1

        seg_start = curr_char
        constructed_parts.append(seg.text)
        curr_char += len(seg.text)
        seg_end = curr_char

        edu_id = idx + 1
        seg_id_to_edu_id[seg.id] = edu_id

        # Simple word tokenization for token anchoring
        seg_words = seg.text.split()
        seg_token_ids: list[int] = []
        word_search_pos = seg_start
        for w in seg_words:
            w_pos = seg.text.find(w, word_search_pos - seg_start)
            w_start = seg_start + w_pos
            w_end = w_start + len(w)
            token_id = token_counter
            token_counter += 1
            tokens.append(DocumentToken(token_id=token_id, text=w, start=w_start, end=w_end))
            seg_token_ids.append(token_id)
            word_search_pos = w_end

        edus.append(
            Edu(
                edu_id=edu_id,
                text=seg.text,
                start=seg_start,
                end=seg_end,
                token_ids=tuple(seg_token_ids),
                source_anchors=(str(seg.id),),
            )
        )

    full_text = "".join(constructed_parts)
    doc = RstDocument(
        document_id=document_id,
        text=full_text,
        tokens=tuple(tokens),
        edus=tuple(edus),
        sentence_boundaries=(),
        paragraph_boundaries=(),
        source=None,
        provenance=ProvenanceRecord(producer="rs4_importer"),
        fidelity=InputFidelityEnum.ALIGNED,
    )

    # 2. Build nodes and primary edges
    nodes: list[RstNode] = []
    primary_edges: list[PrimaryRelationEdge] = []

    # Map node id to children
    children_map: dict[int, list[int]] = {}
    node_relnames: dict[int, str] = {}

    for seg in rs4.segments:
        node_relnames[seg.id] = seg.relname
        if seg.parent is not None:
            children_map.setdefault(seg.parent, []).append(seg.id)

    for grp in rs4.groups:
        node_relnames[grp.id] = grp.relname
        if grp.parent is not None:
            children_map.setdefault(grp.parent, []).append(grp.id)

    # Calculate spans for all nodes
    node_edu_yields: dict[int, list[int]] = {}

    def get_edu_yield(node_id: int) -> list[int]:
        if node_id in node_edu_yields:
            return node_edu_yields[node_id]
        all_edus: list[int] = []
        if node_id in seg_id_to_edu_id:
            all_edus.append(seg_id_to_edu_id[node_id])
        children = children_map.get(node_id, [])
        for ch in children:
            all_edus.extend(get_edu_yield(ch))
        res = sorted(set(all_edus)) if all_edus else [1]
        node_edu_yields[node_id] = res
        return res

    for seg in rs4.segments:
        edu_num = seg_id_to_edu_id[seg.id]
        edu_obj = edus[edu_num - 1]
        nodes.append(
            RstNode(
                node_id=seg.id,
                kind=NodeKindEnum.EDU,
                edu_span=(edu_num, edu_num),
                char_span=(edu_obj.start, edu_obj.end),
                text=seg.text,
            )
        )

    for grp in rs4.groups:
        grp_edus = get_edu_yield(grp.id)
        start_edu = min(grp_edus) if grp_edus else 1
        end_edu = max(grp_edus) if grp_edus else 1
        char_start = edus[start_edu - 1].start if edus else 0
        char_end = edus[end_edu - 1].end if edus else 0
        grp_text = full_text[char_start:char_end]

        kind = NodeKindEnum.MULTINUCLEAR_GROUP if grp.type == "multinuc" else NodeKindEnum.SPAN
        nodes.append(
            RstNode(
                node_id=grp.id,
                kind=kind,
                edu_span=(start_edu, end_edu),
                char_span=(char_start, char_end),
                text=grp_text,
            )
        )

    # Determine primary edges
    for parent_id, children in children_map.items():
        for child_id in children:
            relname = node_relnames.get(child_id, "span")
            # Determine nuclearity
            parent_is_multinuc = any(g.id == parent_id and g.type == "multinuc" for g in rs4.groups)
            if parent_is_multinuc:
                nuclearity = NuclearityPatternEnum.NN
            elif relname == "span":
                nuclearity = NuclearityPatternEnum.SN
            else:
                nuclearity = NuclearityPatternEnum.NS

            primary_edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{parent_id}_{child_id}",
                    parent_id=parent_id,
                    child_id=child_id,
                    relation_raw=relname,
                    relation_concept=relname,
                    nuclearity=nuclearity,
                )
            )

    # 3. Secondary edges
    secondary_edges = [
        SecondaryRelationEdge(
            edge_id=sec.id,
            source_id=sec.source,
            target_id=sec.target,
            relation_raw=sec.relname,
            relation_concept=sec.relname,
        )
        for sec in rs4.secedges
    ]

    # 4. Signals (convert 1-based token strings from RS4 to internal 0-based token index tuples)
    signals = [
        DiscourseSignal(
            signal_id=f"sig_{idx + 1}",
            edge_id=str(sig.source),
            signal_type=sig.type,
            signal_subtype=sig.subtype,
            token_ids=tuple(t - 1 for t in sig.tokens if t > 0),
            status=AnnotationStatusEnum(sig.status)
            if sig.status in AnnotationStatusEnum
            else AnnotationStatusEnum.PREDICTED,
        )
        for idx, sig in enumerate(rs4.signals)
    ]

    formalism = OutputFormalismEnum.ERST_GRAPH if (secondary_edges or signals) else OutputFormalismEnum.RST_TREE

    analysis = RstAnalysis(
        document_id=document_id,
        formalism=formalism,
        nodes=tuple(nodes),
        primary_edges=tuple(primary_edges),
        secondary_edges=tuple(secondary_edges),
        signals=tuple(signals),
        provenance=ProvenanceRecord(producer="rs4_importer"),
        timing=TimingRecord(),
    )

    return doc, analysis


def analysis_to_rs4(
    document: RstDocument,
    analysis: RstAnalysis,
    relations_header: Mapping[str, str] | None = None,
    sigtypes_header: Mapping[str, Sequence[str]] | None = None,
) -> RS4Document:
    """Convert an RstDocument and RstAnalysis back into an RS4Document."""
    segments: list[RS4Segment] = []
    groups: list[RS4Group] = []

    # Map child_id to (parent_id, relname)
    child_to_parent: dict[int, tuple[int, str]] = {}
    for edge in analysis.primary_edges:
        child_to_parent[edge.child_id] = (edge.parent_id, edge.relation_raw)

    for node in analysis.nodes:
        parent_info = child_to_parent.get(node.node_id)
        parent_id = parent_info[0] if parent_info else None
        relname = parent_info[1] if parent_info else "span"

        if node.kind == NodeKindEnum.EDU:
            segments.append(
                RS4Segment(
                    id=node.node_id,
                    text=node.text,
                    parent=parent_id,
                    relname=relname,
                )
            )
        else:
            grp_type = "multinuc" if node.kind == NodeKindEnum.MULTINUCLEAR_GROUP else "span"
            groups.append(
                RS4Group(
                    id=node.node_id,
                    type=grp_type,
                    parent=parent_id,
                    relname=relname,
                )
            )

    secedges = [
        RS4SecEdge(
            id=sec.edge_id,
            source=sec.source_id,
            target=sec.target_id,
            relname=sec.relation_raw,
        )
        for sec in analysis.secondary_edges
    ]

    # Convert 0-based token index tuples back to 1-based RS4 token integers
    signals = [
        RS4Signal(
            source=sig.edge_id.split("_")[-1] if sig.edge_id.startswith("e_") else sig.edge_id,
            type=sig.signal_type,
            subtype=sig.signal_subtype,
            tokens=tuple(t + 1 for t in sig.token_ids),
            status=sig.status.value,
        )
        for sig in analysis.signals
    ]

    rels = dict(relations_header) if relations_header else {}
    sigs = {k: tuple(v) for k, v in sigtypes_header.items()} if sigtypes_header else {}

    return RS4Document(
        relations=rels,
        sigtypes=sigs,
        segments=tuple(segments),
        groups=tuple(groups),
        secedges=tuple(secedges),
        signals=tuple(signals),
    )


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

