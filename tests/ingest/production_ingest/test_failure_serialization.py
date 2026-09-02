"""Canonical safe and explicit diagnostic failure persistence."""

from rdam.rst.ingest import load_contract, serialize_contract
from rdam.rst.ingest.contracts.failure import (
    DiagnosticProductionFailureRecord,
    DiagnosticPolicy,
    FailureCategory,
    LifecycleStage,
    ProductionFailure,
    ProductionIngestError,
    Retryability,
    SafeProductionFailureRecord,
)


def test_safe_and_diagnostic_failure_records_round_trip_canonically() -> None:
    error = ProductionIngestError(
        ProductionFailure(
            failed_stage=LifecycleStage.ACQUISITION,
            category=FailureCategory.MALFORMED_INPUT,
            code="invalid_source_bytes",
            retryability=Retryability.NOT_RETRYABLE,
            message_template="source_is_not_valid_utf8",
        )
    )
    safe = error.safe_record(execution_id="safe")
    assert isinstance(load_contract(serialize_contract(safe)), SafeProductionFailureRecord)
    assert serialize_contract(load_contract(serialize_contract(safe))) == serialize_contract(safe)

    diagnostic = error.diagnostic_record(
        policy=DiagnosticPolicy(include_private_content=True),
        execution_id="diagnostic",
    )
    assert serialize_contract(load_contract(serialize_contract(diagnostic))) == serialize_contract(
        diagnostic
    )


def test_production_failure_serializes_safely_unless_diagnostics_are_explicit() -> None:
    failure = ProductionFailure(
        failed_stage=LifecycleStage.ACQUISITION,
        category=FailureCategory.MALFORMED_INPUT,
        code="invalid_source_bytes",
        retryability=Retryability.NOT_RETRYABLE,
        message_template="source_is_not_valid_utf8",
    )
    assert isinstance(load_contract(serialize_contract(failure)), SafeProductionFailureRecord)
    assert isinstance(
        load_contract(
            serialize_contract(
                failure,
                diagnostic_policy=DiagnosticPolicy(include_private_content=True),
            )
        ),
        DiagnosticProductionFailureRecord,
    )
