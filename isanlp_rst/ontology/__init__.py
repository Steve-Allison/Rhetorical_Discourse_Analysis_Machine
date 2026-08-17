"""Ontology lock loader and adapter interface."""

from isanlp_rst.ontology.adapter import (
    OntologyAdapter,
    ResolvedRelation,
)
from isanlp_rst.ontology.loader import (
    ModelClassMapping,
    OntologyLockData,
    load_ontology_lock,
)

__all__ = [
    "ModelClassMapping",
    "OntologyAdapter",
    "OntologyLockData",
    "ResolvedRelation",
    "load_ontology_lock",
]
