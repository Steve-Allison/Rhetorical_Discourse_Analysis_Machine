"""Megadoc 50,000-word long-context stress test suite."""

import tracemalloc
import pytest

from rdam.ingest.contracts import SourceArtifact, SourceForm
from rdam.ingest.service import ProductionIngestor

pytestmark = pytest.mark.stress


def _generate_synthetic_megadoc(num_chapters: int = 50) -> str:
    """Generate a deterministic 50,000+ word multi-chapter DocLang document."""
    parts: list[str] = [
        '<doclang xmlns="https://www.doclang.ai/ns/v0" version="0.9">',
        "<title>Comprehensive Engineering and Discourse Analysis Megadoc Specification</title>",
        "<text>Author: Steve Allison. Version: 6.1.0-PROD.</text>",
    ]
    words_per_paragraph = (
        "Rhetorical Structure Theory provides a systemic framework for analyzing the coherence, "
        "hierarchical nuclearity, and inter-clausal relations of natural language documents. "
        "Through boundary-partitioned span analysis and asymmetric bilinear attention scoring, "
        "discourse parsers build both primary tree hierarchies and secondary directed acyclic graphs. "
        "Every paragraph in this section establishes evidence, background premises, and elaborative assertions. "
    ) * 4

    for ch in range(1, num_chapters + 1):
        parts.append(f"<heading level=\"1\">Chapter {ch}: Technical Systems and Discourse Architecture</heading>")
        parts.append(f"<text>In this chapter, system component {ch} is formally specified with rigorous mathematical bounds.</text>")

        for sec in range(1, 5):
            parts.append(f"<heading level=\"2\">Section {ch}.{sec}: Analytical Deep Dive into Subsystem {sec}</heading>")
            for _ in range(4):
                parts.append(f"<text>{words_per_paragraph}</text>")

            parts.append(
                f"<code>def compute_layer_{ch}_{sec}(x: float) -&gt; float:\n"
                f"    return x * {ch} + {sec}.0</code>"
            )
            parts.append(
                f"<table><ched/>Metric Component<ched/>Value ({ch}.{sec})<ched/>Status<nl/>"
                f"<fcel/>Precision Head<fcel/>{0.90 + (sec * 0.02):.2f}<fcel/>Verified<nl/>"
                f"<fcel/>Calibration ECE<fcel/>{0.03 + (sec * 0.005):.3f}<fcel/>Calibrated<nl/></table>"
            )
    parts.append("</doclang>")
    return "".join(parts)


def test_megadoc_ingest_and_boundary_integrity() -> None:
    """Ingest and verify a 50,000+ word document with memory profiling."""
    tracemalloc.start()
    raw_doclang = _generate_synthetic_megadoc(num_chapters=50)
    word_count = len(raw_doclang.split())
    assert word_count >= 40000, f"Megadoc must be at least 40,000 words (got {word_count})"

    raw_bytes = raw_doclang.encode("utf-8")
    artifact = SourceArtifact(
        source_name="megadoc_50k.dclg",
        source_form=SourceForm.DOCLANG_XML,
        media_type="application/vnd.doclang+xml",
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
