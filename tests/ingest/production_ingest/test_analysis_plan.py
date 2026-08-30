"""Deterministic public analysis-plan and capacity tests."""

from isanlp_rst.ingest import ParserCapacity, ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.contracts.base import SemanticVersion
from isanlp_rst.ingest.contracts.preparation import CapacityUnit


def _capacity(maximum: int) -> ParserCapacity:
    return ParserCapacity(
        unit=CapacityUnit.EDU_COUNT,
        maximum=maximum,
        estimation_algorithm="fixture_edu_count",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="test",
    )


def test_absent_capacity_returns_explicit_not_planned_state() -> None:
    outcome = ProductionIngestor().prepare(
        SourceArtifact.from_edus(("One.", "Two."), source_name="two.edus")
    )
    plan = outcome.semantic.analysis_plan
    assert plan.status.value == "not_planned"
    assert plan.parser_capacity is None
    assert plan.units == ()


def test_capacity_returns_single_or_subdivided_complete_plan() -> None:
    source = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    single = ProductionIngestor().prepare(source, parser_capacity=_capacity(8)).semantic.analysis_plan
    subdivided = ProductionIngestor().prepare(source, parser_capacity=_capacity(2)).semantic.analysis_plan
    assert single.status.value == "single_unit"
    assert len(single.units) == 1
    assert subdivided.status.value == "subdivided"
    assert len(subdivided.units) == 2
    assert sum(unit.estimated_demand for unit in subdivided.units) == 3
    assert all(unit.estimated_demand <= unit.capacity for unit in subdivided.units)
    assert len(subdivided.recombination.links) == len(subdivided.units) - 1


def test_plan_semantics_are_deterministic() -> None:
    source = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    first = ProductionIngestor().prepare(source, parser_capacity=_capacity(2)).semantic.analysis_plan
    second = ProductionIngestor().prepare(source, parser_capacity=_capacity(2)).semantic.analysis_plan
    assert first == second
    assert first.semantic_digest == second.semantic_digest
