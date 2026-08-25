"""Canonical production package identity."""

from functools import cache
from importlib.metadata import PackageNotFoundError, version as distribution_version

PACKAGE_NAME = "isanlp_rst"
PACKAGE_VERSION = "4.0.0"
TOOL_NAME = "isanlp_rst"


@cache
def resolve_installed_package_version() -> str:
    """Return distribution metadata, or ``unknown`` only when absent."""

    try:
        return distribution_version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"


__all__ = [
    "PACKAGE_NAME",
    "PACKAGE_VERSION",
    "TOOL_NAME",
    "resolve_installed_package_version",
]
