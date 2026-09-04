"""Adversarial CommonMark/GFM inventory and native-anchor conformance."""

from rdam.ingest import ContentInventoryItem, SourceArtifact, SourceForm, TextSpanAnchor
from rdam.ingest.contracts import ContentClass
from rdam.ingest.prepare import inventory_source


MARKDOWN = """---
title: Anchor audit
---
# Héading

Repeated *alpha* and [alpha](https://example.com/a?q=1).

> Quote &amp; **bold**

- item one
  - nested item

| Key | Value |
| --- | --- |
| α | β |

![Alt text](images/chart%201.png)

```py
print("anchor")
```
"""


def _inventory() -> tuple[ContentInventoryItem, ...]:
    artifact = SourceArtifact.from_bytes(
        MARKDOWN.encode("utf-8"),
        source_form=SourceForm.MARKDOWN,
        source_name="adversarial.md",
        media_type="text/markdown; charset=utf-8",
    )
    inventory, _contract = inventory_source(artifact)
    return inventory


def test_every_markdown_character_anchor_round_trips_to_the_exact_source_slice() -> None:
    anchors = tuple(
        anchor
        for item in _inventory()
        for anchor in item.anchors
        if isinstance(anchor, TextSpanAnchor)
    )
    assert len(anchors) == 7
    assert all(anchor.quote is not None for anchor in anchors)
    assert all(MARKDOWN[anchor.start : anchor.end] == anchor.quote for anchor in anchors)
    assert {anchor.quote for anchor in anchors} >= {
        "Héading",
        "Repeated *alpha* and [alpha](https://example.com/a?q=1).",
        "Quote &amp; **bold**",
        "nested item",
        "![Alt text](images/chart%201.png)",
        'print("anchor")',
    }


def test_markdown_relationship_targets_and_nested_structure_are_lossless() -> None:
    inventory = _inventory()
    relationships = {
        (relationship.relation, relationship.target_identity, relationship.target_kind)
        for item in inventory
        for relationship in item.relationships
    }
    assert relationships == {
        ("image", "images/chart%201.png", "external"),
        ("link", "https://example.com/a?q=1", "external"),
    }
    classes = {item.classification for item in inventory}
    assert {
        ContentClass.CODE,
        ContentClass.GROUP,
        ContentClass.HEADING,
        ContentClass.LIST_ITEM,
        ContentClass.METADATA,
        ContentClass.PICTURE,
        ContentClass.TABLE,
        ContentClass.TABLE_CELL,
    } <= classes
    by_id = {item.item_id: item for item in inventory}
    nested_paragraph = next(item for item in inventory if item.text == "nested item")
    assert nested_paragraph.parent_id is not None
    nested_list_item = by_id[nested_paragraph.parent_id]
    assert nested_list_item.parent_id is not None
    nested_list = by_id[nested_list_item.parent_id]
    assert nested_list.parent_id is not None
    outer_list_item = by_id[nested_list.parent_id]
    assert nested_list_item.classification is ContentClass.LIST_ITEM
    assert nested_list.classification is ContentClass.GROUP
    assert outer_list_item.classification is ContentClass.LIST_ITEM
