"""XLM-R hierarchical adapter with a supervised contrastive prototype objective."""

import json
import math
from pathlib import Path
from time import perf_counter

from safetensors.torch import save_file
import torch
from torch import nn
import torch.nn.functional as functional
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from isanlp_rst.erst.environment import load_repository_environment
from research_harness.erst.configuration import HierarchicalAdapterConfig
from research_harness.erst.contracts import AblationName, MandatoryExperimentSystem
from research_harness.erst.data import HarnessCandidate, ScreeningCorpusPayload
from research_harness.erst.runner import (
    ExperimentExecutionError,
    SystemExecutionResult,
    SystemRunContext,
)
from research_harness.erst.systems.common import CandidateScoreBatch, evaluate_and_write
from research_harness.erst.systems.cross_encoder import serialize_candidate


class _HierarchicalAdapterModel(nn.Module):
    encoder: PreTrainedModel

    def __init__(
        self,
        encoder: PreTrainedModel,
        config: HierarchicalAdapterConfig,
        relation_count: int,
    ) -> None:
        super().__init__()
        self.encoder = encoder
        for parameter in self.encoder.parameters():
            parameter.requires_grad = False
        hidden_size = getattr(encoder.config, "hidden_size", None)
        if not isinstance(hidden_size, int) or hidden_size <= 0:
            raise ValueError("hierarchical adapter requires a positive encoder hidden size")
        self.adapter = nn.Sequential(
            nn.Linear(hidden_size, config.adapter_size),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(config.adapter_size, hidden_size),
        )
        self.layer_norm = nn.LayerNorm(hidden_size)
        self.edge_head = nn.Linear(hidden_size, 1)
        self.relation_head = nn.Linear(hidden_size, relation_count)
        self.relation_prototypes = nn.Parameter(torch.empty(relation_count, hidden_size))
        nn.init.normal_(self.relation_prototypes, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        with torch.no_grad():
            hidden = self.encoder(
                input_ids=input_ids,
                attention_mask=attention_mask,
            ).last_hidden_state
        mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        representation = self.layer_norm(pooled + self.adapter(pooled))
        return (
            self.edge_head(representation).squeeze(-1),
            self.relation_head(representation),
            representation,
        )

    def contrastive_logits(
        self,
        representations: torch.Tensor,
        temperature: float,
    ) -> torch.Tensor:
        normalized = functional.normalize(representations, dim=-1)
        prototypes = functional.normalize(self.relation_prototypes, dim=-1)
        return normalized @ prototypes.transpose(0, 1) / temperature


class HierarchicalAdapter:
    """Train/evaluate the pinned XLM-R adapter without modifying backbone weights."""

    system = MandatoryExperimentSystem.XLM_R_HIDAC

    def __init__(
        self,
        *,
        config: HierarchicalAdapterConfig,
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
        relation_count: int,
        device: torch.device,
    ) -> tuple[PreTrainedTokenizerBase, _HierarchicalAdapterModel]:
        environment = load_repository_environment(self.repository_root)
        token = environment.hf_token.get_secret_value() if environment.hf_token is not None else None
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_id,
                revision=self.config.model_revision,
                use_fast=True,
                token=token,
            )
            if not tokenizer.is_fast:
                raise ValueError("hierarchical adapter requires a verified fast tokenizer")
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
                failure_type="HierarchicalAdapterCompatibilityError",
                message="pinned XLM-R adapter failed its authenticated model/tokenizer load",
                evidence=evidence,
                incompatible=True,
            ) from error
        return tokenizer, _HierarchicalAdapterModel(encoder, self.config, relation_count).to(device)

    def _encode(
        self,
        tokenizer: PreTrainedTokenizerBase,
        candidates: tuple[HarnessCandidate, ...],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        serialized = tuple(
            serialize_candidate(
                candidate,
                signal_aware=True,
                include_structure_tokens=True,
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
        tokenizer, model = self._load(len(relations), device)
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
        trainable = tuple(parameter for parameter in model.parameters() if parameter.requires_grad)
        optimizer = torch.optim.AdamW(trainable, lr=self.config.learning_rate, weight_decay=0.01)
        generator = torch.Generator(device="cpu").manual_seed(context.request.seed)
        batch_count = math.ceil(len(input_ids) / self.config.batch_size)
        steps = 0
        final_loss: float | None = None
        model.train()
        for _ in range(self.config.epochs):
            order = torch.randperm(len(input_ids), generator=generator)
            for batch_index in range(batch_count):
                indices = order[
                    batch_index * self.config.batch_size : (batch_index + 1) * self.config.batch_size
                ]
                edge_logits, relation_logits, representations = model(
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
                if bool(positive_mask.any().item()):
                    relation_loss = functional.cross_entropy(
                        relation_logits[positive_mask],
                        batch_relations[positive_mask],
                    )
                    contrastive_loss = functional.cross_entropy(
                        model.contrastive_logits(
                            representations[positive_mask],
                            self.config.contrastive_temperature,
                        ),
                        batch_relations[positive_mask],
                    )
                else:
                    relation_loss = torch.zeros((), device=device)
                    contrastive_loss = torch.zeros((), device=device)
                loss = edge_loss + relation_loss + self.config.contrastive_weight * contrastive_loss
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                final_loss = float(loss.detach().cpu().item())
                steps += 1
        if steps <= 0 or final_loss is None:
            raise RuntimeError("hierarchical adapter completed zero optimization steps")
        checkpoint = context.run_directory / "adapter.safetensors"
        trainable_state = {
            name: tensor.detach().cpu().contiguous()
            for name, tensor in model.state_dict().items()
            if not name.startswith("encoder.")
        }
        save_file(trainable_state, checkpoint)
        tokenizer.save_pretrained(context.run_directory / "tokenizer")

        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            probabilities: list[float] = []
            relation_rows: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for start in range(0, len(candidates), self.config.inference_batch_size):
                    batch = candidates[start : start + self.config.inference_batch_size]
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = perf_counter()
                    ids, mask = self._encode(tokenizer, batch)
                    edge_logits, relation_logits, _ = model(ids.to(device), mask.to(device))
                    edge_probabilities = torch.sigmoid(edge_logits)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in edge_probabilities.cpu().tolist())
                    relation_rows.extend(
                        tuple(float(value) for value in row)
                        for row in relation_logits.cpu().tolist()
                    )
            return CandidateScoreBatch(
                edge_probabilities=tuple(probabilities),
                relation_logits=tuple(relation_rows),
                latency_samples_ms=tuple(latencies),
            )

        return evaluate_and_write(
            payload=payload,
            run_directory=context.run_directory,
            checkpoint_path=checkpoint.name,
            score_candidates=score_candidates,
            edge_threshold=self.config.edge_threshold,
            execution_steps=steps,
            training_loss=final_loss,
            calibration_enabled=context.request.ablation != AblationName.CALIBRATION,
        )


__all__ = ["HierarchicalAdapter"]
