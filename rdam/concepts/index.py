"""Immutable runtime projection of Central_Configs v5.0.0 proper-noun surface rules."""

from functools import cache
from importlib.resources import files
from pathlib import Path
import re
from typing import Literal, Self

from pydantic import Field, model_validator

from rdam._canonical import semantic_sha256
from rdam.ingest.contracts.base import StrictContractModel
from rdam.serialization import decode_object

_CURIE_PATTERN = r"^coe:C[0-9]{5}$"
_WILDCARD_META_RE = re.compile(r"[*+?^$\\|()\[\]{}]")

type MatchPolicy = Literal["unambiguous", "case_exact", "context_anchored", "never_link"]
type ResourceStatus = Literal["active", "deprecated", "historical_only"]


class SemanticResource(StrictContractModel):
    """One LinkableProperNoun resource projected from Central_Configs v5.0.0."""

    curie: str = Field(pattern=_CURIE_PATTERN)
    pref_label: str = Field(min_length=1)
    definition: str
    collection_name: str = Field(min_length=1)
    status: ResourceStatus = "active"


class LexicalEntry(StrictContractModel):
    """One regex-free SurfaceMatchRule projected from Central_Configs v5.0.0 match_lexicon."""

    curie: str = Field(pattern=_CURIE_PATTERN)
    pref_label: str = Field(min_length=1)
    collection_name: str = Field(min_length=1)
    surface: str = Field(min_length=1)
    match_policy: MatchPolicy = "unambiguous"
    case_sensitive: bool = False
    anchor_window_tokens: int = Field(default=25, ge=5, le=100)
    context_anchors: tuple[str, ...] = ()
    negative_phrases: tuple[str, ...] = ()
    requires_llm_disambiguation: bool = False

    @model_validator(mode="after")
    def coherent_surface_rule(self) -> Self:
        if not self.surface.strip() or _WILDCARD_META_RE.search(self.surface):
            raise ValueError("surface must be a non-empty literal without regex metacharacters")
        if self.match_policy == "context_anchored" and not self.context_anchors:
            raise ValueError("context_anchored surface rules require at least one context_anchor")
        if any(not item.strip() for item in self.context_anchors):
            raise ValueError("context_anchors cannot contain empty strings")
        if any(not item.strip() for item in self.negative_phrases):
            raise ValueError("negative_phrases cannot contain empty strings")
        return self


class OntologyIdentity(StrictContractModel):
    distribution_id: str
    version: str
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    domains: tuple[str, ...]


class IndexProjection(StrictContractModel):
    contract: Literal["rdam.concept_index"] = "rdam.concept_index"
    contract_version: Literal["3.0.0"] = "3.0.0"
    distribution_id: str
    version: str
    domains: tuple[str, ...]
    resources: tuple[SemanticResource, ...]
    entries: tuple[LexicalEntry, ...]
    content_digest: str = ""

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        resources = {item.curie: item for item in self.resources}
        if len(resources) != len(self.resources):
            raise ValueError("duplicate ontology resource identifier")
        if not self.domains or tuple(sorted(set(self.domains))) != self.domains:
            raise ValueError("domains must be non-empty, unique and sorted")
        for resource in self.resources:
            if resource.collection_name not in self.domains:
                raise ValueError("resource collection_name absent from projection domains")
        for entry in self.entries:
            owner = resources.get(entry.curie)
            if owner is None:
                raise ValueError(f"dangling surface rule curie: {entry.curie}")
            if entry.pref_label != owner.pref_label or entry.collection_name != owner.collection_name:
                raise ValueError(f"surface rule metadata diverges from resource {entry.curie}")
        expected = semantic_sha256(self.model_dump(exclude={"content_digest"}))
        if self.content_digest and self.content_digest != expected:
            raise ValueError("ontology projection content digest mismatch")
        object.__setattr__(self, "content_digest", expected)
        return self


@cache
def _packaged_projection() -> IndexProjection:
    payload = files("rdam").joinpath("resources/concept-index.json").read_bytes()
    decoded = decode_object(payload)
    if not decoded.get("content_digest"):
        raise ValueError("ontology projection lacks its recorded content digest")
    return IndexProjection.model_validate_json(payload)


class ConceptIndex(StrictContractModel):
    """Load a generated projection without LinkML, YAML, SQLite, models or network access."""

    projection: IndexProjection
    domains: tuple[str, ...]

    @model_validator(mode="after")
    def valid_selection(self) -> Self:
        if not self.domains or tuple(sorted(set(self.domains))) != self.domains:
            raise ValueError("selected domains must be non-empty, unique and sorted")
        unknown = set(self.domains) - set(self.projection.domains)
        if unknown:
            raise ValueError(f"unknown ontology domains: {sorted(unknown)}")
        return self

    @classmethod
    def load(cls, path: Path | None = None, *, domains: tuple[str, ...] | None = None) -> Self:
        """Read a packaged or explicit JSON projection of Central_Configs v5.0.0."""
        if path is None:
            projection = _packaged_projection()
        else:
            location = path / "concept-index.json" if path.is_dir() else path
            payload = location.read_bytes()
            decoded = decode_object(payload)
            if not decoded.get("content_digest"):
                raise ValueError("ontology projection lacks its recorded content digest")
            projection = IndexProjection.model_validate_json(payload)
        return cls(projection=projection, domains=tuple(sorted(domains)) if domains is not None else projection.domains)

    @property
    def identity(self) -> OntologyIdentity:
        return OntologyIdentity(
            distribution_id=self.projection.distribution_id,
            version=self.projection.version,
            content_digest=self.projection.content_digest,
            domains=self.domains,
        )

    def require_active(self, curie: str) -> SemanticResource:
        resource = next((item for item in self.projection.resources if item.curie == curie), None)
        if resource is None:
            raise ValueError(f"unknown ontology identifier: {curie}")
        if resource.status == "historical_only" or resource.collection_name not in self.domains:
            raise ValueError(f"ontology identifier is historical_only or outside selected domains: {curie}")
        return resource
