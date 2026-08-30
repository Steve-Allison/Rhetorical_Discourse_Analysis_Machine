"""Release and canonical ingest-envelope version authority."""

from importlib.metadata import version

import isanlp_rst
from isanlp_rst import _version
from isanlp_rst.ingest import INGEST_SCHEMA_NAME, INGEST_SCHEMA_VERSION


def test_installed_release_matches_package_authority() -> None:
    assert _version.PACKAGE_NAME == "isanlp_rst"
    assert _version.PACKAGE_VERSION == "5.0.0"
    assert version(_version.PACKAGE_NAME) == _version.PACKAGE_VERSION
    assert isanlp_rst.__version__ == _version.PACKAGE_VERSION


def test_canonical_ingest_envelope_is_current() -> None:
    assert INGEST_SCHEMA_NAME == "isanlp_rst.production"
    assert INGEST_SCHEMA_VERSION == "2.0.0"
