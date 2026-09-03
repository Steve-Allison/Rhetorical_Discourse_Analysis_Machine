"""Run deterministic RST format mutants and require the focused suite to kill each one."""

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


MUTANTS = (
    Mutant(
        name="doclang-validator-bypass",
        source=Path("rdam/rst/ingest/_harvest.py"),
        original="            validate(stream.name, allow_empty_namespace=True)",
        replacement="            None  # mutation: validator bypassed",
        tests=(
            "tests/ingest/production_ingest/test_upstream_conformance.py::"
            "test_current_upstream_invalid_doclang_specimen_is_unmodified_and_rejected",
        ),
    ),
    Mutant(
        name="doclang-compression-ratio-bypass",
        source=Path("rdam/rst/doclang/loader.py"),
        original=(
            "    if entry.compress_size and entry.file_size / entry.compress_size "
            "> _MAX_COMPRESSION_RATIO:"
        ),
        replacement="    if False:",
        tests=(
            "tests/ingest/production_ingest/test_doclang_complex.py::"
            "test_doclang_archive_enforces_compression_ratio_limit",
        ),
    ),
    Mutant(
        name="markdown-character-anchor-off-by-one",
        source=Path("rdam/rst/ingest/_harvest.py"),
        original="    start = block_start + relative",
        replacement="    start = block_start + relative + 1",
        tests=(
            "tests/ingest/production_ingest/test_markdown_conformance.py::"
            "test_every_markdown_character_anchor_round_trips_to_the_exact_source_slice",
        ),
    ),
    Mutant(
        name="docling-body-layer-only",
        source=Path("rdam/rst/ingest/_harvest.py"),
        original="        included_content_layers=set(ContentLayer),",
        replacement="        included_content_layers={ContentLayer.BODY},",
        tests=("tests/ingest/production_ingest/test_docling_complex.py",),
    ),
    Mutant(
        name="markdown-front-matter-not-recognised",
        source=Path("rdam/rst/markdown/loader.py"),
        original='        if tok.type == "front_matter":',
        replacement='        if tok.type == "front_matter_mutant":',
        tests=("tests/ingest/test_markdown_loader.py",),
    ),
)


def _copy_test_workspace(destination: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    shutil.copytree(ROOT / "rdam", destination / "rdam", ignore=ignore)
    shutil.copytree(ROOT / "tests", destination / "tests", ignore=ignore)
    shutil.copy2(ROOT / "pyproject.toml", destination / "pyproject.toml")


def _apply_mutant(workspace: Path, mutant: Mutant) -> None:
    source = workspace / mutant.source
    text = source.read_text(encoding="utf-8")
    occurrences = text.count(mutant.original)
    if occurrences != 1:
        raise RuntimeError(
            f"{mutant.name}: expected exactly one mutation site in {mutant.source}, found {occurrences}"
        )
    source.write_text(text.replace(mutant.original, mutant.replacement), encoding="utf-8")


def _run_mutant(mutant: Mutant) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"rdam-mutant-{mutant.name}-") as temporary:
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
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *mutant.tests, "-q"],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        return result.returncode != 0, output


def main() -> int:
    survivors: list[str] = []
    for mutant in MUTANTS:
        killed, output = _run_mutant(mutant)
        status = "KILLED" if killed else "SURVIVED"
        print(f"{status}: {mutant.name}")
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
