"""Shared conversion from self-contained format projections to public contracts."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from isanlp_rst.contracts import (
    FormatRstAnalysis,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    ProvenanceRecord,
    RstAnalysis,
    RstNode,
)


class ProjectedEduLike(Protocol):
    """Structural contract shared by all format-native EDU wire objects."""

    @property
    def id(self) -> int: ...

    @property
    def text(self) -> str: ...

    @property
    def char_span(self) -> tuple[int, int]: ...

    @property
    def edu_span(self) -> tuple[int, int]: ...


class ProjectedRelationLike(ProjectedEduLike, Protocol):
    """Structural contract shared by all format-native relation wire objects."""

    @property
    def relation(self) -> str: ...

    @property
    def nuclearity(self) -> str: ...

    @property
    def left_id(self) -> int: ...

    @property
    def right_id(self) -> int: ...


@dataclass(frozen=True, slots=True)
class ProjectionTree[R: ProjectedRelationLike, E: ProjectedEduLike]:
    """Format-neutral wrapper around one projected document or table tree."""

    document_id: str
    relations: Sequence[R]
    edus: Sequence[E]


def projection_to_rst_analysis[R: ProjectedRelationLike, E: ProjectedEduLike](
    tree: ProjectionTree[R, E],
    *,
    producer: str,
    software_version: str,
    source_revision: str | None,
    model_id: str,
) -> RstAnalysis:
    """Convert one authoritative wire projection into a truthful analysis."""

    nodes = [
        RstNode(
            node_id=edu.id,
            kind=NodeKindEnum.EDU,
            edu_span=edu.edu_span,
            char_span=edu.char_span,
            text=edu.text,
        )
        for edu in tree.edus
    ]
    primary_edges: list[PrimaryRelationEdge] = []
    for relation in tree.relations:
        try:
            nuclearity = NuclearityPatternEnum(relation.nuclearity)
        except ValueError as exc:
            raise ValueError(
                f"Relation node {relation.id} has unsupported nuclearity {relation.nuclearity!r}"
            ) from exc
        nodes.append(
            RstNode(
                node_id=relation.id,
                kind=(NodeKindEnum.MULTINUCLEAR_GROUP if nuclearity is NuclearityPatternEnum.NN else NodeKindEnum.SPAN),
                edu_span=relation.edu_span,
                char_span=relation.char_span,
                text=relation.text,
            )
        )
        for child_id in (relation.left_id, relation.right_id):
            primary_edges.append(
                PrimaryRelationEdge(
                    edge_id=f"e_{relation.id}_{child_id}",
                    parent_id=relation.id,
                    child_id=child_id,
                    relation_raw=relation.relation,
                    relation_concept=relation.relation,
                    nuclearity=nuclearity,
                )
            )

    return RstAnalysis(
        document_id=tree.document_id,
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=tuple(nodes),
        primary_edges=tuple(primary_edges),
        provenance=ProvenanceRecord(
            producer=producer,
            software_version=software_version,
            source_revision=source_revision,
            model_id=model_id,
        ),
    )


def projection_to_format_analysis[
    R: ProjectedRelationLike,
    E: ProjectedEduLike,
](
    document_tree: ProjectionTree[R, E],
    table_trees: Mapping[str, ProjectionTree[R, E]],
    *,
    refs_of_edu: Callable[[E], tuple[str, ...]],
    producer: str,
    software_version: str,
    source_revision: str | None,
    model_id: str,
) -> FormatRstAnalysis:
    """Convert document/table projections through the single analysis path."""

    document_analysis = projection_to_rst_analysis(
        document_tree,
        producer=producer,
        software_version=software_version,
        source_revision=source_revision,
        model_id=model_id,
    )
    table_analyses = {
        table_id: projection_to_rst_analysis(
            tree,
            producer=producer,
            software_version=software_version,
            source_revision=source_revision,
            model_id=model_id,
        )
        for table_id, tree in table_trees.items()
    }
    node_map = {ref: edu.id for edu in document_tree.edus for ref in refs_of_edu(edu)}
    return FormatRstAnalysis(
        document_analysis=document_analysis,
        table_analyses=table_analyses,
        node_map=node_map,
    )


__all__ = [
    "ProjectedEduLike",
    "ProjectedRelationLike",
    "ProjectionTree",
    "projection_to_format_analysis",
    "projection_to_rst_analysis",
]
