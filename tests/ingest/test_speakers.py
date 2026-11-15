"""Explicit source identities, alternate spellings, and exhaustive unresolved accounting."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rdam import AggregateRequest, Machine, Technique
from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.preparation import ContentInventory, SpeakerCoverage
from rdam.ingest.contracts.source import SpeakerIdentity, ContentClass
from rdam.ingest.projection import project
from rdam.ingest.speakers import resolve_speaker
from rdam.sdrt.provider import SdrtProvider


def test_resolution_and_accounting_are_strict() -> None:
    with pytest.raises(ValidationError):
        SpeakerIdentity(resolution="resolved", evidence="missing id")
    with pytest.raises(ValidationError):
        SpeakerIdentity(resolution="unresolved", participant_id="invented", evidence="contradiction")
    with pytest.raises(ValidationError):
        SpeakerCoverage(turn_count=3, resolved_count=1, unresolved_count=1, distinct_participants=1)


def test_transcript_has_zero_invented_speakers(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.dclg"
    transcript.write_bytes(
        b'<doclang xmlns="https://www.doclang.ai/ns/v0" version="0.9">'
        b'<heading level="1">Decision meeting transcript</heading>'
        b"<text>Alex Morgan (participant alex): The replacement would reduce the operating cost.</text>"
        b"<text>Blair Chen (participant blair): Does that include maintenance?</text>"
        b"<text>Casey Patel (participant casey): The table includes maintenance for both systems.</text>"
        b"<text>A. Morgan (participant alex): Then the comparison supports proceeding.</text>"
        b"<text>UNATTRIBUTED: The recording does not identify this speaker.</text>"
        b"<text>Blair Chen (participant blair): We should preserve the assumptions with the decision.</text>"
        b"<text>UNATTRIBUTED: This overlapping turn has no recoverable speaker attribution.</text>"
        b"</doclang>"
    )
    source = SourceArtifact.from_path(transcript)
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    turns = tuple(item for item in inventory.items if item.classification is ContentClass.TURN)
    assert len(turns) == 7
    assert [item.speaker.participant_id for item in turns if item.speaker is not None] == ["alex", "blair", "casey", "alex", None, "blair", None]
    coverage = SpeakerCoverage.from_items(inventory.items)
    assert coverage == SpeakerCoverage(turn_count=7, resolved_count=5, unresolved_count=2, distinct_participants=3)
    projection = project(inventory, SdrtProvider().content_requirement)
    assert len(projection.unmet_requirements) == 1
    assert projection.unmet_requirements[0].affected_item_ids == (turns[4].item_id, turns[6].item_id)
    result = Machine().analyse(AggregateRequest.for_source(transcript, (Technique.SDRT,)))
    assert result.preparation is not None
    assert result.preparation.receipt().speaker_coverage == coverage


def test_equal_display_names_do_not_merge_explicit_participants() -> None:
    first = resolve_speaker("**Alex (participant first):** Hello.")
    second = resolve_speaker("**Alex (participant second):** Hello.")
    assert first.display_name == second.display_name == "Alex"
    assert first.participant_id != second.participant_id
