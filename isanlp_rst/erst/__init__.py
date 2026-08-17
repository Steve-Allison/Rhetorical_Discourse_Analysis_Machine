"""RS4 XML processing, eRST data structures, and converters."""

from isanlp_rst.erst.converter import (
    analysis_to_rs4,
    du_to_analysis,
    rs4_to_document_and_analysis,
)
from isanlp_rst.erst.dag_decoder import AcyclicDagDecoder
from isanlp_rst.erst.dataset import (
    COARSE_CONCEPTS,
    GUMSecondaryEdgeDataset,
    SecondaryEdgeCandidate,
    compute_structural_features,
    extract_eRST_candidates_from_document,
    load_gum_erst_corpus,
)
from isanlp_rst.erst.neural_scorer import (
    AttentionPooling,
    BoundaryAwareSpanEncoder,
    NeuralSecondaryEdgeScorer,
)
from isanlp_rst.erst.rs4 import (
    RS4Document,
    RS4Group,
    RS4Reader,
    RS4SecEdge,
    RS4Segment,
    RS4Signal,
    RS4Writer,
)

__all__ = [
    "AcyclicDagDecoder",
    "AttentionPooling",
    "BoundaryAwareSpanEncoder",
    "COARSE_CONCEPTS",
    "GUMSecondaryEdgeDataset",
    "NeuralSecondaryEdgeScorer",
    "RS4Document",
    "RS4Group",
    "RS4Reader",
    "RS4SecEdge",
    "RS4Segment",
    "RS4Signal",
    "RS4Writer",
    "SecondaryEdgeCandidate",
    "analysis_to_rs4",
    "compute_structural_features",
    "du_to_analysis",
    "extract_eRST_candidates_from_document",
    "load_gum_erst_corpus",
    "rs4_to_document_and_analysis",
]
