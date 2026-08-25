"""RS4 XML processing, eRST data structures, and converters."""

from isanlp_rst.erst.converter import (
    analysis_to_rs4,
    du_to_analysis,
    rs4_to_document_and_analysis,
)
from isanlp_rst.erst.candidates import (
    CandidateMode,
    RelationCompatibilityProfile,
    SecondaryEdgeCandidate,
    compute_structural_features,
    generate_secondary_edge_candidates,
    iter_candidate_batches,
    iter_secondary_edge_candidates,
)
from isanlp_rst.erst.checkpoint import (
    ErstCapabilityError,
    ErstCheckpointError,
    LoadedErstCheckpoint,
    load_erst_checkpoint_bundle,
    validate_erst_checkpoint_bundle,
    verify_erst_checkpoint_test_vector,
)
from isanlp_rst.erst.decoder import DecodedErstEdges, ErstSecondaryEdgeDecoder
from isanlp_rst.erst.neural_scorer import (
    AttentionPooling,
    BoundaryAwareSpanEncoder,
    NeuralSecondaryEdgeScorer,
)
from isanlp_rst.erst.relations import resolve_gum_relation_concept
from isanlp_rst.erst.rs4 import (
    RS4Document,
    RS4Group,
    RS4Reader,
    RS4SecEdge,
    RS4Segment,
    RS4Signal,
    RS4Writer,
)
from isanlp_rst.erst.signals import (
    DEFAULT_SIGNAL_PATTERNS,
    RuleBasedSignalDetector,
    SignalDetectionResult,
    SignalPattern,
)

__all__ = [
    "AttentionPooling",
    "BoundaryAwareSpanEncoder",
    "CandidateMode",
    "DEFAULT_SIGNAL_PATTERNS",
    "DecodedErstEdges",
    "ErstSecondaryEdgeDecoder",
    "ErstCapabilityError",
    "ErstCheckpointError",
    "LoadedErstCheckpoint",
    "NeuralSecondaryEdgeScorer",
    "RS4Document",
    "RS4Group",
    "RS4Reader",
    "RS4SecEdge",
    "RS4Segment",
    "RS4Signal",
    "RS4Writer",
    "RelationCompatibilityProfile",
    "RuleBasedSignalDetector",
    "SecondaryEdgeCandidate",
    "SignalDetectionResult",
    "SignalPattern",
    "analysis_to_rs4",
    "compute_structural_features",
    "du_to_analysis",
    "generate_secondary_edge_candidates",
    "iter_candidate_batches",
    "iter_secondary_edge_candidates",
    "load_erst_checkpoint_bundle",
    "rs4_to_document_and_analysis",
    "resolve_gum_relation_concept",
    "validate_erst_checkpoint_bundle",
    "verify_erst_checkpoint_test_vector",
]
