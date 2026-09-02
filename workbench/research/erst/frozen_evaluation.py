"""Strict checkpoint reload and untouched-corpus inference for every harness system."""

import hashlib
from importlib import import_module
import json
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast

from safetensors.torch import load_file, load_model
import torch
from torch import nn
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel

from workbench.training.erst.dataset import GUMSecondaryEdgeDataset
from rdam.rst.erst.environment import load_repository_environment
from rdam.rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from workbench.research.erst.calibration import TemperatureCalibration
from workbench.research.erst.configuration import ExperimentConfigurationBundle
from workbench.research.erst.contracts import (
    ExperimentRunReceipt,
    ExperimentRunStatus,
    MandatoryExperimentSystem,
)
from workbench.research.erst.data import CandidateShard, HarnessCandidate
from workbench.research.erst.final_data import FinalEvaluationCorpusPayload
from workbench.research.erst.runner import SystemExecutionResult, SystemRunContext
from workbench.research.erst.systems.common import (
    CandidateScoreBatch,
    CandidateScoringFunction,
    ScorerEvidence,
    evaluate_frozen_and_write,
)
from workbench.research.erst.systems.cross_encoder import CrossEncoderAdapter
from workbench.research.erst.systems.dual_encoder import DualEncoderAdapter
from workbench.research.erst.systems.generative_decoder import (
    GenerativeDecoderAdapter,
    _label_tokens,
)
from workbench.research.erst.systems.graph_attention import GraphAttentionAdapter
from workbench.research.erst.systems.hierarchical_adapter import HierarchicalAdapter
from workbench.research.erst.systems.structural import _StructuralClassifier


class _PeftModelType(Protocol):
    @classmethod
    def from_pretrained(
        cls,
        model: PreTrainedModel,
        model_id: str | Path,
        *,
        is_trainable: bool,
    ) -> PreTrainedModel: ...


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_load_complete(model: nn.Module, checkpoint: Path, device: torch.device) -> None:
    missing, unexpected = load_model(model, checkpoint, strict=True, device=str(device))
    if missing or unexpected:
        raise ValueError(f"strict checkpoint reload differed: missing={missing}, unexpected={unexpected}")


def _strict_load_partial(
    model: nn.Module,
    checkpoint: Path,
    *,
    excluded_prefix: str,
    device: torch.device,
) -> None:
    checkpoint_state = load_file(checkpoint, device=str(device))
    current = model.state_dict()
    expected = {name for name in current if not name.startswith(excluded_prefix)}
    if set(checkpoint_state) != expected:
        missing = sorted(expected.difference(checkpoint_state))
        unexpected = sorted(set(checkpoint_state).difference(expected))
        raise ValueError(f"partial checkpoint differs: missing={missing}, unexpected={unexpected}")
    current.update(checkpoint_state)
    model.load_state_dict(current, strict=True)


class FrozenEvaluationAdapter:
    """Reload one selected dev checkpoint and score only test/test2 candidates."""

    def __init__(
        self,
        *,
        source_receipt: ExperimentRunReceipt,
        source_run_directory: Path,
        configurations: ExperimentConfigurationBundle,
        repository_root: Path,
    ) -> None:
        if source_receipt.status != ExperimentRunStatus.SUCCEEDED:
            raise ValueError("frozen evaluation requires a successful source checkpoint")
        if source_receipt.checkpoint_sha256 is None or source_receipt.scorer_output_sha256 is None:
            raise ValueError("frozen evaluation source receipt lacks checkpoint/scorer evidence")
        self.source_receipt = source_receipt
        self.source_run_directory = source_run_directory.resolve()
        self.configurations = configurations
        self.repository_root = repository_root.resolve()
        self.system = source_receipt.system

    @property
    def architecture_config_sha256(self) -> str:
        return self.source_receipt.architecture_config_sha256

    def _calibration(self) -> tuple[TemperatureCalibration, ScorerEvidence]:
        calibration_path = self.source_run_directory / "calibration.json"
        scorer_path = self.source_run_directory / "scorer-output.json"
        if not calibration_path.is_file() or not scorer_path.is_file():
            raise ValueError("frozen source lacks development calibration/scorer artifacts")
        if _sha256_file(scorer_path) != self.source_receipt.scorer_output_sha256:
            raise ValueError("frozen source scorer artifact hash differs from its receipt")
        calibration = TemperatureCalibration.model_validate_json(
            calibration_path.read_text(encoding="utf-8")
        )
        scorer = ScorerEvidence.model_validate_json(scorer_path.read_text(encoding="utf-8"))
        if scorer.calibration_sha256 != calibration.calibration_sha256:
            raise ValueError("frozen source calibration differs from scorer evidence")
        return calibration, scorer

    def checkpoint_path(self) -> Path:
        relative = {
            MandatoryExperimentSystem.STRUCTURAL_ONLY: "model.safetensors",
            MandatoryExperimentSystem.SIGNAL_RULE: "rule-config.json",
            MandatoryExperimentSystem.EXISTING_DUAL_ENCODER: "model.safetensors",
            MandatoryExperimentSystem.TEXT_ONLY: "model.safetensors",
            MandatoryExperimentSystem.ELECTRA: "model.safetensors",
            MandatoryExperimentSystem.MODERNBERT_BASE: "model.safetensors",
            MandatoryExperimentSystem.MODERNBERT_LARGE: "model.safetensors",
            MandatoryExperimentSystem.XLM_R_HIDAC: "adapter.safetensors",
            MandatoryExperimentSystem.QWEN3_DEDISCO: "adapter/adapter_model.safetensors",
            MandatoryExperimentSystem.EDGE_FEATURED_GAT: "graph.safetensors",
        }[self.system]
        checkpoint = (self.source_run_directory / relative).resolve()
        if not checkpoint.is_relative_to(self.source_run_directory) or not checkpoint.is_file():
            raise ValueError("frozen source checkpoint is missing")
        if _sha256_file(checkpoint) != self.source_receipt.checkpoint_sha256:
            raise ValueError("frozen source checkpoint hash differs from its receipt")
        return checkpoint

    def _structural_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        config = self.configurations.structural_only
        model = _StructuralClassifier(config, len(payload.raw_relation_inventory.labels)).to(device)
        _strict_load_complete(model, checkpoint, device)

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            probabilities: list[float] = []
            relations: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for start in range(0, len(candidates), 4096):
                    batch = candidates[start : start + 4096]
                    features = torch.tensor(
                        [item.candidate.structural_features for item in batch],
                        dtype=torch.float32,
                        device=device,
                    )
                    started = perf_counter()
                    edge_logits, relation_logits = model(features)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in torch.sigmoid(edge_logits).cpu().tolist())
                    relations.extend(tuple(float(value) for value in row) for row in relation_logits.cpu().tolist())
            return CandidateScoreBatch(tuple(probabilities), tuple(relations), tuple(latencies))

        return score

    def _signal_rule_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
    ) -> CandidateScoringFunction:
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        config = self.configurations.signal_rule
        if saved.get("config") != config.model_dump(mode="json"):
            raise ValueError("frozen signal-rule configuration differs")
        inventory = payload.raw_relation_inventory
        if saved.get("relation_inventory_sha256") != inventory.inventory_sha256:
            raise ValueError("frozen signal-rule relation inventory differs")
        default_relation = saved.get("default_relation")
        if not isinstance(default_relation, str) or default_relation not in inventory.labels:
            raise ValueError("frozen signal-rule default relation is invalid")
        relation_index = {relation: index for index, relation in enumerate(inventory.labels)}

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            started = perf_counter()
            probabilities: list[float] = []
            rows: list[tuple[float, ...]] = []
            for item in candidates:
                candidate = item.candidate
                compatible = tuple(
                    relation for relation in candidate.compatible_relations if relation in relation_index
                )
                licensed = (
                    bool(item.signal_char_spans)
                    and bool(compatible)
                    and abs(candidate.edu_distance) <= config.maximum_local_edu_distance
                )
                probabilities.append(config.licensed_probability if licensed else config.fallback_probability)
                selected = (
                    max(compatible, key=lambda relation: (inventory.label_counts[relation], relation))
                    if compatible
                    else default_relation
                )
                logits = [-5.0] * len(inventory.labels)
                logits[relation_index[selected]] = 5.0
                rows.append(tuple(logits))
            return CandidateScoreBatch(
                tuple(probabilities),
                tuple(rows),
                ((perf_counter() - started) * 1000.0,),
            )

        return score

    def _cross_encoder_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        config = {
            MandatoryExperimentSystem.TEXT_ONLY: self.configurations.text_only,
            MandatoryExperimentSystem.ELECTRA: self.configurations.electra,
            MandatoryExperimentSystem.MODERNBERT_BASE: self.configurations.modernbert_base,
            MandatoryExperimentSystem.MODERNBERT_LARGE: self.configurations.modernbert_large,
        }.get(self.system)
        if config is None:
            raise ValueError("frozen cross-encoder scorer received a non-cross-encoder system")
        adapter = CrossEncoderAdapter(
            system=self.system,
            config=config,
            architecture_config_sha256=self.architecture_config_sha256,
            repository_root=self.repository_root,
        )
        tokenizer, model = adapter._tokenizer_and_model(
            len(payload.raw_relation_inventory.labels),
            device,
        )
        _strict_load_complete(model, checkpoint, device)

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            probabilities: list[float] = []
            rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for start in range(0, len(candidates), config.inference_batch_size):
                    batch = candidates[start : start + config.inference_batch_size]
                    started = perf_counter()
                    ids, mask = adapter._encode(tokenizer, batch)
                    edge_logits, relation_logits = model(ids.to(device), mask.to(device))
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in torch.sigmoid(edge_logits).cpu().tolist())
                    rows.extend(tuple(float(value) for value in row) for row in relation_logits.cpu().tolist())
            return CandidateScoreBatch(tuple(probabilities), tuple(rows), tuple(latencies))

        return score

    def _dual_encoder_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        config = self.configurations.existing_dual_encoder
        model = NeuralSecondaryEdgeScorer(
            model_name_or_path=config.model_id,
            model_revision=config.model_revision,
            raw_relation_inventory=payload.raw_relation_inventory.labels,
            device=device,
        )
        _strict_load_complete(model, checkpoint, device)

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            dataset = GUMSecondaryEdgeDataset(
                tuple(item.candidate for item in candidates),
                tokenizer=model.tokenizer,
                max_length=config.max_length,
                raw_relation_inventory=payload.raw_relation_inventory.labels,
            )
            loader = DataLoader(dataset, batch_size=config.inference_batch_size, shuffle=False)
            probabilities: list[float] = []
            rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for batch in loader:
                    moved = DualEncoderAdapter._batch_to_device(batch, device)
                    started = perf_counter()
                    result = model(**moved)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in result["edge_probs"].cpu().tolist())
                    rows.extend(tuple(float(value) for value in row) for row in result["rel_logits"].cpu().tolist())
            return CandidateScoreBatch(tuple(probabilities), tuple(rows), tuple(latencies))

        return score

    def _hierarchical_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        config = self.configurations.xlm_r_hidac
        adapter = HierarchicalAdapter(
            config=config,
            architecture_config_sha256=self.architecture_config_sha256,
            repository_root=self.repository_root,
        )
        tokenizer, model = adapter._load(len(payload.raw_relation_inventory.labels), device)
        _strict_load_partial(model, checkpoint, excluded_prefix="encoder.", device=device)

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            probabilities: list[float] = []
            rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for start in range(0, len(candidates), config.inference_batch_size):
                    batch = candidates[start : start + config.inference_batch_size]
                    started = perf_counter()
                    ids, mask = adapter._encode(tokenizer, batch)
                    edge_logits, relation_logits, _ = model(ids.to(device), mask.to(device))
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in torch.sigmoid(edge_logits).cpu().tolist())
                    rows.extend(tuple(float(value) for value in row) for row in relation_logits.cpu().tolist())
            return CandidateScoreBatch(tuple(probabilities), tuple(rows), tuple(latencies))

        return score

    def _generative_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        config = self.configurations.qwen3_dedisco
        environment = load_repository_environment(self.repository_root)
        token = environment.hf_token.get_secret_value() if environment.hf_token is not None else None
        tokenizer_path = self.source_run_directory / "tokenizer"
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, use_fast=True)
        if not tokenizer.is_fast or tokenizer.pad_token_id is None:
            raise ValueError("frozen Qwen3 tokenizer is not a padded fast tokenizer")
        base_model = AutoModelForCausalLM.from_pretrained(
            config.model_id,
            revision=config.model_revision,
            use_safetensors=True,
            token=token,
            torch_dtype=torch.float16 if device.type == "mps" else torch.float32,
        )
        base_model.resize_token_embeddings(len(tokenizer))
        peft_module = import_module("peft")
        if not hasattr(peft_module, "PeftModel"):
            raise ValueError("independent PEFT environment lacks PeftModel")
        peft_model_type = cast(_PeftModelType, peft_module.PeftModel)
        model = peft_model_type.from_pretrained(
            base_model,
            checkpoint.parent,
            is_trainable=False,
        )
        cast(nn.Module, model).to(device)
        adapter = GenerativeDecoderAdapter(
            config=config,
            architecture_config_sha256=self.architecture_config_sha256,
            repository_root=self.repository_root,
        )
        outcome_tokens = _label_tokens(
            payload.raw_relation_inventory.labels,
            config.no_edge_label,
        )
        token_ids = tuple(tokenizer.convert_tokens_to_ids(item) for item in outcome_tokens)
        if any(not isinstance(item, int) or item < 0 for item in token_ids):
            raise ValueError("frozen Qwen3 outcome token identity differs")
        outcome_ids = torch.tensor(token_ids, dtype=torch.long, device=device)

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            probabilities: list[float] = []
            rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            cast(nn.Module, model).eval()
            with torch.inference_mode():
                for start in range(0, len(candidates), config.batch_size):
                    batch = candidates[start : start + config.batch_size]
                    started = perf_counter()
                    ids, mask = adapter._encode_prompts(tokenizer, batch)
                    logits = adapter._outcome_logits(
                        cast(nn.Module, model),
                        ids.to(device),
                        mask.to(device),
                        outcome_ids,
                    )
                    softmax = torch.softmax(logits, dim=-1)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in (1.0 - softmax[:, 0]).cpu().tolist())
                    rows.extend(tuple(float(value) for value in row) for row in logits[:, 1:].cpu().tolist())
            return CandidateScoreBatch(tuple(probabilities), tuple(rows), tuple(latencies))

        return score

    def _graph_scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        config = self.configurations.edge_featured_gat
        structural_size = len(
            payload.load_evaluation_document(payload.evaluation_shards[0])
            .candidates[0]
            .candidate.structural_features
        )
        adapter = GraphAttentionAdapter(
            config=config,
            architecture_config_sha256=self.architecture_config_sha256,
            repository_root=self.repository_root,
        )
        tokenizer, model = adapter._load(
            structural_size=structural_size,
            relation_count=len(payload.raw_relation_inventory.labels),
            device=device,
        )
        _strict_load_partial(model, checkpoint, excluded_prefix="encoder.", device=device)
        active_shard: CandidateShard | None = None
        active_graph: torch.Tensor | None = None
        active_node_index: dict[int, int] | None = None

        def score(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            nonlocal active_shard, active_graph, active_node_index
            document_ids = {item.candidate.document_id for item in candidates}
            if len(document_ids) != 1:
                raise ValueError("frozen graph scorer requires one document per call")
            document_id = next(iter(document_ids))
            shard = next(
                (item for item in payload.evaluation_shards if item.document_id == document_id),
                None,
            )
            if shard is None:
                raise ValueError("frozen graph scorer received an ungoverned document")
            if shard != active_shard:
                analysis = payload.load_evaluation_document(shard).gold_analysis
                model.eval()
                with torch.inference_mode():
                    active_graph, active_node_index = adapter._graph_inputs(
                        tokenizer=tokenizer,
                        model=model,
                        analysis=analysis,
                        device=device,
                    )
                active_shard = shard
            if active_graph is None or active_node_index is None:
                raise RuntimeError("frozen graph scorer failed to initialize")
            probabilities: list[float] = []
            rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            with torch.inference_mode():
                for start in range(0, len(candidates), config.text_batch_size):
                    batch = candidates[start : start + config.text_batch_size]
                    started = perf_counter()
                    sources, targets, structural = adapter._pair_tensors(
                        batch,
                        active_node_index,
                        device,
                    )
                    edge_logits, relation_logits = model.score_pairs(
                        active_graph,
                        sources,
                        targets,
                        structural,
                    )
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in torch.sigmoid(edge_logits).cpu().tolist())
                    rows.extend(tuple(float(value) for value in row) for row in relation_logits.cpu().tolist())
            return CandidateScoreBatch(tuple(probabilities), tuple(rows), tuple(latencies))

        return score

    def _scorer(
        self,
        payload: FinalEvaluationCorpusPayload,
        checkpoint: Path,
        device: torch.device,
    ) -> CandidateScoringFunction:
        if self.system == MandatoryExperimentSystem.STRUCTURAL_ONLY:
            return self._structural_scorer(payload, checkpoint, device)
        if self.system == MandatoryExperimentSystem.SIGNAL_RULE:
            return self._signal_rule_scorer(payload, checkpoint)
        if self.system == MandatoryExperimentSystem.EXISTING_DUAL_ENCODER:
            return self._dual_encoder_scorer(payload, checkpoint, device)
        if self.system in {
            MandatoryExperimentSystem.TEXT_ONLY,
            MandatoryExperimentSystem.ELECTRA,
            MandatoryExperimentSystem.MODERNBERT_BASE,
            MandatoryExperimentSystem.MODERNBERT_LARGE,
        }:
            return self._cross_encoder_scorer(payload, checkpoint, device)
        if self.system == MandatoryExperimentSystem.XLM_R_HIDAC:
            return self._hierarchical_scorer(payload, checkpoint, device)
        if self.system == MandatoryExperimentSystem.QWEN3_DEDISCO:
            return self._generative_scorer(payload, checkpoint, device)
        if self.system == MandatoryExperimentSystem.EDGE_FEATURED_GAT:
            return self._graph_scorer(payload, checkpoint, device)
        raise ValueError(f"unsupported frozen system: {self.system}")

    def execute(
        self,
        context: SystemRunContext[FinalEvaluationCorpusPayload],
    ) -> SystemExecutionResult:
        checkpoint = self.checkpoint_path()
        calibration, scorer_evidence = self._calibration()
        device = torch.device(context.request.device)
        score_candidates = self._scorer(context.data.payload, checkpoint, device)
        reference = context.run_directory / "checkpoint-reference.json"
        reference.write_text(
            json.dumps(
                {
                    "source_receipt_sha256": self.source_receipt.receipt_sha256,
                    "source_checkpoint_sha256": self.source_receipt.checkpoint_sha256,
                    "system": self.system.value,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return evaluate_frozen_and_write(
            payload=context.data.payload,
            run_directory=context.run_directory,
            checkpoint_path=reference.name,
            score_candidates=score_candidates,
            selected_edge_threshold=scorer_evidence.selected_edge_threshold,
            calibration_state=calibration,
            execution_steps=context.data.identity.candidate_count,
        )


__all__ = ["FrozenEvaluationAdapter"]
