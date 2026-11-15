"""Persisted Inference Anchoring Theory (IAT) argument mining output contract."""

from typing import Literal, Self

from pydantic import NonNegativeInt, model_validator

from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.argument_mining.iat import AduRole, IatRelationType, NonEmpty, has_cycle
from rdam.ingest.contracts.evidence import SourceEvidenceSpan


class AduNodeOutput(StrictModel):
    id: NonEmpty
    role: AduRole
    proposition: NonEmpty
    speaker: NonEmpty
    span: SourceEvidenceSpan


class IatRelationOutput(StrictModel):
    id: NonEmpty
    relation_type: IatRelationType
    source_id: NonEmpty
    target_id: NonEmpty


class EnthymemeOutput(StrictModel):
    id: NonEmpty
    inference_relation_id: NonEmpty
    reconstructed_premise: NonEmpty
    grounded: Literal[False] = False


class ArgumentMiningOutput(StrictModel):
    adu_nodes: tuple[AduNodeOutput, ...]
    relations: tuple[IatRelationOutput, ...]
    enthymemes: tuple[EnthymemeOutput, ...]
    major_claim_ids: tuple[NonEmpty, ...]
    node_count: NonNegativeInt
    relation_count: NonNegativeInt
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def verify_graph_invariants(self) -> Self:
        if self.node_count != len(self.adu_nodes) or self.relation_count != len(self.relations):
            raise ValueError("ArgumentMiningOutput counts must match adu_nodes and relations")
        known_nodes = {n.id for n in self.adu_nodes}
        if len(known_nodes) != len(self.adu_nodes):
            raise ValueError("Duplicate ADU node id")
        expected_major = tuple(n.id for n in self.adu_nodes if n.role == "major_claim")
        if self.major_claim_ids != expected_major:
            raise ValueError("major_claim_ids must reproduce adu_nodes with role='major_claim'")
        inf_edges: list[tuple[str, str]] = []
        rel_types: dict[str, IatRelationType] = {}
        for rel in self.relations:
            if rel.source_id not in known_nodes or rel.target_id not in known_nodes or rel.source_id == rel.target_id:
                raise ValueError(f"Invalid endpoints on IAT relation {rel.id!r}")
            rel_types[rel.id] = rel.relation_type
            if rel.relation_type == "inference":
                inf_edges.append((rel.source_id, rel.target_id))
        if inf_edges and has_cycle(known_nodes, inf_edges):
            raise ValueError("IAT inference subgraph contains a cycle")
        for enth in self.enthymemes:
            if rel_types.get(enth.inference_relation_id) != "inference":
                raise ValueError(f"Enthymeme {enth.id!r} does not target an inference relation")
        return self
