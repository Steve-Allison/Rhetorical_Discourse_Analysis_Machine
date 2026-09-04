"""Shared construction mechanics; each provider owns its admitted content classes."""

from rdam.ingest.contracts.base import SemanticVersion
from rdam.ingest.contracts.preparation import (
    AnalysisCapacity, CapacityUnit, ContentRequirement, RepresentationProjection, TableLinearisationParameters,
)
from rdam.ingest.contracts.source import ContentClass
from rdam.ingest.policy import DEFAULT_PLANNING_POLICY

# An application input budget, not a claim about any vendor's context window.
LLM_INPUT_TOKEN_BUDGET = 8192


def llm_requirement(
    requirement_id: str,
    admitted_classes: tuple[ContentClass, ...],
    *,
    requires_speaker_identity: bool,
) -> ContentRequirement:
    tables = bool({ContentClass.TABLE, ContentClass.TABLE_CELL}.intersection(admitted_classes))
    return ContentRequirement(
        requirement_id=requirement_id, admitted_classes=admitted_classes,
        representation_projections=(RepresentationProjection(
            representation_kind="table", parameters=TableLinearisationParameters(),
        ),) if tables else (),
        capacity=AnalysisCapacity(
            unit=CapacityUnit.TOKEN_COUNT, maximum=LLM_INPUT_TOKEN_BUDGET,
            estimation_algorithm="whitespace_token_count", estimation_version=SemanticVersion(root="1.0.0"),
            source="rdam.llm/application-input-budget-v1",
        ),
        boundary_preference=DEFAULT_PLANNING_POLICY.boundary_preference,
        normalization="preserve", requires_speaker_identity=requires_speaker_identity,
    )
