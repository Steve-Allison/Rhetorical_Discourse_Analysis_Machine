"""Fail-closed direct inspection of private candidate outputs."""

import json
from pathlib import Path

from isanlp_rst.ingest import ProductionAnalysisResult
from isanlp_rst.ingest.identity import sha256_file
from tools.production_ingest.contracts import GoldSetManifest


def inspect_candidate_outputs(
    *,
    manifest: GoldSetManifest,
    candidate_output_root: Path,
) -> dict[str, object]:
    """Inspect every persisted preparation/result without exporting source text."""

    records: list[dict[str, object]] = []
    for source in manifest.sources:
        path = candidate_output_root / f"{source.source_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"candidate output must be an object: {source.source_id}")
        prepared = payload.get("prepared")
        result_payload = payload.get("analysis_result")
        checks: dict[str, bool] = {
            "source_record_matches": isinstance(payload.get("source"), dict)
            and payload["source"].get("source_id") == source.source_id,
            "prepared_present": isinstance(prepared, dict),
            "result_present": isinstance(result_payload, dict),
        }
        prepared_digest: str | None = None
        result_digest: str | None = None
        inventory_count = 0
        node_count = 0
        anchor_count = 0
        if isinstance(prepared, dict):
            prepared_digest = prepared.get("semantic_digest") if isinstance(prepared.get("semantic_digest"), str) else None
            segments = prepared.get("segments")
            text = prepared.get("text")
            checks["prepared_ranges_reconstruct"] = (
                isinstance(segments, list)
                and isinstance(text, str)
                and _segments_reconstruct(segments, text)
            )
        inventory = payload.get("inventory")
        dispositions = payload.get("dispositions")
        if isinstance(inventory, list):
            inventory_count = len(inventory)
        checks["inventory_dispositions_reconcile"] = (
            isinstance(inventory, list)
            and isinstance(dispositions, list)
            and len(inventory) == len(dispositions)
            and {item.get("item_id") for item in inventory if isinstance(item, dict)}
            == {item.get("item_id") for item in dispositions if isinstance(item, dict)}
        )
        if isinstance(result_payload, dict):
            result = ProductionAnalysisResult.model_validate(result_payload)
            result_digest = result.semantic_digest
            node_count = len(result.analysis.nodes) if result.analysis is not None else 0
            edge_count = (
                len(result.analysis.primary_edges) + len(result.analysis.secondary_edges)
                if result.analysis is not None
                else 0
            )
            anchor_count = len(result.analysis_anchors)
            checks["persisted_digest_valid"] = bool(result_digest)
            checks["receipt_reconciles"] = (
                result.preparation_receipt.inventory_count == inventory_count
                and result.preparation_receipt.disposition_count == len(dispositions or ())
            )
            checks["analysis_targets_anchored"] = anchor_count == node_count + edge_count
        passed = all(checks.values())
        records.append(
            {
                "source_id": source.source_id,
                "source_form": source.source_form.value,
                "output_sha256": sha256_file(path),
                "prepared_digest": prepared_digest,
                "result_digest": result_digest,
                "inventory_count": inventory_count,
                "node_count": node_count,
                "anchor_count": anchor_count,
                "checks": sorted(checks.items()),
                "inspected": passed,
                "anomaly": None if passed else "inspection_check_failed",
            }
        )
    return {
        "schema_version": "1.0.0",
        "source_count": len(records),
        "all_inspected": all(bool(record["inspected"]) for record in records),
        "sources": records,
    }


def inspection_status_by_id(record: dict[str, object]) -> dict[str, bool]:
    sources = record.get("sources")
    if not isinstance(sources, list):
        raise ValueError("inspection record sources must be a list")
    statuses: dict[str, bool] = {}
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            raise ValueError("inspection source record is invalid")
        statuses[source["source_id"]] = source.get("inspected") is True and source.get("anomaly") is None
    return statuses


def _segments_reconstruct(segments: list[object], text: str) -> bool:
    cursor = 0
    pieces: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict) or not isinstance(segment.get("prepared_range"), dict):
            return False
        prepared_range = segment["prepared_range"]
        segment_text = segment.get("text")
        if (
            prepared_range.get("start") != cursor
            or not isinstance(prepared_range.get("end"), int)
            or not isinstance(segment_text, str)
        ):
            return False
        cursor = prepared_range["end"]
        pieces.append(segment_text)
    return cursor == len(text) and "".join(pieces) == text


__all__ = ["inspect_candidate_outputs", "inspection_status_by_id"]
