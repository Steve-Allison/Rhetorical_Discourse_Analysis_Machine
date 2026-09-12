"""Enumerate represented text without concatenation or inferred content."""

from collections.abc import Iterator

from rdam.concepts.contracts import ExcludedSurface, Surface
from rdam.ingest.contracts.preparation import ContentInventory
from rdam.ingest.contracts.source import (
    AnnotationRepresentation, ContentInventoryItem, ListRepresentation,
    MediaReferenceRepresentation, MetadataRepresentation, RedactedContentRepresentation,
    StructureRepresentation, TableRepresentation, TextRepresentation,
)
from rdam.ingest.inventory_validation import validate_inventory


def _fields(item: ContentInventoryItem) -> Iterator[tuple[str, str | None, str | None]]:
    representation = item.representation
    match representation:
        case TextRepresentation() | AnnotationRepresentation():
            yield "/representation/text", representation.text, None
        case TableRepresentation():
            for index, cell in enumerate(representation.cells):
                yield f"/representation/cells/{index}/text", cell.text, cell.cell_id
        case ListRepresentation():
            for index, child in enumerate(representation.items):
                yield f"/representation/items/{index}/text", child.text, child.item_id
        case MetadataRepresentation():
            for index, entry in enumerate(representation.entries):
                yield f"/representation/entries/{index}/value", entry.value, None
        case MediaReferenceRepresentation():
            yield "/representation/caption", representation.caption, None
            yield "/representation/description", representation.description, None
        case StructureRepresentation():
            yield "/representation/label", representation.label, None
        case _:
            yield "/representation", None, None


def inventory_surfaces(inventory: ContentInventory) -> tuple[tuple[Surface, ...], tuple[ExcludedSurface, ...]]:
    """Retain source order, authorship and explicit duplicate evidence."""
    inventory = ContentInventory.model_validate(inventory.model_dump())
    validate_inventory(inventory.items)
    items = {item.item_id: item for item in inventory.items}
    surfaces: list[Surface] = []
    excluded: list[ExcludedSurface] = []
    for item in inventory.items:
        if any(anchor.artifact_identity != inventory.source.source_id for anchor in item.anchors):
            raise ValueError("inventory surface has a foreign source anchor")
        fields = tuple(_fields(item)) or (("/representation", "", None),)
        for pointer, text, linked_id in fields:
            duplicate = item.disposition.duplicate_of
            if linked_id is not None and linked_id != item.item_id and linked_id in items:
                linked = items[linked_id]
                # An explicit cell/list identity is reusable only when it actually
                # represents the same text. Text equality alone never merges items.
                if linked.text == text and text is not None:
                    duplicate = linked_id
            if duplicate is not None:
                if duplicate not in items:
                    raise ValueError("duplicate surface references absent inventory item")
                excluded.append(ExcludedSurface(item_id=item.item_id, field_pointer=pointer, reason="duplicate", duplicate_of=duplicate))
            elif isinstance(item.representation, RedactedContentRepresentation):
                excluded.append(ExcludedSurface(item_id=item.item_id, field_pointer=pointer, reason="redacted"))
            elif text is None or not text:
                excluded.append(ExcludedSurface(item_id=item.item_id, field_pointer=pointer, reason="non_text" if text is None else "empty"))
            else:
                surfaces.append(Surface(
                    item_id=item.item_id, field_pointer=pointer, text=text,
                    classification=item.classification, origin=item.origin, anchors=item.anchors,
                ))
    return tuple(surfaces), tuple(excluded)
