"""Derive the fail-closed checkpoint selection decision from completed local evidence."""

import argparse
import json
from pathlib import Path

from workbench.research.erst.calibration import TemperatureCalibration
from workbench.research.erst.configuration import ExperimentConfigurationBundle
from workbench.research.erst.contracts import (
    ChampionManifest,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    FinalEvaluationReceipt,
    MandatoryExperimentSystem,
    StatisticalComparison,
)
from workbench.research.erst.frozen_evaluation import FrozenEvaluationAdapter
from workbench.research.erst.runner import ExperimentIndexStore
from workbench.research.erst.selection import (
    CheckpointSelectionCandidateManifest,
    CpuMpsParityEvidence,
    SelectionMeasurements,
    TiedSystemEfficiencyEvidence,
    build_selection_decision,
)
from workbench.research.erst.systems.common import ScorerEvidence


def _load_receipts(root: Path, protocol: ExperimentProtocol) -> dict[str, ExperimentRunReceipt]:
    index = ExperimentIndexStore(root, protocol.protocol_sha256).load_verified()
    receipts = tuple(
        ExperimentRunReceipt.model_validate_json(
            (root / entry.receipt_path).read_text(encoding="utf-8")
        )
        for entry in index.entries
    )
    return {receipt.receipt_sha256: receipt for receipt in receipts}


def _mean_full(receipts: tuple[ExperimentRunReceipt, ...]) -> float:
    if not receipts or any(receipt.metrics is None for receipt in receipts):
        raise ValueError("selection mean requires complete metric-bearing receipts")
    return sum(receipt.metrics.full_f for receipt in receipts if receipt.metrics is not None) / len(receipts)


def _aggregate_final(
    root: Path,
    receipts: tuple[ExperimentRunReceipt, ...],
) -> dict[str, float]:
    evidence = tuple(
        ScorerEvidence.model_validate_json(
            (root / "runs" / receipt.run_id / "scorer-output.json").read_text(encoding="utf-8")
        )
        for receipt in receipts
    )
    gold = sum(item.gold_count for item in evidence)
    predicted = sum(item.predicted_count for item in evidence)

    def f_score(matched: int) -> float:
        precision = matched / predicted if predicted else (1.0 if gold == 0 else 0.0)
        recall = matched / gold if gold else (1.0 if predicted == 0 else 0.0)
        return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0

    candidate_total = sum(receipt.candidate_count for receipt in receipts)
    if candidate_total <= 0:
        raise ValueError("final aggregate has zero candidates")
    return {
        "span_f": f_score(sum(item.matched_span for item in evidence)),
        "direction_f": f_score(sum(item.matched_direction for item in evidence)),
        "relation_f": f_score(sum(item.matched_relation for item in evidence)),
        "full_f": f_score(sum(item.matched_full for item in evidence)),
        "ece": sum(item.ece * receipt.candidate_count for item, receipt in zip(evidence, receipts, strict=True))
        / candidate_total,
        "brier": sum(
            item.brier * receipt.candidate_count
            for item, receipt in zip(evidence, receipts, strict=True)
        )
        / candidate_total,
    }


def _write_new(path: Path, content: str) -> None:
    if path.exists() or path.with_suffix(f"{path.suffix}.tmp").exists():
        raise RuntimeError(f"selection artifact already exists: {path.name}")
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def finalize_selection(*, repository_root: Path) -> None:
    root = repository_root / "experiments/erst/comparison"
    protocol = ExperimentProtocol.model_validate_json(
        (root / "experiment-protocol.json").read_text(encoding="utf-8")
    )
    champion = ChampionManifest.model_validate_json(
        (root / "champion-manifest.json").read_text(encoding="utf-8")
    )
    final = FinalEvaluationReceipt.model_validate_json(
        (root / "final-evaluation.json").read_text(encoding="utf-8")
    )
    parity = CpuMpsParityEvidence.model_validate_json(
        (root / "cpu-mps-parity.json").read_text(encoding="utf-8")
    )
    comparisons_payload = json.loads((root / "statistical-comparisons.json").read_text(encoding="utf-8"))
    comparisons = tuple(StatisticalComparison.model_validate(item) for item in comparisons_payload)
    comparison = next(
        item for item in comparisons if item.candidate_system == champion.champion_system
    )
    receipts_by_hash = _load_receipts(root, protocol)

    def resolve(hashes: tuple[str, ...]) -> tuple[ExperimentRunReceipt, ...]:
        try:
            return tuple(receipts_by_hash[item] for item in hashes)
        except KeyError as error:
            raise ValueError("selection evidence references an unknown run receipt") from error

    champion_dev = resolve(champion.dev_run_receipts)
    baseline_dev = resolve(champion.baseline_dev_run_receipts)
    champion_test = resolve(final.test_run_receipts + final.test2_run_receipts)
    baseline_test = resolve(final.baseline_test_run_receipts + final.baseline_test2_run_receipts)
    electra_test = resolve(final.electra_test_run_receipts + final.electra_test2_run_receipts)
    champion_metrics = _aggregate_final(root, champion_test)
    baseline_metrics = _aggregate_final(root, baseline_test)
    measurements = SelectionMeasurements(
        champion_dev_full_f=_mean_full(champion_dev),
        baseline_dev_full_f=_mean_full(baseline_dev),
        champion_test_span_f=champion_metrics["span_f"],
        champion_test_direction_f=champion_metrics["direction_f"],
        champion_test_relation_f=champion_metrics["relation_f"],
        champion_test_full_f=champion_metrics["full_f"],
        champion_test_ece=champion_metrics["ece"],
        champion_test_brier=champion_metrics["brier"],
        baseline_test_span_f=baseline_metrics["span_f"],
        baseline_test_direction_f=baseline_metrics["direction_f"],
        baseline_test_relation_f=baseline_metrics["relation_f"],
        baseline_test_full_f=baseline_metrics["full_f"],
        baseline_test_brier=baseline_metrics["brier"],
        champion_peak_rss_bytes=max(
            receipt.resources.peak_rss_bytes
            for receipt in champion_test
            if receipt.resources is not None
        ),
        champion_mps_p95_latency_ms=max(
            receipt.resources.p95_latency_ms
            for receipt in champion_test
            if receipt.resources is not None
        ),
        electra_mps_p95_latency_ms=max(
            receipt.resources.p95_latency_ms
            for receipt in electra_test
            if receipt.resources is not None
        ),
    )
    finalist_receipts = tuple(
        receipt
        for receipt in receipts_by_hash.values()
        if receipt.stage == ExperimentStage.FINALIST
        and receipt.status == ExperimentRunStatus.SUCCEEDED
    )
    families = {
        system: tuple(receipt for receipt in finalist_receipts if receipt.system == system)
        for system in MandatoryExperimentSystem
    }
    tied = tuple(
        system
        for system, family in families.items()
        if len(family) == len(protocol.finalist_seeds)
        and abs(_mean_full(family) - measurements.champion_dev_full_f)
        <= protocol.thresholds.efficiency_tie_full_delta
    )
    configurations = ExperimentConfigurationBundle()
    efficiency_values: dict[MandatoryExperimentSystem, tuple[float, int]] = {}
    for system in tied:
        family = families[system]
        selected = max(
            family,
            key=lambda receipt: (
                receipt.metrics.full_f if receipt.metrics is not None else -1.0,
                -receipt.seed,
            ),
        )
        adapter = FrozenEvaluationAdapter(
            source_receipt=selected,
            source_run_directory=root / "runs" / selected.run_id,
            configurations=configurations,
            repository_root=repository_root,
        )
        latencies = tuple(
            receipt.resources.p95_latency_ms
            for receipt in family
            if receipt.resources is not None
        )
        if len(latencies) != len(family):
            raise ValueError("tied finalist family lacks resource evidence")
        efficiency_values[system] = (
            sum(latencies) / len(latencies),
            adapter.checkpoint_path().stat().st_size,
        )
    champion_efficiency = efficiency_values[champion.champion_system]
    efficiency = TiedSystemEfficiencyEvidence(
        selected_system=champion.champion_system,
        tied_systems=tied,
        selected_is_fastest_and_smallest=(
            champion_efficiency[0] <= min(value[0] for value in efficiency_values.values())
            and champion_efficiency[1] <= min(value[1] for value in efficiency_values.values())
        ),
    )
    source_receipt = receipts_by_hash[champion.selected_checkpoint_receipt_sha256]
    if source_receipt.checkpoint_sha256 is None:
        raise ValueError("selected source receipt lacks checkpoint evidence")
    calibration = TemperatureCalibration.model_validate_json(
        (root / "runs" / source_receipt.run_id / "calibration.json").read_text(encoding="utf-8")
    )
    candidate_manifest = CheckpointSelectionCandidateManifest(
        protocol_sha256=protocol.protocol_sha256,
        champion_sha256=champion.champion_sha256,
        system=champion.champion_system,
        source_receipt_sha256=source_receipt.receipt_sha256,
        source_checkpoint_sha256=source_receipt.checkpoint_sha256,
        calibration_sha256=calibration.calibration_sha256,
        raw_relation_inventory_sha256=protocol.raw_relation_inventory_sha256,
    )
    decision = build_selection_decision(
        protocol=protocol,
        champion=champion,
        final_evaluation=final,
        comparison=comparison,
        measurements=measurements,
        parity=parity,
        efficiency=efficiency,
        canonical_checkpoint_manifest_sha256=candidate_manifest.manifest_sha256,
    )
    _write_new(root / "selection-measurements.json", measurements.model_dump_json(indent=2) + "\n")
    _write_new(root / "tied-efficiency.json", efficiency.model_dump_json(indent=2) + "\n")
    _write_new(
        root / "checkpoint-selection-candidate.json",
        candidate_manifest.model_dump_json(indent=2) + "\n",
    )
    _write_new(root / "selection-decision.json", decision.model_dump_json(indent=2) + "\n")
    print(f"outcome={decision.outcome.value} decision_sha256={decision.decision_sha256}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    finalize_selection(repository_root=arguments.repository_root.resolve())


if __name__ == "__main__":
    main()
