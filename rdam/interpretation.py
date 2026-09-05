"""Pure binding of native-owned descriptions to actual persisted records."""

from collections.abc import Mapping
from typing import Literal, Self
from typing import cast
from pydantic import Field, model_validator
from rdam._strict import StrictModel, Sha256Identity, semantic_sha256

from rdam._interpretation_types import (
    AnalysisReadingGuide as AnalysisReadingGuide,
    NativeInterpretationDescriptor as NativeInterpretationDescriptor,
    NativeSectionDescription,
    ReadingGuideEntry,
)
from rdam._json_pointer import resolve_pointer
from rdam.contracts import (
    FailedOutcome,
    NativeTechniqueResult,
    ProviderDeclaration,
    ResultOutcome,
    UnavailableOutcome,
    boundary_for,
    outcome_technique,
    AggregateAnalysis,
    Outcome,
    SourceIdentity,
    BoundaryConfiguration,
    ProviderDependencyReference,
    MachinePreparation,
    ProjectedPreparationBinding,
)
from rdam.frameworks import Technique
from rdam.historical import HistoricalNativeTechniqueResult


def bind_descriptor(result: NativeTechniqueResult, declaration: ProviderDeclaration) -> NativeInterpretationDescriptor:
    descriptor = next(item for item in declaration.interpretations if item.formalism_id == result.formalism_id)
    sections: list[NativeSectionDescription] = []
    for section in descriptor.sections:
        try:
            resolve_pointer(result.model_dump(), section.pointer)
        except ValueError:
            sections.append(section.model_copy(update={"availability": "not_recorded"}))
        else:
            sections.append(section)
    return NativeInterpretationDescriptor.model_validate(
        {
            **descriptor.model_dump(exclude={"identity", "sections"}),
            "sections": tuple(sections),
        }
    )


def reading_guide(
    outcomes: tuple[ResultOutcome | FailedOutcome | UnavailableOutcome, ...],
    upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...],
    declarations: Mapping[Technique, ProviderDeclaration],
) -> AnalysisReadingGuide:
    entries: list[ReadingGuideEntry] = []
    for index, outcome in enumerate(outcomes):
        technique = outcome_technique(outcome)
        success = isinstance(outcome, ResultOutcome)
        entries.append(
            ReadingGuideEntry(
                scope="requested",
                technique=technique,
                record_pointer=f"/outcomes/{index}/result" if success else f"/outcomes/{index}",
                state=outcome.kind,
                descriptor_status="available" if success else "not_applicable",
                descriptor=bind_descriptor(outcome.result, declarations[technique])
                if isinstance(outcome, ResultOutcome)
                else None,
            )
        )
    for index, result in enumerate(upstream_results):
        technique = boundary_for(result.technique)
        declaration = declarations.get(technique)
        compatible = (
            isinstance(result, NativeTechniqueResult)
            and declaration is not None
            and result.provider_id == declaration.provider_id
            and result.provider_contract_version == declaration.contract_version
        )
        descriptor = (
            bind_descriptor(result, declaration)
            if isinstance(result, NativeTechniqueResult) and declaration is not None and compatible
            else None
        )
        entries.append(
            ReadingGuideEntry(
                scope="retained",
                technique=technique,
                record_pointer=f"/upstream_results/{index}",
                state="result",
                descriptor_status="available" if descriptor is not None else "historical_unavailable",
                descriptor=descriptor,
            )
        )
    return AnalysisReadingGuide(entries=tuple(entries))


class ExcludedOutcome(StrictModel):
    technique: Technique
    state: Literal["result", "unavailable", "failed"]
    original_pointer: str


class ViewRequest(StrictModel):
    contract: Literal["rdam.view_request"] = "rdam.view_request"
    contract_version: Literal["1.0.0"] = "1.0.0"
    analysis: AggregateAnalysis
    techniques: tuple[Technique, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_selection(self) -> Self:
        _selection(self.analysis.requested_techniques, self.techniques)
        return self


def _selection(requested: tuple[Technique, ...], selected: tuple[Technique, ...]) -> tuple[Technique, ...]:
    if not selected or len(set(selected)) != len(selected) or not set(selected).issubset(requested):
        raise ValueError("selection must contain unique requested boundaries")
    return tuple(technique for technique in requested if technique in selected)


class AnalysisView(StrictModel):
    contract: Literal["rdam.analysis_view"] = "rdam.analysis_view"
    contract_version: Literal["1.0.0"] = "1.0.0"
    analysis_identity: Sha256Identity
    source: SourceIdentity
    requested_techniques: tuple[Technique, ...] = Field(min_length=1)
    selected_techniques: tuple[Technique, ...] = Field(min_length=1)
    analysis_status: Literal["complete", "partial", "unsuccessful"]
    outcomes: tuple[Outcome, ...] = Field(min_length=1)
    excluded_outcomes: tuple[ExcludedOutcome, ...]
    upstream_results: tuple[NativeTechniqueResult | HistoricalNativeTechniqueResult, ...]
    lineage: tuple[ProviderDependencyReference, ...]
    configurations: tuple[BoundaryConfiguration, ...]
    preparation: MachinePreparation | None
    reading_guide: AnalysisReadingGuide
    omitted_content: Literal["unselected_outcomes_only"] = "unselected_outcomes_only"
    semantic_digest: Sha256Identity | None = None

    @model_validator(mode="after")
    def coherent_view(self) -> Self:
        if len(set(self.requested_techniques)) != len(self.requested_techniques):
            raise ValueError("original requested boundaries must be unique")
        if _selection(self.requested_techniques, self.selected_techniques) != self.selected_techniques:
            raise ValueError("selection must retain original request order")
        if tuple(outcome_technique(outcome) for outcome in self.outcomes) != self.selected_techniques:
            raise ValueError("view outcomes must equal selected boundaries")
        expected = tuple(
            (technique, f"/outcomes/{index}")
            for index, technique in enumerate(self.requested_techniques)
            if technique not in self.selected_techniques
        )
        if tuple((item.technique, item.original_pointer) for item in self.excluded_outcomes) != expected:
            raise ValueError("exclusions must identify every omitted original outcome")
        states = tuple(outcome.kind for outcome in self.outcomes) + tuple(item.state for item in self.excluded_outcomes)
        successes = states.count("result")
        status = "complete" if successes == len(states) else "partial" if successes else "unsuccessful"
        if self.analysis_status != status:
            raise ValueError("view must preserve full analysis status")
        if self.preparation is not None:
            if self.preparation.source != self.source:
                raise ValueError("view preparation belongs to a different source")
            if tuple(binding.technique for binding in self.preparation.bindings) != self.requested_techniques:
                raise ValueError("view preparation must retain original requested bindings")
        configured = tuple(item.technique for item in self.configurations)
        if configured != tuple(technique for technique in self.requested_techniques if technique in configured):
            raise ValueError("view configurations must be unique and request ordered")
        configurations = {item.technique: item for item in self.configurations}
        successful = {outcome_technique(item) for item in self.outcomes if isinstance(item, ResultOutcome)}
        successful.update(item.technique for item in self.excluded_outcomes if item.state == "result")
        if not successful.issubset(configurations):
            raise ValueError("successful boundaries must retain their provider configuration")
        for outcome in self.outcomes:
            if isinstance(outcome, ResultOutcome):
                if outcome.result.source != self.source:
                    raise ValueError("view result has a different source")
                if configurations[outcome.technique].provider_id != outcome.result.provider_id:
                    raise ValueError("view configuration differs from selected provider")
                projection = None
                if self.preparation is not None:
                    binding = next((item for item in self.preparation.bindings if item.technique == outcome.technique), None)
                    if isinstance(binding, ProjectedPreparationBinding):
                        projection = next((item for item in self.preparation.projections
                                           if item.projection_identity is not None and
                                           item.projection_identity.hex_digest == binding.projection_identity.hex_digest), None)
                outcome.result.validate_alignment(projection)
        if any(result.source != self.source for result in self.upstream_results):
            raise ValueError("retained result has a different source")
        retained = tuple(boundary_for(item.technique) for item in self.upstream_results)
        if len(set(retained)) != len(retained) or set(retained).intersection(self.requested_techniques):
            raise ValueError("view retained results collide with original requested boundaries")
        selected_results = {item.technique: item.result for item in self.outcomes if isinstance(item, ResultOutcome)}
        upstreams = {item.semantic_digest: item for item in (*self.upstream_results, *selected_results.values())}
        for reference in self.lineage:
            if reference.consumer_technique not in successful:
                raise ValueError("view lineage consumer must have succeeded in the original analysis")
            if configurations[reference.consumer_technique].provider_id != reference.consumer_provider_id:
                raise ValueError("view lineage consumer differs from provider configuration")
            consumer = selected_results.get(reference.consumer_technique)
            if consumer is not None and consumer.provider_contract_version != reference.consumer_contract_version:
                raise ValueError("view lineage consumer contract differs from selected result")
            upstream = upstreams.get(reference.upstream_result_identity)
            if upstream is None or (
                upstream.technique, upstream.provider_id, upstream.provider_contract_version,
                upstream.provenance.model_identity
            ) != (
                reference.upstream_technique, reference.upstream_provider_id, reference.upstream_contract_version,
                reference.upstream_model_identity
            ):
                raise ValueError("view lineage differs from its retained upstream result")
        expected_entries = tuple(
            (
                "requested",
                outcome_technique(item),
                f"/outcomes/{index}/result" if isinstance(item, ResultOutcome) else f"/outcomes/{index}",
                item.kind,
            )
            for index, item in enumerate(self.outcomes)
        ) + tuple(
            ("retained", boundary_for(item.technique), f"/upstream_results/{index}", "result")
            for index, item in enumerate(self.upstream_results)
        )
        if (
            tuple((item.scope, item.technique, item.record_pointer, item.state) for item in self.reading_guide.entries)
            != expected_entries
        ):
            raise ValueError("view guide must address actual records")
        for entry in self.reading_guide.entries:
            if entry.scope == "requested" and entry.state == "result" and entry.descriptor_status != "available":
                raise ValueError("requested successful results require native descriptions")
            record = resolve_pointer(self.model_dump(), entry.record_pointer)
            if entry.descriptor is not None:
                target = cast(Mapping[str, object], record)
                if (
                    entry.descriptor.formalism_id,
                    entry.descriptor.native_contract_version,
                    entry.descriptor.provider_contract_version,
                ) != (target["formalism_id"], target["contract_version"], target["provider_contract_version"]):
                    raise ValueError("view descriptor differs from native record")
                for section in entry.descriptor.sections:
                    if section.availability == "present":
                        resolve_pointer(record, section.pointer)
        semantic = self.model_dump(exclude={"semantic_digest", "outcomes", "upstream_results"})
        semantic["outcomes"] = tuple(
            {"kind": item.kind, "technique": item.technique, "result_identity": item.result.semantic_digest}
            if isinstance(item, ResultOutcome)
            else item.model_dump()
            for item in self.outcomes
        )
        semantic["upstream_results"] = tuple(item.semantic_digest for item in self.upstream_results)
        digest = Sha256Identity(hex_digest=semantic_sha256(semantic))
        if self.semantic_digest is not None and self.semantic_digest != digest:
            raise ValueError("view semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", digest)
        return self


def select_analysis(analysis: AggregateAnalysis, *, techniques: tuple[Technique, ...]) -> AnalysisView:
    analysis = AggregateAnalysis.model_validate(analysis.model_dump())
    selected = _selection(analysis.requested_techniques, techniques)
    if analysis.semantic_digest is None:
        raise ValueError("analysis has no identity")
    outcomes = tuple(item for item in analysis.outcomes if outcome_technique(item) in selected)
    entries: list[ReadingGuideEntry] = []
    for index, outcome in enumerate(outcomes):
        entry = next(
            item
            for item in analysis.reading_guide.entries
            if item.scope == "requested" and item.technique == outcome_technique(outcome)
        )
        entries.append(
            entry.model_copy(
                update={
                    "record_pointer": f"/outcomes/{index}/result"
                    if isinstance(outcome, ResultOutcome)
                    else f"/outcomes/{index}"
                }
            )
        )
    entries.extend(item for item in analysis.reading_guide.entries if item.scope == "retained")
    return AnalysisView(
        analysis_identity=analysis.semantic_digest,
        source=analysis.source,
        requested_techniques=analysis.requested_techniques,
        selected_techniques=selected,
        analysis_status=analysis.status,
        outcomes=outcomes,
        excluded_outcomes=tuple(
            ExcludedOutcome(technique=outcome_technique(item), state=item.kind, original_pointer=f"/outcomes/{index}")
            for index, item in enumerate(analysis.outcomes)
            if outcome_technique(item) not in selected
        ),
        upstream_results=analysis.upstream_results,
        lineage=analysis.lineage,
        configurations=analysis.configurations,
        preparation=analysis.preparation,
        reading_guide=AnalysisReadingGuide(
            guide_version=analysis.reading_guide.guide_version,
            usage_notes=analysis.reading_guide.usage_notes,
            entries=tuple(entries),
        ),
    )
