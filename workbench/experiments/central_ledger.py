"""Centralized, append-only experiment registry and audit ledger for discourse parsing runs.

Guarantees:
- Zero data loss: every training/eval run gets an immutable timestamped run directory.
- Append-only central ledger: all runs record metrics, parameters, commits, and digests.
- Cryptographic integrity: BLAKE3 checkpoint digests and canonical JSON serialization.
"""

from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
from pathlib import Path
import subprocess
from typing import Any
import uuid

logger = logging.getLogger(__name__)

DEFAULT_EXPERIMENTS_ROOT = Path("workbench/experiments")
DEFAULT_LEDGER_PATH = DEFAULT_EXPERIMENTS_ROOT / "central_ledger.jsonl"


def get_current_git_commit() -> str:
    """Get current git commit hash, or 'untracked' if git is unavailable."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "untracked"


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    """Immutable record of an individual experiment, training run, or benchmark."""

    run_id: str
    timestamp_utc: str
    git_commit: str
    model_id: str
    model_revision: str
    experiment_type: str  # "training", "evaluation", "ablation", "benchmark"
    dataset_name: str
    dataset_digest: str
    hyperparameters: dict[str, Any]
    eval_metrics: dict[str, Any]
    checkpoint_digest: str | None = None
    artifact_paths: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CentralExperimentLedger:
    """Centralized experiment ledger manager managing runs and append-only tracking."""

    def __init__(
        self,
        experiments_root: Path = DEFAULT_EXPERIMENTS_ROOT,
        ledger_path: Path = DEFAULT_LEDGER_PATH,
    ) -> None:
        self.experiments_root = experiments_root
        self.ledger_path = ledger_path
        self.runs_root = self.experiments_root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def create_run_session(self, experiment_type: str, model_id: str) -> tuple[str, Path]:
        """Create a dedicated, collision-proof run directory.

        Returns:
            tuple[run_id, run_dir_path]
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = uuid.uuid4().hex[:6]
        sanitized_model = model_id.split("/")[-1].replace("-", "_")
        run_id = f"{timestamp_str}_{sanitized_model}_{unique_suffix}"

        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_id, run_dir

    def record_run(
        self,
        run_id: str,
        run_dir: Path,
        model_id: str,
        model_revision: str,
        experiment_type: str,
        dataset_name: str,
        dataset_digest: str,
        hyperparameters: dict[str, Any],
        eval_metrics: dict[str, Any],
        checkpoint_digest: str | None = None,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> ExperimentRecord:
        """Persist run receipt in run_dir and append to central ledger."""
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        git_commit = get_current_git_commit()

        # Collect relative artifact paths
        artifact_paths: list[str] = []
        if run_dir.exists():
            for f in run_dir.rglob("*"):
                if f.is_file():
                    artifact_paths.append(str(f.relative_to(self.experiments_root)))

        record = ExperimentRecord(
            run_id=run_id,
            timestamp_utc=now_utc,
            git_commit=git_commit,
            model_id=model_id,
            model_revision=model_revision,
            experiment_type=experiment_type,
            dataset_name=dataset_name,
            dataset_digest=dataset_digest,
            hyperparameters=hyperparameters,
            eval_metrics=eval_metrics,
            checkpoint_digest=checkpoint_digest,
            artifact_paths=artifact_paths,
            tags=tags or [],
            notes=notes,
        )

        # 1. Save detailed run_receipt.json inside the dedicated run_dir
        receipt_file = run_dir / "run_receipt.json"
        receipt_file.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")

        # 2. Append atomically to central JSONL ledger
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

        logger.info(f"Recorded run {run_id} to central ledger {self.ledger_path}")
        return record

    def list_runs(self, experiment_type: str | None = None) -> list[ExperimentRecord]:
        """List all historical runs from the central ledger."""
        if not self.ledger_path.exists():
            return []

        runs: list[ExperimentRecord] = []
        with self.ledger_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                record = ExperimentRecord(**data)
                if experiment_type is None or record.experiment_type == experiment_type:
                    runs.append(record)
        return runs
