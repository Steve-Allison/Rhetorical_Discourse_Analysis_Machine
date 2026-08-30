"""Exact-commit, via-sdist, deterministic build tests."""

from pathlib import Path
import subprocess
import zipfile

from tools.production_boundary.build import source_release_record
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


def test_double_build_publishes_expected_immutable_pair(
    built_release_pair: tuple[Path, Path, str],
) -> None:
    wheel, sdist, commit = built_release_pair
    assert wheel.name == "isanlp_rst-5.0.0-py3-none-any.whl"
    assert sdist.name == "isanlp_rst-5.0.0.tar.gz"
    assert sha256_path(wheel) != sha256_path(sdist)
    with zipfile.ZipFile(wheel) as archive:
        provenance = archive.read("isanlp_rst/build-provenance.json")
    assert commit.encode("ascii") in provenance
