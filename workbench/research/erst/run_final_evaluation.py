"""Execute the one-time untouched test/test2 evaluation for a frozen champion."""

import argparse
import hashlib
from pathlib import Path

from rdam.rst.contracts.erst import CorpusPartition
from workbench.research.erst.configuration import ExperimentConfigurationBundle
from workbench.research.erst.contracts import (
    ChampionManifest,
    EvaluationSetting,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    MandatoryExperimentSystem,
)
from workbench.research.erst.final_data import (
    FinalEvaluationCorpusPayload,
    prepare_final_evaluation_corpus,
    select_final_partition,
)
from workbench.research.erst.frozen_evaluation import FrozenEvaluationAdapter
from workbench.research.erst.runner import ExperimentRunRequest, ExperimentRunner
from workbench.research.erst.parity import compare_prediction_artifacts
from workbench.research.erst.selection import CpuMpsParityEvidence, write_final_evaluation_receipt


def _selected_receipt(experiment_root: Path, receipt_sha256: str) -> ExperimentRunReceipt:
    matches: list[ExperimentRunReceipt] = []
    for path in (experiment_root / "receipts").glob("*.json"):
        receipt = ExperimentRunReceipt.model_validate_json(path.read_text(encoding="utf-8"))
        if receipt.receipt_sha256 == receipt_sha256:
            matches.append(receipt)
    if len(matches) != 1:
        raise ValueError("champion selected checkpoint receipt did not resolve exactly once")
    return matches[0]


def run_final_evaluation(*, repository_root: Path, device: str) -> None:
    """Validate champion authority, open final corpus, and write one immutable receipt."""

    if device != "mps":
        raise ValueError("canonical final evaluation requires MPS plus measured CPU parity")
    experiment_root = repository_root / "experiments/erst/comparison"
    protocol = ExperimentProtocol.model_validate_json(
        (experiment_root / "experiment-protocol.json").read_text(encoding="utf-8")
    )
    champion = ChampionManifest.model_validate_json(
        (experiment_root / "champion-manifest.json").read_text(encoding="utf-8")
    )
    champion_source = _selected_receipt(
        experiment_root,
        champion.selected_checkpoint_receipt_sha256,
    )
    baseline_source = _selected_receipt(
        experiment_root,
        champion.baseline_checkpoint_receipt_sha256,
    )
    electra_source = _selected_receipt(
        experiment_root,
        champion.electra_checkpoint_receipt_sha256,
    )
    prepared = prepare_final_evaluation_corpus(
        corpus_root=repository_root / "corpora/gum-v12.1.0",
        cache_root=repository_root / "experiments/erst/final-candidate-cache-v1",
        protocol=protocol,
        champion=champion,
        verification_receipt_path=repository_root / "experiments/erst/corpus-verification.json",
        relation_inventory_path=repository_root / "config/erst/gum-v12.1.0-raw-relations.json",
    )
    configurations = ExperimentConfigurationBundle()
    adapters = {
        source.system: FrozenEvaluationAdapter(
            source_receipt=source,
            source_run_directory=experiment_root / "runs" / source.run_id,
            configurations=configurations,
            repository_root=repository_root,
        )
        for source in {item.system: item for item in (champion_source, baseline_source, electra_source)}.values()
    }
    runner = ExperimentRunner[FinalEvaluationCorpusPayload](protocol, experiment_root)
    receipts: dict[tuple[MandatoryExperimentSystem, CorpusPartition], ExperimentRunReceipt] = {}
    for source in {item.system: item for item in (champion_source, baseline_source, electra_source)}.values():
        for partition in (CorpusPartition.TEST, CorpusPartition.TEST2):
            partition_data = select_final_partition(prepared, partition)
            request = ExperimentRunRequest(
                run_id=f"final-{source.system.value}-{partition.value}",
                system=source.system,
                stage=ExperimentStage.FINAL_EVALUATION,
                seed=source.seed,
                setting=EvaluationSetting.GOLD_PRIMARY_GOLD_SIGNAL,
                partitions=(partition,),
                device=device,
            )
            receipt = runner.run(adapters[source.system], request, partition_data)
            if receipt.status != ExperimentRunStatus.SUCCEEDED:
                raise RuntimeError(
                    f"final {source.system.value}/{partition.value} evaluation did not succeed: "
                    f"{receipt.status.value}"
                )
            receipts[(source.system, partition)] = receipt
    cpu_receipts: dict[CorpusPartition, ExperimentRunReceipt] = {}
    for partition in (CorpusPartition.TEST, CorpusPartition.TEST2):
        partition_data = select_final_partition(prepared, partition)
        request = ExperimentRunRequest(
            run_id=f"parity-cpu-{champion.champion_system.value}-{partition.value}",
            system=champion.champion_system,
            stage=ExperimentStage.FINAL_EVALUATION,
            seed=champion_source.seed,
            setting=EvaluationSetting.GOLD_PRIMARY_GOLD_SIGNAL,
            partitions=(partition,),
            device="cpu",
        )
        receipt = runner.run(adapters[champion.champion_system], request, partition_data)
        if receipt.status != ExperimentRunStatus.SUCCEEDED:
            raise RuntimeError(f"CPU parity evaluation failed for {partition.value}")
        cpu_receipts[partition] = receipt
    parity_parts = tuple(
        compare_prediction_artifacts(
            cpu_path=experiment_root / "runs" / cpu_receipts[partition].run_id / "predictions.json",
            mps_path=(
                experiment_root
                / "runs"
                / receipts[(champion.champion_system, partition)].run_id
                / "predictions.json"
            ),
            cpu_receipt_sha256=cpu_receipts[partition].receipt_sha256,
            mps_receipt_sha256=receipts[(champion.champion_system, partition)].receipt_sha256,
            tolerance=protocol.thresholds.cpu_mps_probability_tolerance,
        )
        for partition in (CorpusPartition.TEST, CorpusPartition.TEST2)
    )
    parity = CpuMpsParityEvidence(
        cpu_receipt_sha256=hashlib.sha256(
            "".join(item.cpu_receipt_sha256 for item in parity_parts).encode()
        ).hexdigest(),
        mps_receipt_sha256=hashlib.sha256(
            "".join(item.mps_receipt_sha256 for item in parity_parts).encode()
        ).hexdigest(),
        max_probability_delta=max(item.max_probability_delta for item in parity_parts),
        decoded_graphs_equal=all(item.decoded_graphs_equal for item in parity_parts),
        tolerance=protocol.thresholds.cpu_mps_probability_tolerance,
    )
    parity_path = experiment_root / "cpu-mps-parity.json"
    if parity_path.exists():
        raise RuntimeError("CPU/MPS parity evidence already exists")
    parity_path.write_text(parity.model_dump_json(indent=2) + "\n", encoding="utf-8")
    final = write_final_evaluation_receipt(
        path=experiment_root / "final-evaluation.json",
        protocol=protocol,
        champion=champion,
        test_receipts=((receipts[(champion.champion_system, CorpusPartition.TEST)]),),
        test2_receipts=((receipts[(champion.champion_system, CorpusPartition.TEST2)]),),
        baseline_test_receipts=((receipts[(champion.baseline_system, CorpusPartition.TEST)]),),
        baseline_test2_receipts=((receipts[(champion.baseline_system, CorpusPartition.TEST2)]),),
        electra_test_receipts=((receipts[(MandatoryExperimentSystem.ELECTRA, CorpusPartition.TEST)]),),
        electra_test2_receipts=((receipts[(MandatoryExperimentSystem.ELECTRA, CorpusPartition.TEST2)]),),
        longest_document_completed=True,
        candidate_truncation_occurred=False,
        out_of_memory_occurred=False,
    )
    print(f"final_evaluation_sha256={final.receipt_sha256}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--device", choices=("cpu", "mps"), default="mps")
    arguments = parser.parse_args()
    run_final_evaluation(
        repository_root=arguments.repository_root.resolve(),
        device=arguments.device,
    )


if __name__ == "__main__":
    main()
