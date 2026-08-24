"""Release and independent wire-envelope version authority."""

from importlib.metadata import version

import isanlp_rst
from isanlp_rst import _version
from isanlp_rst.doclang import _entry as doclang_entry
from isanlp_rst.docling import _entry as docling_entry
from isanlp_rst.markdown import _entry as markdown_entry


def test_installed_release_matches_package_authority() -> None:
    assert _version.PACKAGE_NAME == "isanlp_rst"
    assert _version.PACKAGE_VERSION == "4.0.0"
    assert version(_version.PACKAGE_NAME) == _version.PACKAGE_VERSION
    assert isanlp_rst.__version__ == _version.PACKAGE_VERSION


def test_format_envelope_versions_are_independent_and_current() -> None:
    assert docling_entry.SCHEMA_NAME == _version.DOCLING_SCHEMA_NAME
    assert docling_entry.SCHEMA_VERSION == _version.DOCLING_SCHEMA_VERSION == "1.2"
    assert doclang_entry.SCHEMA_NAME == _version.DOCLANG_SCHEMA_NAME
    assert doclang_entry.SCHEMA_VERSION == _version.DOCLANG_SCHEMA_VERSION == "1.1"
    assert markdown_entry.SCHEMA_NAME == _version.MARKDOWN_SCHEMA_NAME
    assert markdown_entry.SCHEMA_VERSION == _version.MARKDOWN_SCHEMA_VERSION == "1.1"


def test_all_formats_share_tool_identity_only() -> None:
    assert docling_entry.TOOL_NAME == _version.TOOL_NAME
    assert doclang_entry.TOOL_NAME == _version.TOOL_NAME
    assert markdown_entry.TOOL_NAME == _version.TOOL_NAME
