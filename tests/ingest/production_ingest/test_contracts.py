from pydantic import ValidationError
import pytest

from isanlp_rst.ingest.contracts import (
    AnalysisStatus,
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionKind,
    PreparedRange,
    SourceArtifact,
    SourceForm,
)


def test_contracts_are_frozen_and_reject_unknown_fields() -> None:
    artifact = SourceArtifact.from_text("One paragraph.", source_name="one.txt")
    with pytest.raises(ValidationError):
        SourceArtifact.model_validate({**artifact.model_dump(), "unknown": True})
    with pytest.raises(ValidationError):
        SourceArtifact.__setattr__(artifact, "source_name", "changed.txt")


def test_range_is_non_empty_and_half_open() -> None:
    assert PreparedRange(start=0, end=1).length == 1
    with pytest.raises(ValidationError):
        PreparedRange(start=1, end=1)


def test_inventory_item_has_one_stable_identity() -> None:
    item = ContentInventoryItem(
        item_id="item:1",
        parent_id=None,
        child_ids=(),
        content_class=ContentClass.PARAGRAPH,
        text="One paragraph.",
    )
    assert item.text_sha256 is not None
    disposition = Disposition(
        item_id=item.item_id,
        kind=DispositionKind.PRIMARY,
        reason_code="authored_paragraph",
        policy_rule_id="authored_prose_v1:paragraph",
    )
    assert disposition.item_id == item.item_id


def test_empty_primary_discourse_is_explicit() -> None:
    assert AnalysisStatus.EMPTY_PRIMARY_DISCOURSE.value == "empty_primary_discourse"
    assert SourceForm.DOCLANG_ARCHIVE.value == "doclang_archive"
