"""Primary-tree and formal eRST validation invariants."""

from dataclasses import replace

import pytest

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.parser_result import validate_parser_analysis_result

from .conftest import ParserBuilder


def test_primary_tree_is_connected_acyclic_and_single_rooted(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="tree.txt")
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    validate_parser_analysis_result(parser_result)
    assert len(parser_result.analysis.nodes) == 3
    assert len(parser_result.analysis.primary_edges) == 2

    first_edge = parser_result.analysis.primary_edges[0]
    invalid = replace(
        parser_result.analysis,
        primary_edges=(replace(first_edge, child_id=first_edge.parent_id),),
    )
    invalid_semantic = parser_result.semantic.model_copy(update={"analysis": invalid})
    with pytest.raises(ValueError, match="primary"):
        validate_parser_analysis_result(
            parser_result.model_copy(update={"semantic": invalid_semantic})
        )
