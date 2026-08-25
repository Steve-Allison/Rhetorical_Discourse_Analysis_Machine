"""Shared, isolated execution and evidence persistence for all eRST systems."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path, PurePosixPath
import platform
import resource
import sys
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isanlp_rst.contracts.erst import CorpusPartition
from research_harness.erst.contracts import (
    AblationName,
    DocumentScore,
    EvaluationSetting,
    ExperimentDataIdentity,
    ExperimentIndex,
    ExperimentIndexEntry,
    ExperimentMetrics,
    ExperimentProtocol,
    ExperimentRunReceipt,
    ExperimentRunStatus,
    ExperimentStage,
    MandatoryExperimentSystem,
    ResourceEvidence,
    RunFailure,
)
from research_harness.erst.resources import MpsMemorySampler

PayloadT = TypeVar("PayloadT")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _percentile(samples: Sequence[float], fraction: float) -> float:
    if not samples:
        raise ValueError("latency percentile requires at least one sample")
    ordered = sorted(samples)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _physical_memory_bytes() -> int:
    page_size = os.sysconf("SC_PAGE_SIZE")
    page_count = os.sysconf("SC_PHYS_PAGES")
    if not isinstance(page_size, int) or not isinstance(page_count, int):
        raise RuntimeError("operating system did not report integral physical-memory values")
    return page_size * page_count


def _peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


class ExperimentRunRequest(BaseModel):
    """One requested execution with no corpus paths or mutable implementation state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    system: MandatoryExperimentSystem
    stage: ExperimentStage
    ablation: AblationName | None = None
    seed: int
    setting: EvaluationSetting
    partitions: tuple[CorpusPartition, ...] = Field(min_length=1)
    device: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_partitions(self) -> "ExperimentRunRequest":
        if (self.stage == ExperimentStage.ABLATION) != (self.ablation is not None):
            raise ValueError("ablation identity is required exactly for ablation-stage requests")
        allowed = (
            {CorpusPartition.TEST, CorpusPartition.TEST2}
            if self.stage == ExperimentStage.FINAL_EVALUATION
            else {CorpusPartition.TRAIN, CorpusPartition.DEV}
        )
        if not set(self.partitions).issubset(allowed):
            raise ValueError("run request partitions violate the stage's isolation boundary")
        return self


class SystemExecutionResult(BaseModel):
    """Successful adapter output before the runner verifies and hashes artifacts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_steps: int = Field(gt=0)
    checkpoint_path: str
    predictions_path: str
    scorer_output_path: str
    metrics: ExperimentMetrics
    document_scores: tuple[DocumentScore, ...] = Field(min_length=1)
    latency_samples_ms: tuple[float, ...] = Field(min_length=1)
    mps_peak_allocated_bytes: int | None = Field(default=None, ge=0)

    @field_validator("checkpoint_path", "predictions_path", "scorer_output_path")
    @classmethod
    def validate_artifact_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("system artifacts require relative POSIX paths inside the run directory")
        return value

    @field_validator("latency_samples_ms")
    @classmethod
    def validate_latencies(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if any(sample <= 0.0 for sample in value):
            raise ValueError("latency samples must be positive")
        return value


class ExperimentExecutionError(Exception):
    """Expected, evidence-bearing system failure or measured incompatibility."""

    def __init__(
        self,
        *,
        failure_type: str,
        message: str,
        evidence: bytes,
        incompatible: bool = False,
        retryable: bool = False,
        execution_steps: int = 0,
    ) -> None:
        super().__init__(message)
        if not failure_type or not message or not evidence:
            raise ValueError("experiment failures require a type, message, and non-empty evidence")
        if execution_steps < 0:
            raise ValueError("failed execution steps cannot be negative")
        self.failure_type = failure_type
        self.evidence_sha256 = _sha256_bytes(evidence)
        self.incompatible = incompatible
        self.retryable = retryable
        self.execution_steps = execution_steps


@dataclass(frozen=True, slots=True)
class PreparedExperimentData(Generic[PayloadT]):
    """Internal payload paired with its public, text-free governed identity."""

    identity: ExperimentDataIdentity
    payload: PayloadT


@dataclass(frozen=True, slots=True)
class SystemRunContext(Generic[PayloadT]):
    """One adapter's sandboxed output directory and read-only governed inputs."""

    request: ExperimentRunRequest
    run_directory: Path
    data: PreparedExperimentData[PayloadT]


class ExperimentSystemAdapter(Protocol[PayloadT]):
    """One system implementation accepted by the shared runner."""

    @property
    def system(self) -> MandatoryExperimentSystem: ...

    @property
    def architecture_config_sha256(self) -> str: ...

    def execute(self, context: SystemRunContext[PayloadT]) -> SystemExecutionResult: ...


class ExperimentIndexStore:
    """Atomic, append-only receipt and index persistence."""

    def __init__(self, root: Path, protocol_sha256: str) -> None:
        self.root = root.resolve()
        self.receipts = self.root / "receipts"
        self.index_path = self.root / "index.json"
        self.protocol_sha256 = protocol_sha256

    @staticmethod
    def _write_atomic(path: Path, content: str) -> None:
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        if temporary.exists():
            raise RuntimeError(f"stale atomic-write file exists: {temporary}")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    def load_verified(self) -> ExperimentIndex:
        if not self.index_path.exists():
            return ExperimentIndex(protocol_sha256=self.protocol_sha256, entries=())
        index = ExperimentIndex.model_validate_json(self.index_path.read_text(encoding="utf-8"))
        if index.protocol_sha256 != self.protocol_sha256:
            raise ValueError("experiment index belongs to a different protocol")
        for entry in index.entries:
            receipt_path = self.root / entry.receipt_path
            receipt = ExperimentRunReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
            if receipt.receipt_sha256 != entry.receipt_sha256 or receipt.run_id != entry.run_id:
                raise ValueError(f"experiment index entry does not match its receipt: {entry.run_id}")
        return index

    def append(self, receipt: ExperimentRunReceipt) -> ExperimentIndex:
        self.receipts.mkdir(parents=True, exist_ok=True)
        index = self.load_verified()
        if any(entry.run_id == receipt.run_id for entry in index.entries):
            raise ValueError(f"experiment run ID already exists: {receipt.run_id}")
        relative_path = f"receipts/{receipt.run_id}.json"
        receipt_path = self.root / relative_path
        if receipt_path.exists():
            raise ValueError(f"experiment receipt already exists: {relative_path}")
        self._write_atomic(receipt_path, receipt.model_dump_json(indent=2) + "\n")
        entry = ExperimentIndexEntry(
            run_id=receipt.run_id,
            system=receipt.system,
            stage=receipt.stage,
            status=receipt.status,
            seed=receipt.seed,
            receipt_path=relative_path,
            receipt_sha256=receipt.receipt_sha256,
        )
        updated = ExperimentIndex(
            protocol_sha256=self.protocol_sha256,
            entries=(*index.entries, entry),
        )
        self.root.mkdir(parents=True, exist_ok=True)
        self._write_atomic(self.index_path, updated.model_dump_json(indent=2) + "\n")
        return updated


class ExperimentRunner(Generic[PayloadT]):
    """Execute every architecture through one governed and evidence-bearing path."""

    def __init__(self, protocol: ExperimentProtocol, output_root: Path) -> None:
        self.protocol = protocol
        self.output_root = output_root.resolve()
        self.index_store = ExperimentIndexStore(self.output_root, protocol.protocol_sha256)

    def _system_config_sha256(self, system: MandatoryExperimentSystem) -> str:
        for specification in self.protocol.systems:
            if specification.system == system:
                return specification.config_sha256
        raise ValueError(f"system is absent from experiment protocol: {system}")

    @staticmethod
    def _resolve_artifact(run_directory: Path, relative_path: str) -> Path:
        artifact = (run_directory / relative_path).resolve()
        if not artifact.is_relative_to(run_directory) or not artifact.is_file():
            raise ExperimentExecutionError(
                failure_type="MissingArtifactError",
                message=f"system did not create required artifact: {relative_path}",
                evidence=relative_path.encode(),
            )
        if artifact.stat().st_size <= 0:
            raise ExperimentExecutionError(
                failure_type="EmptyArtifactError",
                message=f"system created an empty required artifact: {relative_path}",
                evidence=relative_path.encode(),
            )
        return artifact

    @staticmethod
    def _resource_evidence(
        *,
        request: ExperimentRunRequest,
        result: SystemExecutionResult,
    ) -> ResourceEvidence:
        return ResourceEvidence(
            machine=platform.node() or "local-machine",
            operating_system=platform.platform(),
            processor=platform.processor() or platform.machine(),
            physical_memory_bytes=_physical_memory_bytes(),
            device=request.device,
            torch_version=version("torch"),
            transformers_version=version("transformers"),
            thread_count=os.cpu_count() or 1,
            p50_latency_ms=_percentile(result.latency_samples_ms, 0.50),
            p95_latency_ms=_percentile(result.latency_samples_ms, 0.95),
            peak_rss_bytes=_peak_rss_bytes(),
            mps_peak_allocated_bytes=result.mps_peak_allocated_bytes,
        )

    def _validate_request(
        self,
        adapter: ExperimentSystemAdapter[PayloadT],
        request: ExperimentRunRequest,
        data: PreparedExperimentData[PayloadT],
    ) -> None:
        if adapter.system != request.system:
            raise ValueError("adapter system does not match the requested system")
        if adapter.architecture_config_sha256 != self._system_config_sha256(request.system):
            raise ValueError("adapter configuration does not match the frozen protocol")
        if request.partitions != data.identity.partitions:
            raise ValueError("run partitions do not match the governed data identity")
        if data.identity.split_manifest_sha256 != self.protocol.split_manifest_sha256:
            raise ValueError("run data uses a different split manifest from the protocol")

    def run(
        self,
        adapter: ExperimentSystemAdapter[PayloadT],
        request: ExperimentRunRequest,
        data: PreparedExperimentData[PayloadT],
    ) -> ExperimentRunReceipt:
        """Execute one system, persist its receipt, and append it to the verified index."""

        self._validate_request(adapter, request, data)
        run_directory = self.output_root / "runs" / request.run_id
        if run_directory.exists():
            raise ValueError(f"experiment run directory already exists: {request.run_id}")
        run_directory.mkdir(parents=True)
        started_at = datetime.now(UTC)
        context = SystemRunContext(request=request, run_directory=run_directory, data=data)
        try:
            with MpsMemorySampler(enabled=request.device == "mps") as memory_sampler:
                result = adapter.execute(context)
            result = result.model_copy(
                update={"mps_peak_allocated_bytes": memory_sampler.peak_allocated_bytes}
            )
            checkpoint = self._resolve_artifact(run_directory, result.checkpoint_path)
            predictions = self._resolve_artifact(run_directory, result.predictions_path)
            scorer_output = self._resolve_artifact(run_directory, result.scorer_output_path)
            observed_score_ids = tuple(score.document_id for score in result.document_scores)
            if observed_score_ids != data.identity.scored_document_ids:
                raise ExperimentExecutionError(
                    failure_type="IncompleteScorerOutputError",
                    message="system did not return one score for every governed document",
                    evidence=json.dumps(
                        {
                            "expected": data.identity.scored_document_ids,
                            "observed": observed_score_ids,
                        },
                        sort_keys=True,
                    ).encode(),
                    execution_steps=result.execution_steps,
                )
            receipt = ExperimentRunReceipt(
                run_id=request.run_id,
                protocol_sha256=self.protocol.protocol_sha256,
                system=request.system,
                stage=request.stage,
                ablation=request.ablation,
                status=ExperimentRunStatus.SUCCEEDED,
                seed=request.seed,
                setting=request.setting,
                partitions=request.partitions,
                architecture_config_sha256=adapter.architecture_config_sha256,
                candidate_selection_sha256=data.identity.candidate_selection_sha256,
                split_manifest_sha256=data.identity.split_manifest_sha256,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                document_count=len(data.identity.documents),
                scored_document_count=len(data.identity.scored_document_ids),
                candidate_count=data.identity.candidate_count,
                execution_steps=result.execution_steps,
                checkpoint_sha256=_sha256_file(checkpoint),
                predictions_sha256=_sha256_file(predictions),
                scorer_output_sha256=_sha256_file(scorer_output),
                metrics=result.metrics,
                document_scores=result.document_scores,
                resources=self._resource_evidence(request=request, result=result),
            )
        except ExperimentExecutionError as error:
            receipt = ExperimentRunReceipt(
                run_id=request.run_id,
                protocol_sha256=self.protocol.protocol_sha256,
                system=request.system,
                stage=request.stage,
                ablation=request.ablation,
                status=(
                    ExperimentRunStatus.INCOMPATIBLE
                    if error.incompatible
                    else ExperimentRunStatus.FAILED
                ),
                seed=request.seed,
                setting=request.setting,
                partitions=request.partitions,
                architecture_config_sha256=adapter.architecture_config_sha256,
                candidate_selection_sha256=data.identity.candidate_selection_sha256,
                split_manifest_sha256=data.identity.split_manifest_sha256,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                document_count=len(data.identity.documents),
                scored_document_count=0,
                candidate_count=data.identity.candidate_count,
                execution_steps=error.execution_steps,
                failure=RunFailure(
                    failure_type=error.failure_type,
                    message=str(error),
                    evidence_sha256=error.evidence_sha256,
                    retryable=error.retryable,
                ),
            )
        self.index_store.append(receipt)
        return receipt


__all__ = [
    "ExperimentExecutionError",
    "ExperimentIndexStore",
    "ExperimentRunRequest",
    "ExperimentRunner",
    "ExperimentSystemAdapter",
    "PreparedExperimentData",
    "SystemExecutionResult",
    "SystemRunContext",
]
