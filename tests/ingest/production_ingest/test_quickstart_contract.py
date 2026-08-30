"""Executable source-valid assertions from the Feature 004 quickstart."""

import pytest

from isanlp_rst.contracts import RstDocument
from isanlp_rst.ingest import (
    AnalysedOutcome,
    Availability,
    CapacityUnit,
    ModelIdentityState,
    ParserCapacity,
    ProductionIngestError,
    ProductionIngestor,
    SafeProductionFailureRecord,
    SemanticVersion,
    SourceArtifact,
    describe_capabilities,
    load_contract,
    serialize_contract,
)

from .conftest import ParserBuilder


def test_model_free_capability_and_preparation_quickstart() -> None:
    capabilities = describe_capabilities()
    assert capabilities.semantic.package_version == "5.0.0"
    assert capabilities.contract_version == "2.0.0"
    assert capabilities.semantic.parser_identity_state is ModelIdentityState.NOT_CONFIGURED
    assert all(
        isinstance(item.availability, Availability)
        for item in capabilities.semantic.source_forms
    )

    source = SourceArtifact.from_text(
        "A claim. Because evidence supports it.",
        source_name="example.txt",
    )
    capacity = ParserCapacity(
        unit=CapacityUnit.TOKEN_COUNT,
        maximum=8192,
        estimation_algorithm="provider_declared",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="consumer_known_capacity",
    )
    prepared = ProductionIngestor().prepare(source, parser_capacity=capacity)
    assert prepared.semantic.inventory_coverage.covered_units == (
        prepared.semantic.inventory_coverage.total_units
    )
    assert prepared.semantic.mapping_coverage.covered_units == (
        prepared.semantic.mapping_coverage.total_units
    )
    assert prepared.semantic.analysis_plan.status.value in {"single_unit", "subdivided"}
    encoded = serialize_contract(prepared)
    assert serialize_contract(load_contract(encoded)) == encoded


def test_parser_result_graph_projection_and_component_receipt_quickstart(
    parser_builder: ParserBuilder,
) -> None:
    parser = parser_builder()
    source = SourceArtifact.from_text(
        "A claim. Because evidence supports it.",
        source_name="example.txt",
    )
    outcome = ProductionIngestor(parser=parser).analyse(source)
    assert isinstance(outcome, AnalysedOutcome)
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    assert parser_result.semantic.loaded_components
    assert outcome.semantic.validation is not None and outcome.semantic.validation.passed

    document = RstDocument.from_text(
        "A claim. Because evidence supports it.",
        document_id="parser-only",
    )
    direct = parser.analyse_document(document)
    projection = parser.parse_document(document)
    assert projection.nodes == direct.semantic.analysis.nodes
    assert projection.primary_edges == direct.semantic.analysis.primary_edges
    assert projection.secondary_edges == direct.semantic.analysis.secondary_edges


def test_typed_failure_quickstart_is_private_by_default() -> None:
    source = SourceArtifact.from_text(
        "A claim. Because evidence supports it.",
        source_name="example.txt",
    )
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor().analyse(source)
    payload = serialize_contract(raised.value.failure)
    assert b"A claim" not in payload
    assert isinstance(load_contract(payload), SafeProductionFailureRecord)
