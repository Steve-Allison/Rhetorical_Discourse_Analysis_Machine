"""Approved repairs are proven against real historical records, never allowlisted."""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm, serialize_contract
from tools.production_boundary.rst_baseline import FIXTURES, RecordComparison, capture, diff_records
from tools.production_boundary.baseline_corrections import BaselineVerificationError


BASELINE = Path("specs/017-universal-source-pipeline/evidence/baseline-dmrst-current")


@pytest.fixture(scope="module")
def records() -> dict[SourceForm, tuple[SourceArtifact, bytes, bytes]]:
    ingestor = ProductionIngestor()
    return {
        form: (
            source := SourceArtifact.from_path(path, source_form=form),
            (BASELINE / f"prepare-{form.value}.json").read_bytes(),
            serialize_contract(ingestor.prepare(source)),
        )
        for form, path in FIXTURES.items()
    }


@pytest.mark.parametrize("form", tuple(FIXTURES))
def test_real_corrections_are_explained_but_not_called_equivalent(
    records: dict[SourceForm, tuple[SourceArtifact, bytes, bytes]], form: SourceForm,
) -> None:
    source, before, after = records[form]
    differences = diff_records(before, after, source=source)
    counts = Counter(item.classification.value for item in differences)
    assert counts["source_identity_correction"] > 0
    assert bool(counts["doclang_table_correction"]) == (form is SourceForm.DOCLANG_XML)
    assert counts["analytical"] == 0
    comparison = RecordComparison("before", "after", differences)
    assert comparison.no_unexplained_regressions
    assert not comparison.analytically_equivalent


def test_corrections_require_the_materialized_source(
    records: dict[SourceForm, tuple[SourceArtifact, bytes, bytes]],
) -> None:
    _, before, after = records[SourceForm.DOCLANG_XML]
    assert any(item.classification.value == "analytical" for item in diff_records(before, after))


@pytest.mark.parametrize("mutation", (
    "source_id", "anchor_id", "source_name", "text", "cell_text", "cell_row",
    "cell_column", "cell_span", "cell_header", "cell_link", "missing_cell",
    "extra_cell", "inventory_text", "inventory_anchor", "missing_inventory_item",
    "unrelated_id", "baseline_cell", "wrong_source", "stale_anchor_id", "old_table_retained",
    "section_row_text", "section_row_anchor", "section_row_reverted", "section_row_header",
))
def test_corrections_reject_deliberate_corruption(
    records: dict[SourceForm, tuple[SourceArtifact, bytes, bytes]], mutation: str,
) -> None:
    source, before_bytes, after_bytes = records[SourceForm.DOCLANG_XML]
    before: dict[str, Any] = json.loads(before_bytes)
    after: dict[str, Any] = json.loads(after_bytes)
    semantic = after["semantic"]
    inventory = semantic["inventory"]
    table = next(item for item in inventory if item["classification"] == "table")
    cell = table["representation"]["cells"][0]
    match mutation:
        case "source_id":
            semantic["source"]["source_id"] = "0" * 64
        case "anchor_id":
            inventory[0]["anchors"][0]["artifact_identity"] = "0" * 64
        case "stale_anchor_id":
            inventory[0]["anchors"][0]["artifact_identity"] = before["semantic"]["source"]["source_id"]
        case "old_table_retained":
            old_table = next(i for i in before["semantic"]["inventory"] if i["classification"] == "table")
            table["representation"] = deepcopy(old_table["representation"])
        case "source_name":
            semantic["source"]["source_name"] = "different.dclg"
        case "text":
            semantic["prepared_document"]["text"] += " Invented."
        case "cell_text":
            cell["text"] = "Invented."
        case "cell_row" | "cell_column" | "cell_span":
            cell[{"cell_row": "row", "cell_column": "column", "cell_span": "row_span"}[mutation]] += 1
        case "cell_header":
            cell["header"] = not cell["header"]
        case "cell_link":
            cell["linked_item_ids"] = []
        case "missing_cell":
            table["representation"]["cells"].pop()
        case "extra_cell":
            table["representation"]["cells"].append(deepcopy(cell))
        case "inventory_text":
            child = next(item for item in inventory if item["item_id"] == cell["cell_id"])
            child["representation"]["text"] = "Invented."
            cell["text"] = "Invented."
        case "inventory_anchor":
            child = next(item for item in inventory if item["item_id"] == cell["cell_id"])
            anchor = next(a for a in child["anchors"] if a["kind"] == "table_coordinate")
            anchor["row"] += 1
            cell["row"] += 1
        case "missing_inventory_item":
            inventory.pop()
        case "unrelated_id":
            before["unrelated"] = {"source_id": before["semantic"]["source"]["source_id"]}
            after["unrelated"] = {"source_id": source.source_id}
        case "baseline_cell":
            old_table = next(i for i in before["semantic"]["inventory"] if i["classification"] == "table")
            old_table["representation"]["cells"][0]["text"] = "Not the historical defect."
        case "wrong_source":
            source = SourceArtifact.from_bytes(
                b"<doclang><text>Different source</text></doclang>",
                source_form=SourceForm.DOCLANG_XML, source_name=source.source_name,
            )
        case "section_row_text" | "section_row_anchor" | "section_row_reverted" | "section_row_header":
            header = next(item for item in inventory if "/srow[" in item["item_id"])
            match mutation:
                case "section_row_text":
                    header["representation"]["text"] = "Invented section."
                case "section_row_anchor":
                    header["anchors"].pop()
                case "section_row_reverted":
                    old_header = next(item for item in before["semantic"]["inventory"] if item["item_id"] == header["item_id"])
                    header["representation"] = deepcopy(old_header["representation"])
                case "section_row_header":
                    header_table = next(item for item in inventory if item["item_id"] == header["parent_id"])
                    header_cell = next(c for c in header_table["representation"]["cells"] if c["cell_id"] == header["item_id"])
                    header_cell["header"] = False
    try:
        differences = diff_records(json.dumps(before).encode(), json.dumps(after).encode(), source=source)
    except BaselineVerificationError as exc:
        assert str(exc)
        return
    assert any(item.classification.value == "analytical" for item in differences), mutation
    assert not RecordComparison("before", "after", differences).no_unexplained_regressions


def test_corrected_to_corrected_comparison_does_not_reapply_repairs(
    records: dict[SourceForm, tuple[SourceArtifact, bytes, bytes]],
) -> None:
    source, _, actual = records[SourceForm.DOCLANG_XML]
    assert diff_records(actual, actual, source=source) == ()


@pytest.mark.parametrize("before,after", (({}, {"text": "<absent>"}), ({"value": 1}, {"value": True})))
def test_json_absence_and_types_cannot_hide_differences(before: object, after: object) -> None:
    differences = diff_records(json.dumps(before).encode(), json.dumps(after).encode())
    assert differences
    assert all(item.classification.value == "analytical" for item in differences)


@pytest.mark.parametrize("mutation", (None, "stale_digest", "missing_record"))
def test_real_comparison_cli_checks_contents_and_preserves_baseline(tmp_path: Path, mutation: str | None) -> None:
    capture(tmp_path, store=None, release_id=None, device="cpu")
    if mutation == "stale_digest":
        path = tmp_path / "prepare-text.json"
        record = json.loads(path.read_bytes())
        record["semantic"]["prepared_document"]["text"] += " Corrupted without updating the digest."
        path.write_text(json.dumps(record), encoding="utf-8")
    elif mutation == "missing_record":
        (tmp_path / "prepare-text.json").unlink()
    else:
        # Preserve the real historical records; a scratch copy mixes those three
        # prepared documents with model-free captures for the other source forms.
        for form in FIXTURES:
            name = f"prepare-{form.value}.json"
            (tmp_path / name).write_bytes((BASELINE / name).read_bytes())
    original = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = subprocess.run(
        [sys.executable, "-m", "tools.production_boundary.rst_baseline", "compare", "--baseline", str(tmp_path), "--no-analysis"],
        capture_output=True, text=True, check=False,
    )
    report = json.loads(result.stdout)
    assert result.returncode == (0 if mutation is None else 1), result.stderr
    assert report["no_unexplained_regressions"] == (mutation is None)
    if mutation is None:
        assert report["equivalent"] is False
        assert report["analytically_equivalent"] is False
        assert report["difference_counts_by_class"]["source_identity_correction"] > 0
        assert report["difference_counts_by_class"]["doclang_table_correction"] > 0
    else:
        assert report["analytical_differences"]["prepare-text"]
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == original
