"""Calibratable structural-only reference system."""

import json
import math
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field
from safetensors.torch import save_file
import torch
from torch import nn
import torch.nn.functional as functional

from workbench.research.erst.contracts import AblationName, MandatoryExperimentSystem
from workbench.research.erst.data import HarnessCandidate, ScreeningCorpusPayload
from workbench.research.erst.runner import SystemExecutionResult, SystemRunContext
from workbench.research.erst.systems.common import CandidateScoreBatch, evaluate_and_write


class StructuralConfig(BaseModel):
    """Frozen finite optimization and decoding configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature_count: int = 9
    hidden_size: int = 64
    epochs: int = 20
    batch_size: int = 512
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class _StructuralClassifier(nn.Module):
    feature_mean: nn.Parameter
    feature_scale: nn.Parameter

    def __init__(self, config: StructuralConfig, relation_count: int) -> None:
        super().__init__()
        self.feature_mean = nn.Parameter(torch.zeros(config.feature_count), requires_grad=False)
        self.feature_scale = nn.Parameter(torch.ones(config.feature_count), requires_grad=False)
        self.encoder = nn.Sequential(
            nn.Linear(config.feature_count, config.hidden_size),
            nn.GELU(),
            nn.Linear(config.hidden_size, config.hidden_size),
            nn.GELU(),
        )
        self.edge_head = nn.Linear(config.hidden_size, 1)
        self.relation_head = nn.Linear(config.hidden_size, relation_count)

    def set_normalization(self, features: torch.Tensor) -> None:
        mean = features.mean(dim=0)
        scale = features.std(dim=0, unbiased=False).clamp_min(1e-6)
        self.feature_mean.copy_(mean)
        self.feature_scale.copy_(scale)

    def forward(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        encoded = self.encoder((features - self.feature_mean) / self.feature_scale)
        return self.edge_head(encoded).squeeze(-1), self.relation_head(encoded)


class StructuralOnlyAdapter:
    """Train and score the structural control through the shared harness path."""

    system = MandatoryExperimentSystem.STRUCTURAL_ONLY

    def __init__(self, *, config: StructuralConfig, architecture_config_sha256: str) -> None:
        self.config = config
        self._architecture_config_sha256 = architecture_config_sha256

    @property
    def architecture_config_sha256(self) -> str:
        return self._architecture_config_sha256

    @staticmethod
    def _training_tensors(
        candidates: tuple[HarnessCandidate, ...],
        relation_to_index: dict[str, int],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        features = torch.tensor(
            [candidate.candidate.structural_features for candidate in candidates],
            dtype=torch.float32,
        )
        edge_targets = torch.tensor(
            [float(candidate.candidate.is_gold_edge) for candidate in candidates],
            dtype=torch.float32,
        )
        relation_targets = torch.tensor(
            [
                relation_to_index[candidate.candidate.gold_relation]
                if candidate.candidate.gold_relation is not None
                else -100
                for candidate in candidates
            ],
            dtype=torch.long,
        )
        return features, edge_targets, relation_targets

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        payload = context.data.payload
        relations = payload.raw_relation_inventory.labels
        relation_to_index = {relation: index for index, relation in enumerate(relations)}
        torch.manual_seed(context.request.seed)
        device = torch.device(context.request.device)
        features, edge_targets, relation_targets = self._training_tensors(
            payload.train_candidates,
            relation_to_index,
        )
        model = _StructuralClassifier(self.config, len(relations)).to(device)
        model.set_normalization(features.to(device))
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        generator = torch.Generator(device="cpu").manual_seed(context.request.seed)
        batch_count = math.ceil(len(features) / self.config.batch_size)
        execution_steps = 0
        final_loss: float | None = None
        model.train()
        for _ in range(self.config.epochs):
            order = torch.randperm(len(features), generator=generator)
            for batch_index in range(batch_count):
                indices = order[
                    batch_index * self.config.batch_size : (batch_index + 1) * self.config.batch_size
                ]
                batch_features = features[indices].to(device)
                batch_edges = edge_targets[indices].to(device)
                batch_relations = relation_targets[indices].to(device)
                edge_logits, relation_logits = model(batch_features)
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
                optimizer.step()
                final_loss = float(loss.detach().cpu().item())
                execution_steps += 1
        if execution_steps <= 0 or final_loss is None:
            raise RuntimeError("structural system completed zero optimization steps")
        checkpoint = context.run_directory / "model.safetensors"
        save_file(model.state_dict(), checkpoint)
        (context.run_directory / "model-config.json").write_text(
            json.dumps(self.config.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            model.eval()
            probabilities: list[float] = []
            all_relation_logits: list[tuple[float, ...]] = []
            latency_samples: list[float] = []
            with torch.inference_mode():
                for start in range(0, len(candidates), 4096):
                    batch = candidates[start : start + 4096]
                    batch_features = torch.tensor(
                        [item.candidate.structural_features for item in batch],
                        dtype=torch.float32,
                        device=device,
                    )
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = perf_counter()
                    edge_logits, relation_logits = model(batch_features)
                    edge_probabilities = torch.sigmoid(edge_logits)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latency_samples.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in edge_probabilities.cpu().tolist())
                    all_relation_logits.extend(
                        tuple(float(value) for value in row)
                        for row in relation_logits.cpu().tolist()
                    )
            return CandidateScoreBatch(
                edge_probabilities=tuple(probabilities),
                relation_logits=tuple(all_relation_logits),
                latency_samples_ms=tuple(latency_samples),
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
            mps_peak_allocated_bytes=None,
        )


__all__ = ["StructuralConfig", "StructuralOnlyAdapter"]
