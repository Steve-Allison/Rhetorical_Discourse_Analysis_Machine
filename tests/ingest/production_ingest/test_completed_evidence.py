"""Monotonic full and safe completed-stage evidence projections."""

import pytest
from pydantic import ValidationError

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.contracts.failure import (
    FailureCategory,
    LifecycleStage,
    PreparationCompletedEvidence,
    ProductionFailure,
    ProductionIngestError,
    Retryability,
)

from .conftest import ParserBuilder


def test_safe_completed_evidence_retains_identities_and_counts_not_content(
    parser_builder: ParserBuilder,
) -> None:
    preparation = ProductionIngestor(parser=parser_builder()).prepare(
        SourceArtifact.from_text("private-marker-content", source_name="private.txt")
    )
    error = ProductionIngestError(
        ProductionFailure(
            failed_stage=LifecycleStage.INFERENCE,
            category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
            code="inference_failed",
            retryability=Retryability.UNKNOWN,
            message_template="parser_execution_failed",
            completed=PreparationCompletedEvidence(preparation=preparation),
        )
    )
    safe = error.safe_record(execution_id="failure-1")
    assert safe.semantic.safe_completed.kind == "preparation"
    assert safe.semantic.safe_completed.item_count == len(preparation.semantic.inventory)
    assert safe.semantic.safe_completed.semantic_identities
    assert "private-marker-content" not in safe.model_dump_json()


def test_completed_evidence_cannot_equal_or_follow_failed_stage(
    parser_builder: ParserBuilder,
) -> None:
    preparation = ProductionIngestor(parser=parser_builder()).prepare(
        SourceArtifact.from_text("content", source_name="source.txt")
    )
    with pytest.raises(ValidationError, match="stage before"):
        ProductionFailure(
            failed_stage=LifecycleStage.PREPARATION,
            category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
            code="preparation_failed",
            retryability=Retryability.UNKNOWN,
            message_template="preparation_operation_failed",
            completed=PreparationCompletedEvidence(preparation=preparation),
        )
