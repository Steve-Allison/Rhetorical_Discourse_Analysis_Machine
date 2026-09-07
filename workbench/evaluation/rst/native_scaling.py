"""Measure real inference and persistence over normalized, explicitly subdivided input.

The repeated text is synthetic and supplies no accuracy evidence. The unit budget
is an explicit experiment setting, not a claimed model or machine capacity.
Traced allocations exclude native tensor memory and the already loaded model.
"""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from rdam.ingest import AnalysedOutcome, ProductionIngestor, SourceArtifact, load_contract, serialize_contract
from rdam.ingest.policy import DEFAULT_PREPARATION_POLICY
from rdam.rst.model_loading import ParserCapacity
from rdam.rst.parser import Parser
from workbench.evaluation.rst.persistence import measure


class BudgetedParser(Parser):
    planning_budget: int | None = None

    @property
    def analysis_capacity(self) -> ParserCapacity:
        return ParserCapacity(
            unit="edu_count", maximum=self.planning_budget, source="experiment/explicit-edu-planning-budget",
        )


def run_case(parser: BudgetedParser, size: int) -> dict[str, object]:
    edus = tuple("Cafe\u0301 patrons left." for _ in range(size))
    source = SourceArtifact.from_edus(edus, source_name=f"synthetic-normalized-{size}-edus")
    policy = DEFAULT_PREPARATION_POLICY.model_copy(update={"normalization": "unicode_nfc", "semantic_digest": None})
    outcome, inference = measure(lambda: ProductionIngestor(parser=parser).analyse(source, policy=policy))
    if not isinstance(outcome, AnalysedOutcome) or outcome.semantic.parser_result is None:
        raise ValueError("real inference did not produce a complete analysed outcome")
    result = outcome.semantic.parser_result
    preparation = outcome.semantic.preparation.semantic
    if len(result.analysed_document.edus) != size or result.analysed_document.text != " ".join(
        "Café patrons left." for _ in range(size)
    ):
        raise ValueError("normalized inference did not preserve the supplied EDU substrate")
    if not preparation.transformations:
        raise ValueError("the experiment did not exercise source transformations")
    encoded, serialization = measure(lambda: serialize_contract(outcome))
    restored, loading = measure(lambda: load_contract(encoded))
    if not isinstance(restored, AnalysedOutcome) or restored.semantic.parser_result != result:
        raise ValueError("native parser evidence differs after stored round-trip")
    if serialize_contract(restored) != encoded:
        raise ValueError("canonical round-trip changed the stored result")
    source_view, resolution = measure(lambda: restored.semantic.anchors)
    if source_view != outcome.semantic.anchors:
        raise ValueError("original-source anchors differ after round-trip")
    return {
        "edus": size, "source_identity": source.summary().source_id,
        "normalized_source_characters": len(result.analysed_document.text),
        "analysis_units": len(preparation.analysis_plan.units),
        "transformations": len(preparation.transformations),
        "canonical_bytes": len(encoded), "canonical_sha256": sha256(encoded).hexdigest(),
        "inference_and_assembly": asdict(inference), "serialization": asdict(serialization),
        "native_loading": asdict(loading), "expanded_source_view": asdict(resolution),
        "canonical_round_trip": "identical", "native_evidence": "identical", "source_anchors": "identical",
    }


def main() -> None:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--model-store", type=Path, required=True)
    arguments.add_argument("--release-id", required=True)
    arguments.add_argument("--device", required=True)
    arguments.add_argument("--unit-edus", type=int, required=True)
    arguments.add_argument("--sizes", type=int, nargs="+", required=True)
    args = arguments.parse_args()
    if args.unit_edus <= 1 or any(size <= 0 for size in args.sizes):
        arguments.error("unit-edus must exceed one and every size must be positive")
    parser = BudgetedParser.from_model_release(args.model_store, args.release_id, device=args.device)
    if not isinstance(parser, BudgetedParser):
        raise TypeError("release construction did not preserve the experimental parser class")
    parser.planning_budget = args.unit_edus
    identity = parser.model_release_identity
    if identity is None:
        raise ValueError("experiment requires an identified released model")
    result = {
        "measurement_version": "1.0.0",
        "source_kind": "synthetic_presegmented_unicode_with_real_inference",
        "source_edu_before_normalization": "Cafe\u0301 patrons left.",
        "normalization": "NFC", "model": identity.model_dump(mode="json"), "device": args.device,
        "unit_edus": args.unit_edus,
        "memory_measure": "tracemalloc_allocations_excluding_loaded_model_and_native_tensors",
        "timing_condition": "tracemalloc_enabled_other_processes_not_controlled",
        "measurement_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases": [run_case(parser, size) for size in args.sizes],
    }
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))


if __name__ == "__main__":
    main()
