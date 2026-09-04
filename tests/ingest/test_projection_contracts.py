"""Declared projections are strict, deterministic, and source-traceable."""

import pytest
from pydantic import ValidationError

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.base import SemanticVersion
from rdam.ingest.contracts.preparation import (
    AnalysisCapacity,
    CapacityUnit,
    ContentInventory,
    ContentRequirement,
    UnmetRequirement,
)
from rdam.ingest.contracts.source import ContentClass, SourceForm
from rdam.ingest.policy import DEFAULT_PLANNING_POLICY, DEFAULT_PREPARATION_POLICY
from rdam.ingest.projection import project
from tests.ingest.test_inventory_completeness import source_case
from rdam.rst.provider import RstProvider


def prose_requirement() -> ContentRequirement:
    return ContentRequirement(
        requirement_id="rst/authored-prose-v1",
        admitted_classes=DEFAULT_PREPARATION_POLICY.primary_classes,
        capacity=AnalysisCapacity(
            unit=CapacityUnit.EDU_COUNT,
            maximum=64,
            estimation_algorithm="provider_declared",
            estimation_version=SemanticVersion(root="2.0.0"),
            source="test_limit",
        ),
        boundary_preference=DEFAULT_PLANNING_POLICY.boundary_preference,
        normalization="preserve",
        requires_speaker_identity=False,
    )


def test_requirement_is_self_checking_and_closed() -> None:
    requirement = prose_requirement()
    assert ContentRequirement.model_validate_json(requirement.model_dump_json()) == requirement
    for change in (
        {"admitted_classes": ()},
        {"admitted_classes": (ContentClass.PARAGRAPH, ContentClass.PARAGRAPH)},
        {"admitted_classes": (ContentClass.TABLE,)},
        {"admitted_classes": (ContentClass.TABLE_CELL,)},
        {"boundary_preference": ()},
        {"requirement_id": ""},
        {"requires_speaker_identity": True},
    ):
        with pytest.raises(ValidationError):
            ContentRequirement.model_validate({**requirement.model_dump(), **change})
    with pytest.raises(ValidationError):
        UnmetRequirement(aspect="capacity", detail="", affected_item_ids=())


@pytest.mark.parametrize("device, safety", (("cpu", "concurrent"), ("mps", "concurrent"), ("cuda", "serialized")))
def test_rst_declares_requirement_and_parallel_safety_without_loading(
    device: str, safety: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("rdam.rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
    provider = RstProvider(device=device)
    declaration = provider.declaration
    assert declaration.content_requirement == provider.content_requirement
    assert declaration.parallel_safety == safety
    assert provider._parser is None
    with pytest.raises(ValidationError):
        type(declaration).model_validate({**declaration.model_dump(), "parallel_safety": "unknown"})


def test_project_reuses_inventory_and_preserves_rst_preparation() -> None:
    source = SourceArtifact.from_edus(("First.", "Second."), source_name="sample")
    requirement = prose_requirement()
    original = ProductionIngestor().prepare(source, capacity=requirement.capacity)
    inventory = ContentInventory.from_preparation(original)
    projection = project(inventory, requirement)
    assert projection == project(inventory, requirement)
    assert projection.prepared_document == original.semantic.prepared_document
    assert projection.analysis_plan == original.semantic.analysis_plan
    assert projection.transformations == original.semantic.transformations
    assert projection.unmet_requirements == ()
    assert projection.inventory_identity == inventory.semantic_digest
    assert inventory.items == original.semantic.inventory
    assert "".join(s.text for s in projection.prepared_document.segments) == "First. Second."


@pytest.mark.parametrize("form", tuple(SourceForm))
def test_rst_projection_preserves_all_source_forms(form: SourceForm) -> None:
    source, _ = source_case(form)
    requirement = prose_requirement()
    original = ProductionIngestor().prepare(source, capacity=requirement.capacity)
    projection = project(ContentInventory.from_preparation(original), requirement)
    assert projection.prepared_document == original.semantic.prepared_document
    assert projection.analysis_plan == original.semantic.analysis_plan
    assert projection.transformations == original.semantic.transformations
