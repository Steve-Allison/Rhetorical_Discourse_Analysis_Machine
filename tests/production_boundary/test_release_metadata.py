"""Release metadata contract tests for the ``rdam`` 6.0.0 distribution."""

from importlib.metadata import metadata, version
from pathlib import Path

import rdam
import rdam.rst
from rdam.rst._version import PACKAGE_NAME


def test_package_declares_and_installs_pep_561_marker() -> None:
    package_root = Path(rdam.__file__).resolve().parent
    marker = package_root / "py.typed"

    assert marker.is_file()
    assert marker.read_bytes() == b"\n"


def test_runtime_and_distribution_report_feature_release_version() -> None:
    assert version(PACKAGE_NAME) == "6.0.0"
    assert rdam.rst.__version__ == "6.0.0"


def test_distribution_declares_exclusive_import_name() -> None:
    assert metadata(PACKAGE_NAME).get_all("Import-Name") == ["rdam"]
