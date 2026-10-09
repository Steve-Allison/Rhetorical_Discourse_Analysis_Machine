"""Closed wire contracts for lexical mentions, never semantic acceptance."""

from typing import Literal, Self

from pydantic import ConfigDict, Field, model_validator

from rdam._canonical import semantic_sha256
from rdam.concepts.index import LexicalEntry, OntologyIdentity, SemanticResource
from rdam.ingest.contracts.base import Sha256Identity, StrictContractModel
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import (
    ContentClass, SourceAnchor, SourceArtifact, SourceContractIdentity, SourceOrigin, SourceSummary,
)


class MatchingOptions(StrictContractModel):
    acronym_case_sensitive: bool = True


class Surface(StrictContractModel):
    item_id: str
    field_pointer: str
    text: str
    text_identity: str = ""
    classification: ContentClass
    origin: SourceOrigin
    anchors: tuple[SourceAnchor, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def identify(self) -> Self:
        expected = semantic_sha256(self.text)
        if self.text_identity and self.text_identity != expected:
            raise ValueError("surface text identity mismatch")
        object.__setattr__(self, "text_identity", expected)
        return self


class ExcludedSurface(StrictContractModel):
    item_id: str
    field_pointer: str
    reason: Literal["non_text", "redacted", "duplicate", "empty"]
    duplicate_of: str | None = None


class CandidateSpan(StrictContractModel):
    item_id: str
    field_pointer: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def exact_length(self) -> Self:
        if self.end - self.start != len(self.quote):
            raise ValueError("candidate range must equal quote length in Python characters")
        return self


class Candidate(StrictContractModel):
    resource: SemanticResource
    reasons: tuple[LexicalEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_target(self) -> Self:
        if any(reason.target != self.resource.identifier for reason in self.reasons):
            raise ValueError("candidate reason target mismatch")
        if self.resource.status == "retired":
            raise ValueError("retired resources cannot be active candidates")
        return self


class Mention(CandidateSpan):
    occurrence_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidates: tuple[Candidate, ...]
    resolution: Literal["unique", "ambiguous", "unmapped"]

    @model_validator(mode="after")
    def consistent_resolution(self) -> Self:
        expected = "unmapped" if not self.candidates else "unique" if len(self.candidates) == 1 else "ambiguous"
        if self.resolution != expected:
            raise ValueError("resolution differs from candidate count")
        identifiers = tuple(item.resource.identifier for item in self.candidates)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("candidates must have unique, sorted identifiers")
        return self


class ConceptLinkRequest(StrictContractModel):
    model_config = ConfigDict(json_schema_extra={
        "oneOf": [
            {"required": ["source"], "properties": {"source": {"not": {"type": "null"}}, "inventory": {"type": "null"}}},
            {"required": ["inventory"], "properties": {"inventory": {"not": {"type": "null"}}, "source": {"type": "null"}}},
        ]
    })
    contract: Literal["rdam.concept_link_request"] = "rdam.concept_link_request"
    contract_version: Literal["1.0.0"] = "1.0.0"
    source: SourceArtifact | None = None
    inventory: ContentInventory | None = None
    domains: tuple[str, ...] | None = None
    options: MatchingOptions = MatchingOptions()
    supplied_candidates: tuple[CandidateSpan, ...] | None = None

    @model_validator(mode="after")
    def one_input(self) -> Self:
        if (self.source is None) == (self.inventory is None):
            raise ValueError("provide exactly one source or inventory")
        return self


class ConceptLinkResult(StrictContractModel):
    contract: Literal["rdam.concept_links"] = "rdam.concept_links"
    contract_version: Literal["2.0.0"] = "2.0.0"
    source: SourceSummary
    inventory_identity: Sha256Identity
    source_adapter: SourceContractIdentity
    ontology: OntologyIdentity
    algorithm: Literal["unicode-lexical-surfaces"] = "unicode-lexical-surfaces"
    algorithm_version: Literal["1.0.0"] = "1.0.0"
    implementation_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    options: MatchingOptions
    surfaces: tuple[Surface, ...]
    exclusions: tuple[ExcludedSurface, ...]
    supplied_candidates: tuple[CandidateSpan, ...] | None = None
    mentions: tuple[Mention, ...]
    semantic_digest: str = ""

    @model_validator(mode="after")
    def consistent_evidence(self) -> Self:
        surfaces = {(item.item_id, item.field_pointer): item for item in self.surfaces}
        if len(surfaces) != len(self.surfaces):
            raise ValueError("duplicate surface pointer")
        occurrences: set[str] = set()
        for mention in self.mentions:
            surface = surfaces.get((mention.item_id, mention.field_pointer))
            if surface is None or surface.text[mention.start:mention.end] != mention.quote:
                raise ValueError("mention does not resolve to exact surface evidence")
            expected = occurrence_identity(self.inventory_identity, mention)
            if mention.occurrence_id != expected or expected in occurrences:
                raise ValueError("duplicate or invalid occurrence identity")
            occurrences.add(expected)
            if not mention.candidates and self.supplied_candidates is None:
                raise ValueError("unmapped mentions require supplied candidates")
        expected = semantic_sha256(self.model_dump(exclude={"semantic_digest"}))
        if self.semantic_digest and self.semantic_digest != expected:
            raise ValueError("concept result semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


def occurrence_identity(inventory: Sha256Identity, span: CandidateSpan) -> str:
    return semantic_sha256({
        "inventory": inventory, "item": span.item_id, "field": span.field_pointer,
        "start": span.start, "end": span.end, "quote": span.quote,
    })
