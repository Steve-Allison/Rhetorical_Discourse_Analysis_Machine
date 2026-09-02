"""Runtime projection of raw GUM eRST relations to ontology concepts."""

from isanlp_rst.contracts.enums import RelationSchemeEnum
from isanlp_rst.ontology.adapter import OntologyAdapter


def resolve_gum_relation_concept(
    raw_relation: str,
    *,
    ontology_adapter: OntologyAdapter | None = None,
) -> str:
    """Project one raw GUM relation while preserving the caller's raw value."""

    adapter = ontology_adapter or OntologyAdapter()
    canonical_raw, concept = adapter.resolve_label(raw_relation, RelationSchemeEnum.GUM_ERST_FINE)
    if canonical_raw != raw_relation:
        raise ValueError("ontology adapter changed a canonical raw GUM relation label")
    return concept


__all__ = ["resolve_gum_relation_concept"]
