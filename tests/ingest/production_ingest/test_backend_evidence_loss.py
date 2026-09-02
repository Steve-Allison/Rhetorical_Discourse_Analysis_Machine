"""Deliberate backend handoff loss must fail closed."""

import pytest

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.parser_result import validate_parser_analysis_result

from .conftest import ParserBuilder


@pytest.mark.parametrize("lost_field", ("structure_decision", "analysis_anchor", "validation_check"))
def test_deliberate_evidence_substitution_is_rejected(
    lost_field: str,
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="loss.txt")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    semantic = result.semantic
    if lost_field == "structure_decision":
        primary = semantic.primary_inference.model_copy(update={"structure_decisions": ()})
        semantic = semantic.model_copy(update={"primary_inference": primary})
    elif lost_field == "analysis_anchor":
        semantic = semantic.model_copy(update={"anchors": semantic.anchors[:-1]})
    else:
        validation = semantic.validation.model_copy(update={"checks": semantic.validation.checks[:-1]})
        semantic = semantic.model_copy(update={"validation": validation})
    with pytest.raises(ValueError):
        validate_parser_analysis_result(result.model_copy(update={"semantic": semantic}))
