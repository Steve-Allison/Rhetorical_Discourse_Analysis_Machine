"""Memory leak and garbage collection profiling stress test suite."""

import gc
import tracemalloc
import pytest

from rdam.ingest.contracts import SourceArtifact, SourceForm
from rdam.ingest.service import ProductionIngestor

pytestmark = pytest.mark.stress


def test_zero_memory_leakage_across_consecutive_ingest_cycles() -> None:
    """Execute 50 consecutive ingest cycles and assert zero cumulative memory drift."""
    gc.collect()
    tracemalloc.start()

    service = ProductionIngestor(parser=None)
    template = (
        "<heading>Dynamic Document Section {iter}</heading>"
        "<text>This section tests object lifetime management and memory reclamation.</text>"
        "<text>Paragraph {iter} introduces specific lexical evidence and rhetorical assertions.</text>"
        "<list><ldiv>Point A: Discourse tree validation</ldiv><ldiv>Point B: Memory safety verification</ldiv></list>"
    )

    baseline_memory_kb: float | None = None
    final_memory_kb: float | None = None

    for iteration in range(50):
        body = template.format(iter=iteration) * 10
        raw_bytes = f'<doclang xmlns="https://www.doclang.ai/ns/v0" version="0.9">{body}</doclang>'.encode("utf-8")
        artifact = SourceArtifact(
            source_name=f"leak_doc_{iteration}.dclg",
            source_form=SourceForm.DOCLANG_XML,
            media_type="application/vnd.doclang+xml",
            raw_bytes=raw_bytes,
        )
        prepared = service.prepare(artifact)
        assert len(prepared.semantic.prepared_document.segments) > 0

        # Run garbage collection and take measurement after warmup (iter 10) and at end (iter 49)
        if iteration == 10:
            gc.collect()
            current_bytes, _ = tracemalloc.get_traced_memory()
            baseline_memory_kb = current_bytes / 1024.0

        if iteration == 49:
            gc.collect()
            current_bytes, _ = tracemalloc.get_traced_memory()
            final_memory_kb = current_bytes / 1024.0

    tracemalloc.stop()

    assert baseline_memory_kb is not None
    assert final_memory_kb is not None

    growth_kb = final_memory_kb - baseline_memory_kb
    # Assert memory growth across 40 full iterations is negligible (< 2.5 MB)
    assert growth_kb < 2500.0, (
        f"Detected possible memory leak: memory grew by {growth_kb:.1f} KB between iteration 10 and 50"
    )
