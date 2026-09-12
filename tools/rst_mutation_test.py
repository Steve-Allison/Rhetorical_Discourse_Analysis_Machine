"""Run deterministic RST format mutants and require the focused suite to kill each one."""

from tools.shared_runtime_mutation_test import causal_failure

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
        source=Path("rdam/ingest/doclang/document.py"),
        original="                validate(stream.name, allow_empty_namespace=True)",
        replacement="                None  # mutation: validator bypassed",
        tests=(
            "tests/ingest/production_ingest/test_upstream_conformance.py::"
            "test_current_upstream_invalid_doclang_specimen_is_unmodified_and_rejected",
        ),
    ),
    Mutant(
        name="doclang-compression-ratio-bypass",
        source=Path("rdam/ingest/doclang/loader.py"),
        original=("    if entry.compress_size and entry.file_size / entry.compress_size > _MAX_COMPRESSION_RATIO:"),
        replacement="    if False:",
        tests=(
            "tests/ingest/production_ingest/test_doclang_complex.py::"
            "test_doclang_archive_enforces_compression_ratio_limit",
        ),
    ),
    Mutant(
        name="markdown-character-anchor-off-by-one",
        source=Path("rdam/ingest/_harvest.py"),
        original="    start = block_start + relative",
        replacement="    start = block_start + relative + 1",
        tests=(
            "tests/ingest/production_ingest/test_markdown_conformance.py::"
            "test_every_markdown_character_anchor_round_trips_to_the_exact_source_slice",
        ),
    ),
    Mutant(
        name="docling-body-layer-only",
        source=Path("rdam/ingest/_harvest.py"),
        original="        included_content_layers=set(ContentLayer),",
        replacement="        included_content_layers={ContentLayer.BODY},",
        tests=("tests/ingest/production_ingest/test_docling_complex.py",),
    ),
    Mutant(
        name="markdown-front-matter-not-recognised",
        source=Path("rdam/ingest/markdown.py"),
        original='        if tok.type == "front_matter":',
        replacement='        if tok.type == "front_matter_mutant":',
        tests=("tests/ingest/test_markdown_loader.py",),
    ),
    Mutant(
        name="doclang-tail-duplication",
        source=Path("rdam/ingest/doclang/text_walker.py"),
        original='            yield child, "tail"',
        replacement='            yield child, "tail"\n            yield child, "tail"',
        tests=(
            "tests/ingest/test_doclang_decoder.py::test_metadata_tails_inline_content_and_comments_are_emitted_once",
        ),
    ),
    Mutant(
        name="doclang-metadata-leak",
        source=Path("rdam/ingest/doclang/text_walker.py"),
        original="            if name not in _METADATA_HEAD_ELEMENTS and name not in excluded_subtrees:",
        replacement="            if name not in excluded_subtrees:",
        tests=(
            "tests/ingest/test_doclang_decoder.py::test_metadata_tails_inline_content_and_comments_are_emitted_once",
        ),
    ),
    Mutant(
        name="doclang-cell-coordinate-shift",
        source=Path("rdam/ingest/doclang/decoder.py"),
        original="            column += 1",
        replacement="            column += 2",
        tests=(
            "tests/ingest/test_doclang_decoder.py::test_table_metadata_is_excluded_and_wrapper_tail_is_not_duplicated",
        ),
    ),
    Mutant(
        name="doclang-merge-span-loss",
        source=Path("rdam/ingest/doclang/decoder.py"),
        original="        spans[owner] = rows, columns",
        replacement="        spans[owner] = 1, 1",
        tests=("tests/ingest/test_doclang_decoder.py::test_rectangular_merge_has_one_owner_and_exact_spans",),
    ),
    Mutant(
        name="doclang-decoder-identity-omission",
        source=Path("rdam/ingest/_doclang.py"),
        original="Path(decoder.__file__),",
        replacement="",
        tests=("tests/ingest/test_doclang_identity.py::test_each_implementation_file_changes_public_identity",),
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
        raise RuntimeError(f"{mutant.name}: expected exactly one mutation site in {mutant.source}, found {occurrences}")
    source.write_text(text.replace(mutant.original, mutant.replacement), encoding="utf-8")


def _run_mutant(mutant: Mutant) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix=f"rdam-mutant-{mutant.name}-") as temporary:
        workspace = Path(temporary)
        _copy_test_workspace(workspace)
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
        command = [sys.executable, "-m", "pytest", *mutant.tests, "-q"]
        baseline = subprocess.run(
            command, cwd=workspace, env=environment, capture_output=True, text=True, check=False, timeout=180
        )
        if baseline.returncode != 0:
            return False, f"unmodified causal tests failed:\n{baseline.stdout}\n{baseline.stderr}"
        _apply_mutant(workspace, mutant)
        report = workspace / "mutant-results.xml"
        result = subprocess.run(
            [*command, f"--junitxml={report}"],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        return causal_failure(result.returncode, report), output


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
