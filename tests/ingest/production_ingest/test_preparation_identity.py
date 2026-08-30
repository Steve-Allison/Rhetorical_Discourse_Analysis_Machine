"""Preparation semantic-identity mutation coverage."""

from isanlp_rst.ingest import ParserCapacity, ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.contracts.base import SemanticVersion
from isanlp_rst.ingest.contracts.preparation import CapacityUnit
from isanlp_rst.ingest.policy import DEFAULT_PLANNING_POLICY, DEFAULT_PREPARATION_POLICY


def test_every_semantic_preparation_dimension_changes_identity() -> None:
    ingestor = ProductionIngestor()
    source = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="source.edus")
    capacity = _capacity(2)
    baseline = ingestor.prepare(source, parser_capacity=capacity)
    baseline_digest = baseline.semantic_digest
    variants = (
        ingestor.prepare(
            SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="renamed.edus"),
            parser_capacity=capacity,
        ),
        ingestor.prepare(
            source,
            policy=DEFAULT_PREPARATION_POLICY.__class__.model_validate(
                {
                    **DEFAULT_PREPARATION_POLICY.model_dump(exclude={"semantic_digest"}),
                    "normalization": "unicode_nfc",
                }
            ),
            parser_capacity=capacity,
        ),
        ingestor.prepare(
            source,
            planning_policy=DEFAULT_PLANNING_POLICY.__class__.model_validate(
                {
                    **DEFAULT_PLANNING_POLICY.model_dump(exclude={"semantic_digest"}),
                    "capacity_margin": 1,
                }
            ),
            parser_capacity=_capacity(3),
        ),
        ingestor.prepare(source, parser_capacity=_capacity(3)),
        ingestor.prepare(
            SourceArtifact.from_edus(("One changed.", "Two.", "Three."), source_name="source.edus"),
            parser_capacity=capacity,
        ),
    )
    assert baseline_digest is not None
    assert all(variant.semantic_digest != baseline_digest for variant in variants)
    assert len({variant.semantic_digest.hex_digest for variant in variants if variant.semantic_digest}) == len(variants)


def _capacity(maximum: int) -> ParserCapacity:
    return ParserCapacity(
        unit=CapacityUnit.EDU_COUNT,
        maximum=maximum,
        estimation_algorithm="fixture_edu_count",
        estimation_version=SemanticVersion(root="2.0.0"),
        source="test",
    )
