"""Deterministic release-tool fixtures."""

from pathlib import Path
import subprocess

import pytest

from tools.production_boundary.build import build_production_artifacts


def _run(*command: str, cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


@pytest.fixture(scope="session")
def built_release_pair(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, str]:
    root = tmp_path_factory.mktemp("release-source")
    (root / "isanlp_rst/ingest/schemas").mkdir(parents=True)
    (root / "isanlp_rst/__init__.py").write_text('__version__ = "5.0.0"\n', encoding="utf-8")
    (root / "isanlp_rst/cli.py").write_text(
        "def main() -> int:\n    return 0\n",
        encoding="utf-8",
    )
    (root / "isanlp_rst/py.typed").write_bytes(b"\n")
    (root / "isanlp_rst/ingest/__init__.py").write_text("", encoding="utf-8")
    (root / "isanlp_rst/ingest/schemas/capabilities.schema.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (root / "isanlp_rst/ingest/public-surface.json").write_text(
        """{"contract":"isanlp_rst.public_surface","contract_version":"2.0.0","entries":[{"qualified_name":"isanlp-rst"},{"qualified_name":"isanlp-rst.local-http./analyse"},{"qualified_name":"isanlp-rst.local-http./capabilities"},{"qualified_name":"isanlp-rst.local-http./health"}]}\n""",
        encoding="utf-8",
    )
    (root / "pixi.lock").write_text("fixture-lock\n", encoding="utf-8")
    (root / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        """[build-system]
requires = ["hatchling>=1.32,<2"]
build-backend = "hatchling.build"

[project]
name = "isanlp_rst"
version = "5.0.0"
requires-python = ">=3.14"
import-names = ["isanlp_rst"]

[project.scripts]
isanlp-rst = "isanlp_rst.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["isanlp_rst"]

[tool.hatch.build.targets.sdist]
include = ["/isanlp_rst", "/pyproject.toml"]
""",
        encoding="utf-8",
    )
    _run("git", "init", "-q", cwd=root)
    _run("git", "config", "user.name", "Release Test", cwd=root)
    _run("git", "config", "user.email", "release@example.invalid", cwd=root)
    _run("git", "add", ".", cwd=root)
    _run("git", "commit", "-q", "-m", "fixture", cwd=root)
    commit = _run("git", "rev-parse", "HEAD", cwd=root)
    build = build_production_artifacts(root, tmp_path_factory.mktemp("release-output"))
    return build.wheel, build.sdist, commit
