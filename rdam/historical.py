"""Explicit v1 persisted contracts. Never synthesize current analytical fields."""

from collections.abc import Mapping
from typing import Annotated, Literal, Self, cast

from pydantic import Field, field_serializer, field_validator, model_validator

from rdam._immutable_json import freeze_json_object, thaw_json
from rdam._strict import JsonValue, SemanticVersion, Sha256Identity, StrictModel, semantic_sha256
from rdam._contract_types import (
    SourceIdentity,
    ProviderProvenance,
    ProviderDependencyReference,
    UnavailableOutcome,
    FailedOutcome,
    TechniqueCapability,
)
from rdam.frameworks import BOUNDARY_TECHNIQUES, Technique
from rdam.ingest.contracts.preparation import PreparationReceipt, PreparedRange
from rdam.ingest.contracts.source import SourceAnchor

AGGREGATE_CONTRACT = "rdam.aggregate"
CAPABILITIES_CONTRACT = "rdam.capabilities"
NATIVE_RESULT_CONTRACT = "rdam.native_result"
CONTRACT_VERSION = "1.0.0"
_SNAKE = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"


class HistoricalResultSourceAlignment(StrictModel):
    """An exact native payload quote mapped to the shared source, without changing the payload."""

    payload_path: str = Field(min_length=1)
    prepared_range: PreparedRange
    contributing_item_ids: tuple[str, ...] = Field(min_length=1)
    source_anchors: tuple[SourceAnchor, ...] = Field(min_length=1)


def _no_alignments(value: tuple[HistoricalResultSourceAlignment, ...]) -> bool:
    return not value


class HistoricalNativeTechniqueResult(StrictModel):
    """One technique's unchanged native payload, with analytical and artifact identities.

    The provider declares exact execution-only object paths. The semantic digest
    normalizes those values to null; the artifact digest still binds every byte of
    their JSON values. No generic machine code interprets a technique's schema.
    """

    contract: Literal["rdam.native_result"] = NATIVE_RESULT_CONTRACT
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION
    technique: Technique
    formalism_id: str = Field(pattern=_SNAKE)
    provider_id: str = Field(min_length=1)
    provider_contract_version: SemanticVersion
    source: SourceIdentity
    payload: Mapping[str, JsonValue]
    provenance: ProviderProvenance
    source_alignment: tuple[HistoricalResultSourceAlignment, ...] = Field(default=(), exclude_if=_no_alignments)
    execution_fields: tuple[tuple[str, ...], ...] = ()
    artifact_digest: Sha256Identity | None = None
    semantic_digest: Sha256Identity | None = None

    @field_validator("payload", mode="before")
    @classmethod
    def normalize_payload(cls, value: object) -> object:
        return thaw_json(cast(Mapping[str, JsonValue], value)) if isinstance(value, Mapping) else value

    @field_validator("payload", mode="after")
    @classmethod
    def freeze_payload(cls, value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
        return freeze_json_object(value)

    @field_serializer("payload")
    def serialize_payload(self, value: Mapping[str, JsonValue]) -> object:
        return thaw_json(value)

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        complete = self.model_dump(exclude={"semantic_digest", "artifact_digest"})
        artifact = Sha256Identity(hex_digest=semantic_sha256(complete))
        if self.artifact_digest is not None and self.artifact_digest != artifact:
            raise ValueError("native result artifact digest mismatch")
        object.__setattr__(self, "artifact_digest", artifact)
        if len(set(self.execution_fields)) != len(self.execution_fields):
            raise ValueError("execution field paths must be unique")
        payload = cast(dict[str, object], complete["payload"])
        for path in self.execution_fields:
            if not path or any(not key for key in path):
                raise ValueError("execution fields must name nonempty payload paths")
            parent = payload
            for key in path[:-1]:
                value = parent.get(key)
                if not isinstance(value, dict):
                    raise ValueError("execution field path does not address a payload object")
                parent = cast(dict[str, object], value)
            if path[-1] not in parent:
                raise ValueError("execution field path does not exist in payload")
            parent[path[-1]] = None
        expected = Sha256Identity(hex_digest=semantic_sha256(complete))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("native result semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class HistoricalResultOutcome(StrictModel):
    kind: Literal["result"] = "result"
    result: HistoricalNativeTechniqueResult


type HistoricalOutcome = Annotated[
    HistoricalResultOutcome | UnavailableOutcome | FailedOutcome, Field(discriminator="kind")
]


def outcome_technique(outcome: HistoricalResultOutcome | UnavailableOutcome | FailedOutcome) -> Technique:
    match outcome:
        case HistoricalResultOutcome():
            return outcome.result.technique
        case UnavailableOutcome():
            return outcome.technique
        case FailedOutcome():
            return outcome.failure.technique


class HistoricalAggregateAnalysis(StrictModel):
    """N explicit outcomes over one source — never a merged node-and-edge view (FR-013, FR-014)."""

    contract: Literal["rdam.aggregate"] = AGGREGATE_CONTRACT
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION
    source: SourceIdentity
    outcomes: tuple[HistoricalOutcome, ...] = Field(min_length=1)
    lineage: tuple[ProviderDependencyReference, ...] = ()
    preparation: PreparationReceipt | None = None
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_aggregate(self) -> Self:
        if (
            self.preparation is not None
            and self.preparation.inventory.source.byte_identity.hex_digest != self.source.source_id.hex_digest
        ):
            raise ValueError("preparation identity differs from aggregate source")
        techniques = [outcome_technique(item) for item in self.outcomes]
        if len(techniques) != len(set(techniques)):
            raise ValueError("an aggregate carries at most one outcome per technique")
        results_by_technique: dict[Technique, HistoricalNativeTechniqueResult] = {}
        results_by_digest: dict[Sha256Identity, HistoricalNativeTechniqueResult] = {}
        for item in self.outcomes:
            if isinstance(item, HistoricalResultOutcome):
                if item.result.source != self.source:
                    raise ValueError("every native result must be about the aggregate's source")
                results_by_technique[item.result.technique] = item.result
                if item.result.semantic_digest is not None:
                    results_by_digest[item.result.semantic_digest] = item.result
        for reference in self.lineage:
            consumer = results_by_technique.get(reference.consumer_technique)
            if consumer is None:
                raise ValueError("lineage consumer is not a successful result of this aggregate")
            if reference.consumer_provider_id != consumer.provider_id:
                raise ValueError("lineage consumer provider does not match the consumer result")
            if reference.consumer_contract_version != consumer.provider_contract_version:
                raise ValueError("lineage consumer contract does not match the consumer result")
            upstream = results_by_digest.get(reference.upstream_result_identity)
            if upstream is None or upstream.technique is not reference.upstream_technique:
                raise ValueError("lineage names an upstream result that is not a result of this aggregate")
            if reference.upstream_provider_id != upstream.provider_id:
                raise ValueError("lineage upstream provider does not match the upstream result")
            if reference.upstream_contract_version != upstream.provider_contract_version:
                raise ValueError("lineage upstream contract does not match the upstream result")
            if reference.upstream_model_identity != upstream.provenance.model_identity:
                raise ValueError("lineage upstream model does not match the upstream result")
        semantic = self.model_dump(exclude={"semantic_digest", "outcomes"})
        semantic["outcomes"] = tuple(
            {"kind": item.kind, "result_identity": item.result.semantic_digest}
            if isinstance(item, HistoricalResultOutcome)
            else item.model_dump()
            for item in self.outcomes
        )
        expected = Sha256Identity(hex_digest=semantic_sha256(semantic))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("aggregate semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    def outcome_for(self, technique: Technique) -> HistoricalResultOutcome | UnavailableOutcome | FailedOutcome | None:
        return next((item for item in self.outcomes if outcome_technique(item) is technique), None)


class HistoricalMachineCapabilities(StrictModel):
    """Every technique the machine knows, each in exactly one state; side-effect-free to produce."""

    contract: Literal["rdam.capabilities"] = CAPABILITIES_CONTRACT
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION
    techniques: tuple[TechniqueCapability, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def every_boundary_exactly_once(self) -> Self:
        declared = tuple(item.technique for item in self.techniques)
        if declared != BOUNDARY_TECHNIQUES:
            raise ValueError("capabilities must list every technique boundary exactly once, in spec order")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("capabilities semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    def capability_for(self, technique: Technique) -> TechniqueCapability:
        return next(item for item in self.techniques if item.technique is technique)
