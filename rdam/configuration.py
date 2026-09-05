"""Immutable, closed settings for one local machine; credentials are never fields."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from rdam._execution import ExecutionPolicy
from rdam._strict import StrictModel
from rdam.frameworks import BOUNDARY_TECHNIQUES, Technique


def _output_retries() -> int:
    from rdam._llm import DEFAULT_OUTPUT_RETRIES

    return DEFAULT_OUTPUT_RETRIES


def _transport_retries() -> int:
    from rdam._llm import DEFAULT_TRANSPORT_RETRIES

    return DEFAULT_TRANSPORT_RETRIES


def _deadline() -> float:
    from rdam._llm import DEFAULT_TRANSPORT_DEADLINE_SECONDS

    return DEFAULT_TRANSPORT_DEADLINE_SECONDS


def _dung_capacity() -> int:
    from rdam.dung.semantics import DEFAULT_CAPACITY

    return DEFAULT_CAPACITY


class LlmSettings(StrictModel):
    model: str | None = None
    output_retries: int = Field(default_factory=_output_retries, ge=0)
    transport_retries: int = Field(default_factory=_transport_retries, ge=0)
    transport_deadline_seconds: float = Field(default_factory=_deadline, gt=0)

    @field_validator("model")
    @classmethod
    def canonical_model(cls, value: str | None) -> str:
        from rdam._llm import configured_model, normalize_model_identity

        return normalize_model_identity(configured_model() if value is None else value)


class TechniqueModels(StrictModel):
    pdtb: str | None = None
    sdrt: str | None = None
    toulmin: str | None = None
    walton: str | None = None

    @field_validator("pdtb", "sdrt", "toulmin", "walton")
    @classmethod
    def canonical_model(cls, value: str | None) -> str | None:
        from rdam._llm import normalize_model_identity

        return None if value is None else normalize_model_identity(value)


class PublishedRstModel(StrictModel):
    kind: Literal["published"] = "published"
    version: str = Field(min_length=1)


class LocalRstModel(StrictModel):
    kind: Literal["local_release"] = "local_release"
    store: Path
    release_id: str = Field(min_length=1)

    @field_validator("release_id")
    @classmethod
    def single_member(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or "\\" in value or not value.strip():
            raise ValueError("release_id must be a single directory member")
        return value

    @field_validator("store")
    @classmethod
    def absolute_store(cls, value: Path) -> Path:
        return value.resolve()


class RstSettings(StrictModel):
    model: Annotated[PublishedRstModel | LocalRstModel, Field(discriminator="kind")] | None = None
    relinventory: str | None = Field(default=None, min_length=1)
    device: str = Field(default="auto", pattern=r"^(auto|cpu|mps|cuda(?::[0-9]+)?)$")
    erst_checkpoint: Path | None = None
    default_formalism: Literal["rst_tree", "erst_graph"] = "rst_tree"
    evidence_detail: Literal["decision_complete", "normalized_distributions"] = "decision_complete"
    marker_refinement: Literal["evidence_preserving", "disabled"] = "evidence_preserving"

    @field_validator("erst_checkpoint")
    @classmethod
    def absolute_checkpoint(cls, value: Path | None) -> Path | None:
        return None if value is None else value.resolve()


class ExecutionSettings(StrictModel):
    max_workers: int = Field(default=ExecutionPolicy().max_workers, ge=1, le=len(BOUNDARY_TECHNIQUES))
    cache_directory: Path | None = None

    @field_validator("cache_directory")
    @classmethod
    def absolute_cache(cls, value: Path | None) -> Path | None:
        return None if value is None else value.resolve()

    def policy(self) -> ExecutionPolicy:
        return ExecutionPolicy(max_workers=self.max_workers, cache_directory=self.cache_directory)


class MachineConfig(StrictModel):
    contract: Literal["rdam.configuration"] = "rdam.configuration"
    contract_version: Literal["1.0.0"] = "1.0.0"
    llm: LlmSettings = Field(default_factory=LlmSettings)
    technique_models: TechniqueModels = Field(default_factory=TechniqueModels)
    rst: RstSettings = Field(default_factory=RstSettings)
    dung_capacity: int = Field(default_factory=_dung_capacity, gt=0)
    execution: ExecutionSettings = Field(default_factory=ExecutionSettings)

    def model_for(self, technique: Technique) -> str:
        selected: str | None = getattr(self.technique_models, technique.value, None)
        resolved = selected or self.llm.model
        if resolved is None:
            raise ValueError("configured machine has no resolved LLM identity")
        return resolved

    @model_validator(mode="after")
    def resolved_configuration(self) -> Self:
        if self.llm.model is None:
            raise ValueError("LLM defaults must be resolved at construction")
        return self
