"""The aggregate analysis contract: the typed form of the 006 data model.

Entities here are the machine layer's — ``Provider``/``Formalism`` declarations,
``CapabilityState``, ``NativeTechniqueResult``, ``Outcome``, ``AggregateAnalysis``,
``ProviderDependencyReference`` — exactly as ``specs/006-rhetorical-discourse-machine/data-model.md``
defines them. Nothing here constrains a technique's *native* payload: it is an opaque JSON
object the machine never renames, removes, or reinterprets (FR-013).
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Literal, Self, cast

from pydantic import Field, TypeAdapter, ValidationInfo, field_serializer, field_validator, model_validator

from rdam._contract_types import (
    Retryability as Retryability,
    UnavailableReason as UnavailableReason,
    AvailableCapability as AvailableCapability,
    UnavailableCapability as UnavailableCapability,
    CapabilityState as CapabilityState,
    FormalismDeclaration as FormalismDeclaration,
    ProviderProvenance as ProviderProvenance,
    SourceIdentity as SourceIdentity,
    ProviderFailure as ProviderFailure,
    ProviderError as ProviderError,
    UnavailableOutcome as UnavailableOutcome,
    FailedOutcome as FailedOutcome,
    ProviderDependencyReference as ProviderDependencyReference,
    TechniqueCapability as TechniqueCapability,
    UpstreamResultReference as UpstreamResultReference,
    StructuredInput as StructuredInput,
    FormalismChoice as FormalismChoice,
    SourceArtifactRef as SourceArtifactRef,
)
from rdam._immutable_json import freeze_json_object, thaw_json
from rdam._interpretation_types import AnalysisReadingGuide, NativeInterpretationDescriptor
from rdam._json_pointer import resolve_pointer
from rdam.historical import HistoricalNativeTechniqueResult
from rdam._strict import JsonValue, SemanticVersion, Sha256Identity, StrictModel, canonical_json_bytes, semantic_sha256, sha256_bytes
from rdam.frameworks import BOUNDARY_TECHNIQUES, STRUCTURED_INPUT_TECHNIQUES, Technique, technique_curie
from rdam.ingest.contracts.preparation import (
    ContentInventory, ContentRequirement, PreparationReceipt, PreparationSemanticEvidence,
    PreparationWarning, SourceProjection, PreparedRange, SpeakerCoverage,
)
from rdam.ingest.contracts.source import SourceArtifact, SourceForm, SourceAnchor
from rdam.ingest.contracts.capabilities import SourceFormCapability

AGGREGATE_CONTRACT: Literal["rdam.aggregate"] = "rdam.aggregate"
CAPABILITIES_CONTRACT: Literal["rdam.capabilities"] = "rdam.capabilities"
NATIVE_RESULT_CONTRACT: Literal["rdam.native_result"] = "rdam.native_result"
NATIVE_RESULT_VERSION: Literal["2.0.0"] = "2.0.0"
AGGREGATE_VERSION: Literal["2.0.0"] = "2.0.0"
CAPABILITIES_VERSION: Literal["2.0.0"] = "2.0.0"

_SNAKE = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"


class ProviderConfiguration(StrictModel):
    settings: Mapping[str, JsonValue]
    identity: Sha256Identity | None = None
    cache_eligible: bool
    cache_reason: str = Field(min_length=1)

    @field_validator("settings", mode="before")
    @classmethod
    def normalize_settings(cls, value: object) -> object:
        return thaw_json(cast(Mapping[str, JsonValue], value)) if isinstance(value, Mapping) else value

    @field_validator("settings", mode="after")
    @classmethod
    def freeze_settings(cls, value: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
        return freeze_json_object(value)

    @field_serializer("settings")
    def serialize_settings(self, value: Mapping[str, JsonValue]) -> object:
        return thaw_json(value)

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        expected = Sha256Identity(hex_digest=semantic_sha256(self.settings))
        if self.identity is not None and self.identity != expected:
            raise ValueError("provider configuration identity mismatch")
        object.__setattr__(self, "identity", expected)
        return self


class ProviderDeclaration(StrictModel):
    """A provider's identity, formalisms, contract version, and standing state."""

    provider_id: str = Field(min_length=1)
    technique: Technique
    technique_curie: str = Field(min_length=1)
    formalisms: tuple[FormalismDeclaration, ...] = Field(min_length=1)
    contract_version: SemanticVersion
    provenance: ProviderProvenance
    capability: CapabilityState
    requires_structured_input: bool
    content_requirement: ContentRequirement | None = None
    parallel_safety: Literal["concurrent", "serialized"] = "concurrent"
    instructions_identity: Sha256Identity | None = None
    configuration: ProviderConfiguration
    interpretations: tuple[NativeInterpretationDescriptor, ...]

    @model_validator(mode="after")
    def coherent_declaration(self) -> Self:
        if len(self.interpretations) != len(self.formalisms):
            raise ValueError("every declared formalism requires one interpretation descriptor")
        if {item.formalism_id for item in self.interpretations} != {item.formalism_id for item in self.formalisms}:
            raise ValueError("interpretations must match declared formalisms")
        for item in self.interpretations:
            if item.native_contract_version != NATIVE_RESULT_VERSION or item.provider_contract_version != str(self.contract_version):
                raise ValueError("interpretation versions differ from provider contracts")
        if self.requires_structured_input and self.content_requirement is not None:
            raise ValueError("structured-input providers cannot declare content requirements")
        if self.technique not in BOUNDARY_TECHNIQUES:
            raise ValueError(f"{self.technique.value!r} is a formalism, not a technique boundary")
        expected = technique_curie(self.technique)
        if self.technique_curie != expected:
            raise ValueError(
                f"provider {self.provider_id!r} names {self.technique_curie!r}; Central names {expected!r}"
            )
        ids = [formalism.formalism_id for formalism in self.formalisms]
        if len(ids) != len(set(ids)):
            raise ValueError("formalism identifiers must be unique")
        if all(formalism.technique is not self.technique for formalism in self.formalisms):
            raise ValueError("a provider must declare at least one formalism of its own technique")
        if self.technique in STRUCTURED_INPUT_TECHNIQUES and not self.requires_structured_input:
            raise ValueError(f"{self.technique.value} analyses a supplied structure and must require structured input")
        if isinstance(self.capability, AvailableCapability):
            if self.provenance.source_revision is None:
                raise ValueError("available provider declaration must carry a source revision")
            if self.capability.provider_id != self.provider_id:
                raise ValueError("available capability must name this provider")
            if self.capability.contract_version != self.contract_version:
                raise ValueError("available capability must carry this provider's contract version")
        if not self.requires_structured_input and self.content_requirement is None:
            raise ValueError("text providers must declare a content requirement")
        return self

    def formalism(self, formalism_id: str) -> FormalismDeclaration | None:
        return next((item for item in self.formalisms if item.formalism_id == formalism_id), None)


class ResultSourceAlignment(StrictModel):
    """An exact native payload quote mapped to the shared source, without changing the payload."""

    payload_path: str = Field(min_length=1)
    prepared_range: PreparedRange
    contributing_item_ids: tuple[str, ...] = Field(min_length=1)
    source_anchors: tuple[SourceAnchor, ...] = Field(min_length=1)
    relationship: Literal["exact_quote", "supporting_passage", "literal_occurrence"]
    projection_identity: Sha256Identity
    quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_quote(self) -> Self:
        if self.prepared_range.end - self.prepared_range.start != len(self.quote):
            raise ValueError("alignment range and quote length differ")
        return self


def _no_alignments(value: tuple[ResultSourceAlignment, ...]) -> bool:
    return not value


class NativeTechniqueResult(StrictModel):
    """One technique's unchanged native payload, with analytical and artifact identities.

    The provider declares exact execution-only object paths. The semantic digest
    normalizes those values to null; the artifact digest still binds every byte of
    their JSON values. No generic machine code interprets a technique's schema.
    """

    contract: Literal["rdam.native_result"] = NATIVE_RESULT_CONTRACT
    contract_version: Literal["2.0.0"] = NATIVE_RESULT_VERSION
    technique: Technique
    formalism_id: str = Field(pattern=_SNAKE)
    provider_id: str = Field(min_length=1)
    provider_contract_version: SemanticVersion
    source: SourceIdentity
    payload: Mapping[str, JsonValue]
    provenance: ProviderProvenance
    source_alignment: tuple[ResultSourceAlignment, ...] = Field(default=(), exclude_if=_no_alignments)
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
        for alignment in self.source_alignment:
            selected = resolve_pointer(self.payload, alignment.payload_path)
            if not isinstance(selected, str) or not selected.strip():
                raise ValueError("alignment pointer must address native textual evidence")
            if alignment.relationship != "supporting_passage" and selected != alignment.quote:
                raise ValueError("literal/exact alignment must equal its selected native field")
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

    def validate_alignment(self, projection: SourceProjection | None) -> None:
        if self.source_alignment and projection is None:
            raise ValueError("aligned results require their exact source projection")
        if projection is None:
            return
        document = projection.prepared_document
        for alignment in self.source_alignment:
            if projection.projection_identity is None or alignment.projection_identity.hex_digest != projection.projection_identity.hex_digest:
                raise ValueError("alignment identifies a different projection")
            start, end = alignment.prepared_range.start, alignment.prepared_range.end
            if end > len(document.text) or document.text[start:end] != alignment.quote:
                raise ValueError("alignment quote does not equal the projected source slice")
            segments = tuple(segment for segment in document.segments
                             if segment.prepared_range.start < end and start < segment.prepared_range.end)
            items = tuple(dict.fromkeys(item for segment in segments for item in segment.contributing_item_ids))
            anchors = tuple(dict.fromkeys(anchor for segment in segments for anchor in segment.source_anchors))
            if alignment.contributing_item_ids != items or alignment.source_anchors != anchors:
                raise ValueError("alignment contributors or anchors differ from source projection")


def boundary_for(technique: Technique) -> Technique:
    return Technique.RST if technique is Technique.ERST else technique


class ResultOutcome(StrictModel):
    kind: Literal["result"] = "result"
    technique: Technique
    result: NativeTechniqueResult

    @model_validator(mode="after")
    def correct_boundary(self) -> Self:
        if self.technique != boundary_for(self.result.technique):
            raise ValueError("success boundary differs from native formalism")
        return self


type Outcome = Annotated[ResultOutcome | UnavailableOutcome | FailedOutcome, Field(discriminator="kind")]


def outcome_technique(outcome: ResultOutcome | UnavailableOutcome | FailedOutcome) -> Technique:
    match outcome:
        case ResultOutcome():
            return outcome.technique
        case UnavailableOutcome():
            return outcome.technique
        case FailedOutcome():
            return outcome.failure.technique


class BoundaryConfiguration(StrictModel):
    technique: Technique
    provider_id: str = Field(min_length=1)
    configuration: ProviderConfiguration


class ProjectedPreparationBinding(StrictModel):
    kind: Literal["projected"] = "projected"
    technique: Technique
    requirement: ContentRequirement
    projection_identity: Sha256Identity
    capability: CapabilityState


class StructuredPreparationBinding(StrictModel):
    kind: Literal["not_applicable"] = "not_applicable"
    technique: Technique
    reason: Literal["structured_input"] = "structured_input"


class UnavailablePreparationBinding(StrictModel):
    kind: Literal["unavailable"] = "unavailable"
    technique: Technique
    reason: Literal["not_implemented"] = "not_implemented"


type PreparationBinding = Annotated[
    ProjectedPreparationBinding | StructuredPreparationBinding | UnavailablePreparationBinding,
    Field(discriminator="kind"),
]


class MachinePreparation(StrictModel):
    contract: Literal["rdam.preparation"] = "rdam.preparation"
    contract_version: Literal["1.0.0"] = "1.0.0"
    source: SourceIdentity
    preparation: PreparationSemanticEvidence
    projections: tuple[SourceProjection, ...]
    bindings: tuple[PreparationBinding, ...]
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="before")
    @classmethod
    def derive_projections(cls, value: object, info: ValidationInfo) -> object:
        """Derive each distinct view once; supplied persisted views must equal it.

        Python construction can omit derived projections and binding identities.
        JSON records must carry both, and neither path can bypass derivation checks.
        """
        if not isinstance(value, Mapping):
            return value
        data = dict(cast(Mapping[str, object], value))
        if "preparation" not in data or "bindings" not in data:
            return data
        preparation = PreparationSemanticEvidence.model_validate_json(canonical_json_bytes(data["preparation"]))
        raw_bindings = data["bindings"]
        if not isinstance(raw_bindings, (tuple, list)):
            return data
        inventory = ContentInventory(
            source=preparation.source, source_contract=preparation.source_contract,
            items=preparation.inventory,
            empty_submitted_content=PreparationWarning.EMPTY_SUBMITTED_CONTENT in preparation.warnings,
        )
        from rdam.ingest.projection import project
        projections: dict[str, SourceProjection] = {}
        bindings: list[PreparationBinding] = []
        binding_adapter: TypeAdapter[PreparationBinding] = TypeAdapter(PreparationBinding)
        for raw_binding in cast(tuple[object, ...] | list[object], raw_bindings):
            if isinstance(raw_binding, (ProjectedPreparationBinding, StructuredPreparationBinding, UnavailablePreparationBinding)):
                binding = raw_binding.model_dump()
            elif isinstance(raw_binding, Mapping):
                binding = dict(cast(Mapping[str, object], raw_binding))
            else:
                return data
            if binding.get("kind") == "projected":
                if "requirement" not in binding:
                    return data
                requirement = ContentRequirement.model_validate_json(canonical_json_bytes(binding["requirement"]))
                if requirement.semantic_digest is None:
                    raise ValueError("projection requirement has no identity")
                key = requirement.semantic_digest.hex_digest
                if key not in projections:
                    projections[key] = project(inventory, requirement)
                identity = projections[key].projection_identity
                if identity is None:
                    raise ValueError("derived projection has no identity")
                if "projection_identity" not in binding:
                    if info.mode == "json":
                        raise ValueError("persisted binding requires a projection identity")
                    binding["projection_identity"] = Sha256Identity(hex_digest=identity.hex_digest)
            bindings.append(binding_adapter.validate_json(canonical_json_bytes(binding)))
        expected = tuple(projections.values())
        if "projections" in data:
            supplied = TypeAdapter(tuple[SourceProjection, ...]).validate_json(canonical_json_bytes(data["projections"]))
            if supplied != expected:
                raise ValueError("persisted projection differs from its declared derivation")
        elif info.mode == "json":
            raise ValueError("persisted preparation requires projections")
        data["preparation"] = preparation
        data["bindings"] = tuple(bindings)
        data["projections"] = expected
        return data

    def receipt(self) -> PreparationReceipt:
        semantic = self.preparation
        inventory = ContentInventory(
            source=semantic.source, source_contract=semantic.source_contract,
            items=semantic.inventory,
            empty_submitted_content=PreparationWarning.EMPTY_SUBMITTED_CONTENT in semantic.warnings,
        )
        transformations = {record.semantic_digest: record for projection in self.projections
                           for record in projection.transformations}
        return PreparationReceipt(
            inventory=inventory, inventory_coverage=semantic.inventory_coverage,
            primary_coverage=semantic.primary_coverage, retained_coverage=semantic.retained_coverage,
            mapping_coverage=semantic.mapping_coverage, projections=self.projections,
            transformations=tuple(transformations.values()),
            speaker_coverage=SpeakerCoverage.from_items(inventory.items),
        )

    @model_validator(mode="after")
    def coherent_preparation(self) -> Self:
        if self.source.source_id.hex_digest != self.preparation.source.byte_identity.hex_digest:
            raise ValueError("preparation must preserve source identity")
        self.receipt()
        techniques = tuple(item.technique for item in self.bindings)
        if len(set(techniques)) != len(techniques) or any(t not in BOUNDARY_TECHNIQUES for t in techniques):
            raise ValueError("preparation bindings must identify unique boundaries")
        projections = {p.projection_identity.hex_digest: p for p in self.projections if p.projection_identity is not None}
        if len(projections) != len(self.projections):
            raise ValueError("preparation projections must be uniquely identified")
        used: set[str] = set()
        for binding in self.bindings:
            if isinstance(binding, ProjectedPreparationBinding):
                projection = projections.get(binding.projection_identity.hex_digest)
                if projection is None or projection.requirement_identity != binding.requirement.semantic_digest:
                    raise ValueError("preparation binding must identify its exact requirement/projection")
                used.add(binding.projection_identity.hex_digest)
                if binding.technique in STRUCTURED_INPUT_TECHNIQUES:
                    raise ValueError("structured boundary cannot receive a projection")
            elif isinstance(binding, StructuredPreparationBinding) and binding.technique not in STRUCTURED_INPUT_TECHNIQUES:
                raise ValueError("only structured boundaries have structured preparation bindings")
        if used != set(projections):
            raise ValueError("every persisted projection must be bound")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("preparation digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class AggregateAnalysis(StrictModel):
    """N explicit outcomes over one source — never a merged node-and-edge view (FR-013, FR-014)."""

    contract: Literal["rdam.aggregate"] = AGGREGATE_CONTRACT
    contract_version: Literal["2.0.0"] = AGGREGATE_VERSION
    source: SourceIdentity
    requested_techniques: tuple[Technique, ...] = Field(min_length=1)
    outcomes: tuple[Outcome, ...] = Field(min_length=1)
    upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = ()
    configurations: tuple[BoundaryConfiguration, ...]
    lineage: tuple[ProviderDependencyReference, ...] = ()
    preparation: MachinePreparation | None = None
    status: Literal["complete", "partial", "unsuccessful"]
    reading_guide: AnalysisReadingGuide
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_aggregate(self) -> Self:
        if self.preparation is not None:
            if self.preparation.source != self.source:
                raise ValueError("preparation identity differs from aggregate source")
        techniques = [outcome_technique(item) for item in self.outcomes]
        if len(techniques) != len(set(techniques)):
            raise ValueError("an aggregate carries at most one outcome per technique")
        if tuple(techniques) != self.requested_techniques or any(t not in BOUNDARY_TECHNIQUES for t in techniques):
            raise ValueError("outcomes must equal requested boundaries in order")
        successful = sum(isinstance(item, ResultOutcome) for item in self.outcomes)
        expected_status = "complete" if successful == len(self.outcomes) else "partial" if successful else "unsuccessful"
        if self.status != expected_status:
            raise ValueError("status must reflect only requested outcomes")
        retained_boundaries = tuple(boundary_for(item.technique) for item in self.upstream_results)
        if len(set(retained_boundaries)) != len(retained_boundaries) or set(retained_boundaries).intersection(techniques):
            raise ValueError("retained results cannot collide with requested or retained boundaries")
        configured = tuple(item.technique for item in self.configurations)
        if configured != tuple(t for t in self.requested_techniques if t in configured):
            raise ValueError("configurations must be unique and request ordered")
        for item in self.outcomes:
            boundary = outcome_technique(item)
            config = next((c for c in self.configurations if c.technique == boundary), None)
            if isinstance(item, ResultOutcome) and (config is None or config.provider_id != item.result.provider_id):
                raise ValueError("every successful boundary must retain its provider configuration")
        results_by_technique: dict[Technique, NativeTechniqueResult | HistoricalNativeTechniqueResult] = {}
        results_by_digest: dict[Sha256Identity, NativeTechniqueResult | HistoricalNativeTechniqueResult] = {}
        for retained in self.upstream_results:
            if retained.source != self.source or retained.semantic_digest is None:
                raise ValueError("retained result source/identity differs from aggregate")
            results_by_digest[retained.semantic_digest] = retained
        for item in self.outcomes:
            if isinstance(item, ResultOutcome):
                if item.result.source != self.source:
                    raise ValueError("every native result must be about the aggregate's source")
                projection = None
                if self.preparation is not None:
                    binding = next((binding for binding in self.preparation.bindings if binding.technique == item.technique), None)
                    if isinstance(binding, ProjectedPreparationBinding):
                        projection = next((p for p in self.preparation.projections if p.projection_identity is not None
                                           and p.projection_identity.hex_digest == binding.projection_identity.hex_digest), None)
                item.result.validate_alignment(projection)
                results_by_technique[item.technique] = item.result
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
        expected_entries = tuple(
            ("requested", outcome_technique(item), f"/outcomes/{index}/result" if isinstance(item, ResultOutcome) else f"/outcomes/{index}", item.kind)
            for index, item in enumerate(self.outcomes)
        ) + tuple(("retained", boundary_for(item.technique), f"/upstream_results/{index}", "result")
                  for index, item in enumerate(self.upstream_results))
        actual_entries = tuple((e.scope, e.technique, e.record_pointer, e.state) for e in self.reading_guide.entries)
        if actual_entries != expected_entries:
            raise ValueError("reading guide must match actual ordered outcomes and retained records")
        for entry in self.reading_guide.entries:
            if entry.scope == "requested" and entry.state == "result" and entry.descriptor_status != "available":
                raise ValueError("requested successful results require native descriptions")
            target = resolve_pointer(self.model_dump(), entry.record_pointer)
            if entry.descriptor is not None:
                record = cast(Mapping[str, object], target)
                descriptor = entry.descriptor
                if (descriptor.formalism_id, descriptor.native_contract_version, descriptor.provider_contract_version) != (
                    record["formalism_id"], record["contract_version"], record["provider_contract_version"]
                ):
                    raise ValueError("reading descriptor differs from native record")
                for section in descriptor.sections:
                    if section.availability == "present":
                        resolve_pointer(target, section.pointer)
        semantic = self.model_dump(exclude={"semantic_digest", "outcomes", "upstream_results"})
        semantic["upstream_results"] = tuple(item.semantic_digest for item in self.upstream_results)
        semantic["outcomes"] = tuple(
            {"kind": item.kind, "technique": item.technique, "result_identity": item.result.semantic_digest}
            if isinstance(item, ResultOutcome)
            else item.model_dump()
            for item in self.outcomes
        )
        expected = Sha256Identity(hex_digest=semantic_sha256(semantic))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("aggregate semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self

    def outcome_for(self, technique: Technique) -> ResultOutcome | UnavailableOutcome | FailedOutcome | None:
        return next((item for item in self.outcomes if outcome_technique(item) is technique), None)


class ContractSupport(StrictModel):
    contract: str
    write_version: str
    read_versions: tuple[str, ...]
    schema_names: tuple[str, ...]


class MachineCapabilities(StrictModel):
    """Every technique the machine knows, each in exactly one state; side-effect-free to produce."""

    contract: Literal["rdam.capabilities"] = CAPABILITIES_CONTRACT
    contract_version: Literal["2.0.0"] = CAPABILITIES_VERSION
    techniques: tuple[TechniqueCapability, ...]
    source_forms: tuple[SourceFormCapability, ...]
    configurations: tuple[BoundaryConfiguration, ...]
    contracts: tuple[ContractSupport, ...]
    http_available: bool
    model_probe: Literal["not_performed"] = "not_performed"
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


class AggregateRequest(StrictModel):
    """One source, the techniques to run on it, and — for formal techniques — their inputs.

    ``upstream_results`` carries the exact native results (from earlier analyses of the
    same source) that structured inputs declare they were derived from. The machine
    re-emits them as outcomes of the aggregate and records each declared consumption in
    the aggregate's ``lineage`` (FR-015).
    """

    contract: Literal["rdam.request"] = "rdam.request"
    contract_version: Literal["1.0.0"] = "1.0.0"
    source: SourceIdentity
    text: str | None = None
    source_artifact: SourceArtifactRef | None = None
    techniques: tuple[Technique, ...] = Field(min_length=1)
    structured_inputs: tuple[StructuredInput, ...] = ()
    formalisms: tuple[FormalismChoice, ...] = ()
    upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = ()

    @model_validator(mode="after")
    def coherent_request(self) -> Self:
        if len(self.techniques) != len(set(self.techniques)):
            raise ValueError("requested techniques must be unique")
        if any(technique not in BOUNDARY_TECHNIQUES for technique in self.techniques):
            raise ValueError("only technique boundaries can be requested")
        if self.text is not None and self.source.source_id.hex_digest != sha256_bytes(self.text.encode("utf-8")):
            raise ValueError("source identity does not match the supplied text")
        supplied = int(self.text is not None) + int(self.source_artifact is not None)
        if supplied > 1 or (
            supplied == 0 and any(technique not in STRUCTURED_INPUT_TECHNIQUES for technique in self.techniques)
        ):
            raise ValueError("exactly one text or source_artifact is required for text analysis")
        if self.source_artifact is not None:
            digest = self.source_artifact.artifact.raw_sha256
            if digest is None or digest.hex_digest != self.source.source_id.hex_digest:
                raise ValueError("source identity does not match supplied bytes")
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
        upstream_techniques = [boundary_for(item.technique) for item in self.upstream_results]
        if len(upstream_techniques) != len(set(upstream_techniques)):
            raise ValueError("at most one upstream result per technique")
        if any(technique in self.techniques for technique in upstream_techniques):
            raise ValueError("an upstream result's technique cannot also be requested in the same aggregate")
        if any(item.source != self.source for item in self.upstream_results):
            raise ValueError("every upstream result must be about this request's source")
        for item in self.structured_inputs:
            if item.derived_from is not None and self.upstream_result(item.derived_from) is None:
                raise ValueError(
                    f"{item.technique.value} input is declared derived from a result this request does not carry "
                    "in upstream_results"
                )
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
        upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = (),
    ) -> Self:
        return cls(
            source=SourceIdentity.from_text(text, source_name=source_name),
            text=text,
            techniques=techniques,
            structured_inputs=structured_inputs,
            formalisms=formalisms,
            upstream_results=upstream_results,
        )

    @classmethod
    def for_source(
        cls,
        path: Path | str,
        techniques: tuple[Technique, ...],
        *,
        source_form: SourceForm | None = None,
        structured_inputs: tuple[StructuredInput, ...] = (),
        formalisms: tuple[FormalismChoice, ...] = (),
        upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = (),
    ) -> Self:
        artifact = SourceArtifact.from_path(Path(path), source_form=source_form)
        return cls._for_artifact(artifact, techniques, structured_inputs, formalisms, upstream_results)

    @classmethod
    def for_bytes(
        cls,
        payload: bytes,
        source_form: SourceForm,
        source_name: str,
        techniques: tuple[Technique, ...],
        *,
        structured_inputs: tuple[StructuredInput, ...] = (),
        formalisms: tuple[FormalismChoice, ...] = (),
        upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = (),
    ) -> Self:
        artifact = SourceArtifact.from_bytes(
            payload,
            source_form=source_form,
            source_name=source_name,
        )
        return cls._for_artifact(artifact, techniques, structured_inputs, formalisms, upstream_results)

    @classmethod
    def _for_artifact(
        cls,
        artifact: SourceArtifact,
        techniques: tuple[Technique, ...],
        structured_inputs: tuple[StructuredInput, ...],
        formalisms: tuple[FormalismChoice, ...],
        upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...],
    ) -> Self:
        digest = artifact.raw_sha256
        if digest is None:
            raise ValueError("source artifact has no byte identity")
        return cls(
            source=SourceIdentity(
                source_id=Sha256Identity(hex_digest=digest.hex_digest),
                source_name=artifact.source_name,
                media_type=artifact.media_type,
            ),
            source_artifact=SourceArtifactRef(artifact=artifact),
            techniques=techniques,
            structured_inputs=structured_inputs,
            formalisms=formalisms,
            upstream_results=upstream_results,
        )

    @classmethod
    def for_edus(
        cls, edus: tuple[str, ...], techniques: tuple[Technique, ...], *, source_name: str = "rdam-source",
        structured_inputs: tuple[StructuredInput, ...] = (), formalisms: tuple[FormalismChoice, ...] = (),
        upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = (),
    ) -> Self:
        return cls._for_artifact(SourceArtifact.from_edus(edus, source_name=source_name),
                                 techniques, structured_inputs, formalisms, upstream_results)

    @classmethod
    def for_structured(
        cls, structured_inputs: tuple[StructuredInput, ...], *,
        techniques: tuple[Technique, ...] | None = None, source: SourceIdentity | None = None,
        source_name: str | None = None,
        upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...] = (),
        formalisms: tuple[FormalismChoice, ...] = (),
    ) -> Self:
        if not structured_inputs:
            raise ValueError("structured-only construction requires at least one supplied structure")
        if upstream_results:
            if any(item.source != upstream_results[0].source for item in upstream_results):
                raise ValueError("upstream results must share one source")
            if source is not None and source != upstream_results[0].source:
                raise ValueError("explicit source differs from retained results")
            source = upstream_results[0].source
        if source is None:
            source = SourceIdentity(source_id=Sha256Identity(hex_digest=semantic_sha256({
                "kind": "rdam.structured_source", "version": "1.0.0",
                "inputs": [{"technique": item.technique, "payload": item.payload}
                           for item in sorted(structured_inputs, key=lambda item: item.technique.value)],
            })), source_name=source_name, media_type="application/json")
        return cls(source=source, techniques=tuple(item.technique for item in structured_inputs)
                   if techniques is None else techniques, structured_inputs=structured_inputs,
                   upstream_results=upstream_results, formalisms=formalisms)

    def structured_input_for(self, technique: Technique) -> Mapping[str, JsonValue] | None:
        return next((item.payload for item in self.structured_inputs if item.technique is technique), None)

    def derivation_for(self, technique: Technique) -> UpstreamResultReference | None:
        return next((item.derived_from for item in self.structured_inputs if item.technique is technique), None)

    def formalism_for(self, technique: Technique) -> str | None:
        return next((item.formalism_id for item in self.formalisms if item.technique is technique), None)

    def upstream_result(self, reference: UpstreamResultReference) -> NativeTechniqueResult | HistoricalNativeTechniqueResult | None:
        """The carried upstream result a reference names: same technique, same semantic digest."""

        return next(
            (
                item
                for item in self.upstream_results
                if item.technique is reference.technique and item.semantic_digest == reference.result_identity
            ),
            None,
        )


class PreparationRequest(StrictModel):
    contract: Literal["rdam.preparation_request"] = "rdam.preparation_request"
    contract_version: Literal["1.0.0"] = "1.0.0"
    source: SourceIdentity
    text: str | None = None
    source_artifact: SourceArtifactRef | None = None
    techniques: tuple[Technique, ...] = ()

    @model_validator(mode="after")
    def coherent_source(self) -> Self:
        if (self.text is None) == (self.source_artifact is None):
            raise ValueError("preparation requires exactly one materialized source")
        if self.text is not None and sha256_bytes(self.text.encode("utf-8")) != self.source.source_id.hex_digest:
            raise ValueError("source identity differs from text")
        if self.source_artifact is not None:
            digest = self.source_artifact.artifact.raw_sha256
            if digest is None or digest.hex_digest != self.source.source_id.hex_digest:
                raise ValueError("source identity differs from artifact")
        if len(set(self.techniques)) != len(self.techniques) or any(t not in BOUNDARY_TECHNIQUES for t in self.techniques):
            raise ValueError("selected preparation techniques must be unique boundaries")
        return self

    @classmethod
    def for_text(cls, text: str, techniques: tuple[Technique, ...] = (), *, source_name: str | None = None) -> Self:
        return cls(source=SourceIdentity.from_text(text, source_name=source_name), text=text, techniques=techniques)

    @classmethod
    def _for_artifact(cls, artifact: SourceArtifact, techniques: tuple[Technique, ...]) -> Self:
        if artifact.raw_sha256 is None:
            raise ValueError("source artifact has no byte identity")
        return cls(source=SourceIdentity(source_id=Sha256Identity(hex_digest=artifact.raw_sha256.hex_digest),
                   source_name=artifact.source_name, media_type=artifact.media_type),
                   source_artifact=SourceArtifactRef(artifact=artifact), techniques=techniques)

    @classmethod
    def for_source(cls, path: Path | str, techniques: tuple[Technique, ...] = (), *, source_form: SourceForm | None = None) -> Self:
        return cls._for_artifact(SourceArtifact.from_path(Path(path), source_form=source_form), techniques)

    @classmethod
    def for_bytes(cls, payload: bytes, source_form: SourceForm, source_name: str,
                  techniques: tuple[Technique, ...] = ()) -> Self:
        return cls._for_artifact(SourceArtifact.from_bytes(payload, source_form=source_form, source_name=source_name), techniques)

    @classmethod
    def for_edus(cls, edus: tuple[str, ...], techniques: tuple[Technique, ...] = (), *, source_name: str = "rdam-source") -> Self:
        return cls._for_artifact(SourceArtifact.from_edus(edus, source_name=source_name), techniques)


class InputIssue(StrictModel):
    path: str
    code: str = Field(pattern=_SNAKE)
    expected: str


class OperationFailure(StrictModel):
    contract: Literal["rdam.operation_error"] = "rdam.operation_error"
    contract_version: Literal["1.0.0"] = "1.0.0"
    operation: Literal["configuration", "capabilities", "prepare", "analyse", "summary", "view", "schema", "version", "serve", "publish"]
    category: Literal["invalid_request", "source_unavailable", "preparation_failed", "dependency_unavailable",
                      "busy", "internal_error", "output_error", "interrupted"]
    code: str = Field(pattern=_SNAKE)
    retryability: Retryability
    message: str
    issues: tuple[InputIssue, ...] = ()
    completed_result_identity: Sha256Identity | None = None
    publication_state: Literal["not_published", "published", "unknown"] | None = None


class OperationError(RuntimeError):
    def __init__(self, failure: OperationFailure) -> None:
        self.failure = failure
        super().__init__(failure.message)


class VersionInfo(StrictModel):
    contract: Literal["rdam.version"] = "rdam.version"
    contract_version: Literal["1.0.0"] = "1.0.0"
    package: Literal["rdam"] = "rdam"
    version: str
    contracts: tuple[ContractSupport, ...]


class ProviderRequest(StrictModel):
    """What the machine hands one provider: the shared source and that provider's input."""

    source: SourceIdentity
    text: str | None
    structured_input: Mapping[str, JsonValue] | None
    formalism_id: str | None = Field(default=None, pattern=_SNAKE)
    derived_from: UpstreamResultReference | None = None
    projection: SourceProjection | None = None
    preparation: PreparationReceipt | None = None

    @model_validator(mode="after")
    def coherent_projection(self) -> Self:
        if self.structured_input is not None and self.projection is not None:
            raise ValueError("structured input cannot receive a source projection")
        if self.projection is not None:
            if self.projection.prepared_document.source.byte_identity.hex_digest != self.source.source_id.hex_digest:
                raise ValueError("projection belongs to a different source")
            if self.text != self.projection.prepared_document.text:
                raise ValueError("provider text must equal its projection")
        return self

    @field_validator("structured_input", mode="before")
    @classmethod
    def normalize_structured_input(cls, value: object) -> object:
        return thaw_json(cast(Mapping[str, JsonValue], value)) if isinstance(value, Mapping) else value

    @field_validator("structured_input", mode="after")
    @classmethod
    def freeze_structured_input(
        cls,
        value: Mapping[str, JsonValue] | None,
    ) -> Mapping[str, JsonValue] | None:
        return None if value is None else freeze_json_object(value)

    @field_serializer("structured_input")
    def serialize_structured_input(self, value: Mapping[str, JsonValue] | None) -> object:
        return None if value is None else thaw_json(value)


__all__ = [
    "AGGREGATE_CONTRACT",
    "CAPABILITIES_CONTRACT",
    "NATIVE_RESULT_VERSION",
    "AGGREGATE_VERSION",
    "CAPABILITIES_VERSION",
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
    "ResultSourceAlignment",
    "Retryability",
    "SourceIdentity",
    "SourceArtifactRef",
    "StructuredInput",
    "TechniqueCapability",
    "UnavailableCapability",
    "UnavailableOutcome",
    "UnavailableReason",
    "UpstreamResultReference",
    "outcome_technique",
]
