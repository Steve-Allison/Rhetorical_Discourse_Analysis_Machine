import resource
from time import perf_counter

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact
from isanlp_rst.ingest.subdivision import build_subdivision_plan
from isanlp_rst.model_loading import ParserCapacity


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if value > 10_000_000 else value * 1_024


def test_one_million_character_preparation_is_lossless_and_locally_bounded() -> None:
    paragraph = "A structurally meaningful paragraph ends here.\n\n"
    text = (paragraph * (1_000_000 // len(paragraph) + 1))[:1_000_000]
    artifact = SourceArtifact.from_text(text, source_name="million.txt")
    rss_before = _peak_rss_bytes()
    started = perf_counter()

    prepared = ProductionIngestor(parser=None).prepare(artifact)
    plan = build_subdivision_plan(
        prepared,
        ParserCapacity(unit="edu_count", maximum=512, source="production-reference"),
    )

    elapsed = perf_counter() - started
    rss_growth = max(0, _peak_rss_bytes() - rss_before)
    assert prepared.text == text
    assert len(plan.units) >= 4
    assert "".join(
        text[unit.output_range.start : unit.output_range.end]
        for unit in plan.units
    ) == text
    assert elapsed < 5.0
    assert rss_growth < 256 * 1024 * 1024
