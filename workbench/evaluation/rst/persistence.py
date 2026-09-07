"""Measure saved RST persistence costs without rerunning model inference.

Run with ``pixi run python -m workbench.evaluation.rst.persistence REPORT``.
Peak allocations are tracemalloc observations, not process RSS or model memory.
Each phase reports separately; timings include tracing overhead. This command
measures an existing artifact and does not certify analytical accuracy.
"""

import argparse
from collections.abc import Callable
from dataclasses import asdict, dataclass
import gc
import hashlib
import json
from pathlib import Path
import platform
from time import perf_counter
import tracemalloc

from rdam.contracts import AggregateAnalysis, ResultOutcome
from rdam.frameworks import Technique
from rdam.rst.output import ErstOutput, RstOutput
from rdam.serialization import load, serialize, validate_native_result
from rdam._strict import canonical_json_bytes


@dataclass(frozen=True, slots=True)
class Measurement:
    elapsed_seconds: float
    peak_traced_bytes: int
    retained_traced_bytes: int


def measure[T](operation: Callable[[], T]) -> tuple[T, Measurement]:
    """Measure one operation with owned allocation tracing and explicit cleanup."""
    gc.collect()
    if tracemalloc.is_tracing():
        raise RuntimeError("measurement requires ownership of tracemalloc")
    tracemalloc.start()
    started = perf_counter()
    try:
        result = operation()
        elapsed = perf_counter() - started
        retained, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, Measurement(elapsed, peak, retained)


def measure_report(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    aggregate, envelope_load = measure(lambda: load(raw))
    if not isinstance(aggregate, AggregateAnalysis):
        raise ValueError("measurement requires a current aggregate")
    outcome = aggregate.outcome_for(Technique.RST)
    if not isinstance(outcome, ResultOutcome):
        raise ValueError("measurement requires a successful RST boundary")
    native, native_load = measure(lambda: validate_native_result(outcome.result))
    if not isinstance(native, (RstOutput, ErstOutput)):
        raise ValueError("measurement requires an RST or eRST native output")
    semantic = native.root.semantic
    parser = semantic.parser_result
    if parser is None:
        raise ValueError("measurement requires an analysed parser result")
    encoded, serialization = measure(lambda: serialize(aggregate))
    if serialize(load(encoded)) != encoded:
        raise ValueError("canonical round-trip changed the aggregate")
    # Warm parser anchors explicitly: current native validation avoids their
    # expansion. Measure only rebuilding the outer source view in this phase.
    warm_parser_anchor_count = len(parser.semantic.anchors)
    fresh = semantic.model_copy()
    anchors, source_resolution = measure(lambda: fresh.anchors)
    if anchors != semantic.anchors or fresh.analysed_document != semantic.analysed_document:
        raise ValueError("reconstructed source evidence differs from native loading")
    document = parser.semantic.analysed_document
    stored = parser.semantic.model_dump(mode="json")
    return {
        "measurement_version": "3.0.0",
        "artifact": str(path.resolve()),
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "memory_measure": "tracemalloc_allocations_excluding_preexisting_objects",
        "timing_condition": "tracemalloc_enabled_no_model_inference",
        "disk_bytes": len(raw),
        "canonical_bytes": len(encoded),
        "source_utf8_bytes": len(document.text.encode("utf-8")),
        "tokens": len(document.tokens),
        "edus": len(document.edus),
        "nodes": len(parser.analysis.nodes),
        "resolved_anchors": len(anchors),
        "warm_parser_anchors": warm_parser_anchor_count,
        "primary_inference_canonical_bytes": len(canonical_json_bytes(stored["primary_inference"])),
        "primary_inference_native_view_bytes": len(canonical_json_bytes(parser.semantic.primary_inference)),
        "analysed_document_canonical_bytes": len(canonical_json_bytes(stored["analysed_document"])),
        "phases": {
            "envelope_load": asdict(envelope_load),
            "native_validation_canonical_evidence": asdict(native_load),
            "aggregate_serialization": asdict(serialization),
            "source_view_rebuild_parser_anchors_warm": asdict(source_resolution),
        },
        "canonical_round_trip": "identical",
        "source_view_reconstruction": "identical",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(json.dumps(measure_report(args.report), ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
