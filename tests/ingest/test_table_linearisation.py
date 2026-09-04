"""Table projections retain geometry and a derivation for every emitted cell."""

from pathlib import Path

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm
from rdam.ingest.contracts.preparation import (
    ContentInventory,
    ContentRequirement,
    RepresentationProjection,
    TableLinearisationParameters,
    SegmentKind,
)
from rdam.ingest.contracts.source import ContentClass, TableRepresentation, TableCoordinateAnchor
from rdam.ingest.projection import project
from tests.ingest.test_projection_contracts import prose_requirement


def table_requirement() -> ContentRequirement:
    base = prose_requirement()
    return ContentRequirement.model_validate(
        {
            **base.model_dump(exclude={"semantic_digest"}),
            "requirement_id": "test/tables-v1",
            "admitted_classes": (*base.admitted_classes, ContentClass.TABLE, ContentClass.TABLE_CELL),
            "representation_projections": (
                RepresentationProjection(representation_kind="table", parameters=TableLinearisationParameters()),
            ),
        }
    )


@pytest.mark.parametrize("name", (
    "tabular-evidence.md", "merged-table.docling.json",
    "../doclang/ok_table_class_data.dclg", "../doclang/ok_table_raw_before.dclg",
    "../doclang/ok_table_raw_none.dclg", "../doclang/ok_table_rectangular.dclg",
    "../doclang/ok_table_wrapped_before.dclg", "../doclang/ok_table_wrapped_none.dclg",
))
def test_every_table_cell_is_anchored_and_derived(name: str) -> None:
    preparation = ProductionIngestor().prepare(SourceArtifact.from_path(Path("tests/fixtures/pipeline") / name))
    inventory = ContentInventory.from_preparation(preparation)
    result = project(inventory, table_requirement())
    tables = [item for item in inventory.items if isinstance(item.representation, TableRepresentation)]
    assert tables
    for table in tables:
        assert isinstance(table.representation, TableRepresentation)
        records = [
            record
            for record in result.transformations
            if record.transformation_kind == "table_linearisation" and table.item_id in record.input_item_ids
        ]
        assert len(records) == 1
        for cell in table.representation.cells:
            original = next(item for item in inventory.items if item.item_id == cell.cell_id)
            assert any(isinstance(anchor, TableCoordinateAnchor) for anchor in original.anchors)
            segment = next(
                segment
                for segment in result.prepared_document.segments
                if cell.cell_id in segment.contributing_item_ids
            )
            assert segment.kind is SegmentKind.DERIVED
            assert cell.text is None or cell.text in segment.text
            assert records[0].transformation_id in segment.transformation_ids
            assert any(
                isinstance(anchor, TableCoordinateAnchor) and (anchor.row, anchor.column) == (cell.row, cell.column)
                for anchor in segment.source_anchors
            )
    assert "".join(segment.text for segment in result.prepared_document.segments) == result.prepared_document.text
    rst = project(inventory, prose_requirement())
    assert not any(
        isinstance(anchor, TableCoordinateAnchor)
        for segment in rst.prepared_document.segments
        for anchor in segment.source_anchors
    )


def test_doclang_wrappers_and_row_markers_are_not_invented_cells() -> None:
    source = SourceArtifact.from_path(Path("tests/fixtures/doclang/ok_table_rectangular.dclg"))
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    tables = [item.representation for item in inventory.items if isinstance(item.representation, TableRepresentation)]
    assert [len(table.cells) for table in tables] == [6, 9, 9]
    projection = project(inventory, table_requirement())
    content = [segment for segment in projection.prepared_document.segments if segment.kind is not SegmentKind.SEPARATOR]
    assert len(content) == 24
    assert all(segment.kind is SegmentKind.DERIVED for segment in content)
    for table in tables:
        for cell in table.cells:
            segment = next(segment for segment in content if segment.contributing_item_ids[0] == cell.cell_id)
            assert set(cell.linked_item_ids).issubset(segment.contributing_item_ids)


def test_repeated_headers_are_source_contributors() -> None:
    source = SourceArtifact.from_path(Path("tests/fixtures/pipeline/tabular-evidence.md"))
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    result = project(inventory, table_requirement())
    for table in inventory.items:
        if not isinstance(table.representation, TableRepresentation):
            continue
        for cell in table.representation.cells:
            headers = tuple(
                header
                for header in table.representation.cells
                if header.header
                and header.row < cell.row
                and header.column <= cell.column < header.column + header.column_span
                and header.text
            )
            if not headers:
                continue
            segment = next(
                segment
                for segment in result.prepared_document.segments
                if segment.contributing_item_ids and segment.contributing_item_ids[0] == cell.cell_id
            )
            for header in headers:
                assert header.cell_id in segment.contributing_item_ids
                original = next(item for item in inventory.items if item.item_id == header.cell_id)
                assert all(anchor in segment.source_anchors for anchor in original.anchors)


@pytest.mark.parametrize("wrapped", (False, True))
def test_doclang_section_row_headers_are_real_cells(wrapped: bool) -> None:
    def text(value: str) -> str:
        return f"<text>{value}</text>" if wrapped else value

    xml = (
        f"<doclang><table><fcel/>{text('Before')}<fcel/>{text('10')}<nl/>"
        f"<srow/>{text('Region')}<srow/>{text('Amount')}<nl/>"
        f"<fcel/>{text('North')}<fcel/>{text('42')}<nl/></table></doclang>"
    )
    source = SourceArtifact.from_bytes(xml.encode(), source_form=SourceForm.DOCLANG_XML, source_name="section-rows.dclg")
    inventory = ContentInventory.from_preparation(ProductionIngestor().prepare(source))
    table = next(item.representation for item in inventory.items if isinstance(item.representation, TableRepresentation))
    assert [(cell.row, cell.column, cell.text) for cell in table.cells] == [
        (0, 0, "Before"), (0, 1, "10"), (1, 0, "Region"), (1, 1, "Amount"), (2, 0, "North"), (2, 1, "42"),
    ]
    assert [cell.header for cell in table.cells] == [False, False, True, True, False, False]
    projection = project(inventory, table_requirement())
    for cell in table.cells[2:4]:
        segment = next(s for s in projection.prepared_document.segments if s.contributing_item_ids and s.contributing_item_ids[0] == cell.cell_id)
        assert any(isinstance(a, TableCoordinateAnchor) and a.row == 1 and a.column == cell.column for a in segment.source_anchors)
        assert cell.text is not None and cell.text in segment.text
