"""Lossless archival reading of v2 ingest evidence, without current-analysis claims.

The digest projection is the v2 projection shipped before evidence normalization.
Digest integrity establishes preservation, not the truth of saved probabilities,
calibration flags, validation receipts or analytical conclusions.
"""

from dataclasses import dataclass
import json
from typing import Any, Literal, cast

from rdam._canonical import canonical_json_bytes, semantic_sha256, validate_ijson_value


@dataclass(frozen=True, slots=True)
class HistoricalProductionRecord:
    """Canonical historical bytes with digest integrity, never a current result.

    ``payload`` returns a detached JSON object. Original values remain available
    for inspection; callers cannot mutate the retained bytes through that view.
    This reader does not run current analytical invariants against historical data.
    """

    canonical_bytes: bytes

    def __post_init__(self) -> None:
        payload = _decode(self.canonical_bytes)
        _verify(payload)
        object.__setattr__(self, "canonical_bytes", canonical_json_bytes(payload))

    @property
    def evidence_status(self) -> Literal["historical_unverified_analysis"]:
        return "historical_unverified_analysis"

    @property
    def payload(self) -> dict[str, Any]:
        return _decode(self.canonical_bytes)


def load_historical_contract(payload: bytes | str) -> HistoricalProductionRecord:
    """Read v2 evidence as an archive; do not migrate or repair saved predictions."""
    return HistoricalProductionRecord(payload.encode("utf-8") if isinstance(payload, str) else payload)


def _decode(payload: bytes) -> dict[str, Any]:
    parsed: Any = json.loads(payload.decode("utf-8", errors="strict"), object_pairs_hook=_unique_object)
    validate_ijson_value(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("historical production record must be a JSON object")
    return cast(dict[str, Any], parsed)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _verify(record: dict[str, Any]) -> None:
    if record.get("contract") != "isanlp_rst.production" or record.get("contract_version") != "2.0.0":
        raise ValueError("historical reader requires isanlp_rst.production 2.0.0")
    if set(record) != {"contract", "contract_version", "kind", "semantic", "execution", "semantic_digest"}:
        raise ValueError("historical production envelope fields do not match v2")
    digest = record["semantic_digest"]
    if not isinstance(digest, dict):
        raise ValueError("historical record requires a SHA-256 semantic digest")
    digest = cast(dict[str, Any], digest)
    if set(digest) != {"algorithm", "hex_digest"} or digest["algorithm"] != "sha256":
        raise ValueError("historical record requires a SHA-256 semantic digest")
    if digest["hex_digest"] != semantic_sha256(_projection(record)):
        raise ValueError("historical production semantic digest mismatch")


def _projection(record: dict[str, Any]) -> dict[str, Any]:
    # Decode a detached copy: normalization must not alter the archived evidence.
    semantic = _decode(canonical_json_bytes(record["semantic"]))
    kind = record["kind"]
    if kind not in {
        "capabilities", "preparation_outcome", "parser_analysis_result", "analysed_outcome",
        "empty_primary_analysis_outcome", "safe_production_failure", "diagnostic_production_failure",
    }:
        raise ValueError("unsupported historical production record kind")
    if kind in {"preparation_outcome", "parser_analysis_result", "analysed_outcome", "empty_primary_analysis_outcome"}:
        semantic.pop("execution", None)
    if kind in {"parser_analysis_result", "analysed_outcome", "empty_primary_analysis_outcome"}:
        analysis = semantic.get("analysis")
        if isinstance(analysis, dict):
            analysis = cast(dict[str, Any], analysis)
            if "timing" in analysis:
                analysis["timing"] = None
            provenance = analysis.get("provenance")
            if isinstance(provenance, dict):
                cast(dict[str, Any], provenance)["timestamp"] = None
        recombination = semantic.get("recombination")
        if isinstance(recombination, dict):
            cast(dict[str, Any], recombination).pop("unit_durations_ms", None)
    if kind in {"analysed_outcome", "empty_primary_analysis_outcome"}:
        for field in ("preparation", "parser_result"):
            nested = semantic.get(field)
            if nested is None and field == "parser_result":
                continue
            if not isinstance(nested, dict):
                raise ValueError(f"historical outcome lacks its {field} envelope")
            nested = cast(dict[str, Any], nested)
            _verify(nested)
            semantic[field] = _projection(nested)
    return {"contract": record["contract"], "contract_version": record["contract_version"],
            "kind": kind, "semantic": semantic}


__all__ = ["HistoricalProductionRecord", "load_historical_contract"]
