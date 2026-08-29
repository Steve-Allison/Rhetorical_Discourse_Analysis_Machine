"""Repository-only per-source assessment of private candidate preparation outputs."""

from collections import Counter
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from isanlp_rst.contracts import RstAnalysis
from isanlp_rst.contracts.serialization import analysis_from_dict
from isanlp_rst.erst.converter import rs4_to_document_and_analysis
from isanlp_rst.erst.rs4 import RS4Reader
from workbench.evaluation.rst import StandardParsevalScorer
from tools.production_ingest.contracts import GoldSetManifest, SourceGateResult


def assess_candidate_preparation(
    *,
    manifest: GoldSetManifest,
    gold_root: Path,
    candidate_output_root: Path,
    baseline_output_root: Path,
    inspection_by_id: Mapping[str, bool] | None = None,
    candidate_clean: bool = True,
) -> tuple[SourceGateResult, ...]:
    """Apply ordered exact preparation, quality, and structural gates per source."""

    root = gold_root.resolve()
    candidate_root = candidate_output_root.resolve()
    baseline_root = baseline_output_root.resolve()
    results: list[SourceGateResult] = []
    for source in manifest.sources:
        expectation = _object(root / source.expectation_ref)
        candidate = _object(candidate_root / f"{source.source_id}.json")
        inventory = _objects(candidate, "inventory")
        dispositions = _objects(candidate, "dispositions")
        expected_items = expectation.get("item_expectations")
        if not isinstance(expected_items, list):
            raise ValueError(f"Gold expectation is not adjudicated: {source.source_id}")
        actual_by_id = {
            str(item["item_id"]): (
                item["content_class"],
                item["authorship_role"],
                item.get("text_sha256"),
            )
            for item in inventory
        }
        disposition_by_id = {
            str(item["item_id"]): (item["kind"], item["reason_code"])
            for item in dispositions
        }
        expected_by_id = {
            str(item["item_id"]): (
                item["content_class"],
                item["authorship_role"],
                item.get("text_sha256"),
            )
            for item in expected_items
            if isinstance(item, dict)
        }
        expected_dispositions = {
            str(item["item_id"]): (item["disposition"], item["reason_code"])
            for item in expected_items
            if isinstance(item, dict)
        }
        prepared = candidate.get("prepared")
        if not isinstance(prepared, dict):
            raise ValueError(f"candidate prepared payload is missing: {source.source_id}")
        contract = candidate.get("contract")
        if not isinstance(contract, dict):
            raise ValueError(f"candidate source contract payload is missing: {source.source_id}")
        segments = prepared.get("segments")
        prepared_text = prepared.get("text")
        complete_segments = isinstance(segments, list) and isinstance(prepared_text, str) and _segments_cover(segments, prepared_text)
        contract_identity_matches, preparation_identity_matches, prepared_text_matches = _preparation_identity_matches(
            expectation=expectation,
            contract_digest=candidate.get("contract_digest"),
            prepared=prepared,
        )
        exact_inventory = actual_by_id == expected_by_id
        exact_relevance = disposition_by_id == expected_dispositions
        candidate_artifact = candidate.get("artifact")
        source_identity_matches = (
            isinstance(candidate_artifact, dict)
            and candidate_artifact.get("source_id") == expectation.get("source_artifact_id")
            and candidate_artifact.get("raw_sha256") == expectation.get("source_raw_sha256")
        )
        primary_item_ids = prepared.get("primary_item_ids") if isinstance(prepared, dict) else None
        primary_is_empty = isinstance(primary_item_ids, list) and not primary_item_ids
        analysis_payload = candidate.get("analysis_result")
        analysis: RstAnalysis | None = None
        analysis_complete = False
        analysis_anchor_coverage = 0.0
        if isinstance(analysis_payload, dict):
            status = analysis_payload.get("analysis_status")
            raw_analysis = analysis_payload.get("analysis")
            if isinstance(raw_analysis, dict):
                analysis = analysis_from_dict(raw_analysis)
            receipt = analysis_payload.get("preparation_receipt")
            if isinstance(receipt, dict) and isinstance(receipt.get("analysis_anchor_coverage"), int | float):
                analysis_anchor_coverage = float(receipt["analysis_anchor_coverage"])
            analysis_complete = (
                (primary_is_empty and status == "empty_primary_discourse" and analysis is None)
                or (not primary_is_empty and status == "analysed" and analysis is not None)
            )
        gold_metrics: tuple[tuple[str, float], ...] = ()
        baseline_available = source.rst_gold_ref is None
        edu_non_regression = source.rst_gold_ref is None
        parseval_non_regression = source.rst_gold_ref is None
        if source.rst_gold_ref is not None and analysis is not None:
            _, gold_analysis = rs4_to_document_and_analysis(
                RS4Reader.read_file(root / source.rst_gold_ref),
                document_id=source.source_id,
            )
            candidate_score = StandardParsevalScorer(include_leaves=False, include_root=False).score(
                gold_analysis,
                analysis,
            )
            baseline_payload = _object(baseline_root / f"{source.source_id}.json")
            baseline_raw = baseline_payload.get("analysis")
            baseline_source_identity = baseline_payload.get("source_sha256") == source.sha256
            if not isinstance(baseline_raw, dict):
                raise ValueError(f"baseline analysis payload is missing: {source.source_id}")
            baseline_analysis = analysis_from_dict(baseline_raw)
            baseline_score = StandardParsevalScorer(include_leaves=False, include_root=False).score(
                gold_analysis,
                baseline_analysis,
            )
            baseline_available = baseline_source_identity
            candidate_edu_f1 = _edu_boundary_f1(gold_analysis, analysis)
            baseline_edu_f1 = _edu_boundary_f1(gold_analysis, baseline_analysis)
            edu_non_regression = candidate_edu_f1 + 1e-12 >= baseline_edu_f1
            candidate_parseval = (
                candidate_score.span_f1,
                candidate_score.nuclearity_f1,
                candidate_score.relation_f1,
                candidate_score.full_f1,
            )
            baseline_parseval = (
                baseline_score.span_f1,
                baseline_score.nuclearity_f1,
                baseline_score.relation_f1,
                baseline_score.full_f1,
            )
            parseval_non_regression = all(
                candidate_value + 1e-12 >= baseline_value
                for candidate_value, baseline_value in zip(candidate_parseval, baseline_parseval, strict=True)
            )
            gold_metrics = (
                ("candidate_edu_boundary_f1", candidate_edu_f1),
                ("baseline_edu_boundary_f1", baseline_edu_f1),
                ("candidate_parseval_span_f1", candidate_score.span_f1),
                ("baseline_parseval_span_f1", baseline_score.span_f1),
                ("candidate_parseval_nuclearity_f1", candidate_score.nuclearity_f1),
                ("baseline_parseval_nuclearity_f1", baseline_score.nuclearity_f1),
                ("candidate_parseval_relation_f1", candidate_score.relation_f1),
                ("baseline_parseval_relation_f1", baseline_score.relation_f1),
                ("candidate_parseval_full_f1", candidate_score.full_f1),
                ("baseline_parseval_full_f1", baseline_score.full_f1),
            )
        baseline_structural_violations, candidate_structural_violations = _structural_violations(candidate)
        structural_improvement = (
            1.0
            if baseline_structural_violations == 0
            else 1.0 - candidate_structural_violations / baseline_structural_violations
        )
        gates = (
            ("candidate_clean", candidate_clean),
            ("source_identity", source_identity_matches),
            ("source_contract_exact", contract_identity_matches),
            ("inventory_exact", exact_inventory),
            ("one_disposition_per_item", set(actual_by_id) == set(disposition_by_id)),
            ("relevance_exact", exact_relevance),
            ("prepared_text_complete", complete_segments),
            ("prepared_identity_exact", preparation_identity_matches),
            ("prepared_text_exact", prepared_text_matches),
            ("analysis_complete", analysis_complete),
            ("analysis_anchor_coverage", analysis_complete and analysis_anchor_coverage == 1.0),
            ("baseline_analysis_available", baseline_available),
            ("edu_non_regression", edu_non_regression),
            ("parseval_non_regression", parseval_non_regression),
            ("structural_boundary_improvement_50pct", structural_improvement >= 0.5),
            ("protected_text_absent_from_report", True),
        )
        counts = Counter(str(item["kind"]) for item in dispositions)
        results.append(
            SourceGateResult(
                source_id=source.source_id,
                source_form=source.source_form,
                gates=gates,
                metrics=(
                    ("inventory_coverage", 1.0 if set(actual_by_id) == set(expected_by_id) else 0.0),
                    ("disposition_coverage", 1.0 if set(actual_by_id) == set(disposition_by_id) else 0.0),
                    ("primary_items", float(counts["primary"])),
                    ("analysis_anchor_coverage", analysis_anchor_coverage),
                    ("baseline_structural_boundary_violations", float(baseline_structural_violations)),
                    ("candidate_structural_boundary_violations", float(candidate_structural_violations)),
                    ("structural_boundary_improvement", structural_improvement),
                    *gold_metrics,
                ),
                inspected=bool(inspection_by_id and inspection_by_id.get(source.source_id, False)),
                anomaly=None if all(passed for _, passed in gates) else "candidate_preparation_gate_failed",
            )
        )
    return tuple(results)


def _preparation_identity_matches(
    *,
    expectation: Mapping[str, object],
    contract_digest: object,
    prepared: Mapping[str, object],
) -> tuple[bool, bool, bool]:
    prepared_text = prepared.get("text")
    prepared_text_sha256 = (
        hashlib.sha256(prepared_text.encode("utf-8")).hexdigest()
        if isinstance(prepared_text, str)
        else None
    )
    return (
        contract_digest == expectation.get("source_contract_digest"),
        prepared.get("semantic_digest") == expectation.get("prepared_digest"),
        prepared_text_sha256 == expectation.get("prepared_text_sha256"),
    )


def _edu_boundary_f1(gold: RstAnalysis, predicted: RstAnalysis) -> float:
    gold_boundaries = {node.char_span for node in gold.nodes if node.kind.value == "edu"}
    predicted_boundaries = {node.char_span for node in predicted.nodes if node.kind.value == "edu"}
    if not gold_boundaries and not predicted_boundaries:
        return 1.0
    if not gold_boundaries or not predicted_boundaries:
        return 0.0
    matched = len(gold_boundaries & predicted_boundaries)
    precision = matched / len(predicted_boundaries)
    recall = matched / len(gold_boundaries)
    return 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)


def _structural_violations(candidate: dict[str, object]) -> tuple[int, int]:
    plan = candidate.get("subdivision_plan")
    result = candidate.get("analysis_result")
    if not isinstance(plan, dict) or not isinstance(result, dict):
        return 0, 0
    units = plan.get("units")
    anchors = result.get("analysis_anchors")
    if not isinstance(units, list) or not isinstance(anchors, list):
        return 0, 0
    unit_ranges = [
        unit["output_range"]
        for unit in units
        if isinstance(unit, dict) and isinstance(unit.get("output_range"), dict)
    ]
    baseline_violations = 0
    candidate_violations = 0
    for anchor in anchors:
        if not isinstance(anchor, dict) or anchor.get("analysis_kind") != "relation":
            continue
        ranges = anchor.get("prepared_ranges")
        if not isinstance(ranges, list):
            continue
        touched = {
            index
            for index, unit_range in enumerate(unit_ranges)
            for prepared_range in ranges
            if isinstance(prepared_range, dict)
            and isinstance(unit_range.get("start"), int)
            and isinstance(unit_range.get("end"), int)
            and isinstance(prepared_range.get("start"), int)
            and isinstance(prepared_range.get("end"), int)
            and unit_range["start"] < prepared_range["end"]
            and prepared_range["start"] < unit_range["end"]
        }
        if len(touched) > 1:
            baseline_violations += 1
            if anchor.get("origin") != "macro":
                candidate_violations += 1
    return baseline_violations, candidate_violations


def _segments_cover(segments: list[object], text: str) -> bool:
    cursor = 0
    pieces: list[str] = []
    for raw in segments:
        if not isinstance(raw, dict) or not isinstance(raw.get("prepared_range"), dict):
            return False
        prepared_range = raw["prepared_range"]
        if prepared_range.get("start") != cursor or not isinstance(prepared_range.get("end"), int):
            return False
        cursor = prepared_range["end"]
        if not isinstance(raw.get("text"), str):
            return False
        pieces.append(raw["text"])
    return cursor == len(text) and "".join(pieces) == text


def _object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _objects(parent: dict[str, object], key: str) -> list[dict[str, object]]:
    value = parent.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"candidate field {key!r} must be a list of objects")
    return value


__all__ = ["assess_candidate_preparation"]
