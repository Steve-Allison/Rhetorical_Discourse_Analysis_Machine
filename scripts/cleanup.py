"""Remove regenerable junk from the repo: bytecode, tool caches, temp files.

Does not touch the pixi env (``.pixi/``), git metadata, lockfiles, or
test fixtures. Those are not temp files.

    pixi run cleanup
    pixi run cleanup --dry-run
    ./cleanup.sh
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Never descend into these, even if they contain bytecode.
SKIP_DIR_NAMES = frozenset({
    ".git",
    ".pixi",
    ".venv",
    "venv",
    "node_modules",
})

JUNK_DIR_NAMES = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pytype",
    ".hypothesis",
    ".ipynb_checkpoints",
    ".tox",
    ".nox",
    ".eggs",
    "htmlcov",
    "build",
    "dist",
})

JUNK_FILE_NAMES = frozenset({
    ".DS_Store",
    "Thumbs.db",
    ".coverage",
    "coverage.xml",
})

JUNK_SUFFIXES = frozenset({
    ".pyc",
    ".pyo",
    ".pyd",
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
})


def is_junk_dir(path: Path) -> bool:
    name = path.name
    return name in JUNK_DIR_NAMES or name.endswith(".egg-info")


def is_junk_file(path: Path) -> bool:
    name = path.name
    if name in JUNK_FILE_NAMES:
        return True
    if name.startswith(".coverage."):
        return True
    if name.endswith("~"):
        return True
    return path.suffix in JUNK_SUFFIXES


def collect_junk(root: Path) -> list[Path]:
    """Return junk paths under ``root``, never descending into skip dirs."""
    found: list[Path] = []

    def walk(directory: Path) -> None:
        try:
            children = list(directory.iterdir())
        except OSError as exc:
            print(f"skip unreadable {directory}: {exc}", file=sys.stderr)
            return
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name in SKIP_DIR_NAMES:
                    continue
                if is_junk_dir(child):
                    found.append(child)
                    continue
                walk(child)
            elif child.is_file() and is_junk_file(child):
                found.append(child)

    walk(root)
    return found


def _display(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def remove_junk(paths: list[Path], *, dry_run: bool, root: Path | None = None) -> int:
    """Delete ``paths``. Returns the number of paths acted on."""
    files = [p for p in paths if p.is_file()]
    dirs = [p for p in paths if p.is_dir()]
    removed = 0
    for path in files:
        print(_display(path, root) if root is not None else path)
        if not dry_run:
            path.unlink()
        removed += 1
    for path in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        print(_display(path, root) if root is not None else path)
        if not dry_run:
            shutil.rmtree(path)
        removed += 1
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="list junk without deleting it",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="directory to clean (default: repository root)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    junk = collect_junk(root)
    if not junk:
        print("nothing to clean")
        return 0
    count = remove_junk(junk, dry_run=args.dry_run, root=root)
    prefix = "would remove" if args.dry_run else "removed"
    print(f"{prefix} {count} path(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
