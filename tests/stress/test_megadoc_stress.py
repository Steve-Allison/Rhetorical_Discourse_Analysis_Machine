"""Megadoc 50,000-word long-context stress test suite."""

import tracemalloc
import pytest

from rdam.rst.ingest.contracts import SourceArtifact, SourceForm
from rdam.rst.ingest.service import ProductionIngestor

pytestmark = pytest.mark.stress


def _generate_synthetic_megadoc(num_chapters: int = 50) -> str:
    """Generate a deterministic 50,000+ word multi-chapter Markdown document."""
    parts: list[str] = [
        "# Comprehensive Engineering & Discourse Analysis Megadoc Specification\n\n",
        "Author: Steve Allison  \nVersion: 4.0.0-PROD  \n\n",
    ]
    words_per_paragraph = (
        "Rhetorical Structure Theory provides a systemic framework for analyzing the coherence, "
        "hierarchical nuclearity, and inter-clausal relations of natural language documents. "
        "Through boundary-partitioned span analysis and asymmetric bilinear attention scoring, "
        "discourse parsers build both primary tree hierarchies and secondary directed acyclic graphs. "
        "Every paragraph in this section establishes evidence, background premises, and elaborative assertions. "
    ) * 4  # ~75 words per paragraph

    for ch in range(1, num_chapters + 1):
        parts.append(f"\n## Chapter {ch}: Technical Systems & Discourse Architecture\n\n")
        parts.append(f"In this chapter, system component {ch} is formally specified with rigorous mathematical bounds.\n\n")

        for sec in range(1, 5):
            parts.append(f"### Section {ch}.{sec}: Analytical Deep Dive into Subsystem {sec}\n\n")
            for _ in range(4):
                parts.append(f"{words_per_paragraph}\n\n")

            # Insert structured elements (tables, code blocks)
            parts.append(
                f"```python\n"
                f"def compute_layer_{ch}_{sec}(x: float) -> float:\n"
                f"    \"\"\"Compute layer activation for chapter {ch} section {sec}.\"\"\"\n"
                f"    return x * {ch} + {sec}.0\n"
                f"```\n\n"
            )
            parts.append(
                f"| Metric Component | Value ({ch}.{sec}) | Target Range | Status |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| Precision Head | {0.90 + (sec * 0.02):.2f} | > 0.85 | Verified |\n"
                f"| Calibration ECE | {0.03 + (sec * 0.005):.3f} | < 0.05 | Calibrated |\n\n"
            )

    return "".join(parts)


def test_megadoc_ingest_and_boundary_integrity() -> None:
    """Ingest and verify a 50,000+ word document with memory profiling."""
    tracemalloc.start()
    raw_markdown = _generate_synthetic_megadoc(num_chapters=50)
    word_count = len(raw_markdown.split())
    assert word_count >= 40000, f"Megadoc must be at least 40,000 words (got {word_count})"

    raw_bytes = raw_markdown.encode("utf-8")
    artifact = SourceArtifact(
        source_name="megadoc_50k.md",
        source_form=SourceForm.MARKDOWN,
        media_type="text/markdown",
        raw_bytes=raw_bytes,
    )
    service = ProductionIngestor(parser=None)
    prepared = service.prepare(artifact)
    document = prepared.semantic.prepared_document

    # 1. Structural Verification
    assert len(document.source.source_id) == 64
    assert len(document.segments) > 100, f"Expected > 100 prepared segments (got {len(document.segments)})"

    # 2. Strict Monotonic Character Span Integrity
    doc_text_len = len(document.text)
    last_end = 0
    for segment in document.segments:
        start = segment.prepared_range.start
        end = segment.prepared_range.end
        assert 0 <= start < end <= doc_text_len, f"Invalid segment span: ({start}, {end}) vs {doc_text_len}"
        assert start >= last_end, f"Overlapping span detected: {start} < {last_end}"
        last_end = end
        # Verify text slicing exact match
        assert document.text[start:end] == segment.text

    # 3. Memory Consumption Assertion (< 500 MB peak RAM)
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak_mem / (1024 * 1024)
    assert peak_mb < 500.0, f"Megadoc ingest exceeded 500 MB memory ceiling (peak was {peak_mb:.1f} MB)"
