"""Run and compare deterministic production behavior across the codeline split."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import warnings

_TEXT = "Because it rained, the match stopped. The crowd left."
_EDUS = ("Because it rained, the match stopped.", "The crowd left.")
_MODELS = (
    ("gumrrg", {}),
    ("unirst", {"relinventory": "eng.erst.gum"}),
)


def _sha256_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tree_payload(tree: object) -> dict[str, object]:
    payload: dict[str, object] = {}
    for name in ("id", "text", "start", "end", "relation", "nuclearity"):
        payload[name] = getattr(tree, name, None)
    for name in ("left", "right"):
        child = getattr(tree, name, None)
        payload[name] = _tree_payload(child) if child is not None else None
    return payload


def _analysis_payload(parser: Any, model: str) -> tuple[str, str, dict[str, object]]:
    from isanlp_rst.contracts import RstDocument, analysis_from_json, to_json

    analysis = parser.parse_document(
        RstDocument.from_text(_TEXT, document_id=f"parity-{model}"),
        prime_markers=False,
    )
    serialized = to_json(analysis)
    payload = json.loads(serialized)
    timing = payload.get("timing")
    if isinstance(timing, dict):
        for key in timing:
            timing[key] = 0.0
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise AssertionError("analysis parity result has no provenance mapping")
    provenance["timestamp"] = "<normalized>"
    provenance["source_revision"] = "<environment-normalized>"
    normalized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    reloaded = analysis_from_json(serialized)
    roundtrip = json.loads(to_json(reloaded))
    roundtrip_timing = roundtrip.get("timing")
    if isinstance(roundtrip_timing, dict):
        for key in roundtrip_timing:
            roundtrip_timing[key] = 0.0
    roundtrip_provenance = roundtrip.get("provenance")
    if isinstance(roundtrip_provenance, dict):
        roundtrip_provenance["timestamp"] = "<normalized>"
        roundtrip_provenance["source_revision"] = "<environment-normalized>"
    return hashlib.sha256(normalized.encode()).hexdigest(), _sha256_json(roundtrip), provenance


def run(device: str) -> dict[str, object]:
    from isanlp_rst import Parser

    cases: dict[str, object] = {}
    for version, options in _MODELS:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            parser = Parser(
                hf_model_version=version,
                device=device,
                relinventory=options.get("relinventory"),
            )
            raw = parser(_TEXT)["rst"][0]
            presegmented = parser.from_edus(_EDUS)["rst"][0]
            analysis_sha256, roundtrip_sha256, provenance = _analysis_payload(parser, version)
        cases[version] = {
            "actual_device": str(parser.predictor._device),
            "family": parser.family,
            "model_identity": version,
            "prepared_raw_sha256": _sha256_json({"mode": "raw", "text": _TEXT}),
            "prepared_edus_sha256": _sha256_json({"mode": "edus", "edus": _EDUS}),
            "raw_result_sha256": _sha256_json(_tree_payload(raw)),
            "presegmented_result_sha256": _sha256_json(_tree_payload(presegmented)),
            "analysis_serialization_sha256": analysis_sha256,
            "analysis_roundtrip_sha256": roundtrip_sha256,
            "provenance": provenance,
            "warnings": [str(item.message) for item in caught],
        }
    try:
        Parser(hf_model_version="unirst", relinventory="eng.rst.gum", device=device)
    except ValueError as exc:
        deterministic_failure = {"exception": type(exc).__name__, "message": str(exc)}
    else:
        raise AssertionError("invalid UniRST relation inventory unexpectedly succeeded")
    return {
        "schema_version": "isanlp_rst_production_parity/v2",
        "input": _TEXT,
        "presegmented_edus": list(_EDUS),
        "requested_device": device,
        "cases": cases,
        "deterministic_failure": deterministic_failure,
    }


def _compare(expected: dict[str, object], actual: dict[str, object]) -> tuple[str, ...]:
    differences: list[str] = []
    for field in ("schema_version", "input", "presegmented_edus", "requested_device", "deterministic_failure"):
        if expected.get(field) != actual.get(field):
            differences.append(field)
    expected_cases = expected.get("cases")
    actual_cases = actual.get("cases")
    if not isinstance(expected_cases, dict) or not isinstance(actual_cases, dict):
        return (*differences, "cases")
    for model in sorted(set(expected_cases) | set(actual_cases)):
        if expected_cases.get(model) != actual_cases.get(model):
            differences.append(f"cases.{model}")
    return tuple(differences)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--compare", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.source_root is not None:
        sys.path.insert(0, str(args.source_root.resolve()))
    result = run(args.device)
    if args.output is not None:
        envelope: dict[str, object] = {"schema_version": "isanlp_rst_production_parity_baseline/v2", "devices": {}}
        if args.output.is_file():
            loaded = json.loads(args.output.read_text(encoding="utf-8"))
            if loaded.get("schema_version") == envelope["schema_version"] and isinstance(loaded.get("devices"), dict):
                envelope = loaded
        devices = envelope["devices"]
        if not isinstance(devices, dict):
            raise ValueError("parity output devices must be a mapping")
        devices[args.device] = result
        args.output.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.compare is not None:
        expected = json.loads(args.compare.read_text(encoding="utf-8"))
        if isinstance(expected.get("devices"), dict):
            expected = expected["devices"][args.device]
        differences = _compare(expected, result)
        result = {"actual": result, "differences": differences, "valid": not differences}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not args.compare or result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
