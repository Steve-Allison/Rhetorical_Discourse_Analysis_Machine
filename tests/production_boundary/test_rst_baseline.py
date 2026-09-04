"""Migration preservation evidence remains explicit and analytically strict."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.production_boundary.rst_baseline import DifferenceClass, diff_records


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_COMPARISON = (
    ROOT
    / "specs"
    / "010-repository-migration"
    / "evidence"
    / "release"
    / "rename-6.0.0-baseline-comparison.json"
)


def test_historical_model_backed_migration_has_no_analytical_difference() -> None:
    report = json.loads(HISTORICAL_COMPARISON.read_text(encoding="utf-8"))
    assert report["analytically_equivalent"] is True
    assert report["analytical_differences"] == {}
    assert {"analyse-text", "analyse-edus"} <= report["comparisons"].keys()
    allowed = {item.value for item in DifferenceClass}
    for name in ("analyse-text", "analyse-edus"):
        differences = report["comparisons"][name]["differences"]
        assert differences, f"{name} must expose why its package-renamed digest changed"
        assert {item["classification"] for item in differences} <= allowed
        assert all(
            item["classification"] != DifferenceClass.ANALYTICAL.value
            for item in differences
        )


def test_historical_comparison_covers_every_baseline_record() -> None:
    report = json.loads(HISTORICAL_COMPARISON.read_text(encoding="utf-8"))
    expected = {
        "capabilities",
        "prepare-text",
        "prepare-edus",
        "prepare-markdown",
        "prepare-docling_json",
        "prepare-doclang_xml",
        "prepare-doclang_archive",
        "analyse-text",
        "analyse-edus",
    }
    assert set(report["comparisons"]) == expected


def _difference_class(
    before: dict[str, object],
    after: dict[str, object],
) -> DifferenceClass:
    differences = diff_records(
        json.dumps(before).encode(),
        json.dumps(after).encode(),
    )
    assert len(differences) == 1
    return differences[0].classification


def test_comparator_classifies_execution_evidence_without_hiding_analysis() -> None:
    assert _difference_class(
        {"execution": {"duration_seconds": 1.0}},
        {"execution": {"duration_seconds": 2.0}},
    ) is DifferenceClass.EXECUTION


def test_comparator_classifies_valid_package_versions_as_identity() -> None:
    assert _difference_class(
        {"package_version": "5.0.0"},
        {"package_version": "6.0.0"},
    ) is DifferenceClass.PACKAGE_IDENTITY


def test_comparator_classifies_declared_derived_digest_changes() -> None:
    assert _difference_class(
        {"semantic_digest": {"hex_digest": "a" * 64}},
        {"semantic_digest": {"hex_digest": "b" * 64}},
    ) is DifferenceClass.DERIVED_DIGEST


def test_comparator_rejects_causal_analytical_changes() -> None:
    assert _difference_class(
        {"analysis": {"nodes": [{"text": "Because it rained"}]}},
        {"analysis": {"nodes": [{"text": "The match continued"}]}},
    ) is DifferenceClass.ANALYTICAL


@pytest.mark.parametrize("capacity", (None, {"maximum": 512, "unit": "edu_count"}))
def test_capacity_rename_is_reported_without_hiding_its_values(capacity: object) -> None:
    before = {"semantic": {"analysis_plan": {"parser_capacity": capacity}}}
    after = {"semantic": {"analysis_plan": {"capacity": capacity}}}
    differences = diff_records(json.dumps(before).encode(), json.dumps(after).encode())
    assert differences
    assert all(item.classification.value == "contract_field_rename" for item in differences)
    assert any("parser_capacity" in item.path for item in differences)
    assert any("capacity" in item.path for item in differences)


@pytest.mark.parametrize("after_capacity", ({"maximum": 256}, None, {}))
def test_capacity_rename_never_hides_changed_limits(after_capacity: object) -> None:
    before = {"analysis_plan": {"parser_capacity": {"maximum": 512}}}
    after = {"analysis_plan": {"capacity": after_capacity}}
    differences = diff_records(json.dumps(before).encode(), json.dumps(after).encode())
    assert any(item.classification is DifferenceClass.ANALYTICAL for item in differences)


def test_capacity_rename_does_not_apply_to_other_fields() -> None:
    before = {"analysis": {"parser_capacity": 512}}
    after = {"analysis": {"capacity": 512}}
    differences = diff_records(json.dumps(before).encode(), json.dumps(after).encode())
    assert all(item.classification is DifferenceClass.ANALYTICAL for item in differences)


def test_capacity_rename_does_not_allow_both_names() -> None:
    before = {"analysis_plan": {"parser_capacity": 512}}
    after = {"analysis_plan": {"parser_capacity": 512, "capacity": 512}}
    differences = diff_records(json.dumps(before).encode(), json.dumps(after).encode())
    assert all(item.classification is DifferenceClass.ANALYTICAL for item in differences)


def test_plan_identity_is_derived_only_when_it_matches_the_embedded_plan() -> None:
    def record(digest: str, reference: str) -> dict[str, object]:
        return {"semantic": {
            "preparation": {"semantic": {"analysis_plan": {"semantic_digest": {"hex_digest": digest}}}},
            "request": {"analysis_plan_identity": {"hex_digest": reference}},
        }}

    before = json.dumps(record("a" * 64, "a" * 64)).encode()
    for reference, expected in (("b" * 64, DifferenceClass.DERIVED_DIGEST), ("c" * 64, DifferenceClass.ANALYTICAL)):
        after = json.dumps(record("b" * 64, reference)).encode()
        differences = diff_records(before, after)
        difference = next(item for item in differences if "analysis_plan_identity" in item.path)
        assert difference.classification is expected


def test_baseline_requires_an_explicit_model_instead_of_a_retired_default(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tools.production_boundary.rst_baseline", "capture", "--output", str(tmp_path / "baseline")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--release-id is required unless --no-analysis is specified" in result.stderr
    assert not (tmp_path / "baseline").exists()
