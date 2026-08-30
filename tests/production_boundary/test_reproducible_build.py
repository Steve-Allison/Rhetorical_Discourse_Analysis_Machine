"""Exact-commit, via-sdist, deterministic build tests."""

from pathlib import Path
import zipfile

from tools.production_boundary.contracts import sha256_path


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
