from pathlib import Path

from isanlp_rst.ingest import (
    CoordinateBoxAnchor,
    PageAnchor,
    PageBoxAnchor,
    SourceArtifact,
    SourceForm,
    SourcePathAnchor,
    TableCoordinateAnchor,
    TextSpanAnchor,
)
from isanlp_rst.ingest.prepare import inventory_source


def test_docling_inventory_retains_page_bbox_and_table_coordinates() -> None:
    artifact = SourceArtifact.from_path(
        Path("tests/fixtures/docling/pdf.docling.json"),
        source_form=SourceForm.DOCLING_JSON,
    )
    inventory, _ = inventory_source(artifact)
    anchor_types = {type(anchor) for item in inventory for anchor in item.anchors}
    assert {SourcePathAnchor, PageAnchor, PageBoxAnchor, TableCoordinateAnchor} <= anchor_types


def test_doclang_and_markdown_use_stable_native_addresses() -> None:
    doclang, _ = inventory_source(
        SourceArtifact.from_path(
            Path("tests/fixtures/doclang/ok_namespaced_and_versioned.dclg"),
            source_form=SourceForm.DOCLANG_XML,
        )
    )
    markdown, _ = inventory_source(SourceArtifact.from_path(Path("tests/fixtures/markdown/gfm-rich.md")))
    assert all(
        isinstance(item.anchors[0], SourcePathAnchor) and item.anchors[0].path_kind == "xml_path" for item in doclang
    )
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
    doclang_anchor_types = {
        type(anchor) for item in (*doclang, *location_inventory, *table_inventory) for anchor in item.anchors
    }
    assert {CoordinateBoxAnchor, TableCoordinateAnchor} <= doclang_anchor_types
    assert all(isinstance(anchor, SourcePathAnchor | TextSpanAnchor) for item in markdown for anchor in item.anchors)
