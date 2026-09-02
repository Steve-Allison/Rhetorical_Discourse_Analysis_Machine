from dataclasses import dataclass

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts.analysis import RstAnalysis
from rdam.rst.contracts.document import DocumentToken, Edu, TextSpan


class ParserInputLimitError(ValueError):
    """The exact inference substrate exceeds a declared parser limit."""


@dataclass(frozen=True, slots=True)
class ParsedRstTreeSpan:
    """A constituent span in the decoded RST discourse tree."""

    start: int
    end: int
    split: int
    nuclearity: str
    relation: str
    score: float


@dataclass(frozen=True, slots=True)
class ParsedRstTreeEvidence:
    """Bounded provider scores for one selected constituent decision."""

    span: ParsedRstTreeSpan
    split_candidates: tuple[int, ...]
    split_logits: tuple[float, ...]
    nuclearity_logits: tuple[float, ...]
    relation_logits: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PredictorAnalysisTrace:
    """Bounded exact substrate and selected-decision evidence from inference."""

    root_unit: DiscourseUnit
    analysis: RstAnalysis
    tokens: tuple[DocumentToken, ...]
    edus: tuple[Edu, ...]
    sentence_boundaries: tuple[TextSpan, ...]
    paragraph_boundaries: tuple[TextSpan, ...]
    structure_decisions: tuple[ParsedRstTreeEvidence, ...]
    segmentation_source: str
    relation_inventory: tuple[str, ...]
