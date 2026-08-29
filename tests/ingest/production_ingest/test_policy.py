from isanlp_rst.ingest.contracts import (
    AnchorKind,
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    DispositionKind,
    NativeAnchor,
    PreparationPolicy,
)
from isanlp_rst.ingest.policy import AUTHORED_PROSE_V1, apply_policy


def _item(
    item_id: str,
    content_class: ContentClass,
    text: str,
    *,
    anchors: tuple[NativeAnchor, ...] = (),
) -> ContentInventoryItem:
    return ContentInventoryItem(
        item_id=item_id,
        parent_id=None,
        content_class=content_class,
        authorship_role=AuthorshipRole.AUTHORED,
        text=text,
        native_anchors=anchors,
    )


def test_default_policy_selects_only_authored_discourse() -> None:
    items = (
        _item("p", ContentClass.PARAGRAPH, "Authored prose."),
        _item("h", ContentClass.HEADING, "Heading"),
        _item("c", ContentClass.CODE, "print('not prose')"),
        _item("n", ContentClass.NOTE, "speaker note"),
        _item("t", ContentClass.TABLE_CELL, "cell"),
    )
    dispositions, _ = apply_policy(items, AUTHORED_PROSE_V1)
    by_id = {item.item_id: item.kind for item in dispositions}
    assert by_id == {
        "p": DispositionKind.PRIMARY,
        "h": DispositionKind.PRIMARY,
        "c": DispositionKind.SIDE_CHANNEL,
        "n": DispositionKind.EXCLUDED,
        "t": DispositionKind.SIDE_CHANNEL,
    }


def test_default_duplicate_detection_reports_but_retains_authored_repetition() -> None:
    items = (
        _item("p1", ContentClass.PARAGRAPH, "Intentional refrain."),
        _item("p2", ContentClass.PARAGRAPH, "Intentional refrain."),
    )
    dispositions, duplicates = apply_policy(items, AUTHORED_PROSE_V1)
    assert [item.kind for item in dispositions] == [DispositionKind.PRIMARY, DispositionKind.PRIMARY]
    assert duplicates[0].item_ids == ("p1", "p2")
    assert duplicates[0].action == "reported_retained"


def test_named_policy_can_explicitly_admit_a_default_excluded_class() -> None:
    policy = PreparationPolicy(
        name="authored_prose_with_notes",
        version="1",
        primary_classes=(*AUTHORED_PROSE_V1.primary_classes, ContentClass.NOTE),
        side_channel_classes=AUTHORED_PROSE_V1.side_channel_classes,
        excluded_classes=tuple(
            content_class
            for content_class in AUTHORED_PROSE_V1.excluded_classes
            if content_class is not ContentClass.NOTE
        ),
    )

    dispositions, _ = apply_policy(
        (_item("note", ContentClass.NOTE, "Deliberately analysed note."),),
        policy,
    )

    assert dispositions[0].kind is DispositionKind.PRIMARY
    assert dispositions[0].policy_rule_id == "authored_prose_with_notes_v1:note"


def test_explicit_deduplication_only_removes_exact_same_origin_conversion_artifacts() -> None:
    same_origin = NativeAnchor(
        artifact_id="source",
        kind=AnchorKind.CHARACTER,
        selector="char=0,20",
    )
    distinct_origin = NativeAnchor(
        artifact_id="source",
        kind=AnchorKind.CHARACTER,
        selector="char=100,120",
    )
    policy = AUTHORED_PROSE_V1.model_copy(
        update={"name": "authored_prose_deduplicated", "deduplicate_conversion_artifacts": True}
    )
    items = (
        _item("canonical", ContentClass.PARAGRAPH, "Repeated conversion.", anchors=(same_origin,)),
        _item("conversion-copy", ContentClass.PARAGRAPH, "Repeated conversion.", anchors=(same_origin,)),
        _item("intentional-refrain", ContentClass.PARAGRAPH, "Repeated conversion.", anchors=(distinct_origin,)),
    )

    dispositions, findings = apply_policy(items, policy)
    by_id = {disposition.item_id: disposition for disposition in dispositions}

    assert by_id["canonical"].kind is DispositionKind.PRIMARY
    assert by_id["conversion-copy"].kind is DispositionKind.DEDUPLICATED
    assert by_id["conversion-copy"].replaced_by_item_id == "canonical"
    assert by_id["intentional-refrain"].kind is DispositionKind.PRIMARY
    assert {finding.action for finding in findings} == {
        "provenance_duplicate_deduplicated",
        "distinct_source_origins_retained",
    }
