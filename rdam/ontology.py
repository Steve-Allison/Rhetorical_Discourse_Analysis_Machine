"""Resolve registered Central_Configs v5.0.0 concepts from packaged lookup projections.

Runtime adapters use explicit ``native_value <-> coe:Cxxxxx`` lookup tables packaged in
``rdam/resources/{discourse-concepts,technique-concepts,walton-crosswalk}.json``
(generated from ``../Central_Configs/dist/build/central.sqlite``, verified 2026-11-15),
with zero CURIE path-splitting and zero vendored snapshot shims.
"""

from functools import cache
from importlib import resources
import json
import re
from typing import Any, Final, Literal, Self, cast

from pydantic import Field, model_validator

from rdam._strict import Sha256Identity, StrictModel, semantic_sha256, sha256_bytes

type AlignedFramework = Literal[
    "toulmin",
    "pdtb",
    "walton",
    "ibis",
    "dung",
    "sdrt",
    "classical_rhetoric",
]

type ObservedVocabularyId = Literal[
    "pdtb3_senses",
    "sdrt_relations",
    "walton_profile",
    "rst_dt_relations",
    "rst_dt_coarse",
    "gum_erst_relations",
    "gum_erst_groups",
]

type MatchingRule = Literal[
    "exact_key",
    "case_insensitive_label",
    "rst_dt_corpus_label",
    "rst_dt_coarse_group",
    "walton_native_profile",
]

CENTRAL_SCHEME: Final = "https://steve-allison.github.io/Central_Configs/v5/schema/coe"
_COE_CURIE_RE: Final = re.compile(r"^coe:C[0-9]{5}$")
_RST_DT_SUFFIX_RE: Final = re.compile(r"-(n-e|s-e|e|n|s)$")


def _projection_bytes(filename: str, identity: Sha256Identity | None = None) -> bytes:
    raw = resources.files("rdam").joinpath("resources").joinpath(filename).read_bytes()
    if identity is not None and sha256_bytes(raw) != identity.hex_digest:
        raise ValueError(f"Projection digest mismatch for {filename}: {identity.hex_digest}")
    return raw


def _authority(framework: AlignedFramework, identity: Sha256Identity | None = None) -> tuple[bytes, dict[str, Any]]:
    filename = "discourse-concepts.json" if framework == "toulmin" else "technique-concepts.json"
    raw = _projection_bytes(filename, identity)
    return raw, cast(dict[str, Any], json.loads(raw))


def technique_projection_identity() -> Sha256Identity:
    return Sha256Identity(hex_digest=sha256_bytes(_projection_bytes("technique-concepts.json")))


class NativeConceptMapping(StrictModel):
    native_value: str = Field(min_length=1)
    concept_id: str = Field(pattern=r"^coe:C[0-9]{5}$")
    label: str = Field(min_length=1)
    relationship: Literal["exact", "broader"]


class UnmappedConcept(StrictModel):
    native_value: str = Field(min_length=1)
    reason: Literal[
        "absent_from_scoped_vocabulary",
        "native_slot_has_no_reviewed_crosswalk",
        "equivalence_not_established",
    ] = "absent_from_scoped_vocabulary"
    explanation: str | None = Field(default=None, min_length=1, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def explanation_matches_disposition(self) -> Self:
        if (self.reason == "equivalence_not_established") != (self.explanation is not None):
            raise ValueError("an explicit non-equivalence disposition requires its explanation")
        return self


class ObservedVocabularyAlignment(StrictModel):
    """Resolve observed spellings within one explicitly identified vocabulary lookup table."""

    authority: Literal["Central_Configs"] = "Central_Configs"
    scheme: str = Field(min_length=1)
    vocabulary: ObservedVocabularyId
    source: str = Field(min_length=1)
    source_identity: Sha256Identity
    projection_identity: Sha256Identity
    matching: MatchingRule
    consumer_profile_identity: Sha256Identity | None = Field(default=None, exclude_if=lambda value: value is None)
    native_values: tuple[str, ...]
    mappings: tuple[NativeConceptMapping, ...]
    unmapped: tuple[UnmappedConcept, ...]

    @model_validator(mode="after")
    def reproduce_resolution(self) -> Self:
        raw, document, vocab_entry = _vocabulary(self.vocabulary, self.projection_identity)
        expected_matching = cast(MatchingRule, vocab_entry["matching"])
        if self.matching != expected_matching:
            raise ValueError("Observed matching rule differs from its scoped vocabulary")
        if self.consumer_profile_identity != _consumer_profile_identity(self.vocabulary, self.consumer_profile_identity):
            raise ValueError("Observed consumer profile differs from the installed binding")
        if (
            self.scheme != document["scheme"]
            or self.source != document["source"]
            or self.source_identity.hex_digest != document["source_sha256"]
            or self.projection_identity.hex_digest != sha256_bytes(raw)
        ):
            raise ValueError("Observed vocabulary requires the identified installed authority projection")
        if len(set(self.native_values)) != len(self.native_values) or any(not value for value in self.native_values):
            raise ValueError("Observed native labels must be non-empty and unique")
        mappings, unmapped = _observed_mappings(
            self.native_values,
            vocab_entry,
            cast(dict[str, Any], document["concepts"]),
            self.consumer_profile_identity,
        )
        if self.mappings != mappings or self.unmapped != unmapped:
            raise ValueError("Observed mappings must account for every native label without inferred aliases")
        return self


def _vocabulary(
    vocabulary: ObservedVocabularyId,
    identity: Sha256Identity | None = None,
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    raw = _projection_bytes("technique-concepts.json", identity)
    document = cast(dict[str, Any], json.loads(raw))
    observed = cast(dict[str, Any], document.get("observed_vocabularies") or {})
    if vocabulary not in observed:
        raise ValueError(f"Unregistered vocabulary: {vocabulary}")
    return raw, document, cast(dict[str, Any], observed[vocabulary])


def _normalize_rst_dt_key(raw_label: str) -> str:
    if raw_label != raw_label.strip():
        return raw_label
    lowered = raw_label.lower()
    if lowered in {"attribution-n", "attribution-n-e"}:
        return "attribution-negative"
    stripped = _RST_DT_SUFFIX_RE.sub("", lowered)
    if stripped == "textualorganization":
        return "textual-organization"
    return stripped


def _normalize_observed_key(value: str, matching: MatchingRule) -> str:
    match matching:
        case "exact_key" | "walton_native_profile":
            return value
        case "case_insensitive_label" | "rst_dt_coarse_group":
            return value.casefold()
        case "rst_dt_corpus_label":
            return _normalize_rst_dt_key(value)


def declared_vocabulary_contains_all(
    vocabulary: ObservedVocabularyId,
    values: tuple[str, ...],
    *,
    projection_identity: Sha256Identity | None = None,
) -> bool:
    """Return whether every value belongs to the declared corpus inventory of ``vocabulary``."""

    _, _, vocab_entry = _vocabulary(vocabulary, projection_identity)
    matching = cast(MatchingRule, vocab_entry["matching"])
    declared = set(cast(list[str], vocab_entry.get("declared_inventory") or []))
    return all(_normalize_observed_key(value, matching) in declared for value in values)


def lookup_curie_for_native(vocabulary: ObservedVocabularyId, native_value: str) -> NativeConceptMapping | None:
    """Look up a single observed native value in the explicit ``native_to_curie`` dictionary."""

    _, document, vocab_entry = _vocabulary(vocabulary)
    matching = cast(MatchingRule, vocab_entry["matching"])
    if matching == "walton_native_profile":
        mappings, _ = _walton_mappings((native_value,), cast(dict[str, Any], document["concepts"]))
        return mappings[0] if mappings else None
    key = _normalize_observed_key(native_value, matching)
    target = cast(dict[str, Any], vocab_entry["native_to_curie"]).get(key)
    if target is None:
        return None
    return NativeConceptMapping(
        native_value=native_value,
        concept_id=str(target["curie"]),
        label=str(target["label"]),
        relationship=cast(Literal["exact", "broader"], target["relationship"]),
    )


def lookup_native_for_curie(vocabulary: ObservedVocabularyId, curie: str) -> tuple[str, ...]:
    """Look up all native values bound to ``curie`` in ``vocabulary``."""

    if not _COE_CURIE_RE.match(curie):
        raise ValueError(f"Expected Central_Configs v5.0.0 CURIE (^coe:C[0-9]{{5}}$): {curie!r}")
    _, _, vocab_entry = _vocabulary(vocabulary)
    reverse = cast(dict[str, list[str]], vocab_entry.get("curie_to_native") or {})
    return tuple(reverse.get(curie, ()))


def _observed_mappings(
    values: tuple[str, ...],
    vocab_entry: dict[str, Any],
    concepts: dict[str, Any],
    consumer_identity: Sha256Identity | None = None,
) -> tuple[tuple[NativeConceptMapping, ...], tuple[UnmappedConcept, ...]]:
    matching = cast(MatchingRule, vocab_entry["matching"])
    if matching == "walton_native_profile":
        return _walton_mappings(values, concepts, consumer_identity)

    native_to_curie = cast(dict[str, dict[str, str]], vocab_entry["native_to_curie"])
    mappings: list[NativeConceptMapping] = []
    unmapped: list[UnmappedConcept] = []
    for value in values:
        key = _normalize_observed_key(value, matching)
        target = native_to_curie.get(key)
        if target is None:
            unmapped.append(UnmappedConcept(native_value=value))
            continue
        curie = target["curie"]
        concept = concepts.get(curie)
        if not _COE_CURIE_RE.match(curie) or concept is None or concept.get("label") != target["label"]:
            raise ValueError(f"Scoped vocabulary binding {key!r} -> {curie!r} is inconsistent with authority")
        mappings.append(
            NativeConceptMapping(
                native_value=value,
                concept_id=curie,
                label=target["label"],
                relationship=cast(Literal["exact", "broader"], target["relationship"]),
            )
        )
    return tuple(mappings), tuple(unmapped)


def _walton_profile(identity: Sha256Identity | None = None) -> tuple[bytes, dict[str, Any], dict[str, str]]:
    from rdam.walton.schemes import SCHEME_SET_ID, SCHEMES

    raw = resources.files("rdam").joinpath("resources/walton-crosswalk.json").read_bytes()
    binding = cast(dict[str, Any], json.loads(raw))
    if binding.get("profile") != SCHEME_SET_ID:
        raise ValueError("Walton crosswalk belongs to a different native profile")
    terms: dict[str, str] = {}
    for scheme_id, scheme in SCHEMES.items():
        terms.update((f"{scheme_id}/premise/{role}", role) for role in scheme.premise_roles)
        terms.update(
            (f"{scheme_id}/question/{index}", question)
            for index, question in enumerate(scheme.critical_questions)
        )
    if identity is not None and identity != _profile_identity(raw, terms):
        raise ValueError(f"Walton profile identity mismatch: {identity.hex_digest}")
    for key, mapping in cast(dict[str, dict[str, str]], binding["mappings"]).items():
        if terms.get(key) != mapping["native_text"]:
            raise ValueError("Walton crosswalk text or index differs from the native profile")
    for key, disposition in cast(dict[str, dict[str, str]], binding.get("unmapped") or {}).items():
        if key in binding["mappings"] or terms.get(key) != disposition["native_text"]:
            raise ValueError("Walton unmapped disposition conflicts with its native profile or mapping")
        if not isinstance(disposition.get("explanation"), str) or not disposition["explanation"].strip():
            raise ValueError("Walton unmapped disposition requires an explanation")
    return raw, binding, terms


def _profile_identity(raw: bytes, terms: dict[str, str]) -> Sha256Identity:
    return Sha256Identity(hex_digest=semantic_sha256({"crosswalk_sha256": sha256_bytes(raw), "terms": terms}))


def _consumer_profile_identity(
    vocabulary: ObservedVocabularyId,
    identity: Sha256Identity | None = None,
) -> Sha256Identity | None:
    if vocabulary != "walton_profile":
        return None
    raw, _, terms = _walton_profile(identity)
    return _profile_identity(raw, terms)


def _walton_mappings(
    values: tuple[str, ...],
    concepts: dict[str, Any],
    identity: Sha256Identity | None = None,
) -> tuple[tuple[NativeConceptMapping, ...], tuple[UnmappedConcept, ...]]:
    _, binding, terms = _walton_profile(identity)
    mappings_table = cast(dict[str, dict[str, str]], binding["mappings"])
    unmapped_table = cast(dict[str, dict[str, str]], binding.get("unmapped") or {})
    mappings: list[NativeConceptMapping] = []
    unmapped: list[UnmappedConcept] = []
    for key in values:
        if key not in terms:
            raise ValueError(f"Unknown Walton profile term: {key}")
        mapping = mappings_table.get(key)
        if mapping is None:
            disposition = unmapped_table.get(key)
            unmapped.append(
                UnmappedConcept(native_value=key, reason="native_slot_has_no_reviewed_crosswalk")
                if disposition is None
                else UnmappedConcept(
                    native_value=key,
                    reason="equivalence_not_established",
                    explanation=disposition["explanation"],
                )
            )
            continue
        curie = mapping["concept_id"]
        concept = concepts.get(curie)
        if not _COE_CURIE_RE.match(curie) or concept is None or concept.get("in_scheme") != CENTRAL_SCHEME:
            raise ValueError(f"Walton crosswalk references an unregistered canonical concept: {curie!r}")
        mappings.append(
            NativeConceptMapping(
                native_value=key,
                concept_id=curie,
                label=str(concept["label"]),
                relationship=cast(Literal["exact", "broader"], mapping["relationship"]),
            )
        )
    return tuple(mappings), tuple(unmapped)


def walton_profile_alignment(
    scheme_ids: tuple[str, ...],
    *,
    projection_identity: Sha256Identity | None = None,
    consumer_profile_identity: Sha256Identity | None = None,
) -> ObservedVocabularyAlignment:
    """Account for all premise fields and questions of the schemes actually used."""
    from rdam.walton.schemes import SCHEMES

    if any(scheme_id not in SCHEMES for scheme_id in scheme_ids):
        raise ValueError("Unknown Walton scheme in observed profile")
    _, _, terms = _walton_profile(consumer_profile_identity)
    selected = tuple(key for key in terms if key.split("/", 1)[0] in scheme_ids)
    return observed_vocabulary_alignment(
        "walton_profile",
        selected,
        projection_identity=projection_identity,
        consumer_profile_identity=consumer_profile_identity,
    )


def observed_vocabulary_alignment(
    vocabulary: ObservedVocabularyId,
    values: tuple[str, ...],
    *,
    projection_identity: Sha256Identity | None = None,
    consumer_profile_identity: Sha256Identity | None = None,
) -> ObservedVocabularyAlignment:
    """Preserve spellings and explicitly record missing canonical terms."""
    raw, document, vocab_entry = _vocabulary(vocabulary, projection_identity)
    unique_values = tuple(dict.fromkeys(values))
    mappings, unmapped = _observed_mappings(
        unique_values,
        vocab_entry,
        cast(dict[str, Any], document["concepts"]),
        consumer_profile_identity,
    )
    return ObservedVocabularyAlignment(
        scheme=str(document["scheme"]),
        vocabulary=vocabulary,
        source=str(document["source"]),
        source_identity=Sha256Identity(hex_digest=str(document["source_sha256"])),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
        consumer_profile_identity=_consumer_profile_identity(vocabulary, consumer_profile_identity),
        matching=cast(MatchingRule, vocab_entry["matching"]),
        native_values=unique_values,
        mappings=mappings,
        unmapped=unmapped,
    )


class NativeOntologyAlignment(StrictModel):
    framework: AlignedFramework = "toulmin"
    authority: Literal["Central_Configs"]
    scheme: str
    source: str
    source_identity: Sha256Identity
    projection_identity: Sha256Identity
    mappings: tuple[NativeConceptMapping, ...]
    unmapped_native_values: tuple[str, ...] = Field(default=(), exclude_if=lambda values: not values)

    @model_validator(mode="after")
    def references_match_installed_authority(self) -> Self:
        raw, projection = _authority(self.framework, self.projection_identity)
        if (
            self.source_identity.hex_digest != projection["source_sha256"]
            or self.projection_identity.hex_digest != sha256_bytes(raw)
            or self.scheme != projection["scheme"]
            or self.source != projection["source"]
        ):
            raise ValueError("Ontology alignment requires the identified installed authority projection")
        if len({mapping.native_value for mapping in self.mappings}) != len(self.mappings):
            raise ValueError("Duplicate native ontology mapping")

        concepts = cast(dict[str, Any], projection["concepts"])
        for mapping in self.mappings:
            concept = concepts.get(mapping.concept_id)
            if (
                not _COE_CURIE_RE.match(mapping.concept_id)
                or concept is None
                or concept.get("label") != mapping.label
                or concept.get("in_scheme") != self.scheme
            ):
                raise ValueError("Ontology mapping has an unknown or inconsistent canonical reference")

        if self.framework == "toulmin":
            expected_toulmin = _toulmin_mapping_values(projection)
            if self.mappings != expected_toulmin or self.unmapped_native_values:
                raise ValueError("Toulmin mappings must include every registered role exactly once")
        else:
            expected_mappings, expected_unmapped = _native_mapping_values(self.framework, projection)
            if self.mappings != expected_mappings or self.unmapped_native_values != expected_unmapped:
                raise ValueError("Ontology mappings must reproduce the registered native inventory")
        return self


@cache
def toulmin_role_alignment() -> NativeOntologyAlignment:
    """Resolve RDAM's six Toulmin roles to Central_Configs v5.0.0 coe:C06101-coe:C06106."""
    raw = _projection_bytes("discourse-concepts.json")
    projection = cast(dict[str, Any], json.loads(raw))
    return NativeOntologyAlignment(
        framework="toulmin",
        authority="Central_Configs",
        scheme=str(projection["scheme"]),
        source=str(projection["source"]),
        source_identity=Sha256Identity(hex_digest=str(projection["source_sha256"])),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
        mappings=_toulmin_mapping_values(projection),
    )


def _toulmin_mapping_values(discourse_projection: dict[str, Any]) -> tuple[NativeConceptMapping, ...]:
    technique_doc = cast(dict[str, Any], json.loads(_projection_bytes("technique-concepts.json")))
    toulmin_table = cast(dict[str, Any], technique_doc["native_frameworks"]["toulmin"])
    native_to_curie = cast(dict[str, dict[str, str]], toulmin_table["native_to_curie"])
    concepts = cast(dict[str, dict[str, Any]], discourse_projection["concepts"])

    mappings: list[NativeConceptMapping] = []
    for role in ("claim", "grounds", "warrant", "backing", "qualifier", "rebuttal"):
        target = native_to_curie.get(role)
        if target is None:
            raise ValueError(f"Missing Toulmin role binding in technique-concepts.json: {role!r}")
        curie = target["curie"]
        concept = concepts.get(curie)
        if (
            not _COE_CURIE_RE.match(curie)
            or concept is None
            or concept.get("collection_name") != "argument_schemes"
            or concept.get("in_scheme") != discourse_projection["scheme"]
            or target["relationship"] != "exact"
        ):
            raise ValueError(f"Toulmin role binding {role!r} -> {curie!r} is inconsistent with discourse-concepts.json")
        mappings.append(
            NativeConceptMapping(
                native_value=role,
                concept_id=curie,
                label=str(concept["label"]),
                relationship="exact",
            )
        )
    return tuple(mappings)


def native_framework_values(framework: AlignedFramework) -> tuple[str, ...]:
    match framework:
        case "pdtb":
            from rdam.pdtb.relations import PdtbSense

            return tuple(item.value for item in PdtbSense)
        case "walton":
            from rdam.walton.schemes import SchemeId

            return tuple(item.value for item in SchemeId)
        case "ibis":
            from rdam.ibis.grammar import NodeKind, Relation

            return tuple(item.value for enum in (NodeKind, Relation) for item in enum)
        case "dung":
            from rdam.dung.semantics import DungInput

            return tuple(DungInput.model_fields)
        case "sdrt":
            from rdam.sdrt.graph import RelationStructure

            return tuple(item.value for item in RelationStructure)
        case "classical_rhetoric":
            return ("ethos", "pathos", "logos")
        case "toulmin":
            return ("claim", "grounds", "warrant", "backing", "qualifier", "rebuttal")


def _native_mapping_values(
    framework: AlignedFramework,
    projection: dict[str, Any],
) -> tuple[tuple[NativeConceptMapping, ...], tuple[str, ...]]:
    frameworks_table = cast(dict[str, Any], projection.get("native_frameworks") or {})
    if framework not in frameworks_table:
        raise ValueError(f"Unregistered native framework lookup table: {framework}")
    entry = cast(dict[str, Any], frameworks_table[framework])
    native_to_curie = cast(dict[str, dict[str, str]], entry["native_to_curie"])
    declared_unmapped = set(cast(list[str], entry["unmapped_native_values"]))
    concepts = cast(dict[str, dict[str, Any]], projection["concepts"])

    mappings: list[NativeConceptMapping] = []
    unmapped: list[str] = []
    for value in native_framework_values(framework):
        target = native_to_curie.get(value)
        if target is None:
            if value not in declared_unmapped:
                raise ValueError(f"Native value {value!r} for {framework!r} is unaccounted for in lookup table")
            unmapped.append(value)
            continue
        curie = target["curie"]
        concept = concepts.get(curie)
        if not _COE_CURIE_RE.match(curie) or concept is None or concept.get("label") != target["label"]:
            raise ValueError(f"Native binding {value!r} -> {curie!r} does not match projected authority")
        mappings.append(
            NativeConceptMapping(
                native_value=value,
                concept_id=curie,
                label=str(concept["label"]),
                relationship=cast(Literal["exact", "broader"], target["relationship"]),
            )
        )
    return tuple(mappings), tuple(unmapped)


@cache
def pdtb_sense_alignment() -> NativeOntologyAlignment:
    """Resolve PDTB-3 senses against Central_Configs v5.0.0 DiscourseRelation resources."""
    return native_vocabulary_alignment("pdtb")


@cache
def native_vocabulary_alignment(framework: AlignedFramework) -> NativeOntologyAlignment:
    """Resolve a framework's closed native inventory via explicit lookup tables."""
    if framework == "toulmin":
        return toulmin_role_alignment()
    raw, projection = _authority(framework)
    mappings, unmapped = _native_mapping_values(framework, projection)
    return NativeOntologyAlignment(
        framework=framework,
        authority="Central_Configs",
        scheme=str(projection["scheme"]),
        source=str(projection["source"]),
        source_identity=Sha256Identity(hex_digest=str(projection["source_sha256"])),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
        mappings=mappings,
        unmapped_native_values=unmapped,
    )
