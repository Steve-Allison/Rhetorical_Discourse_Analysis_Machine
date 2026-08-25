"""Complete screening disposition, finalist seeds, statistics, and dev champion freeze."""

import argparse
import json
from pathlib import Path

from isanlp_rst.contracts.erst import CorpusPartition, PrivateCorpusVerificationReceipt
from research_harness.erst.configuration import ExperimentConfigurationBundle
from research_harness.erst.ablations import (
    AblationAdapter,
    AblationResult,
    canonical_ablation_plan,
)
from research_harness.erst.contracts import (
    AblationName,
    EvaluationSetting,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    MandatoryExperimentSystem,
)
from research_harness.erst.data import ScreeningCorpusPayload, prepare_screening_corpus
from research_harness.erst.protocol import build_experiment_protocol
from research_harness.erst.run_screening import build_adapter
from research_harness.erst.runner import (
    ExperimentIndexStore,
    ExperimentRunRequest,
    ExperimentRunner,
)
from research_harness.erst.selection import freeze_champion, validate_screening_completeness
from research_harness.erst.statistics import compare_systems, holm_correct
from research_harness.erst.technology import TechnologyMatrix

_REFERENCE_BASELINES = {
    MandatoryExperimentSystem.EXISTING_DUAL_ENCODER,
    MandatoryExperimentSystem.STRUCTURAL_ONLY,
    MandatoryExperimentSystem.TEXT_ONLY,
    MandatoryExperimentSystem.ELECTRA,
    MandatoryExperimentSystem.SIGNAL_RULE,
}


def _load_receipts(experiment_root: Path, protocol: ExperimentProtocol) -> tuple[ExperimentRunReceipt, ...]:
    index = ExperimentIndexStore(experiment_root, protocol.protocol_sha256).load_verified()
    return tuple(
        ExperimentRunReceipt.model_validate_json(
            (experiment_root / entry.receipt_path).read_text(encoding="utf-8")
        )
        for entry in index.entries
    )


def _mean_full(receipts: tuple[ExperimentRunReceipt, ...]) -> float:
    metrics = tuple(receipt.metrics for receipt in receipts if receipt.metrics is not None)
    if not metrics or len(metrics) != len(receipts):
        raise ValueError("mean Full requires successful metric-bearing receipts")
    return sum(metric.full_f for metric in metrics) / len(metrics)


def _write_frozen(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"frozen comparison artifact differs: {path.name}")
        return
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    if temporary.exists():
        raise RuntimeError(f"stale comparison atomic-write file exists: {temporary.name}")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _successful_screening(
    receipts: tuple[ExperimentRunReceipt, ...],
) -> dict[MandatoryExperimentSystem, tuple[ExperimentRunReceipt, ...]]:
    return {
        system: tuple(
            receipt
            for receipt in receipts
            if receipt.system == system
            and receipt.stage == ExperimentStage.SCREENING
            and receipt.status == ExperimentRunStatus.SUCCEEDED
        )
        for system in MandatoryExperimentSystem
    }


def run_comparison(*, repository_root: Path, device: str) -> None:
    """Advance governed screening evidence through dev-only champion selection."""

    experiment_root = repository_root / "experiments/erst/comparison"
    prepared = prepare_screening_corpus(
        corpus_root=repository_root / "corpora/gum-v12.1.0",
        verification_receipt_path=repository_root / "experiments/erst/corpus-verification.json",
        relation_inventory_path=repository_root / "config/erst/gum-v12.1.0-raw-relations.json",
        cache_root=repository_root / "experiments/erst/candidate-cache-v1",
    )
    matrix = TechnologyMatrix.model_validate_json(
        (repository_root / "research_harness/erst/technology-matrix.json").read_text(encoding="utf-8")
    )
    configurations = ExperimentConfigurationBundle()
    verification = PrivateCorpusVerificationReceipt.model_validate_json(
        (repository_root / "experiments/erst/corpus-verification.json").read_text(encoding="utf-8")
    )
    protocol = build_experiment_protocol(
        matrix=matrix,
        configurations=configurations,
        verification=verification,
        prepared_data=prepared,
        repository_root=repository_root,
    )
    persisted = ExperimentProtocol.model_validate_json(
        (experiment_root / "experiment-protocol.json").read_text(encoding="utf-8")
    )
    if persisted != protocol:
        raise ValueError("comparison source/environment differs from the frozen screening protocol")
    receipts = _load_receipts(experiment_root, protocol)
    validate_screening_completeness(protocol, receipts)
    screening = _successful_screening(receipts)
    complete_screening = {
        system: system_receipts
        for system, system_receipts in screening.items()
        if len(system_receipts) == len(protocol.screening_seeds)
    }
    if not complete_screening:
        raise ValueError("no mandatory system completed every screening seed")
    leader = max(complete_screening, key=lambda system: (_mean_full(complete_screening[system]), system.value))
    baseline_candidates = {
        system: values
        for system, values in complete_screening.items()
        if system in _REFERENCE_BASELINES
    }
    if not baseline_candidates:
        raise ValueError("no reference baseline completed screening")
    baseline = max(
        baseline_candidates,
        key=lambda system: (_mean_full(baseline_candidates[system]), system.value),
    )
    leading_nonbaseline = max(
        (system for system in complete_screening if system not in _REFERENCE_BASELINES),
        key=lambda system: (_mean_full(complete_screening[system]), system.value),
        default=None,
    )
    if leading_nonbaseline is None:
        raise ValueError("no research architecture completed screening")
    leading_score = _mean_full(complete_screening[leader])
    finalists = {
        system
        for system, values in complete_screening.items()
        if leading_score - _mean_full(values) <= protocol.finalist_delta
    }
    finalists.update((baseline, leading_nonbaseline))
    finalists.add(MandatoryExperimentSystem.ELECTRA)
    runner = ExperimentRunner[ScreeningCorpusPayload](protocol, experiment_root)
    existing = {(receipt.system, receipt.stage, receipt.seed) for receipt in receipts}
    for system in sorted(finalists, key=lambda item: item.value):
        adapter = build_adapter(
            system=system,
            configurations=configurations,
            protocol=protocol,
            repository_root=repository_root,
        )
        for seed in protocol.finalist_seeds:
            identity = (system, ExperimentStage.FINALIST, seed)
            if identity in existing:
                continue
            request = ExperimentRunRequest(
                run_id=f"finalist-{system.value}-seed-{seed}",
                system=system,
                stage=ExperimentStage.FINALIST,
                seed=seed,
                setting=EvaluationSetting.GOLD_PRIMARY_GOLD_SIGNAL,
                partitions=(CorpusPartition.TRAIN, CorpusPartition.DEV),
                device=device,
            )
            runner.run(adapter, request, prepared)
    receipts = _load_receipts(experiment_root, protocol)
    finalist_successes = {
        system: tuple(
            receipt
            for receipt in receipts
            if receipt.system == system
            and receipt.stage == ExperimentStage.FINALIST
            and receipt.status == ExperimentRunStatus.SUCCEEDED
        )
        for system in finalists
    }
    required_seeds = set(protocol.finalist_seeds)
    incomplete = {
        system.value: sorted(
            required_seeds.difference(receipt.seed for receipt in system_receipts)
        )
        for system, system_receipts in finalist_successes.items()
        if {receipt.seed for receipt in system_receipts} != required_seeds
    }
    if incomplete:
        raise ValueError(f"finalist runs are incomplete or unsuccessful: {incomplete}")
    baseline_receipts = finalist_successes[baseline]
    comparison_candidates = tuple(
        system for system in finalists if system not in _REFERENCE_BASELINES
    )
    comparisons = holm_correct(
        tuple(
            compare_systems(
                candidate_receipts=finalist_successes[system],
                baseline_receipts=baseline_receipts,
                bootstrap_seed=protocol.bootstrap_seed,
            )
            for system in comparison_candidates
        )
    )
    comparison_path = experiment_root / "statistical-comparisons.json"
    _write_frozen(
        comparison_path,
        json.dumps(
            [comparison.model_dump(mode="json") for comparison in comparisons],
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    champion_system = max(
        comparison_candidates,
        key=lambda system: (_mean_full(finalist_successes[system]), system.value),
    )
    champion_comparison = next(
        comparison for comparison in comparisons if comparison.candidate_system == champion_system
    )
    config_sha256 = next(
        specification.config_sha256
        for specification in protocol.systems
        if specification.system == champion_system
    )
    champion = freeze_champion(
        protocol=protocol,
        system=champion_system,
        selected_config_sha256=config_sha256,
        finalist_receipts=finalist_successes[champion_system],
        baseline_receipts=baseline_receipts,
        electra_receipts=finalist_successes[MandatoryExperimentSystem.ELECTRA],
        comparison=champion_comparison,
    )
    champion_path = experiment_root / "champion-manifest.json"
    _write_frozen(champion_path, champion.model_dump_json(indent=2) + "\n")
    ablation_plan = canonical_ablation_plan(
        protocol_sha256=protocol.protocol_sha256,
        champion_system=champion_system,
    )
    _write_frozen(
        experiment_root / "ablation-plan.json",
        ablation_plan.model_dump_json(indent=2) + "\n",
    )
    base_adapter = build_adapter(
        system=champion_system,
        configurations=configurations,
        protocol=protocol,
        repository_root=repository_root,
    )
    ablation_adapter = AblationAdapter(base_adapter)
    existing_ablations = {
        (receipt.ablation, receipt.seed)
        for receipt in receipts
        if receipt.system == champion_system and receipt.stage == ExperimentStage.ABLATION
    }
    for ablation in AblationName:
        for seed in protocol.finalist_seeds:
            if (ablation, seed) in existing_ablations:
                continue
            runner.run(
                ablation_adapter,
                ExperimentRunRequest(
                    run_id=f"ablation-{champion_system.value}-{ablation.value}-seed-{seed}",
                    system=champion_system,
                    stage=ExperimentStage.ABLATION,
                    ablation=ablation,
                    seed=seed,
                    setting=EvaluationSetting.GOLD_PRIMARY_GOLD_SIGNAL,
                    partitions=(CorpusPartition.TRAIN, CorpusPartition.DEV),
                    device=device,
                ),
                prepared,
            )
    receipts = _load_receipts(experiment_root, protocol)
    unablated_mean = _mean_full(finalist_successes[champion_system])
    ablation_results: list[AblationResult] = []
    for ablation in AblationName:
        family = tuple(
            receipt
            for receipt in receipts
            if receipt.system == champion_system
            and receipt.stage == ExperimentStage.ABLATION
            and receipt.ablation == ablation
            and receipt.status == ExperimentRunStatus.SUCCEEDED
        )
        if {receipt.seed for receipt in family} != set(protocol.finalist_seeds):
            raise ValueError(f"ablation did not complete every seed: {ablation.value}")
        mean_full = _mean_full(family)
        ablation_results.append(
            AblationResult(
                protocol_sha256=protocol.protocol_sha256,
                plan_sha256=ablation_plan.plan_sha256,
                name=ablation,
                run_receipts=tuple(receipt.receipt_sha256 for receipt in family),
                mean_full_f=mean_full,
                delta_from_unablated=mean_full - unablated_mean,
            )
        )
    _write_frozen(
        experiment_root / "ablation-results.json",
        json.dumps(
            [result.model_dump(mode="json") for result in ablation_results],
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    print(
        f"champion={champion.champion_system.value} champion_sha256={champion.champion_sha256} "
        f"baseline={baseline.value}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--device", choices=("cpu", "mps"), default="mps")
    arguments = parser.parse_args()
    run_comparison(repository_root=arguments.repository_root.resolve(), device=arguments.device)


if __name__ == "__main__":
    main()
