"""Persist graph text as references to the owning analysed document."""

from typing import Self

from pydantic import Field

from rdam.ingest.contracts.base import StrictContractModel
from rdam.rst.contracts.analysis import (
    DiscourseSignal, PrimaryRelationEdge, RstAnalysis, RstNode,
    SecondaryRelationEdge, TimingRecord,
)
from rdam.rst.contracts.document import ProvenanceRecord
from rdam.rst.contracts.enums import FailureCodeEnum, NodeKindEnum, OutputFormalismEnum


class StoredRstNode(StrictContractModel):
    """Node coordinates; retain distinct native text only when it differs from source."""

    node_id: int
    kind: NodeKindEnum
    edu_span: tuple[int, int]
    char_span: tuple[int, int]
    confidence: float | None = None
    text_override: str | None = Field(
        default=None,
        description="Null resolves text from the analysed document's half-open character range. "
        "A string preserves differing native text and is not an exact source quotation.",
    )

    @classmethod
    def capture(cls, node: RstNode, text: str) -> Self:
        start, end = node.char_span
        if start < 0 or end < start or end > len(text):
            raise ValueError("stored node range lies outside its analysed document")
        return cls(
            node_id=node.node_id, kind=node.kind, edu_span=node.edu_span,
            char_span=node.char_span, confidence=node.confidence,
            text_override=None if node.text == text[start:end] else node.text,
        )

    def resolve(self, text: str) -> RstNode:
        start, end = self.char_span
        if start < 0 or end < start or end > len(text):
            raise ValueError("stored node range lies outside its analysed document")
        if self.text_override == text[start:end]:
            raise ValueError("stored node text redundantly repeats its source range")
        return RstNode(
            node_id=self.node_id, kind=self.kind, edu_span=self.edu_span,
            char_span=self.char_span, confidence=self.confidence,
            text=text[start:end] if self.text_override is None else self.text_override,
        )


class StoredRstGraph(StrictContractModel):
    """Graph topology and metadata with document-owned constituent text."""

    document_id: str
    formalism: OutputFormalismEnum
    nodes: tuple[StoredRstNode, ...]
    primary_edges: tuple[PrimaryRelationEdge, ...]
    secondary_edges: tuple[SecondaryRelationEdge, ...]
    signals: tuple[DiscourseSignal, ...]
    provenance: ProvenanceRecord
    timing: TimingRecord
    warnings: tuple[str, ...]
    failure_code: FailureCodeEnum | None

    @classmethod
    def capture(cls, graph: RstAnalysis, text: str) -> Self:
        return cls(
            document_id=graph.document_id, formalism=graph.formalism,
            nodes=tuple(StoredRstNode.capture(node, text) for node in graph.nodes),
            primary_edges=graph.primary_edges, secondary_edges=graph.secondary_edges,
            signals=graph.signals, provenance=graph.provenance, timing=graph.timing,
            warnings=graph.warnings, failure_code=graph.failure_code,
        )

    def resolve(self, text: str) -> RstAnalysis:
        return RstAnalysis(
            document_id=self.document_id, formalism=self.formalism,
            nodes=tuple(node.resolve(text) for node in self.nodes),
            primary_edges=self.primary_edges, secondary_edges=self.secondary_edges,
            signals=self.signals, provenance=self.provenance, timing=self.timing,
            warnings=self.warnings, failure_code=self.failure_code,
        )


__all__ = ["StoredRstGraph", "StoredRstNode"]
