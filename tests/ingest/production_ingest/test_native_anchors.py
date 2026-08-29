from pathlib import Path

from isanlp_rst.ingest import AnchorKind, SourceArtifact, SourceForm
from isanlp_rst.ingest.prepare import inventory_source


def test_docling_inventory_retains_page_bbox_and_table_coordinates() -> None:
    artifact = SourceArtifact.from_path(
        Path("tests/fixtures/docling/pdf.docling.json"),
        source_form=SourceForm.DOCLING_JSON,
    )
    inventory, _ = inventory_source(artifact)
    kinds = {anchor.kind for item in inventory for anchor in item.native_anchors}
    assert {AnchorKind.JSON_POINTER, AnchorKind.PAGE, AnchorKind.BOUNDING_BOX, AnchorKind.TABLE_COORDINATE} <= kinds


def test_doclang_and_markdown_use_stable_native_addresses() -> None:
    doclang, _ = inventory_source(
        SourceArtifact.from_path(
            Path("tests/fixtures/doclang/ok_namespaced_and_versioned.dclg"),
            source_form=SourceForm.DOCLANG_XML,
        )
    )
    markdown, _ = inventory_source(SourceArtifact.from_path(Path("tests/fixtures/markdown/gfm-rich.md")))
    assert all(item.native_anchors[0].kind is AnchorKind.XML_PATH for item in doclang)
    location_inventory, _ = inventory_source(
        SourceArtifact.from_path(
            Path("tests/fixtures/doclang/ok_location_axis_limits.dclg"),
            source_form=SourceForm.DOCLANG_XML,
        )
    )
    table_inventory, _ = inventory_source(
        SourceArtifact.from_path(
            Path("tests/fixtures/doclang/ok_table_rectangular.dclg"),
            source_form=SourceForm.DOCLANG_XML,
        )
    )
    doclang_kinds = {
        anchor.kind
        for item in (*doclang, *location_inventory, *table_inventory)
        for anchor in item.native_anchors
    }
    assert {AnchorKind.BOUNDING_BOX, AnchorKind.TABLE_COORDINATE} <= doclang_kinds
    assert all(
        anchor.kind in {AnchorKind.LINE, AnchorKind.CHARACTER, AnchorKind.XML_PATH}
        for item in markdown
        for anchor in item.native_anchors
    )
