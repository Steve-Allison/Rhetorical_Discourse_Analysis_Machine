"""Projection identities depend only on immutable inventory and requirement content."""

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.preparation import ContentInventory, ContentRequirement
from rdam.ingest.projection import project
from tests.ingest.test_projection_contracts import prose_requirement


def test_projection_is_pure_across_round_trips() -> None:
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(SourceArtifact.from_text("One. Two.", source_name="test")))
    before = inventory.model_dump_json()
    requirement = prose_requirement()
    first = project(inventory, requirement)
    second = project(ContentInventory.model_validate_json(before), ContentRequirement.model_validate_json(requirement.model_dump_json()))
    assert first == second
    assert inventory.model_dump_json() == before
