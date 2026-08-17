"""Discourse analysis result models and graph structures."""

from dataclasses import dataclass, field

from isanlp_rst.contracts.document import ProvenanceRecord
from isanlp_rst.contracts.enums import (
    AnnotationStatusEnum,
    FailureCodeEnum,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
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


@dataclass(frozen=True, slots=True)
class DiscourseSignal:
    """An anchored or unanchored discourse signal."""

    signal_id: str
    edge_id: str
    signal_type: str
    signal_subtype: str
    token_ids: tuple[int, ...] = ()
    status: AnnotationStatusEnum = AnnotationStatusEnum.PREDICTED
    confidence: float | None = None


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
        for node in self.nodes:
            if node.kind == NodeKindEnum.ROOT:
                return node
        if not self.nodes:
            return None

        # Find nodes that are never a child in primary_edges (topological roots)
        child_ids = {e.child_id for e in self.primary_edges}
        unparented = [n for n in self.nodes if n.node_id not in child_ids]
        if unparented:
            return max(
                unparented,
                key=lambda n: (n.char_span[1] - n.char_span[0], n.edu_span[1] - n.edu_span[0]),
            )

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
    table_analyses: dict[str, RstAnalysis] = field(default_factory=dict)
    node_map: dict[str, int] = field(default_factory=dict)
