"""Lint every repository Markdown file outside the declared exclusion classes.

The linted set is computed directly from git (tracked plus untracked, unignored
Markdown) minus the exclusion classes declared below. There is no hand-maintained
manifest: the computation here is the single authority for what gets linted.
"""

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GENERATED_SPEC_KIT_PREFIXES = (
    ".agents/skills/",
    ".claude/skills/",
    ".cursor/skills/",
    ".specify/templates/",
)
GENERATED_PROJECTION_PREFIXES = ("graphify-out/",)
INTENTIONAL_SYNTAX_FIXTURES = frozenset(
    {
        "tests/fixtures/markdown/gfm-rich.md",
        "tests/fixtures/production_api/retained_content/mixed.md",
    }
)


def _repository_markdown() -> tuple[str, ...]:
    completed = subprocess.run(
        (
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
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


def linted_markdown() -> tuple[str, ...]:
    repository_paths = _repository_markdown()
    linted = tuple(path for path in repository_paths if not _is_approved_exclusion(path))
    excluded = tuple(path for path in repository_paths if _is_approved_exclusion(path))
    print(
        json.dumps(
            {
                "schema_version": "2.0",
                "linted_count": len(linted),
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
    return linted


def main() -> int:
    linted = linted_markdown()
    if "--lint" not in sys.argv[1:]:
        return 0
    completed = subprocess.run(
        ("markdownlint-cli2", *linted),
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
