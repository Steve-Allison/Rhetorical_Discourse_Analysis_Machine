"""Persisted Pragma-Dialectics output contract."""

from typing import Self

from pydantic import NonNegativeInt, model_validator

from rdam._native_output import ExtractionRecord
from rdam._strict import StrictModel
from rdam.ingest.contracts.evidence import SourceEvidenceSpan
from rdam.pragma_dialectics.dialectics import NonEmpty, StandpointPolarity
from rdam.pragma_dialectics.rules import (
    CRITICAL_DISCUSSION_RULES,
    CriticalDiscussionRuleId,
    DiscussionStage,
)


class StandpointOutput(StrictModel):
    id: NonEmpty
    protagonist: NonEmpty
    polarity: StandpointPolarity
    proposition: NonEmpty
    span: SourceEvidenceSpan


class StageSegmentOutput(StrictModel):
    id: NonEmpty
    stage: DiscussionStage
    summary: NonEmpty
    span: SourceEvidenceSpan


class StrategicManoeuvreOutput(StrictModel):
    id: NonEmpty
    stage: DiscussionStage
    topical_potential: NonEmpty
    audience_demand: NonEmpty
    presentational_device: NonEmpty
    span: SourceEvidenceSpan


class DerailmentOutput(StrictModel):
    id: NonEmpty
    stage: DiscussionStage
    rule_id: CriticalDiscussionRuleId
    rule_title: NonEmpty
    fallacy_type: NonEmpty
    explanation: NonEmpty
    span: SourceEvidenceSpan

    @model_validator(mode="after")
    def verify_rule_catalogue(self) -> Self:
        rule = CRITICAL_DISCUSSION_RULES[self.rule_id]
        if self.rule_title != rule.title or self.fallacy_type not in rule.recognized_fallacies:
            raise ValueError("DerailmentOutput must match CRITICAL_DISCUSSION_RULES")
        return self


class PragmaDialecticsOutput(StrictModel):
    standpoints: tuple[StandpointOutput, ...]
    stage_segments: tuple[StageSegmentOutput, ...]
    strategic_manoeuvres: tuple[StrategicManoeuvreOutput, ...]
    derailments: tuple[DerailmentOutput, ...]
    derailment_count: NonNegativeInt
    violated_rules: tuple[CriticalDiscussionRuleId, ...]
    extraction: ExtractionRecord

    @model_validator(mode="after")
    def verify_summary_fields(self) -> Self:
        if self.derailment_count != len(self.derailments):
            raise ValueError("derailment_count must match len(derailments)")
        expected_rules = tuple(dict.fromkeys(d.rule_id for d in self.derailments))
        if self.violated_rules != expected_rules:
            raise ValueError("violated_rules must reproduce distinct rule_ids in derailments")
        return self
