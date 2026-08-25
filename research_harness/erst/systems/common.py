"""Shared decoding, repository scoring, calibration, and evidence serialization."""

from collections.abc import Callable
from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from safetensors.numpy import load_file, save_file

from isanlp_rst.contracts.analysis import RstAnalysis, SecondaryRelationEdge
from isanlp_rst.contracts.erst import ErstDecoderConfig
from isanlp_rst.erst.decoder import ErstSecondaryEdgeDecoder
from isanlp_rst.erst.relations import resolve_gum_relation_concept
from offline_workbench.evaluation.rst.erst_scorer import ErstScorer, SecondaryEdgeMetrics
from research_harness.erst.contracts import DocumentScore, ExperimentMetrics
from research_harness.erst.calibration import (
    TemperatureCalibration,
    apply_temperature,
    canonical_threshold_grid,
    fit_temperature,
)
from research_harness.erst.data import HarnessCandidate, ScreeningCorpusPayload
from research_harness.erst.final_data import FinalEvaluationCorpusPayload
from research_harness.erst.runner import SystemExecutionResult


@dataclass(frozen=True, slots=True)
class CandidateScoreBatch:
    """Complete scores for one document's canonical candidate sequence."""

    edge_probabilities: tuple[float, ...]
    relation_logits: tuple[tuple[float, ...], ...]
    latency_samples_ms: tuple[float, ...]

    def validate(self, candidate_count: int, relation_count: int) -> None:
        if len(self.edge_probabilities) != candidate_count or len(self.relation_logits) != candidate_count:
            raise ValueError("candidate scorer output count does not match its document shard")
        if any(len(logits) != relation_count for logits in self.relation_logits):
            raise ValueError("candidate scorer relation width does not match the raw inventory")
        if not self.latency_samples_ms or any(sample <= 0.0 for sample in self.latency_samples_ms):
            raise ValueError("candidate scorer requires positive batch latency samples")


CandidateScoringFunction = Callable[[tuple[HarnessCandidate, ...]], CandidateScoreBatch]


class PredictedEdgeRecord(BaseModel):
    """Private-text-free decoded edge persisted for reproducibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_id: str
    source_id: int
    target_id: int
    relation_raw: str
    relation_concept: str
    confidence: float = Field(ge=0.0, le=1.0)

    @classmethod
    def from_edge(cls, edge: SecondaryRelationEdge) -> "PredictedEdgeRecord":
        if edge.confidence is None:
            raise ValueError("decoded eRST edges require confidence")
        return cls(
            edge_id=edge.edge_id,
            source_id=edge.source_id,
            target_id=edge.target_id,
            relation_raw=edge.relation_raw,
            relation_concept=edge.relation_concept,
            confidence=edge.confidence,
        )


class DocumentPredictionRecord(BaseModel):
    """One development document's decoded edge output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_count: int = Field(gt=0)
    edges: tuple[PredictedEdgeRecord, ...]


class ScorerEvidence(BaseModel):
    """Repository scorer counts and metrics persisted without corpus text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    span_precision: float
    span_recall: float
    span_f: float
    direction_precision: float
    direction_recall: float
    direction_f: float
    relation_precision: float
    relation_recall: float
    relation_f: float
    full_precision: float
    full_recall: float
    full_f: float
    gold_count: int
    predicted_count: int
    matched_span: int
    matched_direction: int
    matched_relation: int
    matched_full: int
    ece: float
    brier: float
    selected_edge_threshold: float = Field(ge=0.0, le=1.0)
    temperature: float = Field(gt=0.0)
    calibration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    score_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class _CalibrationAccumulator:
    def __init__(self, bins: int = 10) -> None:
        if bins < 1:
            raise ValueError("calibration requires at least one bin")
        self.bins = bins
        self.counts = [0] * bins
        self.confidence_sums = [0.0] * bins
        self.positive_sums = [0] * bins
        self.brier_sum = 0.0
        self.total = 0

    def update(self, probabilities: tuple[float, ...], targets: tuple[bool, ...]) -> None:
        if len(probabilities) != len(targets):
            raise ValueError("calibration probability and target counts must match")
        for probability, target in zip(probabilities, targets, strict=True):
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("calibration probabilities must be finite values in [0, 1]")
            index = min(int(probability * self.bins), self.bins - 1)
            self.counts[index] += 1
            self.confidence_sums[index] += probability
            self.positive_sums[index] += int(target)
            self.brier_sum += (probability - float(target)) ** 2
            self.total += 1

    def metrics(self) -> tuple[float, float]:
        if self.total <= 0:
            raise ValueError("calibration cannot summarize zero candidates")
        ece = 0.0
        for count, confidence_sum, positive_sum in zip(
            self.counts,
            self.confidence_sums,
            self.positive_sums,
            strict=True,
        ):
            if count:
                ece += (count / self.total) * abs((positive_sum / count) - (confidence_sum / count))
        return ece, self.brier_sum / self.total


def _aggregate_secondary_metrics(metrics: tuple[SecondaryEdgeMetrics, ...]) -> SecondaryEdgeMetrics:
    gold_count = sum(metric.gold_count for metric in metrics)
    predicted_count = sum(metric.pred_count for metric in metrics)
    matched_span = sum(metric.matched_span for metric in metrics)
    matched_direction = sum(metric.matched_direction for metric in metrics)
    matched_relation = sum(metric.matched_relation for metric in metrics)
    matched_full = sum(metric.matched_full for metric in metrics)

    def prf(matched: int) -> tuple[float, float, float]:
        precision = matched / predicted_count if predicted_count else (1.0 if gold_count == 0 else 0.0)
        recall = matched / gold_count if gold_count else (1.0 if predicted_count == 0 else 0.0)
        f_score = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall > 0.0
            else 0.0
        )
        return precision, recall, f_score

    span = prf(matched_span)
    direction = prf(matched_direction)
    relation = prf(matched_relation)
    full = prf(matched_full)
    return SecondaryEdgeMetrics(
        span_precision=span[0],
        span_recall=span[1],
        span_f1=span[2],
        direction_precision=direction[0],
        direction_recall=direction[1],
        direction_f1=direction[2],
        relation_precision=relation[0],
        relation_recall=relation[1],
        relation_f1=relation[2],
        full_precision=full[0],
        full_recall=full[1],
        full_f1=full[2],
        gold_count=gold_count,
        pred_count=predicted_count,
        matched_span=matched_span,
        matched_direction=matched_direction,
        matched_relation=matched_relation,
        matched_full=matched_full,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _score_cache_path(root: Path, document_id: str) -> Path:
    return root / f"{hashlib.sha256(document_id.encode()).hexdigest()}.safetensors"


def _decoder(relations: tuple[str, ...], edge_threshold: float) -> ErstSecondaryEdgeDecoder:
    return ErstSecondaryEdgeDecoder(
        ErstDecoderConfig(edge_threshold=edge_threshold, raw_relation_inventory=relations),
        ontology_adapter=resolve_gum_relation_concept,
    )


def _decoded_metric(
    *,
    decoder: ErstSecondaryEdgeDecoder,
    scorer: ErstScorer,
    loaded_candidates: tuple[HarnessCandidate, ...],
    analysis: RstAnalysis,
    edge_probabilities: tuple[float, ...],
    relation_logits: tuple[tuple[float, ...], ...],
) -> tuple[tuple[SecondaryRelationEdge, ...], SecondaryEdgeMetrics]:
    raw_candidates = tuple(item.candidate for item in loaded_candidates)
    primary_only = replace(analysis, secondary_edges=())
    sufficient_signal_ids = {signal.signal_id for signal in analysis.signals if signal.sufficient}
    decoded = decoder.decode(
        primary_only,
        raw_candidates,
        edge_probabilities,
        relation_logits,
        sufficient_signal_ids=sufficient_signal_ids,
    )
    predicted = replace(primary_only, secondary_edges=decoded)
    return decoded, scorer.score_secondary_edges(analysis, predicted)


def _decode_precomputed_for_tuning(
    *,
    analysis: RstAnalysis,
    source_ids: np.ndarray,
    target_ids: np.ndarray,
    sufficient_signals: np.ndarray,
    edge_probabilities: np.ndarray,
    best_relation_indices: np.ndarray,
    best_relation_probabilities: np.ndarray,
    relations: tuple[str, ...],
    threshold: float,
) -> tuple[SecondaryRelationEdge, ...]:
    """Apply the production decoder's four constraints after vectorized relation softmax."""

    if not (
        len(source_ids)
        == len(target_ids)
        == len(sufficient_signals)
        == len(edge_probabilities)
        == len(best_relation_indices)
        == len(best_relation_probabilities)
    ):
        raise ValueError("precomputed tuning scores do not align with candidates")
    node_ids = {node.node_id for node in analysis.nodes}
    scored: list[tuple[float, str, int, int, bool, str, float]] = []
    for source_id_value, target_id_value, sufficient, edge_probability, relation_index, relation_probability in zip(
        source_ids,
        target_ids,
        sufficient_signals,
        edge_probabilities,
        best_relation_indices,
        best_relation_probabilities,
        strict=True,
    ):
        probability = float(edge_probability)
        if probability < threshold:
            continue
        source_id = int(source_id_value)
        target_id = int(target_id_value)
        index = int(relation_index)
        if not 0 <= index < len(relations):
            raise ValueError("precomputed relation index is outside the raw inventory")
        relation_raw = relations[index]
        scored.append(
            (
                -(probability * float(relation_probability)),
                analysis.document_id,
                source_id,
                target_id,
                bool(sufficient),
                relation_raw,
                probability,
            )
        )
    scored.sort(key=lambda item: item[:4])
    seen_pairs = {(edge.source_id, edge.target_id) for edge in analysis.secondary_edges}
    accepted: list[SecondaryRelationEdge] = []
    for _, _, source_id, target_id, sufficient, relation_raw, probability in scored:
        pair = (source_id, target_id)
        if not sufficient:
            continue
        if source_id == target_id or source_id not in node_ids or target_id not in node_ids:
            continue
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        accepted.append(
            SecondaryRelationEdge(
                edge_id=f"se_pred_{source_id}_{target_id}",
                source_id=source_id,
                target_id=target_id,
                relation_raw=relation_raw,
                relation_concept=resolve_gum_relation_concept(relation_raw),
                confidence=probability,
                calibrated=True,
            )
        )
    return tuple(accepted)


def evaluate_and_write(
    *,
    payload: ScreeningCorpusPayload,
    run_directory: Path,
    checkpoint_path: str,
    score_candidates: CandidateScoringFunction,
    edge_threshold: float,
    execution_steps: int,
    training_loss: float | None,
    calibration_enabled: bool = True,
    mps_peak_allocated_bytes: int | None = None,
) -> SystemExecutionResult:
    """Tune on dev only, then decode every complete dev shard through the scorer."""

    del edge_threshold
    relations = payload.raw_relation_inventory.labels
    scorer = ErstScorer()
    cache_root = run_directory / "dev-score-cache"
    cache_root.mkdir()
    total_candidates = payload.manifest.complete_dev_count
    probabilities_for_calibration = np.empty(total_candidates, dtype=np.float64)
    targets_for_calibration = np.empty(total_candidates, dtype=np.float64)
    latency_samples: list[float] = []
    cache_digest = hashlib.sha256()
    cursor = 0
    for shard in payload.development_shards:
        loaded = payload.load_development_document(shard)
        started = perf_counter()
        scored = score_candidates(loaded.candidates)
        elapsed_ms = (perf_counter() - started) * 1000.0
        scored.validate(len(loaded.candidates), len(relations))
        latency_samples.extend(scored.latency_samples_ms or (elapsed_ms,))
        edge_array = np.asarray(scored.edge_probabilities, dtype=np.float32)
        relation_array = np.asarray(scored.relation_logits, dtype=np.float32)
        target_array = np.asarray(
            [item.candidate.is_gold_edge for item in loaded.candidates],
            dtype=np.float64,
        )
        end = cursor + len(edge_array)
        probabilities_for_calibration[cursor:end] = edge_array
        targets_for_calibration[cursor:end] = target_array
        cursor = end
        sufficient_signal_ids = {
            signal.signal_id for signal in loaded.gold_analysis.signals if signal.sufficient
        }
        cache_path = _score_cache_path(cache_root, shard.document_id)
        save_file(
            {
                "edge_probabilities": edge_array,
                "relation_logits": relation_array,
                "source_ids": np.asarray(
                    [item.candidate.source_id for item in loaded.candidates],
                    dtype=np.int64,
                ),
                "target_ids": np.asarray(
                    [item.candidate.target_id for item in loaded.candidates],
                    dtype=np.int64,
                ),
                "sufficient_signals": np.asarray(
                    [
                        any(signal_id in sufficient_signal_ids for signal_id in item.candidate.signal_ids)
                        for item in loaded.candidates
                    ],
                    dtype=np.bool_,
                ),
                "gold_edges": target_array.astype(np.bool_),
            },
            cache_path,
        )
        cache_digest.update(shard.document_id.encode())
        cache_digest.update(_sha256_file(cache_path).encode())
    if cursor != total_candidates:
        raise ValueError("development score cache candidate count does not reconcile")
    fitted_calibration = fit_temperature(
        probabilities_for_calibration,
        targets_for_calibration,
    )
    temperature_calibration = (
        fitted_calibration
        if calibration_enabled
        else TemperatureCalibration(
            temperature=1.0,
            nll_before=fitted_calibration.nll_before,
            nll_after=fitted_calibration.nll_before,
            example_count=fitted_calibration.example_count,
        )
    )
    calibration_path = run_directory / "calibration.json"
    calibration_path.write_text(
        temperature_calibration.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    selected_threshold = 0.5
    if calibration_enabled:
        threshold_metrics: dict[float, list[SecondaryEdgeMetrics]] = {
            threshold: [] for threshold in canonical_threshold_grid()
        }
        for shard in payload.development_shards:
            _, analysis = payload.load_analysis(shard)
            cached = load_file(_score_cache_path(cache_root, shard.document_id))
            calibrated = apply_temperature(
                cached["edge_probabilities"],
                temperature_calibration.temperature,
            )
            relation_array = cached["relation_logits"].astype(np.float64)
            row_maxima = np.max(relation_array, axis=1, keepdims=True)
            exponentials = np.exp(relation_array - row_maxima)
            relation_probabilities = exponentials / np.sum(exponentials, axis=1, keepdims=True)
            best_indices = np.argmax(relation_probabilities, axis=1)
            best_probabilities = relation_probabilities[
                np.arange(len(relation_probabilities)),
                best_indices,
            ]
            primary_only = replace(analysis, secondary_edges=())
            for threshold in threshold_metrics:
                decoded = _decode_precomputed_for_tuning(
                    analysis=primary_only,
                    source_ids=cached["source_ids"],
                    target_ids=cached["target_ids"],
                    sufficient_signals=cached["sufficient_signals"],
                    edge_probabilities=calibrated,
                    best_relation_indices=best_indices,
                    best_relation_probabilities=best_probabilities,
                    relations=relations,
                    threshold=threshold,
                )
                predicted = replace(primary_only, secondary_edges=decoded)
                threshold_metrics[threshold].append(
                    scorer.score_secondary_edges(analysis, predicted)
                )
        selected_threshold = max(
            threshold_metrics,
            key=lambda threshold: (
                _aggregate_secondary_metrics(tuple(threshold_metrics[threshold])).full_f1,
                -abs(threshold - 0.5),
                -threshold,
            ),
        )
    calibration = _CalibrationAccumulator()
    document_metrics: list[SecondaryEdgeMetrics] = []
    document_scores: list[DocumentScore] = []
    predictions: list[DocumentPredictionRecord] = []
    for shard in payload.development_shards:
        _, analysis = payload.load_analysis(shard)
        cached = load_file(_score_cache_path(cache_root, shard.document_id))
        calibrated = apply_temperature(
            cached["edge_probabilities"],
            temperature_calibration.temperature,
        )
        edge_probabilities = tuple(float(value) for value in calibrated)
        relation_array = cached["relation_logits"].astype(np.float64)
        row_maxima = np.max(relation_array, axis=1, keepdims=True)
        exponentials = np.exp(relation_array - row_maxima)
        relation_probabilities = exponentials / np.sum(exponentials, axis=1, keepdims=True)
        best_indices = np.argmax(relation_probabilities, axis=1)
        best_probabilities = relation_probabilities[
            np.arange(len(relation_probabilities)),
            best_indices,
        ]
        primary_only = replace(analysis, secondary_edges=())
        decoded = _decode_precomputed_for_tuning(
            analysis=primary_only,
            source_ids=cached["source_ids"],
            target_ids=cached["target_ids"],
            sufficient_signals=cached["sufficient_signals"],
            edge_probabilities=calibrated,
            best_relation_indices=best_indices,
            best_relation_probabilities=best_probabilities,
            relations=relations,
            threshold=selected_threshold,
        )
        metric = scorer.score_secondary_edges(
            analysis,
            replace(primary_only, secondary_edges=decoded),
        )
        document_metrics.append(metric)
        document_scores.append(
            DocumentScore(
                document_id=shard.document_id,
                source_sha256=shard.source_sha256,
                full_f=metric.full_f1,
            )
        )
        predictions.append(
            DocumentPredictionRecord(
                document_id=shard.document_id,
                source_sha256=shard.source_sha256,
                candidate_count=shard.candidate_count,
                edges=tuple(PredictedEdgeRecord.from_edge(edge) for edge in decoded),
            )
        )
        calibration.update(
            edge_probabilities,
            tuple(bool(value) for value in cached["gold_edges"]),
        )
    aggregate = _aggregate_secondary_metrics(tuple(document_metrics))
    ece, brier = calibration.metrics()
    metrics = ExperimentMetrics(
        span_f=aggregate.span_f1,
        direction_f=aggregate.direction_f1,
        relation_f=aggregate.relation_f1,
        full_f=aggregate.full_f1,
        ece=ece,
        brier=brier,
        loss=training_loss,
    )
    predictions_path = run_directory / "predictions.json"
    predictions_path.write_text(
        json.dumps(
            [prediction.model_dump(mode="json") for prediction in predictions],
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = ScorerEvidence(
        span_precision=aggregate.span_precision,
        span_recall=aggregate.span_recall,
        span_f=aggregate.span_f1,
        direction_precision=aggregate.direction_precision,
        direction_recall=aggregate.direction_recall,
        direction_f=aggregate.direction_f1,
        relation_precision=aggregate.relation_precision,
        relation_recall=aggregate.relation_recall,
        relation_f=aggregate.relation_f1,
        full_precision=aggregate.full_precision,
        full_recall=aggregate.full_recall,
        full_f=aggregate.full_f1,
        gold_count=aggregate.gold_count,
        predicted_count=aggregate.pred_count,
        matched_span=aggregate.matched_span,
        matched_direction=aggregate.matched_direction,
        matched_relation=aggregate.matched_relation,
        matched_full=aggregate.matched_full,
        ece=ece,
        brier=brier,
        selected_edge_threshold=selected_threshold,
        temperature=temperature_calibration.temperature,
        calibration_sha256=temperature_calibration.calibration_sha256,
        score_evidence_sha256=cache_digest.hexdigest(),
    )
    scorer_path = run_directory / "scorer-output.json"
    scorer_path.write_text(evidence.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return SystemExecutionResult(
        execution_steps=execution_steps,
        checkpoint_path=checkpoint_path,
        predictions_path=predictions_path.name,
        scorer_output_path=scorer_path.name,
        metrics=metrics,
        document_scores=tuple(document_scores),
        latency_samples_ms=tuple(latency_samples),
        mps_peak_allocated_bytes=mps_peak_allocated_bytes,
    )


def evaluate_frozen_and_write(
    *,
    payload: FinalEvaluationCorpusPayload,
    run_directory: Path,
    checkpoint_path: str,
    score_candidates: CandidateScoringFunction,
    selected_edge_threshold: float,
    calibration_state: TemperatureCalibration,
    execution_steps: int,
) -> SystemExecutionResult:
    """Evaluate untouched test/test2 with calibration frozen from development."""

    relations = payload.raw_relation_inventory.labels
    decoder = _decoder(relations, selected_edge_threshold)
    scorer = ErstScorer()
    calibration = _CalibrationAccumulator()
    document_metrics: list[SecondaryEdgeMetrics] = []
    document_scores: list[DocumentScore] = []
    predictions: list[DocumentPredictionRecord] = []
    latency_samples: list[float] = []
    score_digest = hashlib.sha256()
    for shard in payload.evaluation_shards:
        loaded = payload.load_evaluation_document(shard)
        started = perf_counter()
        scored = score_candidates(loaded.candidates)
        elapsed_ms = (perf_counter() - started) * 1000.0
        scored.validate(len(loaded.candidates), len(relations))
        latency_samples.extend(scored.latency_samples_ms or (elapsed_ms,))
        calibrated = apply_temperature(
            np.asarray(scored.edge_probabilities, dtype=np.float64),
            calibration_state.temperature,
        )
        edge_probabilities = tuple(float(value) for value in calibrated)
        decoded, metric = _decoded_metric(
            decoder=decoder,
            scorer=scorer,
            loaded_candidates=loaded.candidates,
            analysis=loaded.gold_analysis,
            edge_probabilities=edge_probabilities,
            relation_logits=scored.relation_logits,
        )
        document_metrics.append(metric)
        document_scores.append(
            DocumentScore(
                document_id=shard.document_id,
                source_sha256=shard.source_sha256,
                full_f=metric.full_f1,
            )
        )
        predictions.append(
            DocumentPredictionRecord(
                document_id=shard.document_id,
                source_sha256=shard.source_sha256,
                candidate_count=shard.candidate_count,
                edges=tuple(PredictedEdgeRecord.from_edge(edge) for edge in decoded),
            )
        )
        calibration.update(
            edge_probabilities,
            tuple(item.candidate.is_gold_edge for item in loaded.candidates),
        )
        score_digest.update(shard.document_id.encode())
        score_digest.update(np.asarray(edge_probabilities, dtype=np.float32).tobytes())
        score_digest.update(np.asarray(scored.relation_logits, dtype=np.float32).tobytes())
    aggregate = _aggregate_secondary_metrics(tuple(document_metrics))
    ece, brier = calibration.metrics()
    metrics = ExperimentMetrics(
        span_f=aggregate.span_f1,
        direction_f=aggregate.direction_f1,
        relation_f=aggregate.relation_f1,
        full_f=aggregate.full_f1,
        ece=ece,
        brier=brier,
    )
    predictions_path = run_directory / "predictions.json"
    predictions_path.write_text(
        json.dumps(
            [prediction.model_dump(mode="json") for prediction in predictions],
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = ScorerEvidence(
        span_precision=aggregate.span_precision,
        span_recall=aggregate.span_recall,
        span_f=aggregate.span_f1,
        direction_precision=aggregate.direction_precision,
        direction_recall=aggregate.direction_recall,
        direction_f=aggregate.direction_f1,
        relation_precision=aggregate.relation_precision,
        relation_recall=aggregate.relation_recall,
        relation_f=aggregate.relation_f1,
        full_precision=aggregate.full_precision,
        full_recall=aggregate.full_recall,
        full_f=aggregate.full_f1,
        gold_count=aggregate.gold_count,
        predicted_count=aggregate.pred_count,
        matched_span=aggregate.matched_span,
        matched_direction=aggregate.matched_direction,
        matched_relation=aggregate.matched_relation,
        matched_full=aggregate.matched_full,
        ece=ece,
        brier=brier,
        selected_edge_threshold=selected_edge_threshold,
        temperature=calibration_state.temperature,
        calibration_sha256=calibration_state.calibration_sha256,
        score_evidence_sha256=score_digest.hexdigest(),
    )
    scorer_path = run_directory / "scorer-output.json"
    scorer_path.write_text(evidence.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return SystemExecutionResult(
        execution_steps=execution_steps,
        checkpoint_path=checkpoint_path,
        predictions_path=predictions_path.name,
        scorer_output_path=scorer_path.name,
        metrics=metrics,
        document_scores=tuple(document_scores),
        latency_samples_ms=tuple(latency_samples),
    )


__all__ = [
    "CandidateScoreBatch",
    "CandidateScoringFunction",
    "DocumentPredictionRecord",
    "PredictedEdgeRecord",
    "ScorerEvidence",
    "evaluate_and_write",
    "evaluate_frozen_and_write",
]
