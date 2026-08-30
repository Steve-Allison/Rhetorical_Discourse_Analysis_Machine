"""Execute source-only release gates and write strict canonical evidence."""

import argparse
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import subprocess
import sys

from tools.production_boundary.contracts import (
    CheckStatus,
    EvidenceRecord,
    EvidenceState,
    GateResult,
    write_canonical_record,
)


QUALITY_COMMANDS = (
    (
        "focused-tests",
        ("pixi", "run", "-e", "default", "production-api-contract"),
    ),
    (
        "ruff",
        ("pixi", "run", "-e", "default", "lint"),
    ),
    (
        "pyright",
        ("pixi", "run", "-e", "default", "typecheck"),
    ),
)
PERFORMANCE_COMMANDS = (
    (
        "preparation-performance",
        ("pixi", "run", "-e", "default", "production-ingest-performance"),
    ),
)
SOURCE_GATE_COMMANDS = (
    ("ruff", ("pixi", "run", "-e", "default", "lint")),
    ("pyright", ("pixi", "run", "-e", "default", "typecheck")),
    ("markdown", ("pixi", "run", "-e", "default", "mdlint")),
    ("pytest", ("pixi", "run", "-e", "default", "test")),
    (
        "production-contract",
        ("pixi", "run", "-e", "default", "production-api-contract"),
    ),
    (
        "determinism",
        ("pixi", "run", "-e", "default", "production-ingest-determinism"),
    ),
    (
        "performance",
        ("pixi", "run", "-e", "default", "production-ingest-performance"),
    ),
)


def execute_evidence(
    root: Path,
    *,
    schema_suffix: str,
    commands: tuple[tuple[str, tuple[str, ...]], ...],
    output: Path,
) -> bool:
    """Run every named command and persist its exact output identity."""

    results: list[GateResult] = []
    passed = True
    for check_id, command in commands:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            check=False,
        )
        payload = completed.stdout + b"\n--- stderr ---\n" + completed.stderr
        status = CheckStatus.PASSED if completed.returncode == 0 else CheckStatus.FAILED
        passed = passed and status is CheckStatus.PASSED
        results.append(
            GateResult(
                check_id=check_id,
                status=status,
                command=command,
                tool_identity=f"CPython {sys.version.split()[0]}",
                output_sha256=hashlib.sha256(payload).hexdigest(),
                completed_at=datetime.now(UTC),
                summary=f"exit_code={completed.returncode}",
            )
        )
    record = EvidenceRecord(
        schema_name=f"isanlp_rst.release_evidence.{schema_suffix}",
        state=EvidenceState.PRE_SOURCE,
        created_at=datetime.now(UTC),
        checks=tuple(results),
    )
    write_canonical_record(output, record)
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("quality", "performance", "source-gates"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    schema_suffix, commands = {
        "quality": ("pre_release_quality", QUALITY_COMMANDS),
        "performance": ("performance", PERFORMANCE_COMMANDS),
        "source-gates": ("source_release_gates", SOURCE_GATE_COMMANDS),
    }[args.kind]
    return 0 if execute_evidence(
        args.root.resolve(),
        schema_suffix=schema_suffix,
        commands=commands,
        output=args.output.resolve(),
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PERFORMANCE_COMMANDS",
    "QUALITY_COMMANDS",
    "SOURCE_GATE_COMMANDS",
    "execute_evidence",
]
