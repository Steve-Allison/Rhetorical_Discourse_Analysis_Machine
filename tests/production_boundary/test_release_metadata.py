"""Release metadata contract tests for the declared ``rdam`` distribution."""

from importlib.metadata import metadata, version
from pathlib import Path
import tomllib

import rdam
import rdam.rst
from rdam.rst._version import PACKAGE_NAME


def test_package_declares_and_installs_pep_561_marker() -> None:
    package_root = Path(rdam.__file__).resolve().parent
    marker = package_root / "py.typed"

    assert marker.is_file()
    assert marker.read_bytes() == b"\n"


def test_runtime_and_distribution_report_feature_release_version() -> None:
    declared = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    assert version(PACKAGE_NAME) == declared
    assert rdam.rst.__version__ == declared


def test_distribution_declares_exclusive_import_name() -> None:
    assert metadata(PACKAGE_NAME).get_all("Import-Name") == ["rdam"]
