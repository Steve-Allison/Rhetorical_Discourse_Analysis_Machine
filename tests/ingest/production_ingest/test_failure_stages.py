"""Stable nine-stage production failure taxonomy and causality."""

import pytest
from pydantic import ValidationError

from isanlp_rst.ingest import ProductionIngestError, ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.contracts.failure import (
    FailureCategory,
    LifecycleStage,
    NoCompletedEvidence,
    ProductionFailure,
    Retryability,
)
from isanlp_rst.ingest.contracts.base import SemanticVersion
from isanlp_rst.ingest.contracts.preparation import CapacityUnit, ParserCapacity


@pytest.mark.parametrize("stage", tuple(LifecycleStage))
def test_every_lifecycle_stage_has_a_stable_typed_failure(stage: LifecycleStage) -> None:
    failure = ProductionFailure(
        failed_stage=stage,
        category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
        code=f"{stage.value}_failed",
        retryability=Retryability.UNKNOWN,
        message_template="stage_operation_failed",
        completed=NoCompletedEvidence(),
    )
    assert failure.failed_stage is stage
    assert failure.code == f"{stage.value}_failed"


def test_failure_codes_and_templates_are_machine_stable() -> None:
    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        ProductionFailure(
            failed_stage=LifecycleStage.ACQUISITION,
            category=FailureCategory.MALFORMED_INPUT,
            code="private /tmp/path",
            retryability=Retryability.NOT_RETRYABLE,
            message_template="invalid_source",
        )


def test_provider_unavailability_cannot_claim_immediate_retryability() -> None:
    with pytest.raises(ValidationError, match="external state change"):
        ProductionFailure(
            failed_stage=LifecycleStage.INFERENCE,
            category=FailureCategory.PROVIDER_UNAVAILABLE,
            code="parser_unavailable",
            retryability=Retryability.RETRYABLE,
            message_template="parser_is_not_configured",
        )


def test_planning_failure_is_typed_at_the_planning_stage() -> None:
    capacity = ParserCapacity(
        unit=CapacityUnit.TOKEN_COUNT,
        maximum=2,
        estimation_algorithm="test",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="test",
    )
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("one two three", source_name="source.txt"),
            parser_capacity=capacity,
        )
    assert raised.value.failure.failed_stage is LifecycleStage.PLANNING
    assert raised.value.failure.completed.kind == "acquisition"
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE


def test_preparation_validation_failure_retains_complete_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid(_outcome: object) -> None:
        raise ValueError("PRIVATE validation detail")

    monkeypatch.setattr("isanlp_rst.ingest.prepare.validate_preparation_outcome", invalid)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.VALIDATION
    assert raised.value.failure.completed.kind == "preparation"
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE
    assert "PRIVATE" not in str(raised.value)
    assert isinstance(raised.value.__cause__, Exception)


def test_retryability_is_mandatory_on_every_failure() -> None:
    with pytest.raises(ValidationError, match="retryability"):
        ProductionFailure.model_validate(
            {
                "failed_stage": LifecycleStage.ACQUISITION,
                "category": FailureCategory.MALFORMED_INPUT,
                "code": "invalid_source",
                "message_template": "invalid_source",
            }
        )


def test_unconfigured_parser_failure_is_not_retryable() -> None:
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().analyse(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.INFERENCE
    assert raised.value.failure.category is FailureCategory.PROVIDER_UNAVAILABLE
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE


def test_unexpected_internal_failure_is_classified_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("PRIVATE internal detail")

    monkeypatch.setattr("isanlp_rst.ingest.service.prepare_source", unexpected)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.PREPARATION
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "PRIVATE" not in str(raised.value)
