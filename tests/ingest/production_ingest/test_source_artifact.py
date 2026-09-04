from pathlib import Path

import pytest

from rdam.ingest.contracts import SourceArtifact, SourceForm


def test_text_and_edus_preserve_exact_payload() -> None:
    text = SourceArtifact.from_text("e\u0301\r\nNext", source_name="exact.txt")
    assert text.raw_bytes == "e\u0301\r\nNext".encode()
    edus = SourceArtifact.from_edus((" First ", "Second"), source_name="exact.edus")
    assert edus.edus == (" First ", "Second")


def test_empty_edu_fails() -> None:
    with pytest.raises(ValueError, match="EDU at index 1"):
        SourceArtifact.from_edus(("First", ""), source_name="bad.edus")


def test_path_detection_is_bounded(tmp_path: Path) -> None:
    markdown = tmp_path / "source.md"
    markdown.write_text("# Heading\n\nText", encoding="utf-8")
    assert SourceArtifact.from_path(markdown).source_form is SourceForm.MARKDOWN

    ambiguous = tmp_path / "source.txt"
    ambiguous.write_text("Text", encoding="utf-8")
    with pytest.raises(ValueError, match="source_form"):
        SourceArtifact.from_path(ambiguous)


def test_bytes_require_explicit_form_and_strict_utf8() -> None:
    with pytest.raises(UnicodeDecodeError):
        SourceArtifact.from_bytes(
            b"\xff",
            source_form=SourceForm.TEXT,
            source_name="bad.txt",
            media_type="text/plain",
        )
