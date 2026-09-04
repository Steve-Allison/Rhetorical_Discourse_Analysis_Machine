"""Resolved production preparation and planning policies."""

from collections import defaultdict

from rdam.ingest.contracts.base import SemanticVersion
from rdam.ingest.contracts.preparation import (
    BoundaryPreference,
    PlanningPolicy,
    PreparationPolicy,
)
from rdam.ingest.contracts.source import (
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionDecision,
    DispositionReason,
)
from rdam.ingest.identity import sha256_bytes

DEFAULT_PREPARATION_POLICY = PreparationPolicy(
    policy_version=SemanticVersion(root="2.0.0"),
    primary_classes=(
        ContentClass.TITLE,
        ContentClass.HEADING,
        ContentClass.PARAGRAPH,
        ContentClass.LIST_ITEM,
        ContentClass.TURN,
    ),
    retained_classes=(
        ContentClass.CAPTION,
        ContentClass.TABLE,
        ContentClass.TABLE_CELL,
        ContentClass.CODE,
        ContentClass.FORMULA,
        ContentClass.RAW_MARKUP,
        ContentClass.PICTURE,
        ContentClass.PICTURE_DESCRIPTION,
        ContentClass.NOTE,
        ContentClass.NAVIGATION,
        ContentClass.METADATA,
        ContentClass.FURNITURE,
        ContentClass.BACKGROUND,
        ContentClass.INVISIBLE,
        ContentClass.GROUP,
        ContentClass.FIELD,
        ContentClass.ASSET,
        ContentClass.OTHER,
    ),
    duplicate_precedence=("same_source_anchor", "first_source_order"),
    normalization="preserve",
)

DEFAULT_PLANNING_POLICY = PlanningPolicy(
    algorithm="structure_first",
    algorithm_version=SemanticVersion(root="2.0.0"),
    capacity_margin=0,
    boundary_preference=(
        BoundaryPreference.STRUCTURAL_CONTAINER,
        BoundaryPreference.HEADING,
        BoundaryPreference.PARAGRAPH,
        BoundaryPreference.SENTENCE,
        BoundaryPreference.EDU,
    ),
)


def apply_policy(
    inventory: tuple[ContentInventoryItem, ...],
    policy: PreparationPolicy,
) -> tuple[ContentInventoryItem, ...]:
    """Return one fully dispositioned inventory without discarding valid content."""

    primary = set(policy.primary_classes)
    retained = set(policy.retained_classes)
    updates: dict[str, Disposition] = {}
    primary_by_digest: dict[str, list[str]] = defaultdict(list)

    for item in inventory:
        text = item.text
        if item.classification in primary and text is not None and text.strip():
            reason = (
                DispositionReason.MACHINE_GENERATED_PRIMARY
                if item.origin.authorship is AuthorshipRole.MACHINE_GENERATED
                else DispositionReason.AUTHORED_PRIMARY
            )
            updates[item.item_id] = Disposition(
                decision=DispositionDecision.PRIMARY,
                reason=reason,
                primary_segment_ids=(f"segment:{item.item_id}",),
            )
            primary_by_digest[sha256_bytes(text.encode("utf-8"))].append(item.item_id)
        elif item.classification in retained or text is None or not text.strip():
            updates[item.item_id] = Disposition(
                decision=DispositionDecision.RETAINED,
                reason=DispositionReason.VALID_NON_PRIMARY,
            )
        else:
            updates[item.item_id] = Disposition(
                decision=DispositionDecision.RETAINED,
                reason=DispositionReason.UNSUPPORTED_FOR_ANALYSIS,
            )

    by_id = {item.item_id: item for item in inventory}
    if "same_source_anchor" in policy.duplicate_precedence:
        for item_ids in primary_by_digest.values():
            by_anchor: dict[tuple[object, ...], list[str]] = defaultdict(list)
            for item_id in item_ids:
                by_anchor[by_id[item_id].anchors].append(item_id)
            for anchored_ids in by_anchor.values():
                canonical, *duplicates = anchored_ids
                for duplicate in duplicates:
                    updates[duplicate] = Disposition(
                        decision=DispositionDecision.DUPLICATE,
                        reason=DispositionReason.EXACT_CONVERSION_DUPLICATE,
                        duplicate_of=canonical,
                    )

    return tuple(item.model_copy(update={"disposition": updates[item.item_id]}) for item in inventory)


def admit_content(
    inventory: tuple[ContentInventoryItem, ...], admitted_classes: tuple[ContentClass, ...],
) -> tuple[ContentInventoryItem, ...]:
    """Select a requirement's view without re-inventorying or recomputing duplicate evidence."""
    admitted_ids = {item.item_id for item in inventory
                    if item.classification in admitted_classes and item.text is not None and item.text.strip()}
    selected: list[ContentInventoryItem] = []
    for item in inventory:
        if item.item_id not in admitted_ids:
            disposition = Disposition(decision=DispositionDecision.RETAINED, reason=DispositionReason.VALID_NON_PRIMARY)
        elif item.disposition.decision is DispositionDecision.DUPLICATE and item.disposition.duplicate_of in admitted_ids:
            disposition = item.disposition
        else:
            disposition = Disposition(
                decision=DispositionDecision.PRIMARY,
                reason=DispositionReason.MACHINE_GENERATED_PRIMARY if item.origin.authorship is AuthorshipRole.MACHINE_GENERATED else DispositionReason.AUTHORED_PRIMARY,
                primary_segment_ids=(f"segment:{item.item_id}",),
            )
        selected.append(item.model_copy(update={"disposition": disposition}))
    return tuple(selected)


__all__ = ["DEFAULT_PLANNING_POLICY", "DEFAULT_PREPARATION_POLICY", "apply_policy", "admit_content"]
