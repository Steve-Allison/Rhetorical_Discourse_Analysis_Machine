from isanlp_rst.ingest import SourceArtifact
from isanlp_rst.ingest.service import ProductionIngestor
from isanlp_rst.ingest.subdivision import build_subdivision_plan
from isanlp_rst.model_loading import ParserCapacity


def test_one_million_character_source_is_lossless_and_completely_subdivided() -> None:
    paragraph = "A structurally meaningful paragraph ends here.\n\n"
    text = (paragraph * ((1_000_000 // len(paragraph)) + 1))[:1_000_000]
    prepared = ProductionIngestor(parser=None).prepare(SourceArtifact.from_text(text, source_name="million.txt"))
    plan = build_subdivision_plan(
        prepared,
        ParserCapacity(unit="edu_count", maximum=512, source="production-safe-capacity"),
    )
    assert prepared.text == text
    assert len(plan.units) >= 4
    assert "".join(
        prepared.text[unit.output_range.start : unit.output_range.end] for unit in plan.units
    ) == text
