"""RS4 XML processing, eRST data structures, and converters."""

from workbench.erst.converter import (
    analysis_to_rs4,
    du_to_analysis,
    rs4_to_document_and_analysis,
)
from workbench.erst.candidates import (
    CandidateMode,
    RelationCompatibilityProfile,
    SecondaryEdgeCandidate,
    compute_structural_features,
    generate_secondary_edge_candidates,
    iter_candidate_batches,
    iter_secondary_edge_candidates,
)
from workbench.erst.checkpoint import (
    ErstCapabilityError,
    ErstCheckpointError,
    LoadedErstCheckpoint,
    load_erst_checkpoint_bundle,
    validate_erst_checkpoint_bundle,
    verify_erst_checkpoint_test_vector,
)
from workbench.erst.decoder import DecodedErstEdges, ErstSecondaryEdgeDecoder
from workbench.erst.neural_scorer import (
    AttentionPooling,
    BoundaryAwareSpanEncoder,
    NeuralSecondaryEdgeScorer,
)
from workbench.erst.relations import resolve_gum_relation_concept
from workbench.erst.rs4 import (
    RS4Document,
    RS4Group,
    RS4Reader,
    RS4SecEdge,
    RS4Segment,
    RS4Signal,
    RS4Writer,
)
from workbench.erst.signals import (
    DEFAULT_SIGNAL_PATTERNS,
    RuleBasedSignalDetector,
    SignalDetectionResult,
    SignalPattern,
)

__all__ = [
    "DEFAULT_SIGNAL_PATTERNS",
    "AttentionPooling",
    "BoundaryAwareSpanEncoder",
    "CandidateMode",
    "DecodedErstEdges",
    "ErstCapabilityError",
    "ErstCheckpointError",
    "ErstSecondaryEdgeDecoder",
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
    "resolve_gum_relation_concept",
    "rs4_to_document_and_analysis",
    "validate_erst_checkpoint_bundle",
    "verify_erst_checkpoint_test_vector",
]
