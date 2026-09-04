"""The machine-owned contracts expose one name and one wire shape."""

import json

import pytest
from pydantic import ValidationError

import rdam.ingest as ingest
from rdam.ingest import ProductionIngestor, SemanticVersion, SourceArtifact, load_contract, serialize_contract
from rdam.ingest.contracts.preparation import AnalysisCapacity, AnalysisPlan, CapacityUnit, PreparedDocument


def test_only_canonical_type_names_are_exported() -> None:
    assert ingest.AnalysisCapacity is AnalysisCapacity
    assert ingest.PreparedDocument is PreparedDocument
    assert not hasattr(ingest, "ParserCapacity")
    assert not hasattr(ingest, "PreparedRstDocument")


def test_capacity_has_one_python_and_wire_name() -> None:
    capacity = AnalysisCapacity(
        unit=CapacityUnit.EDU_COUNT,
        maximum=2,
        estimation_algorithm="edu_count",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="declared_test_limit",
    )
    outcome = ProductionIngestor().prepare(
        SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="capacity.edus"),
        capacity=capacity,
    )
    plan = outcome.semantic.analysis_plan
    assert plan.capacity == capacity
    assert not hasattr(plan, "parser_capacity")
    assert "capacity" in AnalysisPlan.model_fields
    assert "parser_capacity" not in AnalysisPlan.model_fields
    assert plan.model_dump(mode="json")["capacity"] == capacity.model_dump(mode="json")
    encoded = serialize_contract(outcome)
    assert serialize_contract(load_contract(encoded)) == encoded
    obsolete = plan.model_dump(mode="json")
    obsolete["parser_capacity"] = obsolete.pop("capacity")
    with pytest.raises(ValidationError):
        AnalysisPlan.model_validate_json(json.dumps(obsolete))
