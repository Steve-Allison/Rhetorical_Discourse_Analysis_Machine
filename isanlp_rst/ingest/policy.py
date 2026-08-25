"""Named production relevance policies and exact duplicate evidence."""

from collections import defaultdict

from isanlp_rst.ingest.contracts import (
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionKind,
    DuplicateFinding,
    PreparationPolicy,
)
from isanlp_rst.ingest.identity import sha256_bytes

AUTHORED_PROSE_V1 = PreparationPolicy(
    name="authored_prose",
    version="1",
    primary_classes=(
        ContentClass.TITLE,
        ContentClass.HEADING,
        ContentClass.PARAGRAPH,
        ContentClass.LIST_ITEM,
        ContentClass.TURN,
    ),
    side_channel_classes=(
        ContentClass.CAPTION,
        ContentClass.TABLE,
        ContentClass.TABLE_CELL,
        ContentClass.CODE,
        ContentClass.FORMULA,
        ContentClass.RAW_MARKUP,
        ContentClass.PICTURE,
        ContentClass.METADATA,
        ContentClass.GROUP,
        ContentClass.FIELD,
        ContentClass.ASSET,
        ContentClass.OTHER,
    ),
    excluded_classes=(
        ContentClass.PICTURE_DESCRIPTION,
        ContentClass.NOTE,
        ContentClass.NAVIGATION,
        ContentClass.FURNITURE,
        ContentClass.BACKGROUND,
        ContentClass.INVISIBLE,
    ),
)


def apply_policy(
    inventory: tuple[ContentInventoryItem, ...],
    policy: PreparationPolicy,
) -> tuple[tuple[Disposition, ...], tuple[DuplicateFinding, ...]]:
    """Apply one immutable policy to a complete inventory exactly once."""

    primary = set(policy.primary_classes)
    side_channel = set(policy.side_channel_classes)
    excluded = set(policy.excluded_classes)
    dispositions: list[Disposition] = []
    primary_texts: dict[str, list[str]] = defaultdict(list)

    for item in inventory:
        if item.content_class in primary and item.text is not None and item.text.strip():
            kind = DispositionKind.PRIMARY
            reason = (
                f"explicit_machine_generated_{item.content_class.value}"
                if item.authorship_role is AuthorshipRole.MACHINE_GENERATED
                else f"authored_{item.content_class.value}"
            )
            primary_texts[sha256_bytes(item.text.encode("utf-8"))].append(item.item_id)
        elif item.authorship_role is AuthorshipRole.MACHINE_GENERATED:
            kind = DispositionKind.EXCLUDED
            reason = "machine_generated_content"
        elif item.content_class in excluded:
            kind = DispositionKind.EXCLUDED
            reason = f"excluded_{item.content_class.value}"
        elif item.content_class in side_channel or item.text is None or not item.text.strip():
            kind = DispositionKind.SIDE_CHANNEL
            reason = f"retained_{item.content_class.value}"
        else:
            kind = DispositionKind.SIDE_CHANNEL
            reason = "retained_unknown_valid_content"
        dispositions.append(
            Disposition(
                item_id=item.item_id,
                kind=kind,
                reason_code=reason,
                policy_rule_id=f"{policy.name}_v{policy.version}:{item.content_class.value}",
                side_channel_id=item.item_id if kind is DispositionKind.SIDE_CHANNEL else None,
            )
        )

    disposition_by_id = {disposition.item_id: disposition for disposition in dispositions}
    inventory_by_id = {item.item_id: item for item in inventory}
    duplicates: list[DuplicateFinding] = []
    for digest, item_ids in sorted(primary_texts.items()):
        if len(item_ids) < 2:
            continue
        if not policy.deduplicate_conversion_artifacts:
            duplicates.append(
                DuplicateFinding(
                    normalized_sha256=digest,
                    item_ids=tuple(item_ids),
                    action="reported_retained",
                )
            )
            continue

        provenance_groups: dict[tuple[tuple[str, str, str, int | None, int | None], ...], list[str]] = defaultdict(list)
        for item_id in item_ids:
            signature = _provenance_signature(inventory_by_id[item_id])
            if signature:
                provenance_groups[signature].append(item_id)

        deduplicated_ids: set[str] = set()
        for provenance_item_ids in provenance_groups.values():
            if len(provenance_item_ids) < 2:
                continue
            canonical_id, *duplicates_at_same_origin = provenance_item_ids
            deduplicated_ids.update(duplicates_at_same_origin)
            for duplicate_id in duplicates_at_same_origin:
                disposition_by_id[duplicate_id] = Disposition(
                    item_id=duplicate_id,
                    kind=DispositionKind.DEDUPLICATED,
                    reason_code="exact_conversion_duplicate_same_source_origin",
                    policy_rule_id=f"{policy.name}_v{policy.version}:deduplicate_conversion_artifacts",
                    replaced_by_item_id=canonical_id,
                )
            duplicates.append(
                DuplicateFinding(
                    normalized_sha256=digest,
                    item_ids=tuple(provenance_item_ids),
                    action="provenance_duplicate_deduplicated",
                )
            )

        retained_ids = tuple(item_id for item_id in item_ids if item_id not in deduplicated_ids)
        if len(retained_ids) > 1:
            duplicates.append(
                DuplicateFinding(
                    normalized_sha256=digest,
                    item_ids=retained_ids,
                    action="distinct_source_origins_retained",
                )
            )

    return tuple(disposition_by_id[item.item_id] for item in inventory), tuple(duplicates)


def _provenance_signature(
    item: ContentInventoryItem,
) -> tuple[tuple[str, str, str, int | None, int | None], ...]:
    return tuple(
        (
            anchor.artifact_id,
            anchor.kind.value,
            anchor.selector,
            anchor.range.start if anchor.range is not None else None,
            anchor.range.end if anchor.range is not None else None,
        )
        for anchor in item.native_anchors
    )


__all__ = ["AUTHORED_PROSE_V1", "apply_policy"]
