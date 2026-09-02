"""Fail-closed direct inspection of private candidate outputs."""

import json
from pathlib import Path

from rdam.rst.ingest import (
    AnalysedOutcome,
    EmptyPrimaryAnalysisOutcome,
    PreparationOutcome,
    load_contract,
)
from rdam.rst.ingest.identity import sha256_file
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
        preparation_payload = payload.get("preparation_outcome")
        result_payload = payload.get("analysis_result")
        checks: dict[str, bool] = {
            "source_record_matches": isinstance(payload.get("source"), dict)
            and payload["source"].get("source_id") == source.source_id,
            "preparation_outcome_present": isinstance(preparation_payload, dict),
            "result_present": isinstance(result_payload, dict),
        }
        prepared_digest: str | None = None
        result_digest: str | None = None
        inventory_count = 0
        node_count = 0
        anchor_count = 0
        preparation: PreparationOutcome | None = None
        if isinstance(preparation_payload, dict):
            loaded_preparation = load_contract(json.dumps(preparation_payload, ensure_ascii=False))
            if not isinstance(loaded_preparation, PreparationOutcome):
                raise ValueError(f"candidate preparation has wrong contract kind: {source.source_id}")
            preparation = loaded_preparation
            prepared = preparation.semantic.prepared_document
            if prepared.semantic_digest is None:
                raise ValueError("prepared document omitted its semantic digest")
            prepared_digest = prepared.semantic_digest.hex_digest
            inventory_count = len(preparation.semantic.inventory)
            checks["prepared_ranges_reconstruct"] = _segments_reconstruct(
                [segment.model_dump(mode="json") for segment in prepared.segments],
                prepared.text,
            )
            checks["inventory_dispositions_reconcile"] = (
                len(preparation.dispositions) == inventory_count
                and all(item.disposition == disposition for item, disposition in zip(
                    preparation.semantic.inventory,
                    preparation.dispositions,
                    strict=True,
                ))
            )
        if isinstance(result_payload, dict):
            result = load_contract(json.dumps(result_payload, ensure_ascii=False))
            checks["analysis_outcome_kind"] = isinstance(
                result,
                AnalysedOutcome | EmptyPrimaryAnalysisOutcome,
            )
            if not isinstance(result, AnalysedOutcome | EmptyPrimaryAnalysisOutcome):
                raise ValueError(f"candidate analysis has wrong contract kind: {source.source_id}")
            if result.semantic_digest is None:
                raise ValueError("analysis outcome omitted its semantic digest")
            result_digest = result.semantic_digest.hex_digest
            analysis = result.semantic.analysis
            node_count = len(analysis.nodes) if analysis is not None else 0
            anchor_count = len(result.semantic.anchors)
            checks["persisted_digest_valid"] = True
            checks["embedded_preparation_reconciles"] = (
                preparation is not None
                and result.semantic.preparation.semantic_digest == preparation.semantic_digest
            )
            validation = result.semantic.validation
            checks["analysis_validation_passed"] = (
                isinstance(result, EmptyPrimaryAnalysisOutcome)
                or (
                    validation is not None
                    and validation.passed
                    and validation.anchor_coverage.covered_units
                    == validation.anchor_coverage.total_units
                )
            )
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
