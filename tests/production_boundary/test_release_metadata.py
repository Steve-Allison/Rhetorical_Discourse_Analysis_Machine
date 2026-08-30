"""Release metadata contract tests for the Feature 004 distribution."""

from importlib.metadata import metadata, version
from pathlib import Path

import isanlp_rst


def test_package_declares_and_installs_pep_561_marker() -> None:
    package_root = Path(isanlp_rst.__file__).resolve().parent
    marker = package_root / "py.typed"

    assert marker.is_file()
    assert marker.read_bytes() == b"\n"


def test_runtime_and_distribution_report_feature_release_version() -> None:
    assert version("isanlp_rst") == "5.0.0"
    assert isanlp_rst.__version__ == "5.0.0"


def test_distribution_declares_exclusive_import_name() -> None:
    assert metadata("isanlp_rst").get_all("Import-Name") == ["isanlp_rst"]
