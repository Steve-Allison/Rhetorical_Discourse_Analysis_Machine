"""Canonical final-disposition and duplicate-precedence tests."""

import pytest

from rdam.rst.ingest.contracts.source import (
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    Disposition,
    DispositionDecision,
    DispositionReason,
    ItemAnchor,
    ItemRelationship,
    SourceOrigin,
    TextRepresentation,
)
from rdam.rst.ingest.policy import DEFAULT_PREPARATION_POLICY, apply_policy
from rdam.rst.ingest.validation import validate_inventory


def test_same_origin_exact_duplicate_resolves_to_first_canonical_item() -> None:
    inventory = (_item("item:1"), _item("item:2"))
    dispositioned = apply_policy(inventory, DEFAULT_PREPARATION_POLICY)
    assert dispositioned[0].disposition.decision is DispositionDecision.PRIMARY
    assert dispositioned[1].disposition.decision is DispositionDecision.DUPLICATE
    assert dispositioned[1].disposition.duplicate_of == "item:1"


def test_duplicate_links_are_acyclic_and_every_item_has_one_final_disposition() -> None:
    dispositioned = apply_policy((_item("item:1"), _item("item:2"), _item("item:3")), DEFAULT_PREPARATION_POLICY)
    by_id = {item.item_id: item for item in dispositioned}
    for item in dispositioned:
        seen: set[str] = set()
        current = item
        while current.disposition.duplicate_of is not None:
            assert current.item_id not in seen
            seen.add(current.item_id)
            current = by_id[current.disposition.duplicate_of]
        assert isinstance(item.disposition, Disposition)


def test_inventory_validator_rejects_duplicate_cycles_and_unknown_relationship_targets() -> None:
    first = _item("item:1").model_copy(
        update={
            "disposition": Disposition(
                decision=DispositionDecision.DUPLICATE,
                reason=DispositionReason.EXACT_CONVERSION_DUPLICATE,
                duplicate_of="item:2",
            )
        }
    )
    second = _item("item:2").model_copy(
        update={
            "disposition": Disposition(
                decision=DispositionDecision.DUPLICATE,
                reason=DispositionReason.EXACT_CONVERSION_DUPLICATE,
                duplicate_of="item:1",
            )
        }
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_inventory((first, second))

    external = _item("item:3").model_copy(
        update={
            "relationships": (
                ItemRelationship(
                    relation="references",
                    target_identity="missing",
                    target_kind="inventory_item",
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="does not exist"):
        validate_inventory((external,))


def _item(item_id: str) -> ContentInventoryItem:
    return ContentInventoryItem(
        item_id=item_id,
        classification=ContentClass.PARAGRAPH,
        origin=SourceOrigin(authorship=AuthorshipRole.AUTHORED),
        representation=TextRepresentation(
            text="Repeated conversion artifact",
            semantic_role="paragraph",
        ),
        anchors=(
            ItemAnchor(
                artifact_identity="a" * 64,
                item_identity="shared-source-origin",
            ),
        ),
        disposition=Disposition(
            decision=DispositionDecision.RETAINED,
            reason=DispositionReason.VALID_NON_PRIMARY,
        ),
    )
