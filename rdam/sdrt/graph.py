"""Native Segmented Discourse Representation Structure graph contracts.

SDRT is a graph theory, not a tree encoding.  EDUs and CDUs remain distinct nodes;
relations retain their coordinating/subordinating class; and a deterministic validator
checks references, graph structure, and the right frontier before a proposal is accepted.
"""

from collections.abc import Iterable
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from rdam._strict import JsonValue

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type UnitId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$")]


class GraphError(ValueError):
    """A proposed structure is not a valid native SDRS graph."""


class RelationStructure(StrEnum):
    """The theory-defining structural class of an SDRT relation."""

    COORDINATING = "coordinating"
    SUBORDINATING = "subordinating"


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ElementaryDiscourseUnit(_ClosedModel):
    """One elementary discourse unit anchored to an exact source slice."""

    unit_id: UnitId
    text: NonEmpty
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def positive_span(self) -> Self:
        if self.end <= self.start:
            raise GraphError("an EDU end must be greater than its start")
        return self

    def to_payload(self) -> dict[str, JsonValue]:
        return {"unit_id": self.unit_id, "text": self.text, "start": self.start, "end": self.end}


class ComplexDiscourseUnit(_ClosedModel):
    """A complex discourse unit with explicit, recursively resolvable membership."""

    unit_id: UnitId
    members: list[UnitId] = Field(min_length=2)

    @model_validator(mode="after")
    def unique_non_self_members(self) -> Self:
        if len(self.members) != len(set(self.members)):
            raise GraphError(f"CDU {self.unit_id!r} contains duplicate members")
        if self.unit_id in self.members:
            raise GraphError(f"CDU {self.unit_id!r} contains itself")
        return self

    def to_payload(self) -> dict[str, JsonValue]:
        return {"unit_id": self.unit_id, "members": list(self.members)}


class SdrtRelation(_ClosedModel):
    """One labelled, directed SDRT relation between discourse units."""

    relation_id: UnitId
    source_id: UnitId
    target_id: UnitId
    label: NonEmpty
    structural_type: RelationStructure

    @model_validator(mode="after")
    def distinct_endpoints(self) -> Self:
        if self.source_id == self.target_id:
            raise GraphError(f"relation {self.relation_id!r} is self-referential")
        return self

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
            "structural_type": self.structural_type.value,
        }


def _has_cycle(adjacency: dict[str, set[str]]) -> bool:
    state: dict[str, int] = {}
    for root in adjacency:
        if state.get(root) == 2:
            continue
        pending: list[tuple[str, bool]] = [(root, False)]
        while pending:
            node, expanded = pending.pop()
            if expanded:
                state[node] = 2
                continue
            current_state = state.get(node, 0)
            if current_state == 1:
                return True
            if current_state == 2:
                continue
            state[node] = 1
            pending.append((node, True))
            pending.extend((target, False) for target in adjacency.get(node, ()))
    return False


def _elementary_members(cdu_members: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    """Resolve nested CDU membership once, without recursion."""

    resolved: dict[str, frozenset[str]] = {}
    for root in cdu_members:
        if root in resolved:
            continue
        pending: list[tuple[str, bool]] = [(root, False)]
        while pending:
            unit_id, expanded = pending.pop()
            if unit_id in resolved:
                continue
            nested = cdu_members.get(unit_id)
            if nested is None:
                resolved[unit_id] = frozenset((unit_id,))
                continue
            if expanded:
                resolved[unit_id] = frozenset().union(*(resolved[member] for member in nested))
                continue
            pending.append((unit_id, True))
            pending.extend((member, False) for member in nested if member not in resolved)
    return {cdu_id: resolved[cdu_id] for cdu_id in cdu_members}


def _connected(nodes: set[str], edges: Iterable[tuple[str, str]]) -> bool:
    if not nodes:
        return True
    neighbours = {node: set[str]() for node in nodes}
    for left, right in edges:
        neighbours[left].add(right)
        neighbours[right].add(left)
    reached: set[str] = set()
    pending = [next(iter(nodes))]
    while pending:
        node = pending.pop()
        if node in reached:
            continue
        reached.add(node)
        pending.extend(neighbours[node] - reached)
    return reached == nodes


class SdrtAnalysis(_ClosedModel):
    """A complete native SDRS graph proposed for one source."""

    edus: list[ElementaryDiscourseUnit] = Field(min_length=1)
    cdus: list[ComplexDiscourseUnit] = Field(default_factory=lambda: list[ComplexDiscourseUnit]())
    relations: list[SdrtRelation] = Field(default_factory=lambda: list[SdrtRelation]())

    @model_validator(mode="after")
    def valid_sdrs(self) -> Self:
        self._validate_identities_and_references()
        self._validate_edu_order()
        self._validate_acyclicity()
        self._validate_structural_classes()
        self._validate_connectivity()
        self._validate_right_frontier()
        return self

    def _validate_identities_and_references(self) -> None:
        unit_ids = [unit.unit_id for unit in (*self.edus, *self.cdus)]
        if len(unit_ids) != len(set(unit_ids)):
            raise GraphError("discourse unit ids must be unique across EDUs and CDUs")
        relation_ids = [relation.relation_id for relation in self.relations]
        if len(relation_ids) != len(set(relation_ids)):
            raise GraphError("relation ids must be unique")
        known = set(unit_ids)
        for cdu in self.cdus:
            for member in cdu.members:
                if member not in known:
                    raise GraphError(f"CDU {cdu.unit_id!r} references unknown discourse unit {member!r}")
        for relation in self.relations:
            for endpoint in (relation.source_id, relation.target_id):
                if endpoint not in known:
                    raise GraphError(
                        f"relation {relation.relation_id!r} references unknown discourse unit {endpoint!r}"
                    )

    def _validate_edu_order(self) -> None:
        for previous, current in zip(self.edus, self.edus[1:], strict=False):
            if current.start < previous.end:
                raise GraphError("EDU spans must be ordered and non-overlapping")

    def _validate_acyclicity(self) -> None:
        cdu_ids = {cdu.unit_id for cdu in self.cdus}
        membership = {cdu.unit_id: {member for member in cdu.members if member in cdu_ids} for cdu in self.cdus}
        if _has_cycle(membership):
            raise GraphError("CDU membership is cyclic")
        relation_graph: dict[str, set[str]] = {}
        for relation in self.relations:
            relation_graph.setdefault(relation.source_id, set()).add(relation.target_id)
            relation_graph.setdefault(relation.target_id, set())
        if _has_cycle(relation_graph):
            raise GraphError("SDRT relation graph is cyclic")

    def _validate_structural_classes(self) -> None:
        pair_classes: dict[tuple[str, str], set[RelationStructure]] = {}
        for relation in self.relations:
            pair_classes.setdefault((relation.source_id, relation.target_id), set()).add(relation.structural_type)
        if any(len(classes) > 1 for classes in pair_classes.values()):
            raise GraphError("one discourse-unit pair cannot carry both structural classes")

    def _validate_connectivity(self) -> None:
        nodes = {unit.unit_id for unit in (*self.edus, *self.cdus)}
        edges = [(cdu.unit_id, member) for cdu in self.cdus for member in cdu.members]
        edges.extend((relation.source_id, relation.target_id) for relation in self.relations)
        if not _connected(nodes, edges):
            raise GraphError("SDRS graph is disconnected")

    def _validate_right_frontier(self) -> None:
        if len(self.edus) == 1:
            return
        cdu_members = {cdu.unit_id: set(cdu.members) for cdu in self.cdus}
        elementary_members = _elementary_members(cdu_members)

        for index, current in enumerate(self.edus[1:], start=1):
            prior_edus = {unit.unit_id for unit in self.edus[:index]}
            completed_cdus = {cdu_id for cdu_id, members in elementary_members.items() if members <= prior_edus}
            introduced = prior_edus | completed_cdus
            frontier = {self.edus[index - 1].unit_id}
            changed = True
            while changed:
                changed = False
                for relation in self.relations:
                    if (
                        relation.structural_type is RelationStructure.SUBORDINATING
                        and relation.target_id in frontier
                        and relation.source_id in introduced
                        and relation.source_id not in frontier
                    ):
                        frontier.add(relation.source_id)
                        changed = True
                for cdu_id in completed_cdus:
                    if cdu_id not in frontier and cdu_members[cdu_id] & frontier:
                        frontier.add(cdu_id)
                        changed = True
            if not any(
                relation.target_id == current.unit_id and relation.source_id in frontier for relation in self.relations
            ):
                raise GraphError(f"EDU {current.unit_id!r} has no attachment from the SDRT right frontier")

    def validate_source(self, source: str) -> Self:
        """Prove every EDU quote against the submitted source without repairing offsets."""

        for unit in self.edus:
            if unit.end > len(source) or source[unit.start : unit.end] != unit.text:
                raise GraphError(f"EDU {unit.unit_id!r} text does not equal source slice")
        return self

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "edus": [unit.to_payload() for unit in self.edus],
            "cdus": [unit.to_payload() for unit in self.cdus],
            "relations": [relation.to_payload() for relation in self.relations],
            "edu_count": len(self.edus),
            "cdu_count": len(self.cdus),
            "relation_count": len(self.relations),
            "right_frontier_validated": True,
        }


__all__ = [
    "ComplexDiscourseUnit",
    "ElementaryDiscourseUnit",
    "GraphError",
    "NonEmpty",
    "RelationStructure",
    "SdrtAnalysis",
    "SdrtRelation",
    "UnitId",
]
