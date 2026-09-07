"""Resolve trained local mappings and explicitly scoped Central vocabulary labels.

The bundled legacy inventory provides local coarse projections. It is not a
canonical Central_Configs crosswalk. Central alignment is a separate operation
requiring a declared corpus label scheme.
"""

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Literal, overload

from rdam.rst.contracts.enums import (
    FailureCodeEnum,
    NuclearityPatternEnum,
    RelationSchemeEnum,
)
from rdam.rst.ontology.loader import OntologyLockData, load_ontology_lock
from rdam.ontology import ObservedVocabularyAlignment, observed_vocabulary_alignment


@dataclass(frozen=True, slots=True)
class ResolvedRelation:
    """A model class resolved within the local inventory."""

    canonical_label: str
    concept: str
    nuclearity: NuclearityPatternEnum


class OntologyAdapter:
    """Resolve model outputs and corpus labels against the bundled local mappings."""

    def __init__(self, lock_data: OntologyLockData | None = None) -> None:
        self.lock_data = lock_data or load_ontology_lock()
        gum_category_to_concept: dict[str, str] = {}
        for mapping in self.lock_data.dmrst_gum_model_27.values():
            category = mapping.label.casefold()
            existing = gum_category_to_concept.get(category)
            if existing is not None and existing != mapping.concept:
                raise ValueError(f"GUM ontology category {category!r} maps to conflicting concepts")
            gum_category_to_concept[category] = mapping.concept
        self.gum_category_to_concept = MappingProxyType(gum_category_to_concept)
        self.coarse_concepts_by_label = MappingProxyType({
            concept.casefold(): concept for concept in self.lock_data.coarse_concepts
        })

    @staticmethod
    def central_alignment(raw_labels: tuple[str, ...], scheme: RelationSchemeEnum) -> ObservedVocabularyAlignment:
        """Resolve corpus labels separately from the trained local class encoding."""
        match scheme:
            case RelationSchemeEnum.RST_DT_FINE:
                vocabulary = "coe:artifact/narrative/rst_dt_relations"
            case RelationSchemeEnum.RST_DT_COARSE_18:
                vocabulary = "coe:artifact/narrative/descriptive_rst_taxonomy"
            case RelationSchemeEnum.GUM_ERST_FINE:
                vocabulary = "coe:artifact/narrative/gum_erst_relations"
            case RelationSchemeEnum.GUM_ERST_COARSE:
                vocabulary = "coe:artifact/narrative/gum_erst_groups"
            case _:
                raise ValueError(f"No Central label crosswalk registered for {scheme.value}")
        return observed_vocabulary_alignment(vocabulary, raw_labels)

    @staticmethod
    def normalize_rst_dt_alias(raw_label: str) -> str:
        """Project suffix variants while preserving negative attribution.

        RST-DT's attribution-n is a negation label, not a nuclearity suffix.
        The original raw label remains necessary for other directional variants.
        """
        lab = raw_label.lower().strip()
        if lab in {"attribution-n", "attribution-n-e"}:
            return "attribution-negative"
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
                coarse = self.coarse_concepts_by_label.get(normalized)
                if scheme is RelationSchemeEnum.RST_DT_COARSE_18 and coarse is not None:
                    return coarse, coarse
                alias_norm = self.normalize_rst_dt_alias(normalized)
                if alias_norm in self.lock_data.rst_dt_fine_to_coarse:
                    concept = self.lock_data.rst_dt_fine_to_coarse[alias_norm]
                    return alias_norm, concept
                coarse = self.coarse_concepts_by_label.get(normalized)
                if coarse is not None:
                    return coarse, coarse

            case RelationSchemeEnum.GUM_ERST_FINE | RelationSchemeEnum.GUM_ERST_COARSE:
                if scheme is RelationSchemeEnum.GUM_ERST_COARSE:
                    coarse = self.gum_category_to_concept.get(normalized)
                    if coarse is not None:
                        return normalized, coarse
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
