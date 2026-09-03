"""Native Segmented Discourse Representation Theory analysis."""

from rdam.sdrt.graph import (
    ComplexDiscourseUnit,
    ElementaryDiscourseUnit,
    GraphError,
    RelationStructure,
    SdrtAnalysis,
    SdrtRelation,
)
from rdam.sdrt.provider import (
    CONTRACT_VERSION,
    FORMALISM_ID,
    INSTRUCTIONS,
    LICENCE,
    PROVIDER_ID_PREFIX,
    SdrtProvider,
    source_identity,
)

__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "ComplexDiscourseUnit",
    "ElementaryDiscourseUnit",
    "GraphError",
    "RelationStructure",
    "SdrtAnalysis",
    "SdrtProvider",
    "SdrtRelation",
    "source_identity",
]
