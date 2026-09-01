"""Execute every retained offline command to a bounded, evidence-bearing start."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CommandCategory(BaseModel):
    """One canonical retained command and its bounded-start contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    argv: tuple[str, ...] = Field(min_length=1)
    timeout_seconds: int = Field(gt=0, le=60)


class CommandReceipt(BaseModel):
    """Proof that one command resolved dependencies and reached its safe boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    category: str
    argv: tuple[str, ...]
    status: Literal["started"]
    exit_code: Literal[0]
    elapsed_ms: float = Field(gt=0)
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


COMMANDS = (
    CommandCategory(name="erst-corpus-authority", category="corpus-preparation", argv=("-m", "scripts.derive_gum_erst_relations", "--help"), timeout_seconds=20),
    CommandCategory(name="modernbert-parser-training", category="parser-training", argv=("-m", "scripts.train_modernbert_treebank", "--help"), timeout_seconds=20),
    CommandCategory(name="dmrst-parser-training", category="parser-training", argv=("-m", "workbench.training.parsers.dmrst_runs", "--help"), timeout_seconds=20),
    CommandCategory(name="unirst-parser-training", category="parser-training", argv=("-m", "workbench.training.parsers.unirst_runs", "--help"), timeout_seconds=20),
    CommandCategory(name="segmenter-training", category="segmenter-training", argv=("-m", "scripts.train_segmenter", "--help"), timeout_seconds=20),
    CommandCategory(name="erst-training", category="erst-training", argv=("-m", "scripts.train_erst_scorer", "--help"), timeout_seconds=20),
    CommandCategory(name="rst-evaluation", category="evaluation", argv=("-m", "pytest", "tests/offline/test_parseval_math.py", "-q"), timeout_seconds=60),
    CommandCategory(name="erst-research", category="research", argv=("-m", "pytest", "tests/offline/research/test_runner.py", "-q"), timeout_seconds=60),
    CommandCategory(name="production-benchmark", category="benchmark", argv=("-m", "scripts.bench", "--help"), timeout_seconds=20),
)


def _execute(command: CommandCategory, root: Path) -> CommandReceipt:
    started = time.perf_counter()
    completed = subprocess.run(
        [sys.executable, *command.argv],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=command.timeout_seconds,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    evidence = (completed.stdout + completed.stderr).encode("utf-8")
    if completed.returncode != 0:
        raise RuntimeError(
            f"offline command {command.name!r} failed with exit code {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not evidence:
        raise RuntimeError(f"offline command {command.name!r} produced no bounded-start evidence")
    return CommandReceipt(
        name=command.name,
        category=command.category,
        argv=(sys.executable, *command.argv),
        status="started",
        exit_code=0,
        elapsed_ms=elapsed_ms,
        evidence_sha256=hashlib.sha256(evidence).hexdigest(),
    )


def main() -> int:
    root = Path.cwd().resolve()
    receipts = tuple(_execute(command, root) for command in COMMANDS)
    categories = {receipt.category for receipt in receipts}
    required = {"corpus-preparation", "parser-training", "segmenter-training", "erst-training", "evaluation", "research", "benchmark"}
    missing = sorted(required - categories)
    if missing:
        raise RuntimeError(f"offline command registry is missing categories: {missing}")
    print(
        json.dumps(
            {
                "schema_version": "isanlp_rst_offline_command_receipts/v1",
                "commands": [receipt.model_dump(mode="json") for receipt in receipts],
                "valid": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
