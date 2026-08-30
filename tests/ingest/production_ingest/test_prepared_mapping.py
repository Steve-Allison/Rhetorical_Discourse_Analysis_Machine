import pytest

from isanlp_rst.ingest import SegmentKind, SourceArtifact, TextSpanAnchor
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
    outcome = ProductionIngestor().prepare(SourceArtifact.from_text(text, source_name="unicode.txt"))
    prepared = outcome.semantic.prepared_document
    source_segments = tuple(segment for segment in prepared.segments if segment.kind is SegmentKind.SOURCE)
    assert "".join(segment.text for segment in prepared.segments) == text
    source_anchor = source_segments[0].source_anchors[0]
    assert isinstance(source_anchor, TextSpanAnchor)
    assert source_anchor.end - source_anchor.start == len(text)
    assert source_anchor.quote == text


def test_synthetic_separators_never_claim_source_identity() -> None:
    artifact = SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    prepared = ProductionIngestor().prepare(artifact).semantic.prepared_document
    separators = tuple(segment for segment in prepared.segments if segment.kind is SegmentKind.SEPARATOR)
    assert separators
    assert all(not segment.contributing_item_ids and not segment.source_anchors for segment in separators)
    assert prepared.text == "One. Two. Three."
