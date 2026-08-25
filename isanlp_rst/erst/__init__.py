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
from isanlp_rst.erst.corpus import (
    CorpusLoadError,
    LoadedCorpusDocument,
    LoadedGumCorpus,
    load_gum_corpus_authority,
    load_gum_erst_corpus,
    load_gum_erst_corpus_with_receipt,
    parse_gum_corpus_authority,
)
from isanlp_rst.erst.checkpoint import (
    ErstCapabilityError,
    ErstCheckpointError,
    LoadedErstCheckpoint,
    load_erst_checkpoint_bundle,
    save_erst_checkpoint_bundle,
    validate_erst_checkpoint_bundle,
    verify_erst_checkpoint_test_vector,
)
from isanlp_rst.erst.dataset import (
    COARSE_CONCEPTS,
    GUMSecondaryEdgeDataset,
    extract_eRST_candidates_from_document,
)
from isanlp_rst.erst.decoder import DecodedErstEdges, ErstSecondaryEdgeDecoder
from isanlp_rst.erst.neural_scorer import (
    AttentionPooling,
    BoundaryAwareSpanEncoder,
    NeuralSecondaryEdgeScorer,
)
from isanlp_rst.erst.relations import (
    build_raw_relation_inventory,
    derive_raw_relation_inventory,
    resolve_gum_relation_concept,
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
from isanlp_rst.erst.sampling import (
    PartitionedCandidateSelection,
    candidate_identity_sha256,
    prepare_partition_candidates,
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
    "COARSE_CONCEPTS",
    "CandidateMode",
    "CorpusLoadError",
    "DEFAULT_SIGNAL_PATTERNS",
    "DecodedErstEdges",
    "GUMSecondaryEdgeDataset",
    "ErstSecondaryEdgeDecoder",
    "ErstCapabilityError",
    "ErstCheckpointError",
    "LoadedCorpusDocument",
    "LoadedGumCorpus",
    "LoadedErstCheckpoint",
    "NeuralSecondaryEdgeScorer",
    "PartitionedCandidateSelection",
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
    "build_raw_relation_inventory",
    "candidate_identity_sha256",
    "compute_structural_features",
    "du_to_analysis",
    "derive_raw_relation_inventory",
    "extract_eRST_candidates_from_document",
    "generate_secondary_edge_candidates",
    "iter_candidate_batches",
    "iter_secondary_edge_candidates",
    "load_gum_erst_corpus",
    "load_gum_erst_corpus_with_receipt",
    "load_gum_corpus_authority",
    "load_erst_checkpoint_bundle",
    "parse_gum_corpus_authority",
    "prepare_partition_candidates",
    "rs4_to_document_and_analysis",
    "resolve_gum_relation_concept",
    "save_erst_checkpoint_bundle",
    "validate_erst_checkpoint_bundle",
    "verify_erst_checkpoint_test_vector",
]
