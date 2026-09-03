"""Run deterministic Feature 018 mutants and require causal tests to kill each one."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Mutant:
    name: str
    source: Path
    original: str
    replacement: str
    tests: tuple[str, ...]
    timeout_seconds: int = 30


MUTANTS = (
    Mutant(
        name="deep-freeze-removed",
        source=Path("rdam/_immutable_json.py"),
        original="        return FrozenJsonObject(value)",
        replacement="        return dict(value)",
        tests=(
            "tests/machine/test_contracts.py::TestNativeTechniqueResult::"
            "test_payload_is_recursively_immutable_and_digest_cannot_go_stale",
        ),
    ),
    Mutant(
        name="overall-deadline-removed",
        source=Path("rdam/_llm.py"),
        original="            async with asyncio.timeout(self._transport_deadline_seconds):",
        replacement="            async with asyncio.timeout(None):",
        tests=("tests/llm/test_llm_boundary.py::TestExtraction::test_one_deadline_covers_an_active_model_request",),
        timeout_seconds=3,
    ),
    Mutant(
        name="structured-input-removed-from-cache-key",
        source=Path("rdam/machine.py"),
        original='            "structured_input": request.structured_input,',
        replacement='            "structured_input": None,',
        tests=(
            "tests/machine/test_shared_runtime.py::TestResultCache::"
            "test_every_declared_key_component_changes_the_content_address",
        ),
    ),
    Mutant(
        name="single-flight-cache-recheck-removed",
        source=Path("rdam/machine.py"),
        original="                if cached is not None:",
        replacement="                if False and cached is not None:",
        tests=(
            "tests/machine/test_shared_runtime.py::TestResultCache::"
            "test_single_flight_rechecks_after_waiting_and_avoids_duplicate_calls",
        ),
    ),
    Mutant(
        name="completion-order-leaks-into-outcomes",
        source=Path("rdam/machine.py"),
        original="        outcomes.extend(requested_outcomes[technique] for technique in request.techniques)",
        replacement="        outcomes.extend(requested_outcomes.values())",
        tests=(
            "tests/machine/test_shared_runtime.py::TestExecutionPolicy::"
            "test_outcomes_remain_in_request_order_when_completion_order_is_reversed",
        ),
    ),
    Mutant(
        name="available-provider-source-revision-check-removed",
        source=Path("rdam/contracts.py"),
        original="            if self.provenance.source_revision is None:",
        replacement="            if False and self.provenance.source_revision is None:",
        tests=(
            "tests/machine/test_shared_runtime.py::"
            "test_available_provider_requires_source_revision_but_historical_provenance_remains_valid",
        ),
    ),
)


def _copy_test_workspace(destination: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    shutil.copytree(ROOT / "rdam", destination / "rdam", ignore=ignore)
    shutil.copytree(ROOT / "tests", destination / "tests", ignore=ignore)
    shutil.copy2(ROOT / "pyproject.toml", destination / "pyproject.toml")


def _apply_mutant(workspace: Path, mutant: Mutant) -> None:
    source = workspace / mutant.source
    content = source.read_text(encoding="utf-8")
    occurrences = content.count(mutant.original)
    if occurrences != 1:
        raise RuntimeError(
            f"{mutant.name}: expected exactly one mutation site in {mutant.source}, found {occurrences}"
        )
    source.write_text(content.replace(mutant.original, mutant.replacement), encoding="utf-8")


def _run_mutant(mutant: Mutant) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"rdam-shared-mutant-{mutant.name}-") as temporary:
        workspace = Path(temporary)
        _copy_test_workspace(workspace)
        _apply_mutant(workspace, mutant)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(workspace)
        preflight = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; import rdam; "
                "assert Path(rdam.__file__).resolve().is_relative_to(Path.cwd())",
            ],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if preflight.returncode != 0:
            return False, f"mutation workspace import preflight failed:\n{preflight.stderr}"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", *mutant.tests, "-q"],
                cwd=workspace,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=mutant.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return True, "causal test timed out under the mutant"
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        return result.returncode != 0, output


def main() -> int:
    survivors: list[str] = []
    for mutant in MUTANTS:
        killed, output = _run_mutant(mutant)
        print(f"{'KILLED' if killed else 'SURVIVED'}: {mutant.name}")
        if not killed:
            survivors.append(mutant.name)
            print(output)
    if survivors:
        print(f"Mutation gate failed: {len(survivors)} survivor(s): {', '.join(survivors)}")
        return 1
    print(f"Mutation gate passed: {len(MUTANTS)}/{len(MUTANTS)} critical mutants killed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
