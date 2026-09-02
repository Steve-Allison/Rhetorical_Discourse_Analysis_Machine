"""Composite participating-component and loaded-byte identity."""

import pytest

from rdam.rst.ingest import ProductionIngestor, SourceArtifact
from rdam.rst.ingest.parser_result import validate_parser_analysis_result

from .conftest import ParserBuilder


def test_every_immutable_component_has_an_exact_loaded_member_receipt(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="components.txt")
    )
    result = outcome.semantic.parser_result
    assert result is not None
    immutable = {
        component.component
        for component in (
            result.semantic.composite_identity.primary_parser,
            result.semantic.composite_identity.segmenter,
            result.semantic.composite_identity.marker_refiner,
            result.semantic.composite_identity.relation_inventory,
        )
        if component.state == "immutable_release"
    }
    assert {receipt.component for receipt in result.semantic.loaded_components} == immutable
    validate_parser_analysis_result(result)

    receipt = result.semantic.loaded_components[0]
    damaged = receipt.model_copy(
        update={"declared_identity": receipt.declared_identity.model_copy(update={"hex_digest": "f" * 64})}
    )
    semantic = result.semantic.model_copy(
        update={"loaded_components": (damaged, *result.semantic.loaded_components[1:])}
    )
    with pytest.raises(ValueError, match="receipt"):
        validate_parser_analysis_result(result.model_copy(update={"semantic": semantic}))
