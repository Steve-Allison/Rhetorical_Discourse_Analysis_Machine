from isanlp_rst.ingest import SourceArtifact, SourceForm
from isanlp_rst.ingest.contracts import PreparedRange
from isanlp_rst.ingest.service import ProductionIngestor
from isanlp_rst.ingest.subdivision import build_subdivision_plan
from isanlp_rst.model_loading import ParserCapacity


def test_subdivision_is_complete_ordered_and_deterministic() -> None:
    text = "A" * 700 + "\n\n" + "B" * 700
    prepared = ProductionIngestor(parser=None).prepare(SourceArtifact.from_text(text, source_name="long.txt"))
    capacity = ParserCapacity(unit="edu_count", maximum=2, source="test")
    first = build_subdivision_plan(prepared, capacity)
    second = build_subdivision_plan(prepared, capacity)
    assert first.semantic_digest == second.semantic_digest
    assert first.units[0].output_range.start == 0
    assert first.units[-1].output_range.end == len(text)
    assert all(
        left.output_range.end == right.output_range.start
        for left, right in zip(first.units, first.units[1:], strict=False)
    )


def test_presegmented_edus_never_cross_capacity_or_split_an_edu() -> None:
    artifact = SourceArtifact.from_edus(tuple(f"EDU {index}" for index in range(7)), source_name="seven.edus")
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    plan = build_subdivision_plan(prepared, ParserCapacity(unit="edu_count", maximum=3, source="test"))
    assert len(plan.units) == 3
    edu_ranges = tuple(PreparedRange(start=edu.start, end=edu.end) for edu in prepared.document.edus or ())
    assert all(any(unit.output_range.start <= span.start and span.end <= unit.output_range.end for unit in plan.units) for span in edu_ranges)


def test_heading_structure_is_operative_before_capacity_fallback() -> None:
    artifact = SourceArtifact.from_bytes(
        b"# First\n\nFirst section.\n\n# Second\n\nSecond section.",
        source_form=SourceForm.MARKDOWN,
        source_name="sections.md",
        media_type="text/markdown; charset=utf-8",
    )
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    plan = build_subdivision_plan(prepared, ParserCapacity(unit="edu_count", maximum=512, source="test"))
    assert len(plan.units) == 2
    assert prepared.text[plan.units[1].output_range.start :].startswith("\n\nSecond")
