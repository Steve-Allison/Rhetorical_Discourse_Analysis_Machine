"""Migration preservation evidence remains explicit and analytically strict."""

import json
from pathlib import Path

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
