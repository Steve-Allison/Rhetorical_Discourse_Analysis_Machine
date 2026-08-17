"""Governed enums for RST and eRST representations."""

from enum import StrEnum


class OutputFormalismEnum(StrEnum):
    """Output discourse formalism."""

    RST_TREE = "rst_tree"
    ERST_GRAPH = "erst_graph"


class InputModeEnum(StrEnum):
    """Input representation fidelity mode."""

    RAW_TEXT = "raw_text"
    TEXT_WITH_EDUS = "text_with_edus"
    TEXT_WITH_TOKENS_AND_EDUS = "text_with_tokens_and_edus"
    DOCUMENT_NATIVE = "document_native"


class InputFidelityEnum(StrEnum):
    """Fidelity of input reconstruction."""

    LOSSLESS = "lossless"
    ALIGNED = "aligned"
    RECONSTRUCTED = "reconstructed"
    UNKNOWN = "unknown"


class NodeKindEnum(StrEnum):
    """Discourse tree or graph node kind."""

    EDU = "edu"
    SPAN = "span"
    MULTINUCLEAR_GROUP = "multinuclear_group"
    ROOT = "root"


class EdgeKindEnum(StrEnum):
    """Discourse relation edge kind."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


class NuclearityPatternEnum(StrEnum):
    """Nuclearity pattern for primary relation edges."""

    NS = "NS"
    SN = "SN"
    NN = "NN"


class NuclearityRoleEnum(StrEnum):
    """Role of an endpoint in a rhetorical relation."""

    NUCLEUS = "nucleus"
    SATELLITE = "satellite"


class RelationStructureEnum(StrEnum):
    """Structural type of rhetorical relation."""

    MONONUCLEAR = "mononuclear"
    MULTINUCLEAR = "multinuclear"
    STRUCTURAL_PSEUDO = "structural_pseudo"


class RelationSchemeEnum(StrEnum):
    """Rhetorical relation annotation or model scheme."""

    RST_DT_FINE = "rst_dt_fine"
    RST_DT_COARSE_18 = "rst_dt_coarse_18"
    GUM_ERST_FINE = "gum_erst_fine"
    GUM_ERST_COARSE = "gum_erst_coarse"
    DMRST_RSTDT_MODEL_42 = "dmrst_rstdt_model_42"
    DMRST_GUM_MODEL_27 = "dmrst_gum_model_27"
    RS4_STRUCTURAL = "rs4_structural"


class MappingKindEnum(StrEnum):
    """Ontology mapping relationship kind."""

    EXACT = "exact"
    ALIAS = "alias"
    BROADER_PROJECTION = "broader_projection"
    NARROWER_PROJECTION = "narrower_projection"
    MODEL_ENCODING = "model_encoding"
    STRUCTURAL = "structural"
    DEPRECATED = "deprecated"
    UNSUPPORTED = "unsupported"


class AnnotationStatusEnum(StrEnum):
    """Status or origin of an annotation."""

    GOLD = "gold"
    SILVER = "silver"
    PREDICTED = "predicted"
    DERIVED = "derived"
    IMPORTED = "imported"
    UNKNOWN = "unknown"


class ConfidenceKindEnum(StrEnum):
    """Kind of confidence metric."""

    PROBABILITY = "probability"
    CALIBRATED_PROBABILITY = "calibrated_probability"
    MARGIN = "margin"
    NOT_AVAILABLE = "not_available"


class DeviceEnum(StrEnum):
    """Target execution device."""

    AUTO = "auto"
    CPU = "cpu"
    MPS = "mps"
    CUDA = "cuda"


class CapabilityStatusEnum(StrEnum):
    """Lifecycle capability status."""

    DECLARED = "declared"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    RELEASED = "released"
    DEPRECATED = "deprecated"


class FailureCodeEnum(StrEnum):
    """Structured failure or degradation code."""

    INVALID_INPUT = "invalid_input"
    ALIGNMENT_FAILED = "alignment_failed"
    UNSUPPORTED_SCHEME = "unsupported_scheme"
    UNMAPPED_LABEL = "unmapped_label"
    MODEL_UNAVAILABLE = "model_unavailable"
    RESOURCE_LIMIT = "resource_limit"
    SCORER_MISMATCH = "scorer_mismatch"
    ONTOLOGY_MISMATCH = "ontology_mismatch"
