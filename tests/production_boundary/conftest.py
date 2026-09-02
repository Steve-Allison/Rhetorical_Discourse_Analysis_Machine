"""Deterministic release-tool fixtures.

The fixture project mirrors the real layout — one distribution, one ``rdam`` package with
the RST provider as a sub-package — under a version that is deliberately not the
repository's, so a passing build proves the tools derive names from ``pyproject.toml``.
"""

from pathlib import Path
import subprocess

import pytest

from tools.production_boundary.build import build_production_artifacts
from tools.production_boundary.identity import ReleaseIdentity

FIXTURE_IDENTITY = ReleaseIdentity(distribution="rdam", version="7.7.7", package_dir="rdam")


def _run(*command: str, cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


@pytest.fixture(scope="session")
def fixture_identity() -> ReleaseIdentity:
    return FIXTURE_IDENTITY


@pytest.fixture(scope="session")
def built_release_pair(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, str]:
    root = tmp_path_factory.mktemp("release-source")
    (root / "rdam/rst/ingest/schemas").mkdir(parents=True)
    (root / "rdam/__init__.py").write_text("", encoding="utf-8")
    (root / "rdam/py.typed").write_bytes(b"\n")
    (root / "rdam/rst/__init__.py").write_text(f'__version__ = "{FIXTURE_IDENTITY.version}"\n', encoding="utf-8")
    (root / "rdam/rst/cli.py").write_text(
        "def main() -> int:\n    return 0\n",
        encoding="utf-8",
    )
    (root / "rdam/rst/ingest/__init__.py").write_text("", encoding="utf-8")
    (root / "rdam/rst/ingest/schemas/capabilities.schema.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    (root / "rdam/rst/ingest/public-surface.json").write_text(
        """{"contract":"isanlp_rst.public_surface","contract_version":"2.0.0","entries":[{"qualified_name":"rdam-rst"},{"qualified_name":"rdam-rst.local-http./analyse"},{"qualified_name":"rdam-rst.local-http./capabilities"},{"qualified_name":"rdam-rst.local-http./health"}]}\n""",
        encoding="utf-8",
    )
    (root / "pixi.lock").write_text("fixture-lock\n", encoding="utf-8")
    (root / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["hatchling>=1.32,<2"]
build-backend = "hatchling.build"

[project]
name = "{FIXTURE_IDENTITY.distribution}"
version = "{FIXTURE_IDENTITY.version}"
requires-python = ">=3.14"
import-names = ["rdam"]

[project.scripts]
rdam-rst = "rdam.rst.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["rdam"]

[tool.hatch.build.targets.sdist]
include = ["/rdam", "/pyproject.toml"]
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
