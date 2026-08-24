"""Canonical package and wire-envelope version constants."""

from functools import cache
from importlib.metadata import PackageNotFoundError, version as distribution_version

PACKAGE_NAME = "isanlp_rst"
PACKAGE_VERSION = "4.0.0"
TOOL_NAME = "isanlp_rst"

DOCLING_SCHEMA_NAME = "isanlp_rst_docling"
DOCLING_SCHEMA_VERSION = "1.2"

DOCLANG_SCHEMA_NAME = "isanlp_rst_doclang"
DOCLANG_SCHEMA_VERSION = "1.1"

MARKDOWN_SCHEMA_NAME = "isanlp_rst_markdown"
MARKDOWN_SCHEMA_VERSION = "1.1"


@cache
def resolve_installed_package_version() -> str:
    """Return distribution metadata, or ``unknown`` only when absent."""

    try:
        return distribution_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"

__all__ = [
    "DOCLANG_SCHEMA_NAME",
    "DOCLANG_SCHEMA_VERSION",
    "DOCLING_SCHEMA_NAME",
    "DOCLING_SCHEMA_VERSION",
    "MARKDOWN_SCHEMA_NAME",
    "MARKDOWN_SCHEMA_VERSION",
    "PACKAGE_NAME",
    "PACKAGE_VERSION",
    "TOOL_NAME",
    "resolve_installed_package_version",
]
