"""Discourse analysis result models and graph structures."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rdam.rst.contracts.document import ProvenanceRecord
from rdam.rst.contracts.enums import (
    AnnotationStatusEnum,
    FailureCodeEnum,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    SignalDetectionMethod,
)


@dataclass(frozen=True, slots=True)
class RstNode:
    """A node in a discourse tree or graph."""

    node_id: int
    kind: NodeKindEnum
    edu_span: tuple[int, int]
    char_span: tuple[int, int]
    text: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        start_char, end_char = self.char_span
        if start_char < 0 or end_char < start_char:
            raise ValueError(f"Invalid character span {self.char_span} on node {self.node_id}")
        start_edu, end_edu = self.edu_span
        if start_edu < 1 or end_edu < start_edu:
            raise ValueError(f"Invalid EDU span {self.edu_span} on node {self.node_id}")


@dataclass(frozen=True, slots=True)
class PrimaryRelationEdge:
    """A directed primary rhetorical relation edge with nuclearity."""

    edge_id: str
    parent_id: int
    child_id: int
    relation_raw: str
    relation_concept: str
    nuclearity: NuclearityPatternEnum
    confidence: float | None = None
    calibrated: bool = False


@dataclass(frozen=True, slots=True)
class SecondaryRelationEdge:
    """A directed secondary rhetorical relation edge without nuclearity."""

    edge_id: str
    source_id: int
    target_id: int
    relation_raw: str
    relation_concept: str
    confidence: float | None = None
    calibrated: bool = False


class SignalDetectorProvenance(BaseModel):
    """Immutable identity of the detector or source that produced a signal."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    detector_id: str = Field(min_length=1)
    detector_version: str = Field(min_length=1)
    method: SignalDetectionMethod
    source_revision: str | None = None
    model_revision: str | None = None
    ruleset_digest: str | None = None


class DiscourseSignal(BaseModel):
    """Typed, anchored discourse signal; overlaps are explicitly permitted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    signal_id: str = Field(min_length=1)
    edge_id: str | None
    signal_type: str = Field(min_length=1)
    signal_subtype: str = Field(min_length=1)
    token_ids: tuple[int, ...] = ()
    char_spans: tuple[tuple[int, int], ...] = ()
    compatible_relations: tuple[str, ...] = ()
    detector: SignalDetectorProvenance
    sufficient: bool = True
    status: AnnotationStatusEnum = AnnotationStatusEnum.PREDICTED
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("token_ids")
    @classmethod
    def validate_token_ids(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        """Require unique non-negative token identifiers without reordering."""

        if any(token_id < 0 for token_id in value):
            raise ValueError("signal token IDs must be non-negative")
        if len(value) != len(set(value)):
            raise ValueError("signal token IDs must be unique")
        return value

    @field_validator("char_spans")
    @classmethod
    def validate_char_spans(cls, value: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
        """Require valid half-open anchors while retaining overlap and order."""

        for start, end in value:
            if start < 0 or end <= start:
                raise ValueError(f"invalid signal character span {(start, end)}")
        return value

    @field_validator("compatible_relations")
    @classmethod
    def validate_relations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Require non-empty, unique raw relation labels."""

        if any(not relation.strip() for relation in value):
            raise ValueError("compatible signal relations must be non-empty")
        if len(value) != len(set(value)):
            raise ValueError("compatible signal relations must be unique")
        return value


@dataclass(frozen=True, slots=True)
class TimingRecord:
    """Execution timing profile in milliseconds."""

    segmentation_ms: float = 0.0
    parsing_ms: float = 0.0
    completion_ms: float = 0.0
    total_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class RstAnalysis:
    """Complete discourse analysis result."""

    document_id: str
    formalism: OutputFormalismEnum
    nodes: tuple[RstNode, ...]
    primary_edges: tuple[PrimaryRelationEdge, ...]
    secondary_edges: tuple[SecondaryRelationEdge, ...] = ()
    signals: tuple[DiscourseSignal, ...] = ()
    provenance: ProvenanceRecord = field(default_factory=ProvenanceRecord)
    timing: TimingRecord = field(default_factory=TimingRecord)
    warnings: tuple[str, ...] = ()
    failure_code: FailureCodeEnum | None = None

    @property
    def root_node(self) -> RstNode | None:
        """Find the root node if present."""
        if not self.nodes:
            return None

        # Find nodes that are never a child in primary_edges (topological roots)
        child_ids = {e.child_id for e in self.primary_edges}
        unparented = [n for n in self.nodes if n.node_id not in child_ids]
        if unparented:
            # Prefer unparented node with kind == ROOT if present
            for n in unparented:
                if n.kind == NodeKindEnum.ROOT:
                    return n
            return max(
                unparented,
                key=lambda n: (n.char_span[1] - n.char_span[0], n.edu_span[1] - n.edu_span[0]),
            )

        for node in self.nodes:
            if node.kind == NodeKindEnum.ROOT:
                return node

        # Fallback: node with maximum character/edu span
        return max(
            self.nodes,
            key=lambda n: (n.char_span[1] - n.char_span[0], n.edu_span[1] - n.edu_span[0]),
        )

    def get_node(self, node_id: int) -> RstNode | None:
        """Look up a node by its ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None


@dataclass(frozen=True, slots=True)
class FormatRstAnalysis:
    """Composite analysis for structured documents (Docling, DocLang, Markdown)."""

    document_analysis: RstAnalysis
    table_analyses: Mapping[str, RstAnalysis] = field(default_factory=lambda: dict[str, RstAnalysis]())
    node_map: Mapping[str, int] = field(default_factory=lambda: dict[str, int]())

    def __post_init__(self) -> None:
        object.__setattr__(self, "table_analyses", MappingProxyType(dict(self.table_analyses)))
        object.__setattr__(self, "node_map", MappingProxyType(dict(self.node_map)))
