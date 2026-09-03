"""Compatibility re-exports for provenance now owned by the machine runtime."""

from rdam._provenance import (
    PROVENANCE_FIELDS,
    installed_package_version,
    load_build_provenance,
    resolve_source_revision,
)

resolve_package_version = installed_package_version

__all__ = ["PROVENANCE_FIELDS", "load_build_provenance", "resolve_package_version", "resolve_source_revision"]
