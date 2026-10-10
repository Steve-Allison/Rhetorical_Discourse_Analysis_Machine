"""DocLang <track> transcripts decode into timed, speaker-attributed turns in reading order."""

from pathlib import Path

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm
from rdam.ingest.contracts import AuthorshipRole, ContentClass, DispositionDecision
from rdam.ingest.contracts.source import ContentInventoryItem, MediaReferenceRepresentation, TextRepresentation
from rdam.ingest.doclang.decoder import cue_interval
from rdam.ingest.doclang.errors import InvalidDoclangError
from rdam.ingest.doclang.loader import XmlElement, parse_control_xml
from rdam.ingest.identity import sha256_bytes
from rdam.ingest.speakers import resolve_voice

FIXTURES = Path("tests/fixtures/doclang")


def _prepare(name: str) -> tuple[tuple[ContentInventoryItem, ...], str]:
    source = SourceArtifact.from_path(FIXTURES / name, source_form=SourceForm.DOCLANG_XML)
    semantic = ProductionIngestor().prepare(source).semantic
    return semantic.inventory, semantic.prepared_document.text


def _by_class(items: tuple[ContentInventoryItem, ...], classification: ContentClass) -> list[ContentInventoryItem]:
    return [item for item in items if item.classification is classification]


def _attributes(item: ContentInventoryItem) -> dict[str, str]:
    return dict(item.provider_attributes)


def _text(item: ContentInventoryItem) -> str:
    assert isinstance(item.representation, TextRepresentation)
    return item.representation.text


def _reference(item: ContentInventoryItem) -> str | None:
    assert isinstance(item.representation, MediaReferenceRepresentation)
    return item.representation.source_reference


def test_voices_become_attributed_transcribed_turns_without_their_speaker_labels() -> None:
    items, prepared = _prepare("ok_track_voices.dclg")
    turns = _by_class(items, ContentClass.TURN)
    assert [_text(turn) for turn in turns] == [
        "Hi Mary!", "Hello John!", "First unattributed line.\n    Second unattributed line.", "Hee!", "laughter",
    ]
    assert [turn.speaker.display_name if turn.speaker else None for turn in turns] == [
        "John", "Mary", None, "Esme", None,
    ]
    assert [turn.speaker.resolution if turn.speaker else None for turn in turns] == [
        "resolved", "resolved", "unresolved", "resolved", "unresolved",
    ]
    assert all(turn.disposition.decision is DispositionDecision.PRIMARY for turn in turns)
    assert all(turn.origin.authorship is AuthorshipRole.TRANSCRIBED for turn in turns)
    assert [_attributes(turn)["cue_start_ms"] for turn in turns] == ["2000", "2000", "9000", "12000", "12000"]
    # Speaker labels are attribution, not spoken text: "Esme" never reaches the prepared text.
    assert prepared == "\n\n".join(_text(turn) for turn in turns)
    assert "Esme" not in prepared


def test_named_voice_uses_the_shared_label_identity() -> None:
    speaker = resolve_voice("John")
    assert speaker.participant_id == "label:" + sha256_bytes(b"John")
    assert resolve_voice("Unknown").resolution == "unresolved"


@pytest.mark.parametrize(("name", "intervals"), [
    ("ok_track_mixed_unit_runs.dclg", [(55_000, 55_000), (63_000, 68_000)]),
    ("ok_track_overlapping_blocks.dclg", [(2_000, 8_000), (6_000, 9_000)]),
    ("ok_track_frame_audio.dclg", [(64_000, 69_000)]),
])
def test_cue_intervals_are_inclusive_milliseconds(name: str, intervals: list[tuple[int, int]]) -> None:
    items, _ = _prepare(name)
    turns = _by_class(items, ContentClass.TURN)
    assert [(int(_attributes(t)["cue_start_ms"]), int(_attributes(t)["cue_end_ms"])) for t in turns] == intervals


def test_chapters_are_headings_placed_before_their_cue_text() -> None:
    items, prepared = _prepare("ok_track_chapters.dclg")
    assert prepared.split("\n\n") == [
        "Cold open, no chapter yet.", "Introduction", "Welcome, everyone.",
        "Still the introduction; this cue block starts no chapter.", "Part 1 — Background",
        "Let's start with some history.",
    ]
    chapters = _by_class(items, ContentClass.HEADING)
    assert [_attributes(chapter)["cue_start_ms"] for chapter in chapters] == ["20000", "90000"]


def test_inline_formatting_stays_in_the_turn_text() -> None:
    items, _ = _prepare("ok_track_inline_formatting.dclg")
    (turn,) = _by_class(items, ContentClass.TURN)
    assert _text(turn) == "That was completely unexpected."
    assert turn.speaker is not None and turn.speaker.display_name == "Guest"


def test_frames_covers_and_audio_are_retained_media_with_their_cue() -> None:
    items, _ = _prepare("ok_track_frame_audio.dclg")
    (frame,) = _by_class(items, ContentClass.PICTURE)
    (audio,) = _by_class(items, ContentClass.ASSET)
    for media, uri in ((frame, "assets/frames/00-01-04.jpg"), (audio, "assets/clips/00-01-04.opus")):
        assert media.disposition.decision is DispositionDecision.RETAINED
        assert _reference(media) == uri
        assert (_attributes(media)["cue_start_ms"], _attributes(media)["cue_end_ms"]) == ("64000", "69000")
    cover_items, _ = _prepare("ok_track_cover.dclg")
    (cover,) = _by_class(cover_items, ContentClass.PICTURE)
    assert _reference(cover) == "assets/cover.png"
    assert "cue_id" not in _attributes(cover)


def test_track_in_a_table_cell_stays_table_content() -> None:
    items, prepared = _prepare("ok_track_in_group_and_cell.dclg")
    assert prepared == "Inside a group."
    cell_turn = next(item for item in items if item.item_id == "/doclang[1]/table[1]/track[1]/bdiv[1]")
    assert cell_turn.classification is ContentClass.TABLE_CELL
    assert _attributes(cell_turn)["cue_start_ms"] == "3000"


def _timing(markup: str) -> tuple[XmlElement, ...]:
    return tuple(parse_control_xml(f"<t>{markup}</t>".encode(), part_name="cue.xml"))


@pytest.mark.parametrize(("markup", "message"), [
    ('<minutes value="1"/>', "start time"),
    ('<seconds value="1"/><seconds value="2"/><seconds value="3"/>', "start time"),
    ('<seconds value="x"/>', "non-integer"),
    ('<seconds value="5"/><seconds value="4"/>', "ends before"),
])
def test_malformed_cue_timing_fails_closed(markup: str, message: str) -> None:
    with pytest.raises(InvalidDoclangError, match=message):
        cue_interval("/track/bdiv[1]", _timing(markup))
