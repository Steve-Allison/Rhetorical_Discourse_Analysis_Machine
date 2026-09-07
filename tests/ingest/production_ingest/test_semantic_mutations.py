"""Analysis request, result, and execution identity boundaries."""

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.analysis import MarkerRefinementMode
from rdam.ingest.serialization import load_contract, serialize_contract

from .conftest import ParserBuilder


def test_semantic_mutations_change_identity_and_execution_does_not(
    parser_builder: ParserBuilder,
) -> None:
    source = SourceArtifact.from_text("First. Second.", source_name="identity.txt")
    ingestor = ProductionIngestor(parser=parser_builder())
    first = ingestor.analyse(source)
    second = ingestor.analyse(source)
    assert first.semantic != second.semantic
    assert first.execution != second.execution
    assert first.semantic_digest == second.semantic_digest

    request = first.semantic.request
    policy = request.analysis_policy.__class__.model_validate(
        {
            **request.analysis_policy.model_dump(exclude={"semantic_digest"}),
            "marker_refinement": MarkerRefinementMode.DISABLED,
        }
    )
    changed_request = request.__class__.model_validate(
        {
            **request.model_dump(exclude={"semantic_digest"}),
            "analysis_policy": policy,
        }
    )
    assert changed_request.semantic_digest != request.semantic_digest
    with pytest.raises(ValueError, match="embedded parser result"):
        type(first.semantic).model_validate({
            **{name: getattr(first.semantic, name) for name in type(first.semantic).model_fields},
            "request": changed_request,
        })


def test_recombination_unit_timings_do_not_change_semantic_identity(
    parser_builder: ParserBuilder,
) -> None:
    source = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="identity.edus")
    result = ProductionIngestor(parser=parser_builder(maximum=2)).analyse(source)
    parser_result = result.semantic.parser_result
    assert parser_result is not None
    recombination = parser_result.semantic.recombination
    assert recombination is not None

    changed_recombination = recombination.model_copy(
        update={"unit_durations_ms": tuple(value + 100.0 for value in recombination.unit_durations_ms)}
    )
    changed_semantic = parser_result.semantic.model_copy(
        update={"recombination": changed_recombination}
    )
    changed_result = parser_result.__class__.model_validate(
        {
            **parser_result.model_dump(exclude={"semantic_digest"}),
            "semantic": changed_semantic,
        }
    )
    assert changed_result.semantic_digest == parser_result.semantic_digest


def test_outcome_stores_parser_graph_and_inference_once(parser_builder: ParserBuilder) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="single-evidence-owner")
    )
    parser = result.semantic.parser_result
    assert parser is not None
    assert result.semantic.analysis is parser.semantic.analysis
    assert result.semantic.primary_inference is parser.semantic.primary_inference
    payload = result.model_dump(mode="json")
    assert "policy" not in payload["semantic"]
    assert "composite_identity" not in payload["semantic"]
    assert result.semantic.policy is result.semantic.request.analysis_policy
    assert result.semantic.composite_identity is result.semantic.request.composite_analysis_identity
    assert "analysed_document" not in payload["semantic"]
    assert "anchors" not in payload["semantic"]
    assert "anchors" not in payload["semantic"]["parser_result"]["semantic"]
    assert result.semantic.analysed_document is not None
    assert result.semantic.anchors
    detached = result.semantic.model_copy(update={"parser_result": None})
    assert detached.analysed_document is None
    assert detached.anchors == ()
    for field in ("analysis", "primary_inference", "erst_completion", "recombination"):
        assert field not in payload["semantic"]
        assert field in payload["semantic"]["parser_result"]["semantic"]
    encoded = serialize_contract(result)
    assert serialize_contract(load_contract(encoded)) == encoded
