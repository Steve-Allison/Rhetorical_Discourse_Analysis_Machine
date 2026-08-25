"""Verify and lint the complete repository Markdown manifest."""

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "config/markdownlint/tracked-markdown.txt"
GENERATED_SPEC_KIT_PREFIXES = (
    ".agents/skills/",
    ".claude/skills/",
    ".cursor/skills/",
    ".specify/templates/",
)
GENERATED_PROJECTION_PREFIXES = ("graphify-out/",)
INTENTIONAL_SYNTAX_FIXTURES = frozenset({"tests/fixtures/markdown/gfm-rich.md"})


def _repository_markdown() -> tuple[str, ...]:
    completed = subprocess.run(
        (
            "git",
            "ls-files",
            "--cached",
            "--",
            "*.md",
        ),
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(sorted(line for line in completed.stdout.splitlines() if line))


def _is_approved_exclusion(path: str) -> bool:
    return (
        path in INTENTIONAL_SYNTAX_FIXTURES
        or path.startswith(GENERATED_SPEC_KIT_PREFIXES)
        or path.startswith(GENERATED_PROJECTION_PREFIXES)
    )


def _manifest_paths() -> tuple[str, ...]:
    paths = tuple(line for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines() if line)
    if paths != tuple(sorted(set(paths))):
        raise RuntimeError("Markdown manifest must be sorted and contain no duplicates")
    return paths


def verify_manifest() -> tuple[str, ...]:
    repository_paths = _repository_markdown()
    expected = tuple(path for path in repository_paths if not _is_approved_exclusion(path))
    manifest = _manifest_paths()
    if manifest != expected:
        missing = sorted(set(expected) - set(manifest))
        stale = sorted(set(manifest) - set(expected))
        raise RuntimeError(
            "Markdown manifest is stale: "
            f"missing={json.dumps(missing, ensure_ascii=True)}, "
            f"stale={json.dumps(stale, ensure_ascii=True)}"
        )
    excluded = tuple(path for path in repository_paths if _is_approved_exclusion(path))
    print(
        json.dumps(
            {
                "schema_version": "1.0",
                "linted_count": len(manifest),
                "excluded_count": len(excluded),
                "excluded_classes": {
                    "generated_spec_kit_projection": sum(
                        path.startswith(GENERATED_SPEC_KIT_PREFIXES) for path in excluded
                    ),
                    "generated_repository_projection": sum(
                        path.startswith(GENERATED_PROJECTION_PREFIXES) for path in excluded
                    ),
                    "intentional_markdown_syntax_fixture": sum(
                        path in INTENTIONAL_SYNTAX_FIXTURES for path in excluded
                    ),
                },
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return manifest


def main() -> int:
    manifest = verify_manifest()
    if "--lint" not in sys.argv[1:]:
        return 0
    completed = subprocess.run(
        ("markdownlint-cli2", *manifest),
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
