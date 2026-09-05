"""Stable identity and input primitives shared by current and historical records."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self, cast

from pydantic import Field, field_serializer, field_validator, model_validator

from rdam._immutable_json import freeze_json_object, thaw_json
from rdam._strict import JsonValue, SemanticVersion, Sha256Identity, StrictModel, sha256_bytes
from rdam.frameworks import STRUCTURED_INPUT_TECHNIQUES, Technique, technique_curie
from rdam.ingest.contracts.source import SourceArtifact

_SNAKE = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"


class Retryability(StrEnum):
    """Information for the caller only; the machine never retries (capability contract §Retryability)."""

    RETRYABLE = "retryable"
    NOT_RETRYABLE = "not_retryable"
    UNKNOWN = "unknown"


class UnavailableReason(StrEnum):
    """Stable, enumerated reasons a technique cannot run right now.

    Availability means the provider can actually run, nothing more. Unavailability is
    never retryable: it changes only through an external state change — implementing a
    provider, or configuring a model — so re-asking without one returns the same answer.
    """

    NOT_IMPLEMENTED = "not_implemented"
    MISSING_STRUCTURED_INPUT = "missing_structured_input"
    MODEL_UNAVAILABLE = "model_unavailable"


class AvailableCapability(StrictModel):
    state: Literal["available"] = "available"
    provider_id: str = Field(min_length=1)
    contract_version: SemanticVersion


class UnavailableCapability(StrictModel):
    state: Literal["unavailable"] = "unavailable"
    reason: UnavailableReason


type CapabilityState = Annotated[AvailableCapability | UnavailableCapability, Field(discriminator="state")]


class FormalismDeclaration(StrictModel):
    """One result-kind a provider emits, carrying its own canonical identity and state."""

    formalism_id: str = Field(pattern=_SNAKE)
    technique: Technique
    technique_curie: str = Field(min_length=1)
    capability: CapabilityState

    @model_validator(mode="after")
    def curie_is_the_canonical_identity(self) -> Self:
        expected = technique_curie(self.technique)
        if self.technique_curie != expected:
            raise ValueError(
                f"formalism {self.formalism_id!r} names {self.technique_curie!r}; Central names {expected!r}"
            )
        return self


class ProviderProvenance(StrictModel):
    """Exact code, configuration, and model identity behind a provider."""

    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_revision: str | None = Field(default=None, min_length=1)
    model_identity: str | None = None
    licence: str = Field(min_length=1)


class SourceIdentity(StrictModel):
    """One source, identified by content digest; shared by every outcome of an aggregate."""

    source_id: Sha256Identity
    source_name: str | None = None
    media_type: str | None = None

    @classmethod
    def from_bytes(cls, payload: bytes, *, source_name: str | None = None, media_type: str | None = None) -> Self:
        return cls(
            source_id=Sha256Identity(hex_digest=sha256_bytes(payload)), source_name=source_name, media_type=media_type
        )

    @classmethod
    def from_text(cls, text: str, *, source_name: str | None = None) -> Self:
        return cls.from_bytes(text.encode("utf-8"), source_name=source_name, media_type="text/plain; charset=utf-8")


class ProviderFailure(StrictModel):
    """A typed per-request failure with a mandatory retryability classification."""

    technique: Technique
    provider_id: str = Field(min_length=1)
    failed_operation: str = Field(pattern=_SNAKE)
    retryability: Retryability
    code: str = Field(pattern=_SNAKE)
    exception_type: str = Field(min_length=1)
    message_template: str = Field(pattern=_SNAKE)
    message_parameters: tuple[tuple[str, str], ...] = ()


class ProviderError(RuntimeError):
    """The only exception a provider may raise from ``analyse``; carries its typed failure."""

    def __init__(self, failure: ProviderFailure) -> None:
        self.failure = failure
        super().__init__(f"{failure.technique.value}/{failure.code}: {failure.message_template}")


class UnavailableOutcome(StrictModel):
    kind: Literal["unavailable"] = "unavailable"
    technique: Technique
    reason: UnavailableReason


class FailedOutcome(StrictModel):
    kind: Literal["failed"] = "failed"
    failure: ProviderFailure


class ProviderDependencyReference(StrictModel):
    """One provider consumed a specific result of another; both outputs stay separate (FR-015)."""

    consumer_technique: Technique
    consumer_provider_id: str = Field(min_length=1)
    consumer_contract_version: SemanticVersion
    upstream_technique: Technique
    upstream_provider_id: str = Field(min_length=1)
    upstream_contract_version: SemanticVersion
    upstream_result_identity: Sha256Identity
    upstream_model_identity: str | None = None


class TechniqueCapability(StrictModel):
    technique: Technique
    technique_curie: str = Field(min_length=1)
    capability: CapabilityState
    formalisms: tuple[FormalismDeclaration, ...] = ()
    requires_structured_input: bool

    @model_validator(mode="after")
    def canonical_identity_and_input_mode(self) -> Self:
        if self.technique_curie != technique_curie(self.technique):
            raise ValueError("technique capability must carry its canonical identity")
        expected_structured = self.technique in STRUCTURED_INPUT_TECHNIQUES
        if self.requires_structured_input != expected_structured:
            raise ValueError("technique capability has the wrong structured-input mode")
        return self


class UpstreamResultReference(StrictModel):
    """The exact native result a caller derived a structured input from (FR-015).

    The reference names the artifact by its semantic digest; the aggregate request must
    carry that result in ``upstream_results`` so the aggregate records the exact upstream
    artifact and provider identity, with both native outputs kept separate.
    """

    technique: Technique
    result_identity: Sha256Identity


class StructuredInput(StrictModel):
    """A caller-supplied structure for a formal technique (FR-016, FR-017).

    ``derived_from`` declares, explicitly, that the caller built this structure from an
    earlier native result of another technique. The machine never derives a structure
    itself; it records the declared consumption as lineage.
    """

    technique: Technique
    payload: Mapping[str, JsonValue]
    derived_from: UpstreamResultReference | None = None

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
    def only_for_structured_input_techniques(self) -> Self:
        if self.technique not in STRUCTURED_INPUT_TECHNIQUES:
            raise ValueError(f"{self.technique.value} does not accept structured input")
        return self


class FormalismChoice(StrictModel):
    """Ask one requested technique for a specific declared formalism (e.g. RST's ``erst_graph``)."""

    technique: Technique
    formalism_id: str = Field(pattern=_SNAKE)


class SourceArtifactRef(StrictModel):
    """An immutable materialized source; constructing it performs no inventory."""

    artifact: SourceArtifact


__all__ = [
    "AvailableCapability",
    "CapabilityState",
    "FailedOutcome",
    "FormalismChoice",
    "FormalismDeclaration",
    "ProviderDependencyReference",
    "ProviderError",
    "ProviderFailure",
    "ProviderProvenance",
    "Retryability",
    "SourceArtifactRef",
    "SourceIdentity",
    "StructuredInput",
    "TechniqueCapability",
    "UnavailableCapability",
    "UnavailableOutcome",
    "UnavailableReason",
    "UpstreamResultReference",
]
