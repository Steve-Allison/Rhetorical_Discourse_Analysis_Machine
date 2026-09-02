"""Exact-commit, via-sdist, deterministic build tests."""

import json
from pathlib import Path
import subprocess
import zipfile

import pytest

from isanlp_rst._provenance import PROVENANCE_FIELDS
from tools.production_boundary.build import _reset_output_dir, build_production_artifacts, source_release_record
from tools.production_boundary.contracts import canonical_record_bytes, sha256_path


def _run(*command: str, cwd: Path) -> str:
    completed = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def test_source_release_record_identifies_exact_clean_commit(tmp_path: Path) -> None:
    (tmp_path / "source.txt").write_text("release source\n", encoding="utf-8")
    _run("git", "init", "-q", cwd=tmp_path)
    _run("git", "config", "user.name", "Release Test", cwd=tmp_path)
    _run("git", "config", "user.email", "release@example.invalid", cwd=tmp_path)
    _run("git", "add", ".", cwd=tmp_path)
    _run("git", "commit", "-q", "-m", "source", cwd=tmp_path)

    record = source_release_record(tmp_path)

    assert record.source.commit == _run("git", "rev-parse", "HEAD", cwd=tmp_path)
    assert record.source.tree == _run("git", "rev-parse", "HEAD^{tree}", cwd=tmp_path)
    assert record.source.source_date_epoch == int(
        _run("git", "show", "-s", "--format=%ct", "HEAD", cwd=tmp_path)
    )
    assert canonical_record_bytes(record).startswith(b'{"schema_name"')


def test_double_build_publishes_expected_pair(
    built_release_pair: tuple[Path, Path, str],
) -> None:
    wheel, sdist, commit = built_release_pair
    assert wheel.name == "isanlp_rst-5.0.0-py3-none-any.whl"
    assert sdist.name == "isanlp_rst-5.0.0.tar.gz"
    assert sha256_path(wheel) != sha256_path(sdist)
    with zipfile.ZipFile(wheel) as archive:
        provenance = json.loads(archive.read("isanlp_rst/build-provenance.json"))
    assert provenance["source_commit"] == commit
    # The packaged resource keeps the exact schema-1.0.0 field set the runtime reader
    # enforces; the tag is recorded in the build report, not here.
    assert set(provenance) == PROVENANCE_FIELDS


def test_rebuild_replaces_a_previous_pair_but_refuses_foreign_files(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    (output / "isanlp_rst-5.0.0-py3-none-any.whl").write_bytes(b"stale")
    (output / "unrelated.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not this release's artifacts"):
        _reset_output_dir(output)
    assert (output / "unrelated.txt").read_text(encoding="utf-8") == "keep me"

    (output / "unrelated.txt").unlink()
    _reset_output_dir(output)
    assert output.is_dir()
    assert not any(output.iterdir())


def test_tag_naming_another_version_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "5.0.0"\n', encoding="utf-8")
    _run("git", "init", "-q", cwd=tmp_path)
    _run("git", "config", "user.name", "Release Test", cwd=tmp_path)
    _run("git", "config", "user.email", "release@example.invalid", cwd=tmp_path)
    _run("git", "add", ".", cwd=tmp_path)
    _run("git", "commit", "-q", "-m", "source", cwd=tmp_path)
    _run("git", "tag", "v9.9.9", cwd=tmp_path)
    with pytest.raises(RuntimeError, match="tagged 'v9.9.9' but the package version is 5.0.0"):
        build_production_artifacts(tmp_path, tmp_path / "out")
