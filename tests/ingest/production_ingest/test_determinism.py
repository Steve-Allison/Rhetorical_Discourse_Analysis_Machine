"""Cached and uncached semantic determinism for immutable requests."""

from pathlib import Path

from rdam.ingest import CacheStatus, ProductionIngestor, SourceArtifact
from rdam.ingest.identity import (
    analysis_outcome_semantic_projection,
    canonical_json_bytes,
)

from .conftest import ParserBuilder


def test_cached_and_uncached_runs_have_byte_identical_semantic_payloads(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    source = SourceArtifact.from_text("First. Second.", source_name="determinism.txt")
    ingestor = ProductionIngestor(parser=parser_builder())
    uncached = tuple(ingestor.analyse(source) for _ in range(5))
    cached = tuple(ingestor.analyse(source, cache_directory=tmp_path) for _ in range(5))

    identities = tuple(result.semantic_digest for result in (*uncached, *cached))
    assert all(identity is not None for identity in identities)
    assert len({identity.hex_digest for identity in identities if identity is not None}) == 1
    assert cached[0].execution.cache_status is CacheStatus.WRITTEN
    assert all(result.execution.cache_status is CacheStatus.HIT for result in cached[1:])
    semantic_bytes = {
        canonical_json_bytes(analysis_outcome_semantic_projection(result))
        for result in (*uncached, *cached)
    }
    assert len(semantic_bytes) == 1
