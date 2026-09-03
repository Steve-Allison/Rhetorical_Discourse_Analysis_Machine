"""Native Penn Discourse Treebank 3.0 analysis."""

from rdam.pdtb.relations import (
    PDTB3_SENSES,
    PdtbAnalysis,
    PdtbArgument,
    PdtbRelation,
    PdtbSense,
    RelationError,
    RelationType,
    TextSpan,
)
from rdam.pdtb.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    PdtbProvider,
    source_identity,
)

__all__ = [
    "PDTB3_SENSES",
    "PdtbAnalysis",
    "PdtbArgument",
    "PdtbProvider",
    "PdtbRelation",
    "PdtbSense",
    "RelationError",
    "RelationType",
    "TextSpan",
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "source_identity",
]
