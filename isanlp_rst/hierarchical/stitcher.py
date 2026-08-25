"""Hierarchical two-stage macro/micro section parsing and tree stitching for long documents."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from time import perf_counter

from isanlp_rst.contracts.analysis import (
    DiscourseSignal,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
    SecondaryRelationEdge,
    TimingRecord,
)
from isanlp_rst.contracts.document import DocumentToken, Edu, RstDocument, TextSpan
from isanlp_rst.contracts.enums import (
    FailureCodeEnum,
    NodeKindEnum,
    OutputFormalismEnum,
)
from isanlp_rst.parser import Parser


@dataclass(frozen=True, slots=True)
class SectionSlice:
    """A extracted section slice with coordinate offsets."""

    section_id: int
    char_span: tuple[int, int]
    text: str
    tokens: tuple[DocumentToken, ...]
    edus: tuple[Edu, ...] | None


class HierarchicalSectionStitcher:
    """Two-stage macro/micro discourse parser and tree stitcher.

    1. Micro Stage: Parses each section/paragraph independently into high-density local trees.
    2. Macro Stage: Parses high-level discourse relations across section root nodes.
    3. Stitching Stage: Merges micro subtrees and macro relations into a single valid RstAnalysis.
    """

    def __init__(self, parser: Parser | None) -> None:
        self.parser = parser

    def detect_sections(
        self,
        document: RstDocument,
        custom_boundaries: Sequence[TextSpan] | None = None,
    ) -> list[SectionSlice]:
        """Detect and slice document into section components."""
        raw_text = document.text
        if not raw_text.strip():
            return []

        spans: list[tuple[int, int]] = []
        if custom_boundaries:
            spans = [(b.start, b.end) for b in custom_boundaries if b.end > b.start]
        elif document.paragraph_boundaries:
            spans = [(b.start, b.end) for b in document.paragraph_boundaries if b.end > b.start]
        else:
            # Detect double-newline paragraph blocks
            pos = 0
            for match in re.finditer(r"\n\s*\n+", raw_text):
                block_start = pos
                block_end = match.start()
                if block_end > block_start:
                    raw_slice = raw_text[block_start:block_end]
                    stripped = raw_slice.strip()
                    if stripped:
                        leading_ws = len(raw_slice) - len(raw_slice.lstrip())
                        actual_start = block_start + leading_ws
                        actual_end = actual_start + len(stripped)
                        spans.append((actual_start, actual_end))
                pos = match.end()

            if pos < len(raw_text):
                raw_slice = raw_text[pos:]
                stripped = raw_slice.strip()
                if stripped:
                    leading_ws = len(raw_slice) - len(raw_slice.lstrip())
                    actual_start = pos + leading_ws
                    actual_end = actual_start + len(stripped)
                    spans.append((actual_start, actual_end))

        if not spans:
            spans = [(0, len(raw_text))]

        sections: list[SectionSlice] = []
        for sec_idx, (start_char, end_char) in enumerate(spans):
            sec_text = raw_text[start_char:end_char]
            if not sec_text.strip():
                continue

            # Slice tokens
            sec_tokens = tuple(
                DocumentToken(
                    token_id=tok.token_id,
                    text=tok.text,
                    start=tok.start - start_char,
                    end=tok.end - start_char,
                    sentence_id=tok.sentence_id,
                    paragraph_id=sec_idx,
                )
                for tok in document.tokens
                if start_char <= tok.start and tok.end <= end_char
            )

            # Slice EDUs if present
            sec_edus: tuple[Edu, ...] | None = None
            if document.edus is not None:
                sec_edus = tuple(
                    Edu(
                        edu_id=edu.edu_id,
                        text=edu.text,
                        start=edu.start - start_char,
                        end=edu.end - start_char,
                        token_ids=edu.token_ids,
                        source_anchors=edu.source_anchors,
                    )
                    for edu in document.edus
                    if start_char <= edu.start and edu.end <= end_char
                )

            sections.append(
                SectionSlice(
                    section_id=sec_idx,
                    char_span=(start_char, end_char),
                    text=sec_text,
                    tokens=sec_tokens,
                    edus=sec_edus,
                )
            )

        return sections

    def parse_hierarchical(
        self,
        document: RstDocument,
        custom_boundaries: Sequence[TextSpan] | None = None,
        output: str = "rst_tree",
    ) -> RstAnalysis:
        """Execute two-stage hierarchical parsing over section boundaries."""
        if self.parser is None:
            raise RuntimeError("Hierarchical parsing requires a configured Parser instance")

        t_start = perf_counter()
        sections = self.detect_sections(document, custom_boundaries=custom_boundaries)

        if not sections:
            # Empty document early return
            return RstAnalysis(
                document_id=document.document_id,
                formalism=OutputFormalismEnum(output),
                nodes=(),
                primary_edges=(),
                provenance=document.provenance,
                timing=TimingRecord(total_ms=(perf_counter() - t_start) * 1000),
                failure_code=FailureCodeEnum.INVALID_INPUT,
            )

        if len(sections) == 1:
            # Single section: parse directly
            return self.parser.parse_document(document, output=output)

        # 1. Micro-Stage: Parse each section
        micro_analyses: list[RstAnalysis] = []
        for sec in sections:
            sec_doc = RstDocument(
                document_id=f"{document.document_id}_sec_{sec.section_id}",
                text=sec.text,
                tokens=sec.tokens,
                edus=sec.edus,
                provenance=document.provenance,
            )
            sec_analysis = self.parser.parse_document(sec_doc, output="rst_tree")
            micro_analyses.append(sec_analysis)

        # 2. Macro-Stage: Parse macro relationships across section roots
        section_summary_texts: list[str] = []
        for sec, ana in zip(sections, micro_analyses, strict=True):
            section_summary_texts.append(nuclear_spine_text(ana, fallback=sec.text))

        macro_doc = RstDocument.from_edus(
            edus=section_summary_texts,
            document_id=f"{document.document_id}_macro",
            provenance=document.provenance,
        )
        macro_analysis = self.parser.parse_document(macro_doc, output="rst_tree")

        # 3. Stitching Stage: Merge micro subtrees and macro tree
        stitched_analysis = self.stitch_trees(
            parent_document=document,
            sections=sections,
            micro_analyses=micro_analyses,
            macro_analysis=macro_analysis,
            output_formalism=OutputFormalismEnum(output),
            total_timing_ms=(perf_counter() - t_start) * 1000,
        )

        return stitched_analysis

    def stitch_trees(
        self,
        parent_document: RstDocument,
        sections: list[SectionSlice],
        micro_analyses: list[RstAnalysis],
        macro_analysis: RstAnalysis,
        output_formalism: OutputFormalismEnum,
        total_timing_ms: float,
    ) -> RstAnalysis:
        """Stitch micro subtrees and macro relations into a single global RstAnalysis."""
        all_nodes: list[RstNode] = []
        all_primary_edges: list[PrimaryRelationEdge] = []
        all_secondary_edges: list[SecondaryRelationEdge] = []
        all_signals: list[DiscourseSignal] = []

        global_node_id = 1
        global_edu_id = 1
        edge_counter = 1
        sig_counter = 1

        # Track mapping from (section_idx, local_node_id) -> global_node_id
        # and section_idx -> global_root_node_id
        section_root_global_ids: list[int] = []

        for _sec_idx, (sec, ana) in enumerate(zip(sections, micro_analyses, strict=True)):
            sec_char_offset = sec.char_span[0]
            sec_edu_offset = global_edu_id - 1

            local_to_global_node_map: dict[int, int] = {}
            local_to_global_edge_map: dict[str, str] = {}
            local_edu_count = 0

            # 1. Re-index nodes in this micro-tree
            for node in ana.nodes:
                nid = global_node_id
                global_node_id += 1
                local_to_global_node_map[node.node_id] = nid

                start_edu = node.edu_span[0] + sec_edu_offset
                end_edu = node.edu_span[1] + sec_edu_offset
                start_char = node.char_span[0] + sec_char_offset
                end_char = node.char_span[1] + sec_char_offset

                if node.kind == NodeKindEnum.EDU:
                    local_edu_count += 1

                node_kind = NodeKindEnum.SPAN if node.kind == NodeKindEnum.ROOT else node.kind

                all_nodes.append(
                    RstNode(
                        node_id=nid,
                        kind=node_kind,
                        edu_span=(start_edu, end_edu),
                        char_span=(start_char, end_char),
                        text=node.text,
                        confidence=node.confidence,
                    )
                )

            # Record global ID of section root
            root = ana.root_node
            sec_root_gid = local_to_global_node_map.get(root.node_id) if root is not None else None
            if sec_root_gid is not None:
                section_root_global_ids.append(sec_root_gid)
            elif ana.nodes:
                section_root_global_ids.append(local_to_global_node_map[ana.nodes[-1].node_id])

            # 2. Re-index primary edges
            for edge in ana.primary_edges:
                p_gid = local_to_global_node_map.get(edge.parent_id)
                c_gid = local_to_global_node_map.get(edge.child_id)
                if p_gid is not None and c_gid is not None:
                    global_edge_id = f"e_{edge_counter}"
                    local_to_global_edge_map[edge.edge_id] = global_edge_id
                    all_primary_edges.append(
                        PrimaryRelationEdge(
                            edge_id=global_edge_id,
                            parent_id=p_gid,
                            child_id=c_gid,
                            relation_raw=edge.relation_raw,
                            relation_concept=edge.relation_concept,
                            nuclearity=edge.nuclearity,
                            confidence=edge.confidence,
                            calibrated=edge.calibrated,
                        )
                    )
                    edge_counter += 1

            # 3. Re-index secondary edges
            for sec_edge in ana.secondary_edges:
                s_gid = local_to_global_node_map.get(sec_edge.source_id)
                t_gid = local_to_global_node_map.get(sec_edge.target_id)
                if s_gid is not None and t_gid is not None:
                    global_edge_id = f"se_{len(all_secondary_edges) + 1}"
                    local_to_global_edge_map[sec_edge.edge_id] = global_edge_id
                    all_secondary_edges.append(
                        SecondaryRelationEdge(
                            edge_id=global_edge_id,
                            source_id=s_gid,
                            target_id=t_gid,
                            relation_raw=sec_edge.relation_raw,
                            relation_concept=sec_edge.relation_concept,
                            confidence=sec_edge.confidence,
                            calibrated=sec_edge.calibrated,
                        )
                    )

            # 4. Re-index signals
            for sig in ana.signals:
                all_signals.append(
                    DiscourseSignal(
                        signal_id=f"sig_{sig_counter}",
                        edge_id=local_to_global_edge_map.get(sig.edge_id) if sig.edge_id is not None else None,
                        signal_type=sig.signal_type,
                        signal_subtype=sig.signal_subtype,
                        token_ids=sig.token_ids,
                        char_spans=tuple(
                            (start + sec_char_offset, end + sec_char_offset) for start, end in sig.char_spans
                        ),
                        compatible_relations=sig.compatible_relations,
                        detector=sig.detector,
                        status=sig.status,
                        confidence=sig.confidence,
                    )
                )
                sig_counter += 1

            global_edu_id += local_edu_count

        # 5. Integrate Macro-Tree
        # In macro_analysis: leaf node with edu_span (k, k) corresponds to section k (0-indexed k-1)
        macro_node_map: dict[int, int] = {}
        for node in macro_analysis.nodes:
            if node.kind == NodeKindEnum.EDU:
                sec_idx = node.edu_span[0] - 1
                if 0 <= sec_idx < len(section_root_global_ids):
                    macro_node_map[node.node_id] = section_root_global_ids[sec_idx]
            else:
                # Macro non-leaf node: create new global node
                nid = global_node_id
                global_node_id += 1
                macro_node_map[node.node_id] = nid

                start_sec_idx = node.edu_span[0] - 1
                end_sec_idx = node.edu_span[1] - 1

                # Derive global EDU and Char spans from the constituent sections
                first_sec = sections[min(max(0, start_sec_idx), len(sections) - 1)]
                last_sec = sections[min(max(0, end_sec_idx), len(sections) - 1)]

                # Find EDU span of first and last section roots
                first_root_node = next(
                    (n for n in all_nodes if n.node_id == section_root_global_ids[start_sec_idx]), None
                )
                last_root_node = next((n for n in all_nodes if n.node_id == section_root_global_ids[end_sec_idx]), None)

                start_edu = first_root_node.edu_span[0] if first_root_node is not None else 1
                end_edu = last_root_node.edu_span[1] if last_root_node is not None else len(all_nodes)
                start_char = first_sec.char_span[0]
                end_char = last_sec.char_span[1]

                all_nodes.append(
                    RstNode(
                        node_id=nid,
                        kind=node.kind,
                        edu_span=(start_edu, end_edu),
                        char_span=(start_char, end_char),
                        text=parent_document.text[start_char:end_char],
                        confidence=node.confidence,
                    )
                )

        # 6. Add Macro Primary Edges
        for edge in macro_analysis.primary_edges:
            p_gid = macro_node_map.get(edge.parent_id)
            c_gid = macro_node_map.get(edge.child_id)
            if p_gid is not None and c_gid is not None:
                all_primary_edges.append(
                    PrimaryRelationEdge(
                        edge_id=f"e_{edge_counter}",
                        parent_id=p_gid,
                        child_id=c_gid,
                        relation_raw=edge.relation_raw,
                        relation_concept=edge.relation_concept,
                        nuclearity=edge.nuclearity,
                        confidence=edge.confidence,
                        calibrated=edge.calibrated,
                    )
                )
                edge_counter += 1

        return RstAnalysis(
            document_id=parent_document.document_id,
            formalism=output_formalism,
            nodes=tuple(all_nodes),
            primary_edges=tuple(all_primary_edges),
            secondary_edges=tuple(all_secondary_edges),
            signals=tuple(all_signals),
            provenance=parent_document.provenance,
            timing=TimingRecord(total_ms=total_timing_ms),
        )


def nuclear_spine_text(analysis: RstAnalysis, *, fallback: str) -> str:
    """Return exact source EDU text along the analysis root's nuclear spine."""

    root = analysis.root_node
    if root is None:
        text = fallback.strip()
        if not text:
            raise ValueError("macro representation requires non-empty source text")
        return text
    node_by_id = {node.node_id: node for node in analysis.nodes}
    edges_by_parent: dict[int, list[PrimaryRelationEdge]] = {}
    for edge in analysis.primary_edges:
        edges_by_parent.setdefault(edge.parent_id, []).append(edge)

    def visit(node_id: int, ancestors: frozenset[int]) -> tuple[str, ...]:
        if node_id in ancestors:
            raise ValueError("RST analysis contains a primary-edge cycle")
        node = node_by_id[node_id]
        children = sorted(
            edges_by_parent.get(node_id, ()),
            key=lambda edge: node_by_id[edge.child_id].edu_span,
        )
        if not children:
            text = node.text.strip()
            return (text,) if text else ()
        pattern = children[0].nuclearity.value
        selected = children
        if pattern == "NS":
            selected = children[:1]
        elif pattern == "SN":
            selected = children[-1:]
        return tuple(
            text
            for edge in selected
            for text in visit(edge.child_id, ancestors | {node_id})
        )

    pieces = visit(root.node_id, frozenset())
    representation = " ".join(piece for piece in pieces if piece)
    if not representation:
        representation = fallback.strip()
    if not representation:
        raise ValueError("macro representation requires non-empty nuclear source text")
    return representation


__all__ = ["HierarchicalSectionStitcher", "SectionSlice", "nuclear_spine_text"]
