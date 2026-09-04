from rdam.ingest.contracts import (
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionDecision,
    DispositionReason,
    ItemAnchor,
    PreparationPolicy,
    SourceOrigin,
    TextRepresentation,
)
from rdam.ingest.policy import DEFAULT_PREPARATION_POLICY, apply_policy


def _item(
    item_id: str,
    content_class: ContentClass,
    text: str,
    *,
    anchors: tuple[ItemAnchor, ...] | None = None,
) -> ContentInventoryItem:
    return ContentInventoryItem(
        item_id=item_id,
        classification=content_class,
        origin=SourceOrigin(authorship=AuthorshipRole.AUTHORED),
        representation=TextRepresentation(text=text, semantic_role=content_class.value),
        anchors=anchors or (ItemAnchor(artifact_identity="a" * 64, item_identity=item_id),),
        disposition=Disposition(
            decision=DispositionDecision.RETAINED,
            reason=DispositionReason.VALID_NON_PRIMARY,
        ),
    )


def test_default_policy_selects_only_authored_discourse() -> None:
    items = (
        _item("p", ContentClass.PARAGRAPH, "Authored prose."),
        _item("h", ContentClass.HEADING, "Heading"),
        _item("c", ContentClass.CODE, "print('not prose')"),
        _item("n", ContentClass.NOTE, "speaker note"),
        _item("t", ContentClass.TABLE_CELL, "cell"),
    )
    dispositioned = apply_policy(items, DEFAULT_PREPARATION_POLICY)
    by_id = {item.item_id: item.disposition.decision for item in dispositioned}
    assert by_id == {
        "p": DispositionDecision.PRIMARY,
        "h": DispositionDecision.PRIMARY,
        "c": DispositionDecision.RETAINED,
        "n": DispositionDecision.RETAINED,
        "t": DispositionDecision.RETAINED,
    }


def test_default_duplicate_detection_reports_but_retains_authored_repetition() -> None:
    items = (
        _item("p1", ContentClass.PARAGRAPH, "Intentional refrain."),
        _item("p2", ContentClass.PARAGRAPH, "Intentional refrain."),
    )
    dispositioned = apply_policy(items, DEFAULT_PREPARATION_POLICY)
    assert [item.disposition.decision for item in dispositioned] == [
        DispositionDecision.PRIMARY,
        DispositionDecision.PRIMARY,
    ]


def test_named_policy_can_explicitly_admit_a_default_excluded_class() -> None:
    policy = PreparationPolicy.model_validate(
        {
            **DEFAULT_PREPARATION_POLICY.model_dump(exclude={"semantic_digest"}),
            "primary_classes": (*DEFAULT_PREPARATION_POLICY.primary_classes, ContentClass.NOTE),
            "retained_classes": tuple(
                content_class
                for content_class in DEFAULT_PREPARATION_POLICY.retained_classes
                if content_class is not ContentClass.NOTE
            ),
        }
    )

    dispositioned = apply_policy(
        (_item("note", ContentClass.NOTE, "Deliberately analysed note."),),
        policy,
    )

    assert dispositioned[0].disposition.decision is DispositionDecision.PRIMARY
    assert dispositioned[0].disposition.reason is DispositionReason.AUTHORED_PRIMARY


def test_explicit_deduplication_only_removes_exact_same_origin_conversion_artifacts() -> None:
    same_origin = ItemAnchor(artifact_identity="a" * 64, item_identity="same-origin")
    distinct_origin = ItemAnchor(artifact_identity="a" * 64, item_identity="distinct-origin")
    items = (
        _item("canonical", ContentClass.PARAGRAPH, "Repeated conversion.", anchors=(same_origin,)),
        _item("conversion-copy", ContentClass.PARAGRAPH, "Repeated conversion.", anchors=(same_origin,)),
        _item("intentional-refrain", ContentClass.PARAGRAPH, "Repeated conversion.", anchors=(distinct_origin,)),
    )

    dispositioned = apply_policy(items, DEFAULT_PREPARATION_POLICY)
    by_id = {item.item_id: item.disposition for item in dispositioned}

    assert by_id["canonical"].decision is DispositionDecision.PRIMARY
    assert by_id["conversion-copy"].decision is DispositionDecision.DUPLICATE
    assert by_id["conversion-copy"].duplicate_of == "canonical"
    assert by_id["intentional-refrain"].decision is DispositionDecision.PRIMARY
