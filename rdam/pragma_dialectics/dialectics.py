"""Pragma-Dialectical analysis models and deterministic rule/fallacy verification."""

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from rdam._grounding import GroundingCollector, QuoteRef
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.pragma_dialectics.rules import (
    CRITICAL_DISCUSSION_RULES,
    CriticalDiscussionRuleId,
    DiscussionStage,
)

type NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
type StandpointPolarity = Literal["positive", "negative", "doubt"]


class PragmaDialecticsError(ValueError):
    """Raised when a pragma-dialectical proposal violates the 10-rule catalogue or source grounding."""


class StandpointProposal(StrictModel):
    id: NonEmpty
    protagonist: NonEmpty = Field(default="author")
    polarity: StandpointPolarity
    proposition: NonEmpty
    evidence: QuoteRef


class StageSegmentProposal(StrictModel):
    id: NonEmpty
    stage: DiscussionStage
    summary: NonEmpty
    evidence: QuoteRef


class StrategicManoeuvreProposal(StrictModel):
    id: NonEmpty
    stage: DiscussionStage
    topical_potential: NonEmpty
    audience_demand: NonEmpty
    presentational_device: NonEmpty
    evidence: QuoteRef


class DerailmentProposal(StrictModel):
    id: NonEmpty
    stage: DiscussionStage
    rule_id: CriticalDiscussionRuleId
    fallacy_type: NonEmpty
    explanation: NonEmpty
    evidence: QuoteRef

    @model_validator(mode="after")
    def verify_catalogued_fallacy(self) -> Self:
        rule = CRITICAL_DISCUSSION_RULES[self.rule_id]
        if self.fallacy_type not in rule.recognized_fallacies:
            raise ValueError(
                f"Derailment {self.id!r}: fallacy_type={self.fallacy_type!r} does not belong to "
                f"{self.rule_id!r} ({rule.title}); allowed: {sorted(rule.recognized_fallacies)}."
            )
        return self


class CriticalDiscussionProposal(StrictModel):
    standpoints: list[StandpointProposal] = Field(default_factory=list[StandpointProposal])
    stage_segments: list[StageSegmentProposal] = Field(default_factory=list[StageSegmentProposal])
    strategic_manoeuvres: list[StrategicManoeuvreProposal] = Field(
        default_factory=list[StrategicManoeuvreProposal]
    )
    derailments: list[DerailmentProposal] = Field(default_factory=list[DerailmentProposal])

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        for name, ids in (
            ("standpoint", [s.id for s in self.standpoints]),
            ("stage_segment", [s.id for s in self.stage_segments]),
            ("strategic_manoeuvre", [m.id for m in self.strategic_manoeuvres]),
            ("derailment", [d.id for d in self.derailments]),
        ):
            if len(set(ids)) != len(ids):
                raise ValueError(f"Duplicate {name} id in CriticalDiscussionProposal")
        return self

    def validate_source(
        self,
        source_text: str,
    ) -> tuple[
        dict[str, SourceEvidenceSpan],
        dict[str, SourceEvidenceSpan],
        dict[str, SourceEvidenceSpan],
        dict[str, SourceEvidenceSpan],
    ]:
        collector = GroundingCollector(source_text)
        sp_spans: dict[str, SourceEvidenceSpan] = {}
        st_spans: dict[str, SourceEvidenceSpan] = {}
        sm_spans: dict[str, SourceEvidenceSpan] = {}
        dr_spans: dict[str, SourceEvidenceSpan] = {}

        for idx, sp in enumerate(self.standpoints):
            span = collector.resolve(sp.evidence, field_name=f"standpoints[{idx}] ({sp.id}).evidence")
            if span is not None:
                sp_spans[sp.id] = span

        for idx, st in enumerate(self.stage_segments):
            span = collector.resolve(st.evidence, field_name=f"stage_segments[{idx}] ({st.id}).evidence")
            if span is not None:
                st_spans[st.id] = span

        for idx, sm in enumerate(self.strategic_manoeuvres):
            span = collector.resolve(sm.evidence, field_name=f"strategic_manoeuvres[{idx}] ({sm.id}).evidence")
            if span is not None:
                sm_spans[sm.id] = span

        for idx, dr in enumerate(self.derailments):
            span = collector.resolve(dr.evidence, field_name=f"derailments[{idx}] ({dr.id}).evidence")
            if span is not None:
                dr_spans[dr.id] = span

        try:
            collector.raise_if_errors()
        except ValueError as exc:
            raise PragmaDialecticsError(str(exc)) from exc
        return sp_spans, st_spans, sm_spans, dr_spans


__all__ = [
    "CriticalDiscussionProposal",
    "DerailmentProposal",
    "PragmaDialecticsError",
    "StageSegmentProposal",
    "StandpointPolarity",
    "StandpointProposal",
    "StrategicManoeuvreProposal",
]
