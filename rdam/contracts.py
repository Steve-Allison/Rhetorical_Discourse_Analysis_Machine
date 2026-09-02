"""The aggregate analysis contract: the typed form of the 006 data model.

Entities here are the machine layer's — ``Provider``/``Formalism`` declarations,
``CapabilityState``, ``NativeTechniqueResult``, ``Outcome``, ``AggregateAnalysis``,
``ProviderDependencyReference`` — exactly as ``specs/006-rhetorical-discourse-machine/data-model.md``
defines them. Nothing here constrains a technique's *native* payload: it is an opaque JSON
object the machine never renames, removes, or reinterprets (FR-013).
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from rdam._strict import JsonValue, SemanticVersion, Sha256Identity, StrictModel, semantic_sha256, sha256_bytes
from rdam.frameworks import BOUNDARY_TECHNIQUES, STRUCTURED_INPUT_TECHNIQUES, Technique, technique_curie

AGGREGATE_CONTRACT: Literal["rdam.aggregate"] = "rdam.aggregate"
CAPABILITIES_CONTRACT: Literal["rdam.capabilities"] = "rdam.capabilities"
NATIVE_RESULT_CONTRACT: Literal["rdam.native_result"] = "rdam.native_result"
CONTRACT_VERSION: Literal["1.0.0"] = "1.0.0"

_SNAKE = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"


class Retryability(StrEnum):
    """Information for the caller only; the machine never retries (capability contract §Retryability)."""

    RETRYABLE = "retryable"
    NOT_RETRYABLE = "not_retryable"
    UNKNOWN = "unknown"


class UnavailableReason(StrEnum):
    """Stable, enumerated reasons (FR-020). Unavailability is never retryable."""

    NO_PROMOTED_IMPLEMENTATION = "no_promoted_implementation"
    WITHHELD = "withheld"
    RETIRED = "retired"
    REPLACED = "replaced"
    MISSING_STRUCTURED_INPUT = "missing_structured_input"


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
            raise ValueError(f"formalism {self.formalism_id!r} names {self.technique_curie!r}; Central names {expected!r}")
        return self


class ProviderProvenance(StrictModel):
    """Exact code, configuration, and model identity behind a provider (FR-023)."""

    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    source_revision: str | None = None
    model_identity: str | None = None
    licence_decision: str = Field(min_length=1)


class ProviderDeclaration(StrictModel):
    """A promoted provider's identity, formalisms, contract version, and standing state."""

    provider_id: str = Field(min_length=1)
    technique: Technique
    technique_curie: str = Field(min_length=1)
    formalisms: tuple[FormalismDeclaration, ...] = Field(min_length=1)
    contract_version: SemanticVersion
    provenance: ProviderProvenance
    capability: CapabilityState
    requires_structured_input: bool

    @model_validator(mode="after")
    def coherent_declaration(self) -> Self:
        if self.technique not in BOUNDARY_TECHNIQUES:
            raise ValueError(f"{self.technique.value!r} is a formalism, not a technique boundary")
        expected = technique_curie(self.technique)
        if self.technique_curie != expected:
            raise ValueError(f"provider {self.provider_id!r} names {self.technique_curie!r}; Central names {expected!r}")
        ids = [formalism.formalism_id for formalism in self.formalisms]
        if len(ids) != len(set(ids)):
            raise ValueError("formalism identifiers must be unique")
        if all(formalism.technique is not self.technique for formalism in self.formalisms):
            raise ValueError("a provider must declare at least one formalism of its own technique")
        if self.technique in STRUCTURED_INPUT_TECHNIQUES and not self.requires_structured_input:
            raise ValueError(f"{self.technique.value} analyses a supplied structure and must require structured input")
        if isinstance(self.capability, AvailableCapability):
            if self.capability.provider_id != self.provider_id:
                raise ValueError("available capability must name this provider")
            if self.capability.contract_version != self.contract_version:
                raise ValueError("available capability must carry this provider's contract version")
        return self

    def formalism(self, formalism_id: str) -> FormalismDeclaration | None:
        return next((item for item in self.formalisms if item.formalism_id == formalism_id), None)


class SourceIdentity(StrictModel):
    """One source, identified by content digest; shared by every outcome of an aggregate."""

    source_id: Sha256Identity
    source_name: str | None = None
    media_type: str | None = None

    @classmethod
    def from_bytes(cls, payload: bytes, *, source_name: str | None = None, media_type: str | None = None) -> Self:
        return cls(source_id=Sha256Identity(hex_digest=sha256_bytes(payload)), source_name=source_name, media_type=media_type)

    @classmethod
    def from_text(cls, text: str, *, source_name: str | None = None) -> Self:
        return cls.from_bytes(text.encode("utf-8"), source_name=source_name, media_type="text/plain; charset=utf-8")


class NativeTechniqueResult(StrictModel):
    """One technique's result in its own theory's terms. ``payload`` is opaque to the machine."""

    contract: Literal["rdam.native_result"] = NATIVE_RESULT_CONTRACT
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION
    technique: Technique
    formalism_id: str = Field(pattern=_SNAKE)
    provider_id: str = Field(min_length=1)
    provider_contract_version: SemanticVersion
    source: SourceIdentity
    payload: Mapping[str, JsonValue]
    provenance: ProviderProvenance
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("native result semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


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


class ResultOutcome(StrictModel):
    kind: Literal["result"] = "result"
    result: NativeTechniqueResult


class UnavailableOutcome(StrictModel):
    kind: Literal["unavailable"] = "unavailable"
    technique: Technique
    reason: UnavailableReason


class FailedOutcome(StrictModel):
    kind: Literal["failed"] = "failed"
    failure: ProviderFailure


type Outcome = Annotated[ResultOutcome | UnavailableOutcome | FailedOutcome, Field(discriminator="kind")]


def outcome_technique(outcome: ResultOutcome | UnavailableOutcome | FailedOutcome) -> Technique:
    match outcome:
        case ResultOutcome():
            return outcome.result.technique
        case UnavailableOutcome():
            return outcome.technique
        case FailedOutcome():
            return outcome.failure.technique


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


class AggregateAnalysis(StrictModel):
    """N explicit outcomes over one source — never a merged node-and-edge view (FR-013, FR-014)."""

    contract: Literal["rdam.aggregate"] = AGGREGATE_CONTRACT
    contract_version: Literal["1.0.0"] = CONTRACT_VERSION
    source: SourceIdentity
    outcomes: tuple[Outcome, ...] = Field(min_length=1)
    lineage: tuple[ProviderDependencyReference, ...] = ()
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_aggregate(self) -> Self:
        techniques = [outcome_technique(item) for item in self.outcomes]
        if len(techniques) != len(set(techniques)):
            raise ValueError("an aggregate carries at most one outcome per technique")
        result_digests: dict[Sha256Identity, Technique] = {}
        for item in self.outcomes:
            if isinstance(item, ResultOutcome):
                if item.result.source != self.source:
                    raise ValueError("every native result must be about the aggregate's source")
                if item.result.semantic_digest is not None:
                    result_digests[item.result.semantic_digest] = item.result.technique
        for reference in self.lineage:
            if reference.consumer_technique not in techniques:
                raise ValueError("lineage consumer is not an outcome of this aggregate")
            upstream = result_digests.get(reference.upstream_result_identity)
            if upstream is None or upstream is not reference.upstream_technique:
                raise ValueError("lineage names an upstream result that is not a result of this aggregate")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("aggregate semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    def outcome_for(self, technique: Technique) -> ResultOutcome | UnavailableOutcome | FailedOutcome | None:
        return next((item for item in self.outcomes if outcome_technique(item) is technique), None)


class TechniqueCapability(StrictModel):
    technique: Technique
    technique_curie: str = Field(min_length=1)
    capability: CapabilityState
    formalisms: tuple[FormalismDeclaration, ...] = ()
    requires_structured_input: bool


class MachineCapabilities(StrictModel):
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


class StructuredInput(StrictModel):
    """A caller-supplied structure for a formal technique (FR-016, FR-017)."""

    technique: Technique
    payload: Mapping[str, JsonValue]


class FormalismChoice(StrictModel):
    """Ask one requested technique for a specific declared formalism (e.g. RST's ``erst_graph``)."""

    technique: Technique
    formalism_id: str = Field(pattern=_SNAKE)


class AggregateRequest(StrictModel):
    source: SourceIdentity
    text: str | None
    techniques: tuple[Technique, ...] = Field(min_length=1)
    structured_inputs: tuple[StructuredInput, ...] = ()
    formalisms: tuple[FormalismChoice, ...] = ()

    @model_validator(mode="after")
    def coherent_request(self) -> Self:
        if len(self.techniques) != len(set(self.techniques)):
            raise ValueError("requested techniques must be unique")
        if any(technique not in BOUNDARY_TECHNIQUES for technique in self.techniques):
            raise ValueError("only technique boundaries can be requested")
        if self.text is not None and self.source.source_id.hex_digest != sha256_bytes(self.text.encode("utf-8")):
            raise ValueError("source identity does not match the supplied text")
        if self.text is None and any(technique not in STRUCTURED_INPUT_TECHNIQUES for technique in self.techniques):
            raise ValueError("text is required for every requested technique that analyses text")
        structured = [item.technique for item in self.structured_inputs]
        if len(structured) != len(set(structured)):
            raise ValueError("at most one structured input per technique")
        if any(technique not in self.techniques for technique in structured):
            raise ValueError("structured input supplied for a technique that was not requested")
        chosen = [item.technique for item in self.formalisms]
        if len(chosen) != len(set(chosen)):
            raise ValueError("at most one formalism choice per technique")
        if any(technique not in self.techniques for technique in chosen):
            raise ValueError("formalism chosen for a technique that was not requested")
        return self

    @classmethod
    def for_text(
        cls,
        text: str,
        techniques: tuple[Technique, ...],
        *,
        source_name: str | None = None,
        structured_inputs: tuple[StructuredInput, ...] = (),
        formalisms: tuple[FormalismChoice, ...] = (),
    ) -> Self:
        return cls(
            source=SourceIdentity.from_text(text, source_name=source_name),
            text=text,
            techniques=techniques,
            structured_inputs=structured_inputs,
            formalisms=formalisms,
        )

    def structured_input_for(self, technique: Technique) -> Mapping[str, JsonValue] | None:
        return next((item.payload for item in self.structured_inputs if item.technique is technique), None)

    def formalism_for(self, technique: Technique) -> str | None:
        return next((item.formalism_id for item in self.formalisms if item.technique is technique), None)


class ProviderRequest(StrictModel):
    """What the machine hands one provider: the shared source and that provider's input."""

    source: SourceIdentity
    text: str | None
    structured_input: Mapping[str, JsonValue] | None
    formalism_id: str | None = Field(default=None, pattern=_SNAKE)


__all__ = [
    "AGGREGATE_CONTRACT",
    "CAPABILITIES_CONTRACT",
    "CONTRACT_VERSION",
    "NATIVE_RESULT_CONTRACT",
    "AggregateAnalysis",
    "AggregateRequest",
    "AvailableCapability",
    "CapabilityState",
    "FailedOutcome",
    "FormalismChoice",
    "FormalismDeclaration",
    "MachineCapabilities",
    "NativeTechniqueResult",
    "Outcome",
    "ProviderDeclaration",
    "ProviderDependencyReference",
    "ProviderError",
    "ProviderFailure",
    "ProviderProvenance",
    "ProviderRequest",
    "ResultOutcome",
    "Retryability",
    "SourceIdentity",
    "StructuredInput",
    "TechniqueCapability",
    "UnavailableCapability",
    "UnavailableOutcome",
    "UnavailableReason",
    "outcome_technique",
]
