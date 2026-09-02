"""Run one mandatory screening system/seed through the isolated shared harness."""

import argparse
from pathlib import Path

from rdam.rst.contracts.erst import CorpusPartition, PrivateCorpusVerificationReceipt
from workbench.research.erst.configuration import ExperimentConfigurationBundle
from workbench.research.erst.contracts import (
    EvaluationSetting,
    ExperimentProtocol,
    ExperimentStage,
    MandatoryExperimentSystem,
)
from workbench.research.erst.data import ScreeningCorpusPayload, prepare_screening_corpus
from workbench.research.erst.protocol import build_experiment_protocol, freeze_protocol_artifacts
from workbench.research.erst.runner import (
    ExperimentRunRequest,
    ExperimentRunner,
    ExperimentSystemAdapter,
)
from workbench.research.erst.systems.cross_encoder import CrossEncoderAdapter
from workbench.research.erst.systems.dual_encoder import DualEncoderAdapter
from workbench.research.erst.systems.generative_decoder import GenerativeDecoderAdapter
from workbench.research.erst.systems.graph_attention import GraphAttentionAdapter
from workbench.research.erst.systems.hierarchical_adapter import HierarchicalAdapter
from workbench.research.erst.systems.signal_rule import SignalRuleAdapter
from workbench.research.erst.systems.structural import StructuralOnlyAdapter
from workbench.research.erst.technology import TechnologyMatrix


def _config_sha256(protocol: ExperimentProtocol, system: MandatoryExperimentSystem) -> str:
    return next(
        specification.config_sha256
        for specification in protocol.systems
        if specification.system == system
    )


def build_adapter(
    *,
    system: MandatoryExperimentSystem,
    configurations: ExperimentConfigurationBundle,
    protocol: ExperimentProtocol,
    repository_root: Path,
) -> ExperimentSystemAdapter[ScreeningCorpusPayload]:
    config_sha256 = _config_sha256(protocol, system)
    if system == MandatoryExperimentSystem.EXISTING_DUAL_ENCODER:
        return DualEncoderAdapter(
            config=configurations.existing_dual_encoder,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.STRUCTURAL_ONLY:
        return StructuralOnlyAdapter(
            config=configurations.structural_only,
            architecture_config_sha256=config_sha256,
        )
    if system == MandatoryExperimentSystem.TEXT_ONLY:
        return CrossEncoderAdapter(
            system=system,
            config=configurations.text_only,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.ELECTRA:
        return CrossEncoderAdapter(
            system=system,
            config=configurations.electra,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.SIGNAL_RULE:
        return SignalRuleAdapter(
            config=configurations.signal_rule,
            architecture_config_sha256=config_sha256,
        )
    if system == MandatoryExperimentSystem.MODERNBERT_BASE:
        return CrossEncoderAdapter(
            system=system,
            config=configurations.modernbert_base,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.MODERNBERT_LARGE:
        return CrossEncoderAdapter(
            system=system,
            config=configurations.modernbert_large,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.XLM_R_HIDAC:
        return HierarchicalAdapter(
            config=configurations.xlm_r_hidac,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.QWEN3_DEDISCO:
        return GenerativeDecoderAdapter(
            config=configurations.qwen3_dedisco,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    if system == MandatoryExperimentSystem.EDGE_FEATURED_GAT:
        return GraphAttentionAdapter(
            config=configurations.edge_featured_gat,
            architecture_config_sha256=config_sha256,
            repository_root=repository_root,
        )
    raise ValueError(f"screening adapter is not implemented yet: {system}")


def run_screening(
    *,
    repository_root: Path,
    system: MandatoryExperimentSystem,
    seed: int,
    device: str,
) -> None:
    """Load governed inputs, verify the frozen protocol, and execute one run."""

    experiment_root = repository_root / "workbench/experiments/erst/comparison"
    prepared = prepare_screening_corpus(
        corpus_root=repository_root / "workbench/corpora/gum-v12.1.0",
        verification_receipt_path=repository_root / "workbench/experiments/erst/corpus-verification.json",
        relation_inventory_path=repository_root / "config/erst/gum-v12.1.0-raw-relations.json",
        cache_root=repository_root / "workbench/experiments/erst/candidate-cache-v1",
    )
    matrix = TechnologyMatrix.model_validate_json(
        (repository_root / "workbench/research/erst/technology-matrix.json").read_text(encoding="utf-8")
    )
    configurations = ExperimentConfigurationBundle()
    verification = PrivateCorpusVerificationReceipt.model_validate_json(
        (repository_root / "workbench/experiments/erst/corpus-verification.json").read_text(encoding="utf-8")
    )
    protocol = build_experiment_protocol(
        matrix=matrix,
        configurations=configurations,
        verification=verification,
        prepared_data=prepared,
        repository_root=repository_root,
    )
    protocol_path = experiment_root / "experiment-protocol.json"
    if protocol_path.exists():
        persisted = ExperimentProtocol.model_validate_json(protocol_path.read_text(encoding="utf-8"))
        if persisted != protocol:
            raise ValueError("persisted experiment protocol differs from current governed inputs")
    else:
        freeze_protocol_artifacts(
            protocol=protocol,
            configurations=configurations,
            output_root=experiment_root,
        )
    adapter = build_adapter(
        system=system,
        configurations=configurations,
        protocol=protocol,
        repository_root=repository_root,
    )
    request = ExperimentRunRequest(
        run_id=f"screening-{system.value}-seed-{seed}",
        system=system,
        stage=ExperimentStage.SCREENING,
        seed=seed,
        setting=EvaluationSetting.GOLD_PRIMARY_GOLD_SIGNAL,
        partitions=(CorpusPartition.TRAIN, CorpusPartition.DEV),
        device=device,
    )
    receipt = ExperimentRunner[ScreeningCorpusPayload](protocol, experiment_root).run(
        adapter,
        request,
        prepared,
    )
    metric = receipt.metrics.full_f if receipt.metrics is not None else None
    failure_type = receipt.failure.failure_type if receipt.failure is not None else None
    print(
        f"run_id={receipt.run_id} status={receipt.status.value} "
        f"full_f={metric} failure_type={failure_type} receipt_sha256={receipt.receipt_sha256}"
    )


def main() -> None:
    """CLI entry point for one system/seed run."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--system", type=MandatoryExperimentSystem, required=True)
    parser.add_argument("--seed", type=int, choices=(17, 42, 73), required=True)
    parser.add_argument("--device", choices=("cpu", "mps"), default="mps")
    arguments = parser.parse_args()
    run_screening(
        repository_root=arguments.repository_root.resolve(),
        system=arguments.system,
        seed=arguments.seed,
        device=arguments.device,
    )


if __name__ == "__main__":
    main()


__all__ = ["build_adapter", "run_screening"]
