"""Signal-aware and text-only pairwise cross-encoder systems."""

import json
import math
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field, model_validator
from safetensors.torch import save_model
import torch
from torch import nn
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from rdam.rst.erst.environment import load_repository_environment
from workbench.research.erst.contracts import AblationName, MandatoryExperimentSystem
from workbench.research.erst.data import HarnessCandidate, ScreeningCorpusPayload
from workbench.research.erst.runner import (
    ExperimentExecutionError,
    SystemExecutionResult,
    SystemRunContext,
)
from workbench.research.erst.systems.common import CandidateScoreBatch, evaluate_and_write


class CrossEncoderConfig(BaseModel):
    """Frozen model, serialization, optimization, and decoding configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1)
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    signal_aware: bool
    include_structure_tokens: bool
    max_length: int = Field(default=256, gt=0)
    epochs: int = Field(default=2, gt=0)
    batch_size: int = Field(default=32, gt=0)
    inference_batch_size: int = Field(default=1024, gt=0)
    learning_rate: float = Field(default=2e-5, gt=0.0)
    weight_decay: float = Field(default=0.01, ge=0.0)
    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_serialization(self) -> "CrossEncoderConfig":
        if not self.signal_aware and self.include_structure_tokens:
            raise ValueError("text-only control cannot include structural serialization tokens")
        return self


class _CrossEncoder(nn.Module):
    encoder: PreTrainedModel

    def __init__(self, encoder: PreTrainedModel, relation_count: int) -> None:
        super().__init__()
        self.encoder = encoder
        hidden_size = getattr(encoder.config, "hidden_size", None)
        if not isinstance(hidden_size, int) or hidden_size <= 0:
            raise ValueError("cross-encoder config requires a positive hidden size")
        self.dropout = nn.Dropout(0.1)
        self.edge_head = nn.Linear(hidden_size, 1)
        self.relation_head = nn.Linear(hidden_size, relation_count)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        pooled = self.dropout(pooled)
        return self.edge_head(pooled).squeeze(-1), self.relation_head(pooled)


def _relative_overlaps(
    node_span: tuple[int, int],
    signal_spans: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    relative: list[tuple[int, int]] = []
    for start, end in signal_spans:
        overlap_start = max(start, node_span[0])
        overlap_end = min(end, node_span[1])
        if overlap_start < overlap_end:
            relative.append((overlap_start - node_span[0], overlap_end - node_span[0]))
    return tuple(relative)


def _coordinates(spans: tuple[tuple[int, int], ...]) -> str:
    return ",".join(f"{start}:{end}" for start, end in spans) if spans else "none"


def serialize_candidate(
    harness_candidate: HarnessCandidate,
    *,
    signal_aware: bool,
    include_structure_tokens: bool,
) -> tuple[str, str]:
    """Serialize exact signal anchors without collapsing overlapping spans."""

    candidate = harness_candidate.candidate
    if not signal_aware:
        return candidate.source_text, candidate.target_text
    source_signals = _relative_overlaps(
        candidate.source_char_span,
        harness_candidate.signal_char_spans,
    )
    target_signals = _relative_overlaps(
        candidate.target_char_span,
        harness_candidate.signal_char_spans,
    )
    source_prefix = f"[source-signals={_coordinates(source_signals)}]"
    target_prefix = f"[target-signals={_coordinates(target_signals)}]"
    if include_structure_tokens:
        structural = (
            f"[direction={candidate.direction}] [edu-distance={candidate.edu_distance}] "
            f"[primary-relation={candidate.existing_primary_relation or 'none'}] "
            f"[primary-path={'|'.join(candidate.primary_path) or 'none'}]"
        )
        source_prefix = f"{source_prefix} {structural}"
    return (
        f"{source_prefix} {candidate.source_text}",
        f"{target_prefix} {candidate.target_text}",
    )


class CrossEncoderAdapter:
    """Fine-tune and evaluate one pinned cross-encoder through the shared runner."""

    def __init__(
        self,
        *,
        system: MandatoryExperimentSystem,
        config: CrossEncoderConfig,
        architecture_config_sha256: str,
        repository_root: Path,
    ) -> None:
        allowed = {
            MandatoryExperimentSystem.TEXT_ONLY,
            MandatoryExperimentSystem.ELECTRA,
            MandatoryExperimentSystem.MODERNBERT_BASE,
            MandatoryExperimentSystem.MODERNBERT_LARGE,
        }
        if system not in allowed:
            raise ValueError(f"unsupported cross-encoder system: {system}")
        self.system = system
        self.config = config
        self._architecture_config_sha256 = architecture_config_sha256
        self.repository_root = repository_root.resolve()

    @property
    def architecture_config_sha256(self) -> str:
        return self._architecture_config_sha256

    def _tokenizer_and_model(
        self,
        relation_count: int,
        device: torch.device,
    ) -> tuple[PreTrainedTokenizerBase, _CrossEncoder]:
        environment = load_repository_environment(self.repository_root)
        token = (
            environment.hf_token.get_secret_value()
            if environment.hf_token is not None
            else None
        )
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_id,
                revision=self.config.model_revision,
                use_fast=True,
                token=token,
            )
            if not tokenizer.is_fast:
                raise ValueError("cross-encoder requires a verified fast tokenizer")
            encoder = AutoModel.from_pretrained(
                self.config.model_id,
                revision=self.config.model_revision,
                use_safetensors=None,
                token=token,
            )
        except (OSError, RuntimeError, ValueError) as error:
            evidence = json.dumps(
                {
                    "exception_type": type(error).__name__,
                    "model_id": self.config.model_id,
                    "model_revision": self.config.model_revision,
                },
                sort_keys=True,
            ).encode()
            raise ExperimentExecutionError(
                failure_type="CrossEncoderCompatibilityError",
                message="pinned cross-encoder failed its authenticated tokenizer/model load",
                evidence=evidence,
                incompatible=True,
            ) from error
        return tokenizer, _CrossEncoder(encoder, relation_count).to(device)

    def _encode(
        self,
        tokenizer: PreTrainedTokenizerBase,
        candidates: tuple[HarnessCandidate, ...],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        serialized = tuple(
            serialize_candidate(
                candidate,
                signal_aware=self.config.signal_aware,
                include_structure_tokens=self.config.include_structure_tokens,
            )
            for candidate in candidates
        )
        encoded = tokenizer(
            [item[0] for item in serialized],
            [item[1] for item in serialized],
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        return encoded["input_ids"], encoded["attention_mask"]

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        payload = context.data.payload
        relations = payload.raw_relation_inventory.labels
        relation_to_index = {relation: index for index, relation in enumerate(relations)}
        device = torch.device(context.request.device)
        torch.manual_seed(context.request.seed)
        tokenizer, model = self._tokenizer_and_model(len(relations), device)
        input_ids, attention_mask = self._encode(tokenizer, payload.train_candidates)
        edge_targets = torch.tensor(
            [float(item.candidate.is_gold_edge) for item in payload.train_candidates],
            dtype=torch.float32,
        )
        relation_targets = torch.tensor(
            [
                relation_to_index[item.candidate.gold_relation]
                if item.candidate.gold_relation is not None
                else -100
                for item in payload.train_candidates
            ],
            dtype=torch.long,
        )
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        generator = torch.Generator(device="cpu").manual_seed(context.request.seed)
        batch_count = math.ceil(len(input_ids) / self.config.batch_size)
        execution_steps = 0
        final_loss: float | None = None
        model.train()
        for _ in range(self.config.epochs):
            order = torch.randperm(len(input_ids), generator=generator)
            for batch_index in range(batch_count):
                indices = order[
                    batch_index * self.config.batch_size : (batch_index + 1) * self.config.batch_size
                ]
                edge_logits, relation_logits = model(
                    input_ids[indices].to(device),
                    attention_mask[indices].to(device),
                )
                batch_edges = edge_targets[indices].to(device)
                batch_relations = relation_targets[indices].to(device)
                edge_loss = functional.binary_cross_entropy_with_logits(
                    edge_logits,
                    batch_edges,
                    pos_weight=torch.tensor(4.0, device=device),
                )
                positive_mask = batch_relations != -100
                relation_loss = (
                    functional.cross_entropy(
                        relation_logits[positive_mask],
                        batch_relations[positive_mask],
                    )
                    if bool(positive_mask.any().item())
                    else torch.zeros((), device=device)
                )
                loss = edge_loss + relation_loss
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                final_loss = float(loss.detach().cpu().item())
                execution_steps += 1
        if execution_steps <= 0 or final_loss is None:
            raise RuntimeError("cross-encoder completed zero optimization steps")
        checkpoint = context.run_directory / "model.safetensors"
        save_model(model, str(checkpoint))
        tokenizer.save_pretrained(context.run_directory / "tokenizer")
        (context.run_directory / "model-config.json").write_text(
            json.dumps(self.config.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            model.eval()
            probabilities: list[float] = []
            all_relation_logits: list[tuple[float, ...]] = []
            latencies: list[float] = []
            with torch.inference_mode():
                for start in range(0, len(candidates), self.config.inference_batch_size):
                    batch = candidates[start : start + self.config.inference_batch_size]
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = perf_counter()
                    batch_ids, batch_mask = self._encode(tokenizer, batch)
                    edge_logits, relation_logits = model(
                        batch_ids.to(device),
                        batch_mask.to(device),
                    )
                    probabilities_batch = torch.sigmoid(edge_logits)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in probabilities_batch.cpu().tolist())
                    all_relation_logits.extend(
                        tuple(float(value) for value in row)
                        for row in relation_logits.cpu().tolist()
                    )
            return CandidateScoreBatch(
                edge_probabilities=tuple(probabilities),
                relation_logits=tuple(all_relation_logits),
                latency_samples_ms=tuple(latencies),
            )

        return evaluate_and_write(
            payload=payload,
            run_directory=context.run_directory,
            checkpoint_path=checkpoint.name,
            score_candidates=score_candidates,
            edge_threshold=self.config.edge_threshold,
            execution_steps=execution_steps,
            training_loss=final_loss,
            calibration_enabled=context.request.ablation != AblationName.CALIBRATION,
        )


__all__ = ["CrossEncoderAdapter", "CrossEncoderConfig", "serialize_candidate"]
