"""Immutable runtime projection of Central's authored semantic resources."""

from importlib.resources import files
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from rdam._canonical import semantic_sha256
from rdam.ingest.contracts.base import StrictContractModel
from rdam.serialization import decode_object


# Central's terminology model (coe_terminology): every name other than a resource's label is a
# Term inline on that resource, typed and given a normative status after LexInfo.
type TermType = Literal["full_form", "short_form", "acronym", "initialism", "abbreviation", "product_code", "codename"]
type TermStatus = Literal["admitted", "superseded", "deprecated"]

# Letter-code names whose case distinguishes them from ordinary words ("Ps", "AEM").
CASE_SENSITIVE_TERM_TYPES: frozenset[TermType] = frozenset({"acronym", "initialism", "product_code"})


class SemanticResource(StrictContractModel):
    identifier: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str
    domain: str = Field(min_length=1)
    status: Literal["draft", "candidate", "canonical", "retired"]
    resource_type: str = Field(min_length=1)
    source_path: str = Field(min_length=1)


class LexicalEntry(StrictContractModel):
    """One name of one resource: its label, or one of its Central terms."""

    literal: str = Field(min_length=1)
    target: str = Field(min_length=1)
    method: Literal["label", "term"]
    term_type: TermType | None = None
    term_status: TermStatus | None = None
    valid_from: str | None = Field(default=None, pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$")
    valid_to: str | None = Field(default=None, pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$")
    usage_note: str | None = None

    @model_validator(mode="after")
    def coherent_reason(self) -> Self:
        if self.method == "label":
            if any(value is not None for value in (
                self.term_type, self.term_status, self.valid_from, self.valid_to, self.usage_note,
            )):
                raise ValueError("label evidence cannot carry term attributes")
        elif self.term_type is None or self.term_status is None:
            raise ValueError("term evidence requires its term type and status")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("term validity ends before it begins")
        return self

    @property
    def case_sensitive(self) -> bool:
        return self.term_type in CASE_SENSITIVE_TERM_TYPES


class OntologyIdentity(StrictContractModel):
    distribution_id: str
    version: str
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    domains: tuple[str, ...]


class IndexProjection(StrictContractModel):
    contract: Literal["rdam.concept_index"] = "rdam.concept_index"
    contract_version: Literal["2.0.0"] = "2.0.0"
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
