"""Existing dual-encoder, bilinear, structural reference adapter."""

import json
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field
from safetensors.torch import save_model
import torch
from torch.utils.data import DataLoader

from offline_workbench.training.erst.dataset import GUMSecondaryEdgeDataset
from isanlp_rst.erst.environment import load_repository_environment
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from research_harness.erst.contracts import AblationName, MandatoryExperimentSystem
from research_harness.erst.data import HarnessCandidate, ScreeningCorpusPayload
from research_harness.erst.runner import (
    ExperimentExecutionError,
    SystemExecutionResult,
    SystemRunContext,
)
from research_harness.erst.systems.common import CandidateScoreBatch, evaluate_and_write


class DualEncoderConfig(BaseModel):
    """Frozen current-code reference optimization configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str = Field(min_length=1)
    model_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    epochs: int = Field(default=4, gt=0)
    batch_size: int = Field(default=16, gt=0)
    inference_batch_size: int = Field(default=64, gt=0)
    learning_rate: float = Field(default=3e-5, gt=0.0)
    weight_decay: float = Field(default=0.01, ge=0.0)
    max_length: int = Field(default=128, gt=0)
    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class DualEncoderAdapter:
    """Exercise the unchanged repository scorer or retain measured incompatibility."""

    system = MandatoryExperimentSystem.EXISTING_DUAL_ENCODER

    def __init__(
        self,
        *,
        config: DualEncoderConfig,
        architecture_config_sha256: str,
        repository_root: Path,
    ) -> None:
        self.config = config
        self._architecture_config_sha256 = architecture_config_sha256
        self.repository_root = repository_root.resolve()

    @property
    def architecture_config_sha256(self) -> str:
        return self._architecture_config_sha256

    @staticmethod
    def _batch_to_device(
        batch: dict[str, torch.Tensor],
        device: torch.device,
    ) -> dict[str, torch.Tensor]:
        return {name: tensor.to(device) for name, tensor in batch.items()}

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        payload = context.data.payload
        environment = load_repository_environment(self.repository_root)
        del environment
        device = torch.device(context.request.device)
        torch.manual_seed(context.request.seed)
        try:
            model = NeuralSecondaryEdgeScorer(
                model_name_or_path=self.config.model_id,
                model_revision=self.config.model_revision,
                raw_relation_inventory=payload.raw_relation_inventory.labels,
                device=device,
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
                failure_type="DualEncoderCompatibilityError",
                message="pinned existing dual-encoder could not satisfy fast-tokenizer/safetensors runtime contracts",
                evidence=evidence,
                incompatible=True,
            ) from error
        raw_train = tuple(item.candidate for item in payload.train_candidates)
        train_dataset = GUMSecondaryEdgeDataset(
            raw_train,
            tokenizer=model.tokenizer,
            max_length=self.config.max_length,
            raw_relation_inventory=payload.raw_relation_inventory.labels,
        )
        generator = torch.Generator(device="cpu").manual_seed(context.request.seed)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            generator=generator,
        )
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        execution_steps = 0
        final_loss: float | None = None
        model.train()
        for _ in range(self.config.epochs):
            for batch in train_loader:
                device_batch = self._batch_to_device(batch, device)
                result = model(**device_batch)
                loss = result["loss"]
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                final_loss = float(loss.detach().cpu().item())
                execution_steps += 1
        if execution_steps <= 0 or final_loss is None:
            raise RuntimeError("dual-encoder completed zero optimization steps")
        checkpoint = context.run_directory / "model.safetensors"
        save_model(model, str(checkpoint))
        (context.run_directory / "model-config.json").write_text(
            json.dumps(self.config.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            dataset = GUMSecondaryEdgeDataset(
                tuple(item.candidate for item in candidates),
                tokenizer=model.tokenizer,
                max_length=self.config.max_length,
                raw_relation_inventory=payload.raw_relation_inventory.labels,
            )
            loader = DataLoader(
                dataset,
                batch_size=self.config.inference_batch_size,
                shuffle=False,
            )
            probabilities: list[float] = []
            relation_logits: list[tuple[float, ...]] = []
            latencies: list[float] = []
            model.eval()
            with torch.inference_mode():
                for batch in loader:
                    device_batch = self._batch_to_device(batch, device)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    started = perf_counter()
                    result = model(**device_batch)
                    if device.type == "mps":
                        torch.mps.synchronize()
                    latencies.append((perf_counter() - started) * 1000.0)
                    probabilities.extend(float(value) for value in result["edge_probs"].cpu().tolist())
                    relation_logits.extend(
                        tuple(float(value) for value in row)
                        for row in result["rel_logits"].cpu().tolist()
                    )
            return CandidateScoreBatch(
                edge_probabilities=tuple(probabilities),
                relation_logits=tuple(relation_logits),
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


__all__ = ["DualEncoderAdapter", "DualEncoderConfig"]
