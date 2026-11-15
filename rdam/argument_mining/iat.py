"""Inference Anchoring Theory (Budzynska & Reed 2011) argument mining structures & DAG validation."""

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from rdam._grounding import GroundingCollector, QuoteRef
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type AduRole = Literal["major_claim", "claim", "premise"]
type IatRelationType = Literal["inference", "conflict", "rephrase"]


class ArgumentMiningError(ValueError):
    """Raised when an IAT proposal violates graph, enthymeme, or source-grounding invariants."""


class AduNodeProposal(StrictModel):
    id: NonEmpty
    role: AduRole
    proposition: NonEmpty
    speaker: NonEmpty = Field(default="author")
    evidence: QuoteRef


class IatRelationProposal(StrictModel):
    id: NonEmpty
    relation_type: IatRelationType
    source_id: NonEmpty
    target_id: NonEmpty

    @model_validator(mode="after")
    def distinct_endpoints(self) -> Self:
        if self.source_id == self.target_id:
            raise ValueError(f"IAT relation {self.id!r} cannot link {self.source_id!r} to itself")
        return self


class EnthymemeProposal(StrictModel):
    id: NonEmpty
    inference_relation_id: NonEmpty
    reconstructed_premise: NonEmpty


def has_cycle(node_ids: set[str], edges: list[tuple[str, str]]) -> bool:
    in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for src, dst in edges:
        adj[src].append(dst)
        in_degree[dst] += 1
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    visited = 0
    while queue:
        cur = queue.pop()
        visited += 1
        for nxt in adj[cur]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    return visited != len(node_ids)


class IatGraphProposal(StrictModel):
    adu_nodes: list[AduNodeProposal] = Field(default_factory=list[AduNodeProposal])
    relations: list[IatRelationProposal] = Field(default_factory=list[IatRelationProposal])
    enthymemes: list[EnthymemeProposal] = Field(default_factory=list[EnthymemeProposal])

    @model_validator(mode="after")
    def validate_iat_graph(self) -> Self:
        known_nodes: set[str] = set()
        for node in self.adu_nodes:
            if node.id in known_nodes:
                raise ValueError(f"Duplicate ADU node id: {node.id!r}")
            known_nodes.add(node.id)

        known_relations: dict[str, IatRelationProposal] = {}
        edge_triples: set[tuple[str, str, str]] = set()
        inference_edges: list[tuple[str, str]] = []
        for rel in self.relations:
            if rel.id in known_relations:
                raise ValueError(f"Duplicate IAT relation id: {rel.id!r}")
            if rel.source_id not in known_nodes:
                raise ValueError(f"Relation {rel.id!r} references unknown source_id {rel.source_id!r}")
            if rel.target_id not in known_nodes:
                raise ValueError(f"Relation {rel.id!r} references unknown target_id {rel.target_id!r}")
            triple = (rel.relation_type, rel.source_id, rel.target_id)
            if triple in edge_triples:
                raise ValueError(f"Duplicate IAT relation {triple!r}")
            edge_triples.add(triple)
            known_relations[rel.id] = rel
            if rel.relation_type == "inference":
                inference_edges.append((rel.source_id, rel.target_id))

        if inference_edges and has_cycle(known_nodes, inference_edges):
            raise ValueError("IAT inference relations must form an acyclic graph (DAG)")

        seen_enthymemes: set[str] = set()
        for enth in self.enthymemes:
            if enth.id in seen_enthymemes:
                raise ValueError(f"Duplicate enthymeme id: {enth.id!r}")
            seen_enthymemes.add(enth.id)
            target_rel = known_relations.get(enth.inference_relation_id)
            if target_rel is None or target_rel.relation_type != "inference":
                raise ValueError(
                    f"Enthymeme {enth.id!r} must reference an existing 'inference' relation, "
                    f"got {enth.inference_relation_id!r}."
                )
        return self

    def validate_source(self, source_text: str) -> dict[str, SourceEvidenceSpan]:
        collector = GroundingCollector(source_text)
        resolved: dict[str, SourceEvidenceSpan] = {}
        for idx, node in enumerate(self.adu_nodes):
            span = collector.resolve(node.evidence, field_name=f"adu_nodes[{idx}] ({node.id}).evidence")
            if span is not None:
                resolved[node.id] = span
        try:
            collector.raise_if_errors()
        except ValueError as exc:
            raise ArgumentMiningError(str(exc)) from exc
        return resolved


__all__ = [
    "AduNodeProposal",
    "AduRole",
    "ArgumentMiningError",
    "EnthymemeProposal",
    "IatGraphProposal",
    "IatRelationProposal",
    "IatRelationType",
    "has_cycle",
]
