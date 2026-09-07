"""Normalize RS4 primary trees for binary attachment evaluation.

Expand EDU parents into constituents, collapse unary structural groups, and
prefer right branching while keeping a nucleus in every intermediate group.
Thus S N S becomes S (N S), whereas N S S becomes (N S) S; an S S attachment
would invent a nucleus. Multinuclear groups associate to the right. Secondary
edges and signals remain on the original RS4 analysis, not on this projection.
"""

from dataclasses import dataclass

from rdam.rst.contracts import (
    NodeKindEnum, NuclearityPatternEnum, OutputFormalismEnum,
    PrimaryRelationEdge, RstAnalysis, RstDocument, RstNode,
)
from workbench.erst.converter import rs4_to_document_and_analysis
from workbench.erst.rs4 import RS4Document, RS4Group, RS4Segment


@dataclass(frozen=True)
class _Part:
    node: RstNode
    nucleus: bool
    relation: str


def binarize_rs4(rs4: RS4Document, *, document_id: str) -> tuple[RstDocument, RstAnalysis]:
    """Return a source-aligned primary projection without mutating annotations."""
    units: dict[int, RS4Segment | RS4Group] = {}
    for unit in (*rs4.segments, *rs4.groups):
        if unit.id in units:
            raise ValueError("RS4 normalization requires unique node IDs")
        units[unit.id] = unit
    if not rs4.segments:
        raise ValueError("RS4 normalization requires at least one EDU")
    children: dict[int, list[int]] = {}
    roots: list[int] = []
    for unit in units.values():
        if unit.parent is None:
            roots.append(unit.id)
        elif unit.parent not in units:
            raise ValueError("RS4 normalization found a missing parent")
        else:
            children.setdefault(unit.parent, []).append(unit.id)
    if len(roots) != 1:
        raise ValueError("RS4 normalization requires exactly one root")
    # Validate topology before invoking the existing source-coordinate importer.
    postorder: list[int] = []
    visited: set[int] = set()
    pending = [(roots[0], False)]
    while pending:
        node_id, exiting = pending.pop()
        if exiting:
            postorder.append(node_id)
            continue
        if node_id in visited:
            raise ValueError("RS4 normalization found a cycle or shared node")
        visited.add(node_id)
        pending.append((node_id, True))
        pending.extend((child, False) for child in children.get(node_id, ()))
    if visited != units.keys():
        raise ValueError("RS4 normalization found disconnected nodes")
    document, _ = rs4_to_document_and_analysis(rs4, document_id=document_id)
    edus = document.edus
    if edus is None:
        raise ValueError("RS4 source import did not preserve EDUs")
    nodes: list[RstNode] = []
    edges: list[PrimaryRelationEdge] = []
    projections: dict[int, RstNode] = {}
    leaves: dict[int, RstNode] = {}
    for segment, edu in zip(rs4.segments, edus, strict=True):
        leaf = RstNode(node_id=segment.id, kind=NodeKindEnum.EDU,
                       edu_span=(edu.edu_id, edu.edu_id), char_span=(edu.start, edu.end), text=edu.text)
        leaves[segment.id] = leaf
        nodes.append(leaf)
    next_id = max(units) + 1

    def attach(left: RstNode, right: RstNode, pattern: str, relation: str) -> RstNode:
        nonlocal next_id
        if left.edu_span[1] + 1 != right.edu_span[0]:
            raise ValueError("RS4 normalization cannot invent a contiguous yield for discontinuous children")
        if not relation or relation == "span":
            raise ValueError("RS4 attachment lacks a native rhetorical relation")
        node = RstNode(
            node_id=next_id,
            kind=NodeKindEnum.MULTINUCLEAR_GROUP if pattern == "NN" else NodeKindEnum.SPAN,
            edu_span=(left.edu_span[0], right.edu_span[1]),
            char_span=(left.char_span[0], right.char_span[1]),
            text=document.text[left.char_span[0]:right.char_span[1]],
        )
        next_id += 1
        nodes.append(node)
        for child, raw in ((left, "span" if pattern == "NS" else relation),
                           (right, "span" if pattern == "SN" else relation)):
            edges.append(PrimaryRelationEdge(
                edge_id=f"e_{node.node_id}_{child.node_id}", parent_id=node.node_id, child_id=child.node_id,
                relation_raw=raw, relation_concept=raw, nuclearity=NuclearityPatternEnum(pattern),
            ))
        return node

    for node_id in postorder:
        unit = units[node_id]
        parts: list[_Part] = []
        if isinstance(unit, RS4Segment):
            parts.append(_Part(leaves[node_id], True, "span"))
        elif unit.type not in ("span", "multinuc"):
            raise ValueError(f"Unsupported RS4 group type: {unit.type!r}")
        for child_id in children.get(node_id, ()):
            child = units[child_id]
            relation = child.relname
            if relation == "span":
                nucleus = True
            elif relation not in rs4.relations:
                raise ValueError(f"RS4 relation absent from header: {relation!r}")
            elif rs4.relations[relation] == "multinuc":
                nucleus = True
            elif rs4.relations[relation] == "rst":
                nucleus = False
            else:
                raise ValueError(f"Unsupported RS4 relation type: {rs4.relations[relation]!r}")
            parts.append(_Part(projections[child_id], nucleus, relation))
        parts.sort(key=lambda part: part.node.edu_span)
        nuclei = [part for part in parts if part.nucleus]
        if not nuclei:
            raise ValueError("RS4 group has no annotated nucleus")
        if len(nuclei) > 1 and (len({part.relation for part in nuclei}) != 1 or nuclei[0].relation == "span"):
            raise ValueError("RS4 multinuclear children must share a rhetorical relation")
        # Peel outer attachments, then assemble from the innermost nucleus.
        operations: list[tuple[_Part, str]] = []
        start, stop = 0, len(parts)
        while stop - start > 1:
            if not parts[start].nucleus:
                operations.append((parts[start], "SN"))
                start += 1
            elif not parts[stop - 1].nucleus:
                operations.append((parts[stop - 1], "NS"))
                stop -= 1
            else:
                operations.append((parts[start], "NN"))
                start += 1
        result = parts[start].node
        for part, pattern in reversed(operations):
            result = (attach(result, part.node, pattern, part.relation) if pattern == "NS"
                      else attach(part.node, result, pattern, part.relation))
        projections[node_id] = result
    expected = len(edus) - 1
    if len(edges) != 2 * expected or len(nodes) != 2 * len(edus) - 1:
        raise ValueError("RS4 normalization did not preserve the expected binary tree size")
    return document, RstAnalysis(document_id=document_id, formalism=OutputFormalismEnum.RST_TREE,
                                 nodes=tuple(nodes), primary_edges=tuple(edges))
