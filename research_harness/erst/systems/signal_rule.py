"""Deterministic signal-plus-rule reference system."""

import json
from time import perf_counter

from pydantic import BaseModel, ConfigDict, Field

from research_harness.erst.contracts import AblationName, MandatoryExperimentSystem
from research_harness.erst.data import HarnessCandidate, ScreeningCorpusPayload
from research_harness.erst.runner import SystemExecutionResult, SystemRunContext
from research_harness.erst.systems.common import CandidateScoreBatch, evaluate_and_write


class SignalRuleConfig(BaseModel):
    """Frozen deterministic scoring policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edge_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    licensed_probability: float = Field(default=0.75, ge=0.0, le=1.0)
    fallback_probability: float = Field(default=0.10, ge=0.0, le=1.0)
    maximum_local_edu_distance: int = Field(default=2, ge=0)


class SignalRuleAdapter:
    """Apply a train-inventory-aware rule without reading any gold candidate label."""

    system = MandatoryExperimentSystem.SIGNAL_RULE

    def __init__(self, *, config: SignalRuleConfig, architecture_config_sha256: str) -> None:
        self.config = config
        self._architecture_config_sha256 = architecture_config_sha256

    @property
    def architecture_config_sha256(self) -> str:
        return self._architecture_config_sha256

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        payload = context.data.payload
        inventory = payload.raw_relation_inventory
        default_relation = max(
            inventory.labels,
            key=lambda relation: (inventory.label_counts[relation], relation),
        )
        relation_index = {relation: index for index, relation in enumerate(inventory.labels)}
        checkpoint = context.run_directory / "rule-config.json"
        checkpoint.write_text(
            json.dumps(
                {
                    "config": self.config.model_dump(mode="json"),
                    "default_relation": default_relation,
                    "relation_inventory_sha256": inventory.inventory_sha256,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        def score_candidates(candidates: tuple[HarnessCandidate, ...]) -> CandidateScoreBatch:
            started = perf_counter()
            probabilities: list[float] = []
            relation_logits: list[tuple[float, ...]] = []
            for harness_candidate in candidates:
                candidate = harness_candidate.candidate
                compatible = tuple(
                    relation
                    for relation in candidate.compatible_relations
                    if relation in relation_index
                )
                locally_licensed = (
                    bool(harness_candidate.signal_char_spans)
                    and bool(compatible)
                    and abs(candidate.edu_distance) <= self.config.maximum_local_edu_distance
                )
                probabilities.append(
                    self.config.licensed_probability
                    if locally_licensed
                    else self.config.fallback_probability
                )
                selected_relation = (
                    max(
                        compatible,
                        key=lambda relation: (inventory.label_counts[relation], relation),
                    )
                    if compatible
                    else default_relation
                )
                logits = [-5.0] * len(inventory.labels)
                logits[relation_index[selected_relation]] = 5.0
                relation_logits.append(tuple(logits))
            elapsed_ms = (perf_counter() - started) * 1000.0
            return CandidateScoreBatch(
                edge_probabilities=tuple(probabilities),
                relation_logits=tuple(relation_logits),
                latency_samples_ms=(elapsed_ms,),
            )

        return evaluate_and_write(
            payload=payload,
            run_directory=context.run_directory,
            checkpoint_path=checkpoint.name,
            score_candidates=score_candidates,
            edge_threshold=self.config.edge_threshold,
            execution_steps=len(payload.train_candidates),
            training_loss=None,
            calibration_enabled=context.request.ablation != AblationName.CALIBRATION,
        )


__all__ = ["SignalRuleAdapter", "SignalRuleConfig"]
