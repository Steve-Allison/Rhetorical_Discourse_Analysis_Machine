"""Validation policy, checks, coverage, disposition, and digest."""

import pytest

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.parser_result import validate_parser_analysis_result

from .conftest import ParserBuilder


def test_required_validation_checks_are_complete_and_reproducible(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="validation.txt")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    receipt = result.validation_receipt
    assert receipt.passed
    assert all(check.outcome.value == "passed" for check in receipt.checks)
    assert receipt.semantic_digest is not None

    damaged = receipt.model_copy(update={"checks": receipt.checks[:-1]})
    semantic = result.semantic.model_copy(update={"validation": damaged})
    with pytest.raises(ValueError, match="receipt"):
        validate_parser_analysis_result(result.model_copy(update={"semantic": semantic}))
