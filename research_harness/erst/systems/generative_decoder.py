"""Qwen3 PEFT constrained decoder with an explicit no-edge outcome."""

from collections.abc import Callable
from importlib import import_module
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast

import torch
from torch import nn
import torch.nn.functional as functional
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from isanlp_rst.erst.environment import load_repository_environment
from research_harness.erst.configuration import GenerativeDecoderConfig
from research_harness.erst.contracts import AblationName, MandatoryExperimentSystem
from research_harness.erst.data import HarnessCandidate, ScreeningCorpusPayload
from research_harness.erst.runner import (
    ExperimentExecutionError,
    SystemExecutionResult,
    SystemRunContext,
)
from research_harness.erst.systems.common import CandidateScoreBatch, evaluate_and_write
from research_harness.erst.systems.cross_encoder import serialize_candidate


class _PeftApi(Protocol):
    LoraConfig: Callable[..., object]
    get_peft_model: Callable[[PreTrainedModel, object], PreTrainedModel]


def _load_peft() -> _PeftApi:
    """Load the harness-only PEFT dependency through a typed lazy boundary."""

    try:
        module = import_module("peft")
    except ModuleNotFoundError as error:
        raise ExperimentExecutionError(
            failure_type="MissingHarnessDependencyError",
            message="Qwen3 comparison requires the independent research_harness Pixi environment",
            evidence=b"missing-peft-0.20.0",
            incompatible=True,
        ) from error
    if not hasattr(module, "LoraConfig") or not hasattr(module, "get_peft_model"):
        raise ExperimentExecutionError(
            failure_type="InvalidHarnessDependencyError",
            message="installed PEFT module does not expose the required LoRA API",
            evidence=b"invalid-peft-api",
            incompatible=True,
        )
    return cast(_PeftApi, module)


def _label_tokens(relations: tuple[str, ...], no_edge_label: str) -> tuple[str, ...]:
    """Create stable single-token decoder outcomes without encoding label semantics."""

    labels = (no_edge_label, *relations)
    width = max(2, len(str(len(labels) - 1)))
    return tuple(f"<ERST_{index:0{width}d}>" for index in range(len(labels)))


def _serialize_prompt(candidate: HarnessCandidate) -> str:
    source, target = serialize_candidate(
        candidate,
        signal_aware=True,
        include_structure_tokens=True,
    )
    return (
        "Classify the licensed eRST secondary edge. Return exactly one outcome token.\n"
        f"SOURCE: {source}\nTARGET: {target}\nOUTCOME:"
    )


class GenerativeDecoderAdapter:
    """Train and evaluate Qwen3 by next-token decoding over edge/no-edge labels."""

    system = MandatoryExperimentSystem.QWEN3_DEDISCO

    def __init__(
        self,
        *,
        config: GenerativeDecoderConfig,
        architecture_config_sha256: str,
        repository_root: Path,
    ) -> None:
        self.config = config
        self._architecture_config_sha256 = architecture_config_sha256
        self.repository_root = repository_root.resolve()

    @property
    def architecture_config_sha256(self) -> str:
        return self._architecture_config_sha256

    def _load(
        self,
        *,
        relations: tuple[str, ...],
        device: torch.device,
    ) -> tuple[PreTrainedTokenizerBase, PreTrainedModel, tuple[int, ...]]:
        environment = load_repository_environment(self.repository_root)
        token = environment.hf_token.get_secret_value() if environment.hf_token is not None else None
        outcome_tokens = _label_tokens(relations, self.config.no_edge_label)
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_id,
                revision=self.config.model_revision,
                use_fast=True,
                token=token,
            )
            if not tokenizer.is_fast:
                raise ValueError("Qwen3 decoder requires a verified fast tokenizer")
            tokenizer.add_special_tokens({"additional_special_tokens": list(outcome_tokens)})
            if tokenizer.pad_token_id is None:
                if tokenizer.eos_token_id is None:
                    raise ValueError("Qwen3 tokenizer has neither a pad nor EOS token")
                tokenizer.pad_token = tokenizer.eos_token
            model = AutoModelForCausalLM.from_pretrained(
                self.config.model_id,
                revision=self.config.model_revision,
                use_safetensors=True,
                token=token,
                torch_dtype=torch.float16 if device.type == "mps" else torch.float32,
            )
            model.resize_token_embeddings(len(tokenizer))
            token_ids = tuple(tokenizer.convert_tokens_to_ids(item) for item in outcome_tokens)
            if any(not isinstance(item, int) or item < 0 for item in token_ids):
                raise ValueError("Qwen3 outcome tokens did not resolve to tokenizer IDs")
            peft = _load_peft()
            lora_config = peft.LoraConfig(
                r=self.config.lora_rank,
                lora_alpha=self.config.lora_alpha,
                lora_dropout=self.config.lora_dropout,
                target_modules=list(self.config.target_modules),
                bias="none",
                task_type="CAUSAL_LM",
            )
            model = peft.get_peft_model(model, lora_config)
            cast(nn.Module, model).to(device)
        except ExperimentExecutionError:
            raise
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            evidence = json.dumps(
                {
                    "exception_type": type(error).__name__,
                    "model_id": self.config.model_id,
                    "model_revision": self.config.model_revision,
                },
                sort_keys=True,
            ).encode()
            raise ExperimentExecutionError(
                failure_type="GenerativeDecoderCompatibilityError",
                message="pinned Qwen3 PEFT decoder failed its authenticated compatibility load",
                evidence=evidence,
                incompatible=True,
            ) from error
        return tokenizer, model, cast(tuple[int, ...], token_ids)

    def _encode_prompts(
        self,
        tokenizer: PreTrainedTokenizerBase,
        candidates: tuple[HarnessCandidate, ...],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = tokenizer(
            [_serialize_prompt(candidate) for candidate in candidates],
            max_length=self.config.max_length,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        return encoded["input_ids"], encoded["attention_mask"]

    @staticmethod
    def _outcome_logits(
        model: nn.Module,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        outcome_ids: torch.Tensor,
    ) -> torch.Tensor:
        output = model(input_ids=input_ids, attention_mask=attention_mask)
        last_positions = attention_mask.sum(dim=1) - 1
        rows = torch.arange(len(input_ids), device=input_ids.device)
        return output.logits[rows, last_positions][:, outcome_ids]

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        payload = context.data.payload
        relations = payload.raw_relation_inventory.labels
        relation_to_index = {relation: index for index, relation in enumerate(relations)}
        device = torch.device(context.request.device)
        torch.manual_seed(context.request.seed)
        tokenizer, model, token_ids = self._load(relations=relations, device=device)
        input_ids, attention_mask = self._encode_prompts(tokenizer, payload.train_candidates)
        targets = torch.tensor(
            [
                relation_to_index[item.candidate.gold_relation] + 1
                if item.candidate.gold_relation is not None
                else 0
                for item in payload.train_candidates
            ],
            dtype=torch.long,
        )
        trainable = tuple(parameter for parameter in model.parameters() if parameter.requires_grad)
        if not trainable:
            raise RuntimeError("Qwen3 PEFT decoder exposed no trainable adapter parameters")
        optimizer = torch.optim.AdamW(trainable, lr=self.config.learning_rate)
        generator = torch.Generator(device="cpu").manual_seed(context.request.seed)
        outcome_ids = torch.tensor(token_ids, dtype=torch.long, device=device)
        batch_count = math.ceil(len(input_ids) / self.config.batch_size)
        steps = 0
        final_loss: float | None = None
        optimizer.zero_grad()
        model.train()
        for _ in range(self.config.epochs):
            order = torch.randperm(len(input_ids), generator=generator)
            for batch_index in range(batch_count):
                indices = order[
                    batch_index * self.config.batch_size : (batch_index + 1) * self.config.batch_size
                ]
                logits = self._outcome_logits(
                    model,
                    input_ids[indices].to(device),
                    attention_mask[indices].to(device),
                    outcome_ids,
                )
                loss = functional.cross_entropy(logits, targets[indices].to(device))
                (loss / self.config.gradient_accumulation_steps).backward()
                should_step = (
                    (batch_index + 1) % self.config.gradient_accumulation_steps == 0
                    or batch_index + 1 == batch_count
                )
                if should_step:
                    torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                    optimizer.step()
                    optimizer.zero_grad()
                    steps += 1
                final_loss = float(loss.detach().cpu().item())
        if steps <= 0 or final_loss is None:
            raise RuntimeError("Qwen3 PEFT decoder completed zero optimization steps")
        adapter_directory = context.run_directory / "adapter"
        model.save_pretrained(adapter_directory, safe_serialization=True)
        tokenizer.save_pretrained(context.run_directory / "tokenizer")
        checkpoint = adapter_directory / "adapter_model.safetensors"
        if not checkpoint.is_file():
            raise RuntimeError("Qwen3 PEFT save did not create adapter_model.safetensors")

        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            edge_probabilities: list[float] = []
            relation_rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for start in range(0, len(candidates), self.config.batch_size):
                    batch = candidates[start : start + self.config.batch_size]
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = perf_counter()
                    ids, mask = self._encode_prompts(tokenizer, batch)
                    logits = self._outcome_logits(
                        model,
                        ids.to(device),
                        mask.to(device),
                        outcome_ids,
                    )
                    probabilities = torch.softmax(logits, dim=-1)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    edge_probabilities.extend(
                        float(value) for value in (1.0 - probabilities[:, 0]).cpu().tolist()
                    )
                    relation_rows.extend(
                        tuple(float(value) for value in row)
                        for row in logits[:, 1:].cpu().tolist()
                    )
            return CandidateScoreBatch(
                edge_probabilities=tuple(edge_probabilities),
                relation_logits=tuple(relation_rows),
                latency_samples_ms=tuple(latencies),
            )

        return evaluate_and_write(
            payload=payload,
            run_directory=context.run_directory,
            checkpoint_path=checkpoint.relative_to(context.run_directory).as_posix(),
            score_candidates=score_candidates,
            edge_threshold=self.config.edge_threshold,
            execution_steps=steps,
            training_loss=final_loss,
            calibration_enabled=context.request.ablation != AblationName.CALIBRATION,
        )


__all__ = ["GenerativeDecoderAdapter"]
