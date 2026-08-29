"""Regression tests for calibration, statistics, resources, and system constraints."""

from dataclasses import replace
from datetime import UTC, datetime

import numpy as np
import pytest

from isanlp_rst.contracts.analysis import PrimaryRelationEdge, RstAnalysis, RstNode
from isanlp_rst.contracts.enums import NodeKindEnum, NuclearityPatternEnum, OutputFormalismEnum
from isanlp_rst.contracts.erst import CorpusPartition
from workbench.research.erst.calibration import apply_temperature, fit_temperature
from workbench.research.erst.contracts import (
    DocumentScore,
    EvaluationSetting,
    ExperimentMetrics,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    ExperimentSystemSpec,
    MandatoryExperimentSystem,
    ResourceEvidence,
)
from workbench.research.erst.resources import MpsMemorySampler
from workbench.research.erst.selection import validate_screening_completeness
from workbench.research.erst.statistics import compare_systems, holm_correct
from workbench.research.erst.systems.generative_decoder import _label_tokens
from workbench.research.erst.systems.graph_attention import _validate_complete_primary_tree

_NOW = datetime(2026, 8, 25, 12, tzinfo=UTC)


def _protocol() -> ExperimentProtocol:
    return ExperimentProtocol(
        corpus_revision="b" * 40,
        environment_lock_sha256="e" * 64,
        harness_source_sha256="0" * 64,
        production_source_sha256="f" * 64,
        corpus_receipt_sha256="a" * 64,
        split_manifest_sha256="1" * 64,
        candidate_schema_sha256="2" * 64,
        signal_detector_sha256="3" * 64,
        raw_relation_inventory_sha256="4" * 64,
        ontology_mapping_sha256="5" * 64,
        decoder_config_sha256="6" * 64,
        systems=tuple(
            ExperimentSystemSpec(
                system=system,
                implementation=f"workbench.research.erst.systems.{system.value}",
                model_license="test",
                config_sha256=f"{index:x}" * 64,
            )
            for index, system in enumerate(MandatoryExperimentSystem, start=1)
        ),
    )


def _resource() -> ResourceEvidence:
    return ResourceEvidence(
        machine="Mac",
        operating_system="macOS",
        processor="Apple Silicon",
        physical_memory_bytes=48 * 1024**3,
        device="cpu",
        torch_version="2.13.0",
        transformers_version="5.15.1",
        thread_count=1,
        p50_latency_ms=1.0,
        p95_latency_ms=2.0,
        peak_rss_bytes=1024,
    )


def _receipt(
    protocol: ExperimentProtocol,
    *,
    system: MandatoryExperimentSystem,
    seed: int,
    scores: tuple[float, float],
    stage: ExperimentStage = ExperimentStage.SCREENING,
) -> ExperimentRunReceipt:
    mean_score = sum(scores) / len(scores)
    return ExperimentRunReceipt(
        run_id=f"{system.value}-seed-{seed}",
        protocol_sha256=protocol.protocol_sha256,
        system=system,
        stage=stage,
        status=ExperimentRunStatus.SUCCEEDED,
        seed=seed,
        setting=EvaluationSetting.GOLD_PRIMARY_GOLD_SIGNAL,
        partitions=(CorpusPartition.TRAIN, CorpusPartition.DEV),
        architecture_config_sha256="7" * 64,
        candidate_selection_sha256="8" * 64,
        split_manifest_sha256=protocol.split_manifest_sha256,
        started_at=_NOW,
        completed_at=_NOW,
        document_count=2,
        scored_document_count=2,
        candidate_count=10,
        execution_steps=1,
        checkpoint_sha256="9" * 64,
        predictions_sha256="a" * 64,
        scorer_output_sha256="b" * 64,
        metrics=ExperimentMetrics(
            span_f=mean_score,
            direction_f=mean_score,
            relation_f=mean_score,
            full_f=mean_score,
            ece=0.04,
            brier=0.2,
        ),
        document_scores=(
            DocumentScore(document_id="doc-a", source_sha256="c" * 64, full_f=scores[0]),
            DocumentScore(document_id="doc-b", source_sha256="d" * 64, full_f=scores[1]),
        ),
        resources=_resource(),
    )


def test_temperature_fit_is_deterministic_and_does_not_increase_development_nll() -> None:
    probabilities = np.asarray((0.99, 0.90, 0.80, 0.20, 0.10, 0.01), dtype=np.float64)
    targets = np.asarray((1, 0, 1, 0, 1, 0), dtype=np.float64)

    first = fit_temperature(probabilities, targets)
    second = fit_temperature(probabilities, targets)
    calibrated = apply_temperature(probabilities, first.temperature)

    assert first == second
    assert first.nll_after <= first.nll_before
    assert np.all((calibrated >= 0.0) & (calibrated <= 1.0))


def test_bootstrap_and_holm_are_reproducible_and_content_hashed() -> None:
    protocol = _protocol()
    baseline = tuple(
        _receipt(
            protocol,
            system=MandatoryExperimentSystem.ELECTRA,
            seed=seed,
            scores=(0.10, 0.20),
        )
        for seed in protocol.screening_seeds
    )
    candidate = tuple(
        _receipt(
            protocol,
            system=MandatoryExperimentSystem.MODERNBERT_BASE,
            seed=seed,
            scores=(0.20, 0.30),
        )
        for seed in protocol.screening_seeds
    )

    comparison = compare_systems(
        candidate_receipts=candidate,
        baseline_receipts=baseline,
        bootstrap_seed=protocol.bootstrap_seed,
    )
    corrected = holm_correct((comparison,))

    assert comparison.mean_difference == pytest.approx(0.1)
    assert comparison.ci_lower > 0.0
    assert len(corrected[0].comparison_sha256) == 64
    assert corrected == holm_correct((comparison,))


def test_screening_completeness_requires_every_system_seed_disposition() -> None:
    protocol = _protocol()
    complete = tuple(
        _receipt(protocol, system=system, seed=seed, scores=(0.1, 0.2))
        for system in MandatoryExperimentSystem
        for seed in protocol.screening_seeds
    )

    validate_screening_completeness(protocol, complete)
    with pytest.raises(ValueError, match="incomplete"):
        validate_screening_completeness(protocol, complete[:-1])


def test_generative_outcomes_are_unique_and_include_explicit_no_edge() -> None:
    tokens = _label_tokens(("cause", "contrast"), "NO_EDGE")

    assert tokens == ("<ERST_00>", "<ERST_01>", "<ERST_02>")
    assert len(set(tokens)) == 3


def test_graph_attention_rejects_incomplete_primary_structure() -> None:
    nodes = (
        RstNode(1, NodeKindEnum.ROOT, (1, 2), (0, 3), "all"),
        RstNode(2, NodeKindEnum.EDU, (1, 1), (0, 1), "a"),
        RstNode(3, NodeKindEnum.EDU, (2, 2), (2, 3), "b"),
    )
    edge = PrimaryRelationEdge(
        edge_id="p1",
        parent_id=1,
        child_id=2,
        relation_raw="span",
        relation_concept="span",
        nuclearity=NuclearityPatternEnum.NS,
    )
    incomplete = RstAnalysis(
        document_id="doc",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=nodes,
        primary_edges=(edge,),
    )
    complete = replace(
        incomplete,
        primary_edges=(
            edge,
            replace(edge, edge_id="p2", child_id=3),
        ),
    )

    with pytest.raises(ValueError, match="complete"):
        _validate_complete_primary_tree(incomplete)
    _validate_complete_primary_tree(complete)


def test_disabled_mps_sampler_has_no_measurement_side_effect() -> None:
    with MpsMemorySampler(enabled=False) as sampler:
        assert sampler.peak_allocated_bytes is None
