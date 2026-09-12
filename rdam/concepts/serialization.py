"""Canonical JSON and independent JSONL mention records."""

from collections.abc import Iterator
from typing import Any, Literal, Self

from pydantic import model_validator

from rdam._canonical import canonical_json_bytes
from rdam.serialization import decode_object
from rdam.concepts.contracts import ConceptLinkRequest, ConceptLinkResult, MatchingOptions, Mention, Surface, occurrence_identity
from rdam.concepts.index import OntologyIdentity
from rdam.ingest.contracts.base import Sha256Identity, StrictContractModel
from rdam.ingest.contracts.source import SourceContractIdentity, SourceSummary


class MentionExport(StrictContractModel):
    contract: Literal["rdam.concept_mention"] = "rdam.concept_mention"
    contract_version: Literal["1.0.0"] = "1.0.0"
    source: SourceSummary
    inventory_identity: Sha256Identity
    source_adapter: SourceContractIdentity
    ontology: OntologyIdentity
    algorithm: str
    algorithm_version: str
    implementation_identity: str
    options: MatchingOptions
    surface: Surface
    mention: Mention

    @model_validator(mode="after")
    def exact_evidence(self) -> Self:
        mention, surface = self.mention, self.surface
        if (mention.item_id, mention.field_pointer) != (surface.item_id, surface.field_pointer):
            raise ValueError("exported mention addresses another surface")
        if surface.text[mention.start:mention.end] != mention.quote:
            raise ValueError("exported quote differs from surface")
        if mention.occurrence_id != occurrence_identity(self.inventory_identity, mention):
            raise ValueError("exported occurrence identity mismatch")
        return self


def mention_records(result: ConceptLinkResult) -> Iterator[MentionExport]:
    result = ConceptLinkResult.model_validate(result.model_dump())
    surfaces = {(item.item_id, item.field_pointer): item for item in result.surfaces}
    for mention in result.mentions:
        yield MentionExport(
            source=result.source, inventory_identity=result.inventory_identity, source_adapter=result.source_adapter,
            ontology=result.ontology, algorithm=result.algorithm, algorithm_version=result.algorithm_version,
            implementation_identity=result.implementation_identity, options=result.options,
            surface=surfaces[mention.item_id, mention.field_pointer], mention=mention,
        )


def export_jsonl(result: ConceptLinkResult) -> bytes:
    return b"\n".join(canonical_json_bytes(item) for item in mention_records(result))


def load_request(payload: bytes | str) -> ConceptLinkRequest:
    return ConceptLinkRequest.model_validate_json(canonical_json_bytes(decode_object(payload)))


def load_result(payload: bytes | str) -> ConceptLinkResult:
    parsed = decode_object(payload)
    if not parsed.get("semantic_digest"):
        raise ValueError("persisted concept result requires its semantic digest")
    return ConceptLinkResult.model_validate_json(canonical_json_bytes(parsed))


def serialize(record: ConceptLinkRequest | ConceptLinkResult | MentionExport) -> bytes:
    validated = type(record).model_validate(record.model_dump())
    return canonical_json_bytes(validated)


def schema(name: str, *, mode: Literal["validation", "serialization"] = "validation") -> dict[str, Any]:
    models = {"concept-link-request": ConceptLinkRequest, "concept-links": ConceptLinkResult, "concept-mention": MentionExport}
    if name not in models:
        raise ValueError(f"unknown concept schema: {name}")
    document = models[name].model_json_schema(mode=mode)
    document["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    document["$id"] = f"https://schemas.rdam.local/{models[name].model_fields['contract'].default}/1.0.0/{mode}.schema.json"
    return document
