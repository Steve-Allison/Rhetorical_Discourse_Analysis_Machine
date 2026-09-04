"""Privacy-safe default exception and failure-record rendering."""

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.failure import (
    DiagnosticPolicy,
    FailureCategory,
    LifecycleStage,
    PreparationCompletedEvidence,
    ProductionFailure,
    ProductionIngestError,
    Retryability,
)

from .conftest import ParserBuilder


def test_default_rendering_redacts_nested_completed_evidence(
    parser_builder: ParserBuilder,
) -> None:
    marker = "PRIVATE-MARKER-9fbb"
    preparation = ProductionIngestor(parser=parser_builder()).prepare(
        SourceArtifact.from_text(marker, source_name="/private/location/source.txt")
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
    assert marker not in str(error)
    assert marker not in repr(error)
    assert "/private/location" not in str(error)
    assert "/private/location" not in repr(error)
    assert marker not in error.safe_record(execution_id="safe").model_dump_json()

    diagnostic = error.diagnostic_record(
        policy=DiagnosticPolicy(include_private_content=True),
        execution_id="diagnostic",
    )
    assert marker in diagnostic.model_dump_json()
