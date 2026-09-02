"""Checked ontology adapters for model encodings and corpus label mappings."""

from dataclasses import dataclass
import re
from typing import Literal, overload

from rdam.rst.contracts.enums import (
    FailureCodeEnum,
    NuclearityPatternEnum,
    RelationSchemeEnum,
)
from rdam.rst.ontology.loader import OntologyLockData, load_ontology_lock


@dataclass(frozen=True, slots=True)
class ResolvedRelation:
    """Ontology-resolved rhetorical relation."""

    canonical_label: str
    concept: str
    nuclearity: NuclearityPatternEnum


class OntologyAdapter:
    """Adapts and resolves model outputs and corpus labels against the pinned ontology."""

    def __init__(self, lock_data: OntologyLockData | None = None) -> None:
        self.lock_data = lock_data or load_ontology_lock()
        gum_category_to_concept: dict[str, str] = {}
        for mapping in self.lock_data.dmrst_gum_model_27.values():
            category = mapping.label.casefold()
            existing = gum_category_to_concept.get(category)
            if existing is not None and existing != mapping.concept:
                raise ValueError(f"GUM ontology category {category!r} maps to conflicting concepts")
            gum_category_to_concept[category] = mapping.concept
        self.gum_category_to_concept = gum_category_to_concept

    @staticmethod
    def normalize_rst_dt_alias(raw_label: str) -> str:
        """Strip embedded (-e) and nuclearity (-s/-n) suffixes from RST-DT labels."""
        lab = raw_label.lower().strip()
        # Remove trailing -e, -n, -s, -n-e, -s-e
        lab = re.sub(r"-(n-e|s-e|e|n|s)$", "", lab)
        if lab == "textualorganization":
            lab = "textual-organization"
        return lab

    @overload
    def resolve_label(
        self,
        raw_label: str,
        scheme: RelationSchemeEnum = RelationSchemeEnum.RST_DT_FINE,
        *,
        raise_on_unmapped: Literal[True] = True,
    ) -> tuple[str, str]: ...

    @overload
    def resolve_label(
        self,
        raw_label: str,
        scheme: RelationSchemeEnum = RelationSchemeEnum.RST_DT_FINE,
        *,
        raise_on_unmapped: Literal[False],
    ) -> tuple[str, str] | None: ...

    @overload
    def resolve_label(
        self,
        raw_label: str,
        scheme: RelationSchemeEnum = RelationSchemeEnum.RST_DT_FINE,
        *,
        raise_on_unmapped: bool,
    ) -> tuple[str, str] | None: ...

    def resolve_label(
        self,
        raw_label: str,
        scheme: RelationSchemeEnum = RelationSchemeEnum.RST_DT_FINE,
        *,
        raise_on_unmapped: bool = True,
    ) -> tuple[str, str] | None:
        """Resolve a raw corpus label to its canonical label and coarse concept."""
        normalized = raw_label.lower().strip()

        match scheme:
            case RelationSchemeEnum.RST_DT_FINE | RelationSchemeEnum.RST_DT_COARSE_18:
                alias_norm = self.normalize_rst_dt_alias(normalized)
                if alias_norm in self.lock_data.rst_dt_fine_to_coarse:
                    concept = self.lock_data.rst_dt_fine_to_coarse[alias_norm]
                    return alias_norm, concept
                if normalized.capitalize() in self.lock_data.coarse_concepts:
                    return normalized.capitalize(), normalized.capitalize()

            case RelationSchemeEnum.GUM_ERST_FINE | RelationSchemeEnum.GUM_ERST_COARSE:
                if normalized in self.lock_data.gum_fine_to_coarse:
                    category = self.lock_data.gum_fine_to_coarse[normalized]
                    concept = self.gum_category_to_concept.get(category)
                    if concept is None:
                        if not raise_on_unmapped:
                            return None
                        raise KeyError(
                            f"GUM ontology category {category!r} has no canonical concept "
                            f"(code: {FailureCodeEnum.ONTOLOGY_MISMATCH.value})"
                        )
                    return normalized, concept

            case _:
                pass

        if not raise_on_unmapped:
            return None

        # If unmapped, raise or fail closed
        raise KeyError(
            f"Unmapped label {raw_label!r} in scheme {scheme.value} (code: {FailureCodeEnum.UNMAPPED_LABEL.value})"
        )

    @overload
    def resolve_model_class(
        self,
        class_index: int,
        model_scheme: RelationSchemeEnum = RelationSchemeEnum.DMRST_RSTDT_MODEL_42,
        *,
        raise_on_unmapped: Literal[True] = True,
    ) -> ResolvedRelation: ...

    @overload
    def resolve_model_class(
        self,
        class_index: int,
        model_scheme: RelationSchemeEnum = RelationSchemeEnum.DMRST_RSTDT_MODEL_42,
        *,
        raise_on_unmapped: Literal[False],
    ) -> ResolvedRelation | None: ...

    @overload
    def resolve_model_class(
        self,
        class_index: int,
        model_scheme: RelationSchemeEnum = RelationSchemeEnum.DMRST_RSTDT_MODEL_42,
        *,
        raise_on_unmapped: bool,
    ) -> ResolvedRelation | None: ...

    def resolve_model_class(
        self,
        class_index: int,
        model_scheme: RelationSchemeEnum = RelationSchemeEnum.DMRST_RSTDT_MODEL_42,
        *,
        raise_on_unmapped: bool = True,
    ) -> ResolvedRelation | None:
        """Resolve a predicted model class integer index into canonical label, concept, and nuclearity."""
        match model_scheme:
            case RelationSchemeEnum.DMRST_RSTDT_MODEL_42:
                mapping = self.lock_data.dmrst_rstdt_model_42.get(class_index)
            case RelationSchemeEnum.DMRST_GUM_MODEL_27:
                mapping = self.lock_data.dmrst_gum_model_27.get(class_index)
            case _:
                mapping = None

        if mapping is None:
            if not raise_on_unmapped:
                return None
            raise KeyError(
                f"Class index {class_index} not found in model scheme {model_scheme.value} "
                f"(code: {FailureCodeEnum.UNMAPPED_LABEL.value})"
            )

        nuc = NuclearityPatternEnum(mapping.nuclearity.upper())
        return ResolvedRelation(
            canonical_label=mapping.label,
            concept=mapping.concept,
            nuclearity=nuc,
        )

    def get_concept_uri(self, concept: str, base_prefix: str = "http://example.org/central/ontology/DiscourseRelation#") -> str:
        """Return canonical Central ontology URI for a coarse discourse concept."""
        normalized = concept.strip()
        return f"{base_prefix}{normalized}"

    def get_nuclearity_uri(self, nuclearity: NuclearityPatternEnum, base_prefix: str = "http://example.org/central/ontology/Nuclearity#") -> str:
        """Return canonical Central ontology URI for a nuclearity pattern."""
        return f"{base_prefix}{nuclearity.name}"

    def get_node_uri(self, document_id: str, node_id: int, base_prefix: str = "http://example.org/documents/") -> str:
        """Return canonical document-scoped URI for a discourse unit node."""
        return f"{base_prefix}{document_id}#node_{node_id}"
