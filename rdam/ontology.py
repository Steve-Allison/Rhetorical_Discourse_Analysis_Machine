"""Resolve registered discourse concepts from the generated Central projection."""

from functools import cache
from importlib import resources
import json
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from rdam._strict import Sha256Identity, StrictModel, sha256_bytes, semantic_sha256

type AlignedFramework = Literal["toulmin", "pdtb", "walton", "ibis", "dung", "sdrt"]

# Consumer bindings reference Central identities; definitions remain generated data.
_SCHEMES = {
    "pdtb": "coe:artifact/narrative/pdtb3_senses",
    "walton": "coe:artifact/narrative/argumentation_schemes_taxonomy",
    "ibis": "coe:artifact/narrative/ibis_vocabulary",
    "dung": "coe:artifact/narrative/dung_semantics",
    "sdrt": "coe:artifact/narrative/sdrt_vocabulary",
}


def _projection_bytes(filename: str, identity: Sha256Identity | None = None) -> bytes:
    root = resources.files("rdam").joinpath("resources")
    raw = root.joinpath(filename).read_bytes()
    if identity is None or sha256_bytes(raw) == identity.hex_digest:
        return raw
    snapshot = root.joinpath(f"ontology-snapshots/{identity.hex_digest}.json")
    if not snapshot.is_file():
        raise ValueError(f"Required ontology snapshot is unavailable: {identity.hex_digest}")
    raw = snapshot.read_bytes()
    if sha256_bytes(raw) != identity.hex_digest:
        raise ValueError("Archived ontology snapshot digest mismatch")
    return raw


def _authority(framework: AlignedFramework, identity: Sha256Identity | None = None) -> tuple[bytes, dict[str, Any]]:
    filename = "discourse-concepts.json" if framework == "toulmin" else "technique-concepts.json"
    raw = _projection_bytes(filename, identity)
    document = json.loads(raw)
    return raw, document if framework == "toulmin" else document[_SCHEMES[framework]]


def technique_projection_identity() -> Sha256Identity:
    return Sha256Identity(hex_digest=sha256_bytes(_projection_bytes("technique-concepts.json")))


class NativeConceptMapping(StrictModel):
    native_value: str = Field(min_length=1)
    concept_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    relationship: Literal["exact", "broader"]


class UnmappedConcept(StrictModel):
    native_value: str = Field(min_length=1)
    reason: Literal["absent_from_scoped_vocabulary", "native_slot_has_no_reviewed_crosswalk", "equivalence_not_established"] = "absent_from_scoped_vocabulary"
    explanation: str | None = Field(default=None, min_length=1, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def explanation_matches_disposition(self) -> Self:
        if (self.reason == "equivalence_not_established") != (self.explanation is not None):
            raise ValueError("an explicit non-equivalence disposition requires its explanation")
        return self


class ObservedVocabularyAlignment(StrictModel):
    """Resolve observed spellings within one explicitly identified vocabulary.

    A lexical match identifies a term, not the correctness of its application.
    Only the declared matching rule is applied; no relation direction or
    attachment class is inferred from spelling.
    """

    authority: Literal["Central_Configs"] = "Central_Configs"
    scheme: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_identity: Sha256Identity
    projection_identity: Sha256Identity
    matching: Literal["case_insensitive_label", "rst_dt_corpus_label", "rst_dt_coarse_group", "walton_native_profile"]
    consumer_profile_identity: Sha256Identity | None = Field(default=None, exclude_if=lambda value: value is None)
    native_values: tuple[str, ...]
    mappings: tuple[NativeConceptMapping, ...]
    unmapped: tuple[UnmappedConcept, ...]

    @model_validator(mode="after")
    def reproduce_resolution(self) -> Self:
        raw, projection = _vocabulary(self.scheme, self.projection_identity)
        if self.matching != _matching_rule(self.scheme):
            raise ValueError("Observed matching rule differs from its scoped vocabulary")
        if self.consumer_profile_identity != _consumer_profile_identity(self.scheme, self.consumer_profile_identity):
            raise ValueError("Observed consumer profile differs from the installed binding")
        if (self.source != projection["source"]
                or self.source_identity.hex_digest != projection["source_sha256"]
                or self.projection_identity.hex_digest != sha256_bytes(raw)):
            raise ValueError("Observed vocabulary requires the identified installed authority snapshot")
        if len(set(self.native_values)) != len(self.native_values) or any(not value for value in self.native_values):
            raise ValueError("Observed native labels must be non-empty and unique")
        mappings, unmapped = _observed_mappings(self.native_values, projection, self.consumer_profile_identity)
        if self.mappings != mappings or self.unmapped != unmapped:
            raise ValueError("Observed mappings must account for every native label without inferred aliases")
        return self


def _vocabulary(scheme: str, identity: Sha256Identity | None = None) -> tuple[bytes, dict[str, Any]]:
    raw = _projection_bytes("technique-concepts.json", identity)
    document = json.loads(raw)
    if scheme not in document:
        raise ValueError(f"Unregistered vocabulary scheme: {scheme}")
    return raw, document[scheme]


def _observed_mappings(
    values: tuple[str, ...], projection: dict[str, Any], consumer_identity: Sha256Identity | None = None,
) -> tuple[tuple[NativeConceptMapping, ...], tuple[UnmappedConcept, ...]]:
    if _matching_rule(projection["scheme"]) == "walton_native_profile":
        return _walton_mappings(values, projection, consumer_identity)
    labels: dict[str, Any] = {}
    for concept in projection["concepts"].values():
        if projection["scheme"] == "coe:artifact/narrative/descriptive_rst_taxonomy" and (
            "coe:concept/descriptive_rst_taxonomy/relation_class" not in concept.get("broader", [])
        ):
            continue
        label = _label_key(concept["label"], projection["scheme"])
        if label in labels:
            raise ValueError("Scoped vocabulary has ambiguous case-insensitive labels")
        labels[label] = concept
    mappings: list[NativeConceptMapping] = []
    unmapped: list[UnmappedConcept] = []
    for value in values:
        concept = labels.get(_label_key(value, projection["scheme"]))
        if concept is None:
            unmapped.append(UnmappedConcept(native_value=value))
        else:
            mappings.append(NativeConceptMapping(
                native_value=value, concept_id=concept["id"], label=concept["label"], relationship="exact",
            ))
    return tuple(mappings), tuple(unmapped)


def _matching_rule(scheme: str) -> Literal["case_insensitive_label", "rst_dt_corpus_label", "rst_dt_coarse_group", "walton_native_profile"]:
    match scheme:
        case "coe:artifact/narrative/rst_dt_relations":
            return "rst_dt_corpus_label"
        case "coe:artifact/narrative/descriptive_rst_taxonomy":
            return "rst_dt_coarse_group"
        case "coe:artifact/narrative/argumentation_schemes_taxonomy":
            return "walton_native_profile"
        case _:
            return "case_insensitive_label"


def _label_key(value: str, scheme: str) -> str:
    value = value.casefold()
    match _matching_rule(scheme):
        case "rst_dt_coarse_group":
            return value.replace("-", " ")
        case "rst_dt_corpus_label":
            value = value.removesuffix("-e")
            if value == "attribution-negative":
                return "attribution-n"
            if value == "textual-organization":
                return "textualorganization"
        case "case_insensitive_label" | "walton_native_profile":
            return value
    return value


def _walton_profile(identity: Sha256Identity | None = None) -> tuple[bytes, dict[str, Any], dict[str, str]]:
    from rdam.walton.schemes import SCHEMES, SCHEME_SET_ID

    raw = resources.files("rdam").joinpath("resources/walton-crosswalk.json").read_bytes()
    binding = json.loads(raw)
    if binding["profile"] != SCHEME_SET_ID:
        raise ValueError("Walton crosswalk belongs to a different native profile")
    terms: dict[str, str] = {}
    for scheme_id, scheme in SCHEMES.items():
        terms.update((f"{scheme_id}/premise/{role}", role) for role in scheme.premise_roles)
        terms.update((f"{scheme_id}/question/{index}", question)
                     for index, question in enumerate(scheme.critical_questions))
    if identity is not None and identity != _profile_identity(raw, terms):
        path = resources.files("rdam").joinpath(f"resources/walton-profiles/{identity.hex_digest}.json")
        if not path.is_file():
            raise ValueError(f"Required Walton profile snapshot is unavailable: {identity.hex_digest}")
        snapshot = json.loads(path.read_bytes())
        raw = snapshot["crosswalk"].encode("utf-8")
        binding, terms = json.loads(raw), snapshot["terms"]
        if identity != _profile_identity(raw, terms):
            raise ValueError("Archived Walton profile digest mismatch")
    for key, mapping in binding["mappings"].items():
        if terms.get(key) != mapping["native_text"]:
            raise ValueError("Walton crosswalk text or index differs from the native profile")
    for key, disposition in binding.get("unmapped", {}).items():
        if key in binding["mappings"] or terms.get(key) != disposition["native_text"]:
            raise ValueError("Walton unmapped disposition conflicts with its native profile or mapping")
        if not isinstance(disposition["explanation"], str) or not disposition["explanation"].strip():
            raise ValueError("Walton unmapped disposition requires an explanation")
    return raw, binding, terms


def _profile_identity(raw: bytes, terms: dict[str, str]) -> Sha256Identity:
    return Sha256Identity(hex_digest=semantic_sha256({"crosswalk_sha256": sha256_bytes(raw), "terms": terms}))


def walton_profile_snapshot() -> tuple[str, bytes]:
    """Return the identified consumer binding for preservation before updates."""
    raw, _, terms = _walton_profile()
    snapshot = json.dumps({"crosswalk": raw.decode("utf-8"), "terms": terms}, sort_keys=True, indent=2) + "\n"
    return _profile_identity(raw, terms).hex_digest, snapshot.encode("utf-8")


def _consumer_profile_identity(scheme: str, identity: Sha256Identity | None = None) -> Sha256Identity | None:
    if _matching_rule(scheme) != "walton_native_profile":
        return None
    raw, _, terms = _walton_profile(identity)
    return _profile_identity(raw, terms)


def _walton_mappings(
    values: tuple[str, ...], projection: dict[str, Any], identity: Sha256Identity | None = None,
) -> tuple[tuple[NativeConceptMapping, ...], tuple[UnmappedConcept, ...]]:
    _, binding, terms = _walton_profile(identity)
    mappings: list[NativeConceptMapping] = []
    unmapped: list[UnmappedConcept] = []
    for key in values:
        if key not in terms:
            raise ValueError(f"Unknown Walton profile term: {key}")
        mapping = binding["mappings"].get(key)
        if mapping is None:
            disposition = binding.get("unmapped", {}).get(key)
            unmapped.append(
                UnmappedConcept(native_value=key, reason="native_slot_has_no_reviewed_crosswalk")
                if disposition is None else UnmappedConcept(
                    native_value=key, reason="equivalence_not_established", explanation=disposition["explanation"],
                )
            )
            continue
        concept = projection["concepts"].get(mapping["concept_id"])
        if concept is None or concept["in_scheme"] != projection["scheme"]:
            raise ValueError("Walton crosswalk references an unregistered canonical concept")
        mappings.append(NativeConceptMapping(
            native_value=key, concept_id=concept["id"], label=concept["label"], relationship=mapping["relationship"],
        ))
    return tuple(mappings), tuple(unmapped)


def walton_profile_alignment(
    scheme_ids: tuple[str, ...], *, projection_identity: Sha256Identity | None = None,
    consumer_profile_identity: Sha256Identity | None = None,
) -> ObservedVocabularyAlignment:
    """Account for all premise fields and questions of the schemes actually used."""
    from rdam.walton.schemes import SCHEMES

    if any(scheme_id not in SCHEMES for scheme_id in scheme_ids):
        raise ValueError("Unknown Walton scheme in observed profile")
    _, _, terms = _walton_profile(consumer_profile_identity)
    return observed_vocabulary_alignment(
        "coe:artifact/narrative/argumentation_schemes_taxonomy",
        tuple(key for key in terms if key.partition("/")[0] in scheme_ids),
        projection_identity=projection_identity, consumer_profile_identity=consumer_profile_identity,
    )


def observed_vocabulary_alignment(
    scheme: str, values: tuple[str, ...], *, projection_identity: Sha256Identity | None = None,
    consumer_profile_identity: Sha256Identity | None = None,
) -> ObservedVocabularyAlignment:
    """Preserve spellings and explicitly record missing canonical terms."""
    raw, projection = _vocabulary(scheme, projection_identity)
    values = tuple(dict.fromkeys(values))
    mappings, unmapped = _observed_mappings(values, projection, consumer_profile_identity)
    return ObservedVocabularyAlignment(
        scheme=scheme, source=projection["source"],
        source_identity=Sha256Identity(hex_digest=projection["source_sha256"]),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
        consumer_profile_identity=_consumer_profile_identity(scheme, consumer_profile_identity),
        matching=_matching_rule(scheme), native_values=values, mappings=mappings, unmapped=unmapped,
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
        if (self.source_identity.hex_digest != projection["source_sha256"]
                or self.projection_identity.hex_digest != sha256_bytes(raw)
                or self.scheme != projection["scheme"] or self.source != projection["source"]):
            raise ValueError("Ontology alignment requires the identified installed authority snapshot")
        if len({mapping.native_value for mapping in self.mappings}) != len(self.mappings):
            raise ValueError("Duplicate native ontology mapping")
        for mapping in self.mappings:
            concept = projection["concepts"].get(mapping.concept_id)
            if concept is None or concept["label"] != mapping.label or concept["in_scheme"] != self.scheme:
                raise ValueError("Ontology mapping has an unknown or inconsistent canonical reference")
            if self.framework == "toulmin" and (mapping.relationship != "exact"
                    or mapping.native_value != mapping.concept_id.rpartition("/")[2]
                    or not any(parent.endswith("/argument_role") for parent in concept.get("broader", []))):
                raise ValueError("Exact Toulmin mapping must preserve its registered role")
        if self.framework != "toulmin":
            mappings, unmapped = _native_mapping_values(self.framework, projection)
            if self.mappings != mappings or self.unmapped_native_values != unmapped:
                raise ValueError("Ontology mappings must reproduce the registered native inventory")
        else:
            if self.mappings != _toulmin_mapping_values(projection) or self.unmapped_native_values:
                raise ValueError("Toulmin mappings must include every registered role exactly once")
        return self


@cache
def toulmin_role_alignment() -> NativeOntologyAlignment:
    """Central explicitly registers the six Toulmin roles verbatim.

    This function resolves their IDs; it does not classify source content or
    generalize the mapping to other analytical frameworks.
    """
    raw = resources.files("rdam").joinpath("resources/discourse-concepts.json").read_bytes()
    projection = json.loads(raw)
    return NativeOntologyAlignment(
        authority=projection["authority"], scheme=projection["scheme"], source=projection["source"],
        source_identity=Sha256Identity(hex_digest=projection["source_sha256"]),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
        mappings=_toulmin_mapping_values(projection),
    )


def _toulmin_mapping_values(projection: dict[str, Any]) -> tuple[NativeConceptMapping, ...]:
    concepts = projection["concepts"]
    parents = [concept for concept in concepts.values() if concept["id"].endswith("/argument_role")]
    if len(parents) != 1:
        raise ValueError("Toulmin role authority must resolve to one registered group")
    parent = parents[0]
    mappings: list[NativeConceptMapping] = []
    for identifier, concept in concepts.items():
        if parent["id"] not in concept.get("broader", []):
            continue
        if identifier != concept["id"] or concept["in_scheme"] != projection["scheme"]:
            raise ValueError("Toulmin role identity is inconsistent with its authority")
        mappings.append(NativeConceptMapping(
            native_value=identifier.rpartition("/")[2], concept_id=identifier,
            label=concept["label"], relationship="exact",
        ))
    if not mappings:
        raise ValueError("Toulmin role authority is empty")
    return tuple(mappings)


def _native_values(framework: AlignedFramework) -> tuple[str, ...]:
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
            from rdam.dung.output import ExtensionOutput
            return tuple(ExtensionOutput.model_fields)
        case "sdrt":
            from rdam.sdrt.graph import RelationStructure
            return tuple(item.value for item in RelationStructure)
        case _:
            raise ValueError(f"No native inventory binding for {framework}")


def _native_mapping_values(
    framework: AlignedFramework, projection: dict[str, Any],
) -> tuple[tuple[NativeConceptMapping, ...], tuple[str, ...]]:
    profile: dict[str, Any] = {}
    for concept in projection["concepts"].values():
        if framework == "walton" and not any(
            parent.endswith("/scheme") for parent in concept.get("broader", [])
        ):
            continue
        value = concept["label"] if framework == "pdtb" else concept["id"].rpartition("/")[2]
        if value in profile:
            raise ValueError("Ambiguous canonical vocabulary binding")
        profile[value] = concept
    mappings: list[NativeConceptMapping] = []
    unmapped: list[str] = []
    for value in _native_values(framework):
        concept = profile.get(value)
        if concept is None:
            unmapped.append(value)
        else:
            mappings.append(NativeConceptMapping(
                native_value=value, concept_id=concept["id"], label=concept["label"], relationship="exact",
            ))
    return tuple(mappings), tuple(unmapped)


@cache
def pdtb_sense_alignment() -> NativeOntologyAlignment:
    """Resolve PDTB senses without losing direction or pragmatic qualifiers."""
    return native_vocabulary_alignment("pdtb")


@cache
def native_vocabulary_alignment(framework: AlignedFramework) -> NativeOntologyAlignment:
    """Resolve the bound closed inventory; SDRT binds structural classes only."""
    if framework == "toulmin":
        return toulmin_role_alignment()
    raw, projection = _authority(framework)
    mappings, unmapped = _native_mapping_values(framework, projection)
    return NativeOntologyAlignment(
        framework=framework, authority=projection["authority"], scheme=projection["scheme"],
        source=projection["source"], source_identity=Sha256Identity(hex_digest=projection["source_sha256"]),
        projection_identity=Sha256Identity(hex_digest=sha256_bytes(raw)),
        mappings=mappings, unmapped_native_values=unmapped,
    )
