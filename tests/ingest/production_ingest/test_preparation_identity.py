"""Preparation semantic-identity mutation coverage."""

from rdam.ingest import AnalysisCapacity, ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.base import SemanticVersion
from rdam.ingest.contracts.preparation import CapacityUnit
from rdam.ingest.policy import DEFAULT_PLANNING_POLICY, DEFAULT_PREPARATION_POLICY


def test_every_semantic_preparation_dimension_changes_identity() -> None:
    ingestor = ProductionIngestor()
    source = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="source.edus")
    capacity = _capacity(2)
    baseline = ingestor.prepare(source, capacity=capacity)
    baseline_digest = baseline.semantic_digest
    variants = (
        ingestor.prepare(
            SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="renamed.edus"),
            capacity=capacity,
        ),
        ingestor.prepare(
            source,
            policy=DEFAULT_PREPARATION_POLICY.__class__.model_validate(
                {
                    **DEFAULT_PREPARATION_POLICY.model_dump(exclude={"semantic_digest"}),
                    "normalization": "unicode_nfc",
                }
            ),
            capacity=capacity,
        ),
        ingestor.prepare(
            source,
            planning_policy=DEFAULT_PLANNING_POLICY.__class__.model_validate(
                {
                    **DEFAULT_PLANNING_POLICY.model_dump(exclude={"semantic_digest"}),
                    "capacity_margin": 1,
                }
            ),
            capacity=_capacity(3),
        ),
        ingestor.prepare(source, capacity=_capacity(3)),
        ingestor.prepare(
            SourceArtifact.from_edus(("One changed.", "Two.", "Three."), source_name="source.edus"),
            capacity=capacity,
        ),
    )
    assert baseline_digest is not None
    assert all(variant.semantic_digest != baseline_digest for variant in variants)
    assert len({variant.semantic_digest.hex_digest for variant in variants if variant.semantic_digest}) == len(variants)


def _capacity(maximum: int) -> AnalysisCapacity:
    return AnalysisCapacity(
        unit=CapacityUnit.EDU_COUNT,
        maximum=maximum,
        estimation_algorithm="fixture_edu_count",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="test",
    )
