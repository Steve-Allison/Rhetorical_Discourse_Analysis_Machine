"""Analysis request, result, and execution identity boundaries."""

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.contracts.analysis import MarkerRefinementMode

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
