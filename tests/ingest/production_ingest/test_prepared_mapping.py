import pytest

from isanlp_rst.ingest import SegmentKind, SourceArtifact
from isanlp_rst.ingest.service import ProductionIngestor


@pytest.mark.parametrize(
    "text",
    (
        "ASCII.\r\n\r\nSecond.",
        "Café in composed form.",
        "Cafe\u0301 in decomposed form.",
        "Emoji 👩🏽‍💻 and العربية and 中文.",
    ),
)
def test_plain_source_mapping_is_character_exact(text: str) -> None:
    prepared = ProductionIngestor(parser=None).prepare(SourceArtifact.from_text(text, source_name="unicode.txt"))
    source_segments = tuple(segment for segment in prepared.segments if segment.kind is SegmentKind.SOURCE)
    assert "".join(segment.text for segment in prepared.segments) == text
    assert source_segments[0].original_text == text
    assert source_segments[0].source_range is not None
    assert source_segments[0].source_range.length == len(text)
    assert source_segments[0].native_anchors[0].quote == text


def test_synthetic_separators_never_claim_source_identity() -> None:
    artifact = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    prepared = ProductionIngestor(parser=None).prepare(artifact)
    separators = tuple(segment for segment in prepared.segments if segment.kind is SegmentKind.SEPARATOR)
    assert separators
    assert all(segment.source_item_id is None and segment.source_range is None for segment in separators)
    assert prepared.text == "One. Two. Three."
