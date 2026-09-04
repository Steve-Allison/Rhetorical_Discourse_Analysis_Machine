"""One inventory, independently reproducible plans with different capacity units."""

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.preparation import ContentInventory, ContentRequirement, AnalysisCapacity, CapacityUnit, BoundaryPreference
from rdam.ingest.contracts.source import SourceForm
from rdam.ingest.projection import project
from tests.ingest.test_projection_contracts import prose_requirement


def test_plans_use_their_own_capacity_and_preserve_every_character() -> None:
    source = SourceArtifact.from_edus(("One two.", "Three four.", "Five six.", "Seven eight."), source_name="capacity.edus")
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    base = prose_requirement()
    for unit in CapacityUnit:
        capacity = AnalysisCapacity.model_validate({**base.capacity.model_dump(), "unit": unit, "maximum": 3})
        requirement = ContentRequirement.model_validate({**base.model_dump(exclude={"semantic_digest"}), "capacity": capacity})
        result = project(inventory, requirement)
        assert result.inventory_identity == inventory.semantic_digest
        assert result.analysis_plan.capacity == capacity
        assert capacity.estimation_algorithm and capacity.estimation_version
        document = result.prepared_document
        rebuilt = "".join(document.text[document.segments[part.first_segment_order].prepared_range.start:
                                       document.segments[part.last_segment_order].prepared_range.end]
                          for part in result.analysis_plan.units)
        assert rebuilt == document.text
        assert all(part.estimated_demand <= part.capacity for part in result.analysis_plan.units)


def test_boundary_preferences_change_where_units_cut() -> None:
    source = SourceArtifact.from_bytes(b"First.\n\n# Heading\n\nSecond.\n\nThird.", source_form=SourceForm.MARKDOWN, source_name="boundaries.md")
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    base = prose_requirement()
    capacity = AnalysisCapacity.model_validate({**base.capacity.model_dump(), "maximum": 3})
    plans = []
    for preferences in ((BoundaryPreference.HEADING, BoundaryPreference.PARAGRAPH),
                        (BoundaryPreference.PARAGRAPH, BoundaryPreference.HEADING)):
        requirement = ContentRequirement.model_validate({**base.model_dump(exclude={"semantic_digest"}), "capacity": capacity, "boundary_preference": preferences})
        plans.append(project(inventory, requirement).analysis_plan)
    assert plans[0].units[0].last_segment_order != plans[1].units[0].last_segment_order
