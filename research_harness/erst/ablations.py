"""Frozen, model-neutral ablation definitions and evidence boundaries."""

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_harness.erst.contracts import AblationName, MandatoryExperimentSystem
from research_harness.erst.data import ScreeningCorpusPayload
from research_harness.erst.runner import (
    ExperimentSystemAdapter,
    PreparedExperimentData,
    SystemExecutionResult,
    SystemRunContext,
)


class AblationDefinition(BaseModel):
    """Exact intervention represented by one required ablation run family."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: AblationName
    intervention: str = Field(min_length=1)
    preserved_inputs: tuple[str, ...] = Field(min_length=1)


class AblationPlan(BaseModel):
    """Complete, hashed intervention plan frozen before ablation execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    champion_system: MandatoryExperimentSystem
    definitions: tuple[AblationDefinition, ...]
    plan_sha256: str = ""

    @model_validator(mode="after")
    def validate_plan(self) -> "AblationPlan":
        if tuple(item.name for item in self.definitions) != tuple(AblationName):
            raise ValueError("ablation plan must define every intervention exactly once in order")
        encoded = json.dumps(
            self.model_dump(mode="json", exclude={"plan_sha256"}),
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        expected = hashlib.sha256(encoded).hexdigest()
        if self.plan_sha256 and self.plan_sha256 != expected:
            raise ValueError("ablation plan hash does not match canonical content")
        object.__setattr__(self, "plan_sha256", expected)
        return self


class AblationResult(BaseModel):
    """Seed-complete measured delta for one intervention."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    plan_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    name: AblationName
    run_receipts: tuple[str, ...] = Field(min_length=1)
    mean_full_f: float = Field(ge=0.0, le=1.0)
    delta_from_unablated: float


def canonical_ablation_plan(
    *,
    protocol_sha256: str,
    champion_system: MandatoryExperimentSystem,
) -> AblationPlan:
    """Create the complete intervention authority without architecture-specific shortcuts."""

    descriptions = {
        AblationName.SIGNAL_MARKING: "remove signal boundary marking while preserving raw candidate text",
        AblationName.STRUCTURAL_FEATURES: "zero structural features while preserving candidate membership",
        AblationName.PRIMARY_PATH_ENCODING: "remove primary-path tokens or graph path features",
        AblationName.CONTEXT: "remove sentence context outside the two candidate node spans",
        AblationName.GRAPH_FUSION: "bypass graph message passing while preserving node representations",
        AblationName.HARD_NEGATIVES: "replace hard negatives with an equal-count seeded uniform sample",
        AblationName.CALIBRATION: "use unscaled probabilities and the neutral 0.5 threshold",
        AblationName.RAW_VS_COARSE_LABELS: "train coarse ontology labels while preserving raw labels for scoring",
    }
    return AblationPlan(
        protocol_sha256=protocol_sha256,
        champion_system=champion_system,
        definitions=tuple(
            AblationDefinition(
                name=name,
                intervention=descriptions[name],
                preserved_inputs=(
                    "official_train_dev_partitions",
                    "complete_dev_candidates",
                    "repository_scorer",
                    "seed_and_hardware_protocol",
                ),
            )
            for name in AblationName
        ),
    )


class AblationAdapter:
    """Apply one frozen feature intervention before invoking the unchanged system adapter."""

    def __init__(self, base: ExperimentSystemAdapter[ScreeningCorpusPayload]) -> None:
        self.base = base
        self.system = base.system

    @property
    def architecture_config_sha256(self) -> str:
        return self.base.architecture_config_sha256

    def execute(self, context: SystemRunContext[ScreeningCorpusPayload]) -> SystemExecutionResult:
        if context.request.ablation is None:
            raise ValueError("ablation adapter requires an ablation-stage request")
        transformed = context.data.payload.for_ablation(
            context.request.ablation,
            seed=context.request.seed,
        )
        return self.base.execute(
            SystemRunContext(
                request=context.request,
                run_directory=context.run_directory,
                data=PreparedExperimentData(identity=context.data.identity, payload=transformed),
            )
        )


__all__ = [
    "AblationAdapter",
    "AblationDefinition",
    "AblationPlan",
    "AblationResult",
    "canonical_ablation_plan",
]
