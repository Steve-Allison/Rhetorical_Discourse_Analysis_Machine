from pathlib import Path

from rdam.ingest import (
    CoordinateBoxAnchor,
    PageAnchor,
    SourceArtifact,
    SourceForm,
    SourcePathAnchor,
    TableCoordinateAnchor,
    TextSpanAnchor,
)
from rdam.ingest.prepare import inventory_source


def test_doclang_inventory_retains_page_coordinate_box_table_and_dclq_xpath() -> None:
    doclang, _ = inventory_source(
        SourceArtifact.from_path(
            Path("tests/fixtures/doclang/ok_namespaced_and_versioned.dclg"),
            source_form=SourceForm.DOCLANG_XML,
        )
    )
    assert all(
        isinstance(item.anchors[0], SourcePathAnchor) and item.anchors[0].path_kind == "xml_path" for item in doclang
    )
    assert all(dict(item.provider_attributes).get("dclq_xpath", "").startswith("/d:doclang") for item in doclang)
    page_inventory, _ = inventory_source(
        SourceArtifact.from_path(
            Path("tests/fixtures/doclang/ok_page_break_top_level.dclg"),
            source_form=SourceForm.DOCLANG_XML,
        )
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
        type(anchor)
        for item in (*doclang, *page_inventory, *location_inventory, *table_inventory)
        for anchor in item.anchors
    }
    assert {SourcePathAnchor, PageAnchor, CoordinateBoxAnchor, TableCoordinateAnchor} <= doclang_anchor_types

    plain_text, _ = inventory_source(SourceArtifact.from_text("Plain sentence.", source_name="plain.txt"))
    assert len(plain_text) == 1
    assert any(isinstance(anchor, TextSpanAnchor) for anchor in plain_text[0].anchors)
    assert dict(plain_text[0].provider_attributes).get("dclq_xpath") == "/d:doclang/d:text[1]"
