"""Complete preparation outcome construction and canonical persistence."""

from rdam.ingest import (
    PreparationPolicy,
    PreparationOutcome,
    ProductionIngestor,
    SourceArtifact,
    load_contract,
    serialize_contract,
)
from rdam.ingest.policy import DEFAULT_PREPARATION_POLICY


def test_preparation_outcome_contains_complete_semantic_and_execution_sections() -> None:
    outcome = ProductionIngestor().prepare(
        SourceArtifact.from_text("First paragraph.\n\nSecond paragraph.", source_name="source.txt")
    )
    assert outcome.kind == "preparation_outcome"
    assert outcome.contract == "isanlp_rst.production"
    assert outcome.contract_version == "2.0.0"
    assert outcome.semantic.source.source_name == "source.txt"
    assert outcome.semantic.source_contract.adapter
    assert outcome.semantic.inventory
    assert outcome.semantic.prepared_document.text
    assert outcome.semantic.analysis_plan.status.value == "not_planned"
    assert outcome.execution.execution_id
    assert outcome.execution.duration_ms >= 0.0
    assert outcome.semantic_digest is not None


def test_preparation_round_trip_is_canonical_and_execution_is_not_semantic() -> None:
    ingestor = ProductionIngestor()
    source = SourceArtifact.from_text("Stable preparation.", source_name="stable.txt")
    first = ingestor.prepare(source)
    second = ingestor.prepare(source)
    assert first.semantic == second.semantic
    assert first.execution != second.execution
    assert first.semantic_digest == second.semantic_digest

    encoded = serialize_contract(first)
    loaded = load_contract(encoded)
    assert isinstance(loaded, PreparationOutcome)
    assert serialize_contract(loaded) == encoded


def test_declared_normalization_is_applied_and_provenanced() -> None:
    policy = PreparationPolicy.model_validate(
        {
            **DEFAULT_PREPARATION_POLICY.model_dump(exclude={"semantic_digest"}),
            "normalization": "unicode_nfc",
        }
    )
    outcome = ProductionIngestor().prepare(
        SourceArtifact.from_text("Cafe\u0301", source_name="decomposed.txt"),
        policy=policy,
    )
    assert outcome.semantic.prepared_document.text == "Café"
    assert [item.transformation_kind for item in outcome.semantic.transformations] == [
        "unicode_normalization"
    ]
    segment = outcome.semantic.prepared_document.segments[0]
    assert segment.transformation_ids == (
        outcome.semantic.transformations[0].transformation_id,
    )
