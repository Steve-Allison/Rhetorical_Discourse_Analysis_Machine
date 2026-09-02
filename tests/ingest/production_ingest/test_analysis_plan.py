"""Deterministic public analysis-plan and capacity tests."""

from rdam.rst.ingest import ParserCapacity, ProductionIngestor, SourceArtifact, SourceForm
from rdam.rst.ingest.contracts.base import SemanticVersion
from rdam.rst.ingest.contracts.preparation import BoundaryPreference, CapacityUnit
from rdam.rst.ingest.subdivision import build_analysis_plan
from rdam.rst.ingest.policy import DEFAULT_PLANNING_POLICY


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


def test_boundary_reason_states_the_actual_boundary_kind() -> None:
    source = SourceArtifact.from_bytes(
        b"# Title\n\nBody paragraph text.",
        source_form=SourceForm.MARKDOWN,
        source_name="doc.md",
        media_type="text/markdown; charset=utf-8",
    )
    prepared = ProductionIngestor().prepare(source).semantic.prepared_document
    capacity = ParserCapacity(
        unit=CapacityUnit.TOKEN_COUNT,
        maximum=3,
        estimation_algorithm="test",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="test",
    )
    plan = build_analysis_plan(prepared, capacity=capacity, policy=DEFAULT_PLANNING_POLICY)
    assert plan.status.value == "subdivided"
    assert plan.units[0].boundary_reason is BoundaryPreference.HEADING
    assert plan.units[1].boundary_reason is BoundaryPreference.PARAGRAPH


def test_plan_semantics_are_deterministic() -> None:
    source = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    first = ProductionIngestor().prepare(source, parser_capacity=_capacity(2)).semantic.analysis_plan
    second = ProductionIngestor().prepare(source, parser_capacity=_capacity(2)).semantic.analysis_plan
    assert first == second
    assert first.semantic_digest == second.semantic_digest
