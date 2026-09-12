"""Immutable runtime projection of Central's authored semantic resources."""

from importlib.resources import files
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from rdam._canonical import semantic_sha256
from rdam.ingest.contracts.base import StrictContractModel
from rdam.serialization import decode_object


type SynonymScope = Literal["exact", "broad", "narrow", "acronym", "deprecated_form"]


class SemanticResource(StrictContractModel):
    identifier: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str
    domain: str = Field(min_length=1)
    status: Literal["draft", "candidate", "canonical", "retired"]
    resource_type: str = Field(min_length=1)
    source_path: str = Field(min_length=1)


class LexicalEntry(StrictContractModel):
    literal: str = Field(min_length=1)
    target: str = Field(min_length=1)
    method: Literal["label", "term", "synonym"]
    scope: SynonymScope = "exact"
    term_id: str | None = None
    sense_id: str | None = None
    definition: str | None = None
    distinguished_from: tuple[str, ...] = ()
    usage_note: str | None = None
    synonym_id: str | None = None
    status: Literal["draft", "candidate", "canonical", "retired"] = "canonical"

    @model_validator(mode="after")
    def coherent_reason(self) -> Self:
        if self.method == "label":
            if any((self.term_id, self.sense_id, self.synonym_id, self.definition)) or self.scope != "exact":
                raise ValueError("label evidence cannot carry terminology or synonym scope")
        elif not self.term_id or not self.sense_id or not self.definition:
            raise ValueError("terminology evidence requires term, sense and definition")
        if (self.method == "synonym") != (self.synonym_id is not None):
            raise ValueError("synonym evidence requires exactly one synonym identity")
        return self


class OntologyIdentity(StrictContractModel):
    distribution_id: str
    version: str
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    domains: tuple[str, ...]


class IndexProjection(StrictContractModel):
    contract: Literal["rdam.concept_index"] = "rdam.concept_index"
    contract_version: Literal["1.0.0"] = "1.0.0"
    distribution_id: str
    version: str
    domains: tuple[str, ...]
    source_files: tuple[tuple[str, str], ...]
    resources: tuple[SemanticResource, ...]
    entries: tuple[LexicalEntry, ...]
    authorable_predicates: tuple[str, ...]
    content_digest: str = ""

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        resources = {item.identifier: item for item in self.resources}
        if len(resources) != len(self.resources):
            raise ValueError("duplicate ontology resource identifier")
        if not self.domains or tuple(sorted(set(self.domains))) != self.domains:
            raise ValueError("domains must be non-empty, unique and sorted")
        for resource in self.resources:
            if resource.domain not in self.domains:
                raise ValueError("resource domain absent from distribution")
        for entry in self.entries:
            if entry.target not in resources:
                raise ValueError(f"dangling terminology target: {entry.target}")
            if entry.sense_id is not None:
                sense = resources.get(entry.sense_id)
                if sense is None or sense.resource_type != "TermSense":
                    raise ValueError("terminology sense is absent")
            for identifier in entry.distinguished_from:
                sense = resources.get(identifier)
                if sense is None or sense.resource_type != "TermSense":
                    raise ValueError("dangling distinguished_from sense")
        expected = semantic_sha256(self.model_dump(exclude={"content_digest"}))
        if self.content_digest and self.content_digest != expected:
            raise ValueError("ontology projection content digest mismatch")
        object.__setattr__(self, "content_digest", expected)
        return self


class ConceptIndex(StrictContractModel):
    """Load a generated projection without LinkML, YAML, models or network access."""

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
        """Read a packaged or explicit JSON projection of an identified distribution."""
        if path is None:
            payload = files("rdam").joinpath("resources/concept-index.json").read_bytes()
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
            distribution_id=self.projection.distribution_id, version=self.projection.version,
            content_digest=self.projection.content_digest, domains=self.domains,
        )

    def require_active(self, identifier: str) -> SemanticResource:
        resource = next((item for item in self.projection.resources if item.identifier == identifier), None)
        if resource is None:
            raise ValueError(f"unknown ontology identifier: {identifier}")
        if resource.status == "retired" or resource.domain not in self.domains:
            raise ValueError(f"ontology identifier is retired or outside selected domains: {identifier}")
        return resource
