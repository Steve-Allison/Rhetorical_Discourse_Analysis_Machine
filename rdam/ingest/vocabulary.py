"""Shared vocabulary evidence and capture from declared parser runtime data."""

from collections.abc import Mapping, Sequence
from typing import Literal, Self, cast

from pydantic import Field, model_validator

from rdam.ingest.contracts.base import Sha256Identity, StrictContractModel
from rdam.ingest.identity import semantic_sha256
from rdam.ontology import ObservedVocabularyAlignment, observed_vocabulary_alignment, technique_projection_identity
from rdam._strict import Sha256Identity as ProjectionIdentity


def _alignment(
    corpus: str | None, labels: tuple[str, ...], identity: ProjectionIdentity | None = None,
    *, inventory_scope: Literal["corpus", "shared_classifier"] = "corpus",
) -> tuple[ObservedVocabularyAlignment | None, str | None]:
    if inventory_scope == "shared_classifier":
        return None, "shared_classifier_crosswalk_unavailable"
    if corpus is None:
        return None, "corpus_not_declared"
    match corpus.casefold().strip():
        case "gum":
            schemes = ("coe:artifact/narrative/gum_erst_groups", "coe:artifact/narrative/gum_erst_relations")
        case "rst-dt" | "rstdt":
            schemes = ("coe:artifact/narrative/descriptive_rst_taxonomy", "coe:artifact/narrative/rst_dt_relations")
        case _:
            return None, "no_registered_corpus_crosswalk"
    candidates = tuple(observed_vocabulary_alignment(scheme, labels, projection_identity=identity) for scheme in schemes)
    complete = tuple(candidate for candidate in candidates if not candidate.unmapped)
    if len(complete) != 1:
        return None, "inventory_scope_ambiguous" if complete else "inventory_has_unmapped_labels"
    return complete[0], None


class RuntimeRelationVocabulary(StrictContractModel):
    corpus_name: str | None
    scope_basis: Literal["selected_corpus", "configured_corpus", "not_declared"]
    labels: tuple[str, ...] = Field(min_length=1)
    inventory_identity: Sha256Identity
    alignment: ObservedVocabularyAlignment | None
    mapping_reason: str | None
    authority_snapshot: ProjectionIdentity | None = Field(default=None, exclude_if=lambda value: value is None)
    inventory_scope: Literal["corpus", "shared_classifier"] = Field(
        default="corpus", exclude_if=lambda value: value == "corpus",
    )

    @model_validator(mode="after")
    def coherent_vocabulary(self) -> Self:
        if (self.corpus_name is None) != (self.scope_basis == "not_declared"):
            raise ValueError("Corpus scope requires its declared basis")
        if len(set(self.labels)) != len(self.labels) or any(not label for label in self.labels):
            raise ValueError("Runtime relation labels must be nonempty and unique")
        if self.inventory_identity.hex_digest != semantic_sha256(self.labels):
            raise ValueError("Runtime vocabulary identity differs from captured labels")
        snapshot = self.authority_snapshot or (self.alignment.projection_identity if self.alignment is not None else None)
        if (self.alignment, self.mapping_reason) != _alignment(
            self.corpus_name, self.labels, snapshot, inventory_scope=self.inventory_scope,
        ):
            raise ValueError("Runtime vocabulary mapping differs from declared corpus and labels")
        return self


def _native_labels(table: object) -> tuple[str, ...]:
    if not isinstance(table, Sequence) or isinstance(table, str) or not table:
        raise ValueError("Loaded relation table must be a nonempty sequence")
    raw_labels: list[str] = []
    for item in cast(Sequence[object], table):
        if not isinstance(item, str):
            raise ValueError("Loaded relation table contains non-text labels")
        relation, separator, nuclearity = item.rpartition("_")
        if not relation or not separator or nuclearity.upper() not in {"NN", "NS", "SN"}:
            raise ValueError("Loaded relation class lacks its relation or nuclearity")
        raw_labels.append(relation)
    return tuple(dict.fromkeys(raw_labels))


def capture_runtime_vocabulary(predictor: object, labels: tuple[str, ...]) -> RuntimeRelationVocabulary:
    """Check captured labels against the loaded corpus or shared classifier table."""
    table = getattr(predictor, "relation_table", None)
    scope: Literal["corpus", "shared_classifier"] = "corpus"
    if table is not None and _native_labels(table) != labels:
        model = getattr(predictor, "model", None)
        shared = getattr(model, "relation_vocab", None)
        if getattr(model, "dataset_masks", None) is None or _native_labels(shared) != labels:
            raise ValueError("Captured inventory differs from the loaded relation table")
        scope = "shared_classifier"
    corpus: str | None = None
    basis: Literal["selected_corpus", "configured_corpus", "not_declared"] = "not_declared"
    names = getattr(predictor, "dataset_names", None)
    index = getattr(predictor, "relinventory_idx", None)
    if names is not None or index is not None:
        if not isinstance(names, Sequence) or isinstance(names, str) or type(index) is not int:
            raise ValueError("Selected corpus scope is inconsistent with loaded inventories")
        corpus_names = cast(Sequence[object], names)
        if not 0 <= index < len(corpus_names):
            raise ValueError("Selected corpus index is outside the loaded inventories")
        selected = corpus_names[index]
        if not isinstance(selected, str) or not selected.strip():
            raise ValueError("Selected corpus name must be nonempty text")
        corpus, basis = selected, "selected_corpus"
    else:
        config = getattr(predictor, "config", None)
        data = cast(Mapping[object, object], config).get("data") if isinstance(config, Mapping) else None
        declared = cast(Mapping[object, object], data).get("corpus") if isinstance(data, Mapping) else None
        if declared is not None:
            if not isinstance(declared, str) or not declared.strip():
                raise ValueError("Configured corpus must be nonempty text")
            corpus, basis = declared, "configured_corpus"
    snapshot = technique_projection_identity()
    alignment, reason = _alignment(corpus, labels, snapshot, inventory_scope=scope)
    return RuntimeRelationVocabulary(
        corpus_name=corpus, scope_basis=basis, labels=labels,
        inventory_identity=Sha256Identity(hex_digest=semantic_sha256(labels)),
        alignment=alignment, mapping_reason=reason,
        authority_snapshot=snapshot,
        inventory_scope=scope,
    )
