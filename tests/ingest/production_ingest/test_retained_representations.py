"""Closed retained-content representation construction and round-trip tests."""

from pydantic import TypeAdapter
import pytest

from rdam.rst.ingest.contracts.base import Sha256Identity
from rdam.rst.ingest.contracts.source import (
    AnnotationRepresentation,
    ContentRepresentation,
    CrossReferenceRepresentation,
    ListItemRepresentation,
    ListRepresentation,
    MediaReferenceRepresentation,
    MetadataEntry,
    MetadataRepresentation,
    StructureRepresentation,
    TableCell,
    TableRepresentation,
    TextRepresentation,
)


@pytest.mark.parametrize(
    "representation",
    (
        TextRepresentation(text="Authored text", language="en", semantic_role="paragraph"),
        TableRepresentation(
            cells=(
                TableCell(
                    cell_id="cell:1",
                    row=0,
                    column=0,
                    row_span=2,
                    column_span=1,
                    text="Header",
                    header=True,
                    linked_item_ids=("item:detail",),
                ),
            )
        ),
        ListRepresentation(
            ordered=True,
            marker="1.",
            items=(
                ListItemRepresentation(
                    item_id="list:1",
                    text="Nested item",
                    child_item_ids=("list:1:1",),
                ),
            ),
        ),
        MetadataRepresentation(
            entries=(MetadataEntry(key="author", value="Steve", value_type="string"),)
        ),
        AnnotationRepresentation(label="caption", text="Figure caption"),
        MediaReferenceRepresentation(
            media_identity="media:1",
            source_reference="assets/figure.png",
            caption="Figure caption",
            description="A described figure",
        ),
        StructureRepresentation(
            structure_type="section",
            label="Results",
            child_ids=("paragraph:1",),
        ),
        CrossReferenceRepresentation(
            target_identity="section:results",
            relation="references",
        ),
    ),
)
def test_every_representation_variant_round_trips_without_flattening(
    representation: ContentRepresentation,
) -> None:
    adapter = TypeAdapter(ContentRepresentation)
    encoded = adapter.dump_json(representation)
    assert adapter.validate_json(encoded) == representation


def test_representation_union_is_closed() -> None:
    adapter = TypeAdapter(ContentRepresentation)
    with pytest.raises(ValueError):
        adapter.validate_python(
            {
                "kind": "embedding",
                "identity": Sha256Identity(hex_digest="a" * 64).model_dump(),
            }
        )
