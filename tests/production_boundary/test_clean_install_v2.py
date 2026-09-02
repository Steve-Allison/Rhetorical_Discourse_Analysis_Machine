"""Genuine isolated-wheel mechanics before final release-artifact selection."""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from rdam.rst.doclang.loader import load_doclang_archive
from tools.production_boundary import clean_install
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
                    "import json, pathlib, site, rdam.rst; "
                    "print(json.dumps({'package': str(pathlib.Path(rdam.rst.__file__).resolve()), "
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


def test_full_clean_install_runs_inference_in_core_and_formats(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: list[tuple[str, bool, str | None]] = []

    def fake_install_and_run(**kwargs: object) -> dict[str, object]:
        name = kwargs["name"]
        full = kwargs["full"]
        release_id = kwargs["release_id"]
        assert isinstance(name, str)
        assert isinstance(full, bool)
        assert release_id is None or isinstance(release_id, str)
        observed.append((name, full, release_id))
        return {"environment": name, "valid": True}

    monkeypatch.setattr(clean_install, "_install_and_run", fake_install_and_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clean_install.py",
            "--wheel",
            str(tmp_path / "rdam-7.7.7-py3-none-any.whl"),
            "--root",
            str(tmp_path),
            "--model-store",
            str(tmp_path / "model-releases"),
            "--release-id",
            "dmrst-v1-gumrrg",
            "--full",
        ],
    )

    assert clean_install.main() == 0
    assert observed == [
        ("core", True, "dmrst-v1-gumrrg"),
        ("formats", True, "dmrst-v1-gumrrg"),
    ]
    assert json.loads(capsys.readouterr().out)["valid"] is True


def test_full_clean_install_requires_explicit_release_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "clean_install.py",
            "--wheel",
            str(tmp_path / "rdam-7.7.7-py3-none-any.whl"),
            "--model-store",
            str(tmp_path / "model-releases"),
            "--full",
        ],
    )

    with pytest.raises(ValueError, match="requires --release-id"):
        clean_install.main()
