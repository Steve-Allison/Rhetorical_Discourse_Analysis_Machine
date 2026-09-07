from dataclasses import dataclass

from rdam.rst.annotation_rst import DiscourseUnit
from rdam.rst.contracts.analysis import RstAnalysis
from rdam.rst.contracts.document import DocumentToken, Edu, TextSpan
from rdam.rst.inference_evidence import NetworkStructureDecision


class ParserInputLimitError(ValueError):
    """The exact inference substrate exceeds a declared parser limit."""


@dataclass(frozen=True, slots=True)
class PredictorAnalysisTrace:
    """Bounded exact substrate and selected-decision evidence from inference."""

    root_unit: DiscourseUnit
    analysis: RstAnalysis
    tokens: tuple[DocumentToken, ...]
    edus: tuple[Edu, ...]
    sentence_boundaries: tuple[TextSpan, ...]
    paragraph_boundaries: tuple[TextSpan, ...]
    structure_decisions: tuple[NetworkStructureDecision, ...]
    segmentation_source: str
    relation_inventory: tuple[str, ...]
