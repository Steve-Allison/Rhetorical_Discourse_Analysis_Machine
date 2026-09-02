"""Ontology lock loader and adapter interface."""

from rdam.rst.ontology.adapter import (
    OntologyAdapter,
    ResolvedRelation,
)
from rdam.rst.ontology.loader import (
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
