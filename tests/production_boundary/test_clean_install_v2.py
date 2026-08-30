"""Genuine isolated-wheel mechanics before final release-artifact selection."""

import json
from pathlib import Path
import subprocess
import sys

from isanlp_rst.doclang.loader import load_doclang_archive
from tools.production_boundary.installed_acceptance import _archive_bytes


def _run(command: tuple[str, ...], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_fixture_wheel_installs_without_checkout_or_system_site_packages(
    built_release_pair: tuple[Path, Path, str],
    tmp_path: Path,
) -> None:
    wheel, _, _ = built_release_pair
    environment = tmp_path / "isolated"
    _run((sys.executable, "-m", "venv", str(environment)), tmp_path)
    python = environment / "bin/python"
    _run((str(python), "-m", "pip", "install", "--no-deps", str(wheel)), tmp_path)
    payload = json.loads(
        _run(
            (
                str(python),
                "-I",
                "-c",
                (
                    "import json, pathlib, site, isanlp_rst; "
                    "print(json.dumps({'package': str(pathlib.Path(isanlp_rst.__file__).resolve()), "
                    "'site': site.getsitepackages()}))"
                ),
            ),
            tmp_path,
        )
    )
    assert not Path(payload["package"]).is_relative_to(Path.cwd())
    assert all(str(environment) in path for path in payload["site"])
    _run((str(python), "-m", "pip", "check"), tmp_path)
    inspection = json.loads(_run((str(python), "-m", "pip", "inspect"), tmp_path))
    assert inspection["version"] == "1"


def test_installed_acceptance_builds_a_valid_doclang_opc_archive() -> None:
    document = b"<doclang><text>Installed acceptance.</text></doclang>"
    loaded = load_doclang_archive(_archive_bytes(document))
    assert loaded.document_bytes == document
