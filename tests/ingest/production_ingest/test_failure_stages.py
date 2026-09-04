"""Stable nine-stage production failure taxonomy and causality."""

from typing import Any

import pytest
from pydantic import ValidationError

from rdam.ingest import ProductionIngestError, ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.failure import (
    FailureCategory,
    LifecycleStage,
    NoCompletedEvidence,
    PreparationCompletedEvidence,
    ProductionFailure,
    Retryability,
)
from rdam.ingest.contracts.base import SemanticVersion
from rdam.ingest.contracts.preparation import CapacityUnit, AnalysisCapacity
from rdam.ingest.contracts.analysis import AnalysisPolicy
from rdam.ingest.contracts.inference import OutputFormalism
from rdam.ingest.service import DEFAULT_ANALYSIS_POLICY

from .conftest import ParserBuilder


def _erst_policy() -> AnalysisPolicy:
    return AnalysisPolicy.model_validate(
        {
            **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
            "output_formalism": OutputFormalism.ERST_GRAPH,
        }
    )


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
    capacity = AnalysisCapacity(
        unit=CapacityUnit.TOKEN_COUNT,
        maximum=2,
        estimation_algorithm="test",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="test",
    )
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("one two three", source_name="source.txt"),
            capacity=capacity,
        )
    assert raised.value.failure.failed_stage is LifecycleStage.PLANNING
    assert raised.value.failure.completed.kind == "acquisition"
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE


def test_preparation_validation_failure_retains_complete_preparation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def invalid(_outcome: object) -> None:
        raise ValueError("PRIVATE validation detail")

    monkeypatch.setattr("rdam.ingest.prepare.validate_preparation_outcome", invalid)
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

    monkeypatch.setattr("rdam.ingest.service.prepare_source", unexpected)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.PREPARATION
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "PRIVATE" not in str(raised.value)


def test_harvest_io_error_is_internal_unknown_not_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unreadable(*_args: object) -> None:
        raise OSError("PRIVATE io detail")

    monkeypatch.setattr("rdam.ingest._harvest.inventory_source", unreadable)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.PREPARATION
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "PRIVATE" not in str(raised.value)


def test_preparation_type_error_is_internal_unknown_not_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_args: object) -> None:
        raise TypeError("PRIVATE bug detail")

    monkeypatch.setattr("rdam.ingest.prepare.apply_policy", broken)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "PRIVATE" not in str(raised.value)


def test_completed_evidence_must_precede_the_failed_stage() -> None:
    preparation = ProductionIngestor().prepare(
        SourceArtifact.from_text("content", source_name="source.txt")
    )
    evidence = PreparationCompletedEvidence(preparation=preparation)
    with pytest.raises(ValidationError, match="before the failed stage"):
        ProductionFailure(
            failed_stage=LifecycleStage.PREPARATION,
            category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
            code="stage_operation_failed",
            retryability=Retryability.UNKNOWN,
            message_template="stage_operation_failed",
            completed=evidence,
        )
    inference_failure = ProductionFailure(
        failed_stage=LifecycleStage.INFERENCE,
        category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
        code="stage_operation_failed",
        retryability=Retryability.UNKNOWN,
        message_template="stage_operation_failed",
        completed=evidence,
    )
    assert inference_failure.completed.kind == "preparation"


def test_subdivided_erst_without_completion_support_is_typed_provider_unavailable(
    parser_builder: ParserBuilder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rdam.rst.contracts import RstDocument

    text = "First. Second. Third. Fourth."
    parser = parser_builder(maximum=2)
    unit_result = parser.analyse_document(
        RstDocument.from_text(text, document_id="subdivided.txt")
    )
    source = SourceArtifact.from_edus(
        ("First.", "Second.", "Third.", "Fourth."), source_name="subdivided.txt"
    )
    # The deterministic fixture parser has no subdivided-unit support; unit
    # analysis and recombination are not under test here, only the branch that
    # fires when the recombined parser lacks document-global eRST completion.
    monkeypatch.setattr(
        "rdam.ingest.service._analyse_parser_unit",
        lambda *_args, **_kwargs: unit_result,
    )
    monkeypatch.setattr(
        "rdam.ingest.recombination.recombine_parser_results",
        lambda **_kwargs: unit_result,
    )
    ingestor = ProductionIngestor(parser=parser)
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(source, analysis_policy=_erst_policy())
    assert raised.value.failure.failed_stage is LifecycleStage.INFERENCE
    assert raised.value.failure.code == "erst_completion_unsupported"
    assert raised.value.failure.category is FailureCategory.PROVIDER_UNAVAILABLE
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE
    assert raised.value.failure.completed.kind == "preparation"


def test_validation_internal_failure_is_not_labelled_a_validation_verdict(
    parser_builder: ParserBuilder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rdam.ingest import validation as validation_module

    original = validation_module.build_analysis_validation_receipt
    calls = {"count": 0}

    def broken_after_parser_internal_call(*args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        if calls["count"] > 1:
            raise RuntimeError("PRIVATE validator bug")
        return original(*args, **kwargs)

    monkeypatch.setattr(
        "rdam.ingest.validation.build_analysis_validation_receipt",
        broken_after_parser_internal_call,
    )
    ingestor = ProductionIngestor(parser=parser_builder())
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(
            SourceArtifact.from_text("First. Second.", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.VALIDATION
    assert raised.value.failure.code == "analysis_validation_internal_failure"
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "PRIVATE" not in str(raised.value)


def test_safe_cause_rejects_free_text_message_templates() -> None:
    from rdam.ingest.contracts.failure import SafeCause

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        SafeCause(
            category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
            exception_type="ValueError",
            message_template="leaked private detail: /private/path",
        )


def test_unrelated_missing_module_is_not_blamed_on_a_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_unrelated(*_args: object) -> None:
        raise ModuleNotFoundError(
            "No module named 'definitely_not_installed'",
            name="definitely_not_installed",
        )

    monkeypatch.setattr("rdam.ingest._harvest.inventory_source", missing_unrelated)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(
            SourceArtifact.from_text("content", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.CLASSIFICATION
    assert raised.value.failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert raised.value.failure.diagnostic_context == ()


def test_matching_missing_adapter_reports_the_true_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rdam.ingest import SourceForm
    from rdam.ingest.contracts.failure import MissingDistributionContext

    def missing_adapter(*_args: object) -> None:
        raise ModuleNotFoundError("No module named 'markdown_it'", name="markdown_it")

    monkeypatch.setattr("rdam.ingest._harvest.inventory_source", missing_adapter)
    source = SourceArtifact.from_bytes(
        b"# heading",
        source_form=SourceForm.MARKDOWN,
        source_name="doc.md",
        media_type="text/markdown; charset=utf-8",
    )
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().prepare(source)
    assert raised.value.failure.category is FailureCategory.PROVIDER_UNAVAILABLE
    assert raised.value.failure.retryability is Retryability.NOT_RETRYABLE
    context = raised.value.failure.diagnostic_context[0]
    assert isinstance(context, MissingDistributionContext)
    assert context.distributions == ("markdown-it-py",)
    assert context.required_extra == "formats"


def test_enrichment_failure_claims_only_inference_completed(
    parser_builder: ParserBuilder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("PRIVATE enrichment bug")

    monkeypatch.setattr("rdam.ingest.enrichment.enrich_parser_evidence", broken)
    ingestor = ProductionIngestor(parser=parser_builder())
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(
            SourceArtifact.from_text("First. Second.", source_name="source.txt")
        )
    assert raised.value.failure.failed_stage is LifecycleStage.ASSEMBLY
    assert raised.value.failure.code == "source_evidence_enrichment_failed"
    assert raised.value.failure.completed.kind == "inference"
    assert raised.value.failure.retryability is Retryability.UNKNOWN
    assert "PRIVATE" not in str(raised.value)


def test_identity_contradiction_carries_completed_inference_evidence(
    parser_builder: ParserBuilder,
    tmp_path: Any,
) -> None:
    from .conftest import DeterministicParser

    class MismatchedParser(DeterministicParser):
        def describe_analysis_identity(self, **kwargs: Any) -> Any:
            kwargs["segmentation_source"] = "presegmented"
            return super().describe_analysis_identity(**kwargs)

    base = parser_builder()
    parser = MismatchedParser(
        analysis_capacity=base.analysis_capacity,
        model_release_identity=base.model_release_identity,
    )
    ingestor = ProductionIngestor(parser=parser)
    with pytest.raises(ProductionIngestError) as raised:
        ingestor.analyse(
            SourceArtifact.from_text("First. Second.", source_name="source.txt"),
            cache_directory=tmp_path,
        )
    assert raised.value.failure.failed_stage is LifecycleStage.VALIDATION
    assert raised.value.failure.code == "runtime_identity_contradiction"
    assert raised.value.failure.completed.kind == "inference"


def test_cli_boundary_failure_labels_follow_the_exception_kind() -> None:
    from rdam.rst.cli import _safe_boundary_failure

    io_failure = _safe_boundary_failure(
        OSError("disk momentarily unavailable"),
        stage=LifecycleStage.ACQUISITION,
        category=FailureCategory.MALFORMED_INPUT,
        code="cli_source_acquisition_failed",
        message_template="cli_source_could_not_be_acquired",
    )
    assert io_failure.category is FailureCategory.INTERNAL_PROCESSING_FAILURE
    assert io_failure.retryability is Retryability.UNKNOWN

    parse_failure = _safe_boundary_failure(
        ValueError("bad value"),
        stage=LifecycleStage.ACQUISITION,
        category=FailureCategory.MALFORMED_INPUT,
        code="cli_source_acquisition_failed",
        message_template="cli_source_could_not_be_acquired",
    )
    assert parse_failure.category is FailureCategory.MALFORMED_INPUT
    assert parse_failure.retryability is Retryability.NOT_RETRYABLE

    from rdam.ingest.contracts.failure import AcquisitionCompletedEvidence

    source = SourceArtifact.from_text("content", source_name="source.txt")
    configured_failure = _safe_boundary_failure(
        ValueError("bad release"),
        stage=LifecycleStage.INFERENCE,
        category=FailureCategory.PROVIDER_UNAVAILABLE,
        code="cli_provider_configuration_failed",
        message_template="configured_parser_could_not_be_created",
        completed=AcquisitionCompletedEvidence(source=source.summary()),
    )
    assert configured_failure.completed.kind == "acquisition"
