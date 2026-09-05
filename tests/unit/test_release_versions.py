"""Release and canonical ingest-envelope version authority."""

from importlib.metadata import version

import rdam.rst
from rdam.rst import _version
from rdam.ingest import INGEST_SCHEMA_NAME, INGEST_SCHEMA_VERSION


def test_installed_release_matches_package_authority() -> None:
    assert _version.PACKAGE_NAME == "rdam"
    assert _version.TOOL_NAME == "rdam"
    assert _version.PACKAGE_VERSION == "6.0.0"
    assert version(_version.PACKAGE_NAME) == _version.PACKAGE_VERSION
    assert rdam.rst.__version__ == _version.PACKAGE_VERSION


def test_canonical_ingest_envelope_is_current() -> None:
    assert INGEST_SCHEMA_NAME == "isanlp_rst.production"
    assert INGEST_SCHEMA_VERSION == "2.0.0"
