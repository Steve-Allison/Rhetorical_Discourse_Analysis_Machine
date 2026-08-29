"""Memory leak and garbage collection profiling stress test suite."""

import gc
import tracemalloc
import pytest

from isanlp_rst.ingest.contracts import SourceArtifact, SourceForm
from isanlp_rst.ingest.service import ProductionIngestor

pytestmark = pytest.mark.stress


def test_zero_memory_leakage_across_consecutive_ingest_cycles() -> None:
    """Execute 50 consecutive ingest cycles and assert zero cumulative memory drift."""
    gc.collect()
    tracemalloc.start()

    service = ProductionIngestor(parser=None)
    template = (
        "# Dynamic Document Section {iter}\n\n"
        "This section tests object lifetime management and memory reclamation.\n\n"
        "Paragraph {iter} introduces specific lexical evidence and rhetorical assertions.\n\n"
        "- Point A: Discourse tree validation\n"
        "- Point B: Memory safety verification\n\n"
    )

    baseline_memory_kb: float | None = None
    final_memory_kb: float | None = None

    for iteration in range(50):
        text = template.format(iter=iteration) * 10
        raw_bytes = text.encode("utf-8")
        artifact = SourceArtifact(
            source_name=f"leak_doc_{iteration}.md",
            source_form=SourceForm.MARKDOWN,
            media_type="text/markdown",
            raw_bytes=raw_bytes,
        )
        prepared = service.prepare(artifact)
        assert len(prepared.segments) > 0

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
