"""IBIS: a typed issue–position–argument structure under a constrained link grammar.

IBIS (Kunz & Rittel 1970) maps deliberation about a wicked problem into *issues*
(questions), *positions* (candidate answers), and *arguments* (pro or con a position).
It records what was said, not what is valid: nothing here judges an argument's strength.

The link grammar implemented is gIBIS's (Conklin & Begeman 1988), the typed form in
which each link relation is permitted only between specific node kinds:

| relation | from | to |
|---|---|---|
| ``responds_to`` | position | issue |
| ``supports`` | argument | position |
| ``objects_to`` | argument | position |
| ``generalizes`` | issue | issue |
| ``specializes`` | issue | issue |
| ``replaces`` | issue | issue |
| ``questions`` | issue | issue, position, argument |
| ``is_suggested_by`` | issue | issue, position, argument |

Structural rules beyond link typing: every position responds to exactly one issue;
every argument supports or objects to exactly one position; identifiers are unique;
self-links are not permitted. A structure that breaks a rule is not an IBIS structure and
is refused as malformed input; observations about a valid structure (issues with no
positions, positions with no arguments, isolated nodes) are the analysis.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Self, TypeGuard, cast
from pydantic import Field, model_validator
from rdam._strict import StrictModel


def _non_empty_string(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value)


def _node_kind(value: object) -> TypeGuard[NodeKind]:
    return isinstance(value, NodeKind)


def _relation(value: object) -> TypeGuard[Relation]:
    return isinstance(value, Relation)


class NodeKind(StrEnum):
    ISSUE = "issue"
    POSITION = "position"
    ARGUMENT = "argument"


class Relation(StrEnum):
    RESPONDS_TO = "responds_to"
    SUPPORTS = "supports"
    OBJECTS_TO = "objects_to"
    GENERALIZES = "generalizes"
    SPECIALIZES = "specializes"
    REPLACES = "replaces"
    QUESTIONS = "questions"
    IS_SUGGESTED_BY = "is_suggested_by"


GRAMMAR: Final[Mapping[Relation, tuple[NodeKind, frozenset[NodeKind]]]] = {
    Relation.RESPONDS_TO: (NodeKind.POSITION, frozenset({NodeKind.ISSUE})),
    Relation.SUPPORTS: (NodeKind.ARGUMENT, frozenset({NodeKind.POSITION})),
    Relation.OBJECTS_TO: (NodeKind.ARGUMENT, frozenset({NodeKind.POSITION})),
    Relation.GENERALIZES: (NodeKind.ISSUE, frozenset({NodeKind.ISSUE})),
    Relation.SPECIALIZES: (NodeKind.ISSUE, frozenset({NodeKind.ISSUE})),
    Relation.REPLACES: (NodeKind.ISSUE, frozenset({NodeKind.ISSUE})),
    Relation.QUESTIONS: (NodeKind.ISSUE, frozenset(NodeKind)),
    Relation.IS_SUGGESTED_BY: (NodeKind.ISSUE, frozenset(NodeKind)),
}
"""The permitted (from-kind, to-kinds) for every relation — the grammar itself."""

ATTACHMENT: Final[Mapping[NodeKind, frozenset[Relation]]] = {
    NodeKind.POSITION: frozenset({Relation.RESPONDS_TO}),
    NodeKind.ARGUMENT: frozenset({Relation.SUPPORTS, Relation.OBJECTS_TO}),
}
"""Kinds that must attach through exactly one outgoing link of these relations."""


type PositionEntry = dict[str, str | list[str]]
type IssueEntry = dict[str, str | list[str] | list[PositionEntry]]
type DeliberationMap = dict[str, list[IssueEntry] | list[str]]


class StructureError(ValueError):
    """The supplied structure is not an IBIS structure under the grammar."""


@dataclass(frozen=True, slots=True)
class Node:
    node_id: str
    kind: NodeKind
    text: str

    def __post_init__(self) -> None:
        if not _non_empty_string(self.node_id):
            raise StructureError("every node needs a non-empty string id")
        if not _node_kind(self.kind):
            raise StructureError(f"node {self.node_id!r} has an unknown kind: {self.kind!r}")
        if not _non_empty_string(self.text) or not self.text.strip():
            raise StructureError(f"node {self.node_id!r} needs non-empty text")


@dataclass(frozen=True, slots=True)
class Link:
    source: str
    relation: Relation
    target: str

    def __post_init__(self) -> None:
        if not _non_empty_string(self.source):
            raise StructureError("every link needs a non-empty source id")
        if not _non_empty_string(self.target):
            raise StructureError("every link needs a non-empty target id")
        if not _relation(self.relation):
            raise StructureError(f"unknown relation: {self.relation!r}")
        if self.source == self.target:
            raise StructureError(f"self-link on {self.source!r} is not permitted")


def _is_node(value: object) -> TypeGuard[Node]:
    return isinstance(value, Node)


def _is_link(value: object) -> TypeGuard[Link]:
    return isinstance(value, Link)


@dataclass(frozen=True, slots=True)
class IbisStructure:
    nodes: tuple[Node, ...]
    links: tuple[Link, ...]

    def __post_init__(self) -> None:
        """Enforce the complete grammar for every public construction path."""

        if not self.nodes:
            raise StructureError("nodes must be a non-empty tuple")
        if not all(_is_node(node) for node in self.nodes):
            raise StructureError("every native node must be a Node")
        kinds: dict[str, NodeKind] = {}
        for node in self.nodes:
            if node.node_id in kinds:
                raise StructureError(f"duplicate node id: {node.node_id!r}")
            kinds[node.node_id] = node.kind
        if not all(_is_link(link) for link in self.links):
            raise StructureError("every native link must be a Link")
        if len(set(self.links)) != len(self.links):
            raise StructureError("duplicate links are not permitted")
        for link in self.links:
            if link.source not in kinds or link.target not in kinds:
                raise StructureError(f"link references an unknown node: {link.source!r} -> {link.target!r}")
            from_kind, to_kinds = GRAMMAR[link.relation]
            if kinds[link.source] is not from_kind or kinds[link.target] not in to_kinds:
                raise StructureError(
                    f"{kinds[link.source].value} {link.source!r} --{link.relation.value}--> "
                    f"{kinds[link.target].value} {link.target!r} is not permitted by the grammar"
                )
        self._check_attachment()

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Self:
        """Validate ``{"nodes": [{"id", "kind", "text"}], "links": [{"from", "relation", "to"}]}`` against the grammar."""

        if set(payload) != {"nodes", "links"}:
            raise StructureError("structure requires exactly nodes and links")
        raw_nodes = payload.get("nodes")
        raw_links = payload.get("links")
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise StructureError("nodes must be a non-empty list")
        if not isinstance(raw_links, list):
            raise StructureError("links must be a list")
        nodes: list[Node] = []
        seen: set[str] = set()
        for item in cast(list[object], raw_nodes):
            if not isinstance(item, dict):
                raise StructureError("every node must be an object")
            node_payload = cast(dict[str, object], item)
            if set(node_payload) != {"id", "kind", "text"}:
                raise StructureError("node requires exactly id, kind and text")
            node_id, kind, text = node_payload.get("id"), node_payload.get("kind"), node_payload.get("text")
            if not isinstance(node_id, str) or not node_id:
                raise StructureError("every node needs a non-empty string id")
            if node_id in seen:
                raise StructureError(f"duplicate node id: {node_id!r}")
            if not isinstance(kind, str) or kind not in NodeKind.__members__.values():
                raise StructureError(f"node {node_id!r} has an unknown kind: {kind!r}")
            if not isinstance(text, str) or not text.strip():
                raise StructureError(f"node {node_id!r} needs non-empty text")
            seen.add(node_id)
            nodes.append(Node(node_id=node_id, kind=NodeKind(kind), text=text))
        kinds = {node.node_id: node.kind for node in nodes}
        links: list[Link] = []
        for item in cast(list[object], raw_links):
            if not isinstance(item, dict):
                raise StructureError("every link must be an object")
            link_payload = cast(dict[str, object], item)
            if set(link_payload) != {"from", "relation", "to"}:
                raise StructureError("link requires exactly from, relation and to")
            source, relation, target = (
                link_payload.get("from"),
                link_payload.get("relation"),
                link_payload.get("to"),
            )
            if not isinstance(source, str) or not isinstance(target, str) or not isinstance(relation, str):
                raise StructureError("every link needs string from, relation, and to")
            if source not in kinds or target not in kinds:
                raise StructureError(f"link references an unknown node: {source!r} -> {target!r}")
            if relation not in Relation.__members__.values():
                raise StructureError(f"unknown relation: {relation!r}")
            if source == target:
                raise StructureError(f"self-link on {source!r} is not permitted")
            typed = Relation(relation)
            from_kind, to_kinds = GRAMMAR[typed]
            if kinds[source] is not from_kind or kinds[target] not in to_kinds:
                raise StructureError(
                    f"{kinds[source].value} {source!r} --{typed.value}--> {kinds[target].value} {target!r} is not permitted by the grammar"
                )
            links.append(Link(source=source, relation=typed, target=target))
        return cls(nodes=tuple(nodes), links=tuple(links))

    def _check_attachment(self) -> None:
        outgoing: dict[str, list[Link]] = {node.node_id: [] for node in self.nodes}
        for link in self.links:
            outgoing[link.source].append(link)
        for node in self.nodes:
            required = ATTACHMENT.get(node.kind)
            if required is None:
                continue
            attachments = [link for link in outgoing[node.node_id] if link.relation in required]
            if len(attachments) != 1:
                expected = " or ".join(sorted(relation.value for relation in required))
                raise StructureError(
                    f"{node.kind.value} {node.node_id!r} must have exactly one {expected} link; found {len(attachments)}"
                )

    def node(self, node_id: str) -> Node:
        return next(node for node in self.nodes if node.node_id == node_id)

    def of_kind(self, kind: NodeKind) -> tuple[Node, ...]:
        return tuple(node for node in self.nodes if node.kind is kind)

    def links_from(self, node_id: str, relation: Relation | None = None) -> tuple[Link, ...]:
        return tuple(
            link for link in self.links if link.source == node_id and (relation is None or link.relation is relation)
        )

    def links_to(self, node_id: str, relation: Relation | None = None) -> tuple[Link, ...]:
        return tuple(
            link for link in self.links if link.target == node_id and (relation is None or link.relation is relation)
        )

    def to_payload(self) -> dict[str, list[dict[str, str]]]:
        return {
            "nodes": [{"id": node.node_id, "kind": node.kind.value, "text": node.text} for node in self.nodes],
            "links": [{"from": link.source, "relation": link.relation.value, "to": link.target} for link in self.links],
        }


def _ids(nodes: Iterable[Node]) -> list[str]:
    return [node.node_id for node in nodes]


class IbisInputNode(StrictModel):
    id: str = Field(min_length=1)
    kind: NodeKind
    text: str = Field(min_length=1)


class IbisInputLink(StrictModel):
    source: str = Field(alias="from", min_length=1)
    relation: Relation
    target: str = Field(alias="to", min_length=1)


class IbisInput(StrictModel):
    """Caller-authored JSON shape, validated by the actual gIBIS grammar."""

    nodes: tuple[IbisInputNode, ...] = Field(min_length=1)
    links: tuple[IbisInputLink, ...]

    @model_validator(mode="after")
    def valid_structure(self) -> Self:
        IbisStructure.from_payload(self.model_dump(mode="json", by_alias=True))
        return self


def deliberation_map(structure: IbisStructure) -> DeliberationMap:
    """What was said, organised: each issue with its positions and each position's pro and con arguments."""

    node_by_id = {node.node_id: node for node in structure.nodes}
    nodes_by_kind = {kind: tuple(node for node in structure.nodes if node.kind is kind) for kind in NodeKind}
    incoming: dict[tuple[str, Relation], list[Link]] = {}
    outgoing: dict[tuple[str, Relation], list[Link]] = {}
    for link in structure.links:
        incoming.setdefault((link.target, link.relation), []).append(link)
        outgoing.setdefault((link.source, link.relation), []).append(link)

    issues: list[IssueEntry] = []
    for issue in nodes_by_kind[NodeKind.ISSUE]:
        positions: list[PositionEntry] = []
        for link in incoming.get((issue.node_id, Relation.RESPONDS_TO), ()):
            position = node_by_id[link.source]
            positions.append(
                {
                    "id": position.node_id,
                    "supporting": [item.source for item in incoming.get((position.node_id, Relation.SUPPORTS), ())],
                    "objecting": [item.source for item in incoming.get((position.node_id, Relation.OBJECTS_TO), ())],
                }
            )
        issues.append(
            {
                "id": issue.node_id,
                "positions": positions,
                "raised_by": [link.target for link in outgoing.get((issue.node_id, Relation.IS_SUGGESTED_BY), ())],
                "questions": [link.target for link in outgoing.get((issue.node_id, Relation.QUESTIONS), ())],
                "generalizes": [link.target for link in outgoing.get((issue.node_id, Relation.GENERALIZES), ())],
                "specializes": [link.target for link in outgoing.get((issue.node_id, Relation.SPECIALIZES), ())],
                "replaces": [link.target for link in outgoing.get((issue.node_id, Relation.REPLACES), ())],
            }
        )
    linked = {link.source for link in structure.links} | {link.target for link in structure.links}
    return {
        "issues": issues,
        "issues_without_positions": [
            issue.node_id
            for issue in nodes_by_kind[NodeKind.ISSUE]
            if (issue.node_id, Relation.RESPONDS_TO) not in incoming
        ],
        "positions_without_arguments": [
            position.node_id
            for position in nodes_by_kind[NodeKind.POSITION]
            if (position.node_id, Relation.SUPPORTS) not in incoming
            and (position.node_id, Relation.OBJECTS_TO) not in incoming
        ],
        "isolated_nodes": _ids(node for node in structure.nodes if node.node_id not in linked),
    }


__all__ = [
    "ATTACHMENT",
    "GRAMMAR",
    "DeliberationMap",
    "IbisStructure",
    "IssueEntry",
    "Link",
    "Node",
    "NodeKind",
    "PositionEntry",
    "Relation",
    "StructureError",
    "deliberation_map",
]
