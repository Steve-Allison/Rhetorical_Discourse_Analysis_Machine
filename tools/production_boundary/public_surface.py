"""Generate the exact installed production public-surface authority."""

from enum import EnumType
import inspect
from pathlib import Path
from typing import Any, Final

import rfc8785

import isanlp_rst.ingest as ingest
from tools.production_boundary.schemas import SCHEMA_BASE, generated_schemas

PUBLIC_SURFACE_PATH: Final = Path("isanlp_rst/ingest/public-surface.json")


def generated_public_surface() -> bytes:
    """Return canonical bytes for every supported root export and installed resource."""

    entries = [_root_entry(name, getattr(ingest, name)) for name in sorted(ingest.__all__)]
    entries.extend(
        (
            _special_entry(
                "isanlp_rst.Parser.analyse_document",
                "function",
                documentation_anchor="6-analyse-with-an-immutable-model-release",
            ),
            _special_entry("isanlp_rst.Parser.complete_erst_document", "function"),
            _special_entry(
                "isanlp_rst.ingest.ProductionIngestor.prepare",
                "function",
                public_import="isanlp_rst.ingest:ProductionIngestor.prepare",
                documentation_anchor="4-prepare-and-inspect-complete-evidence",
            ),
            _special_entry(
                "isanlp_rst.ingest.ProductionIngestor.analyse",
                "function",
                public_import="isanlp_rst.ingest:ProductionIngestor.analyse",
                documentation_anchor="6-analyse-with-an-immutable-model-release",
            ),
            _special_entry(
                "isanlp_rst.ingest.ProductionIngestor.capabilities",
                "function",
                public_import="isanlp_rst.ingest:ProductionIngestor.capabilities",
            ),
            _special_entry(
                "isanlp-rst",
                "console_command",
                public_import="isanlp_rst.cli:main",
                documentation_anchor="10-verify-installed-command-parity",
            ),
            _special_entry(
                "isanlp-rst.local-http./analyse",
                "local_endpoint",
                compatibility="serialized_contract",
                documentation_anchor="10-verify-installed-command-parity",
            ),
            _special_entry(
                "isanlp-rst.local-http./capabilities",
                "local_endpoint",
                compatibility="serialized_contract",
                documentation_anchor="10-verify-installed-command-parity",
            ),
            _special_entry(
                "isanlp-rst.local-http./health",
                "local_endpoint",
                compatibility="semver",
                documentation_anchor="10-verify-installed-command-parity",
            ),
            _special_entry(
                "isanlp_rst.ingest.public-surface.json",
                "resource",
                compatibility="release_bound",
                documentation_anchor="9-verify-a-consumer-uses-only-the-public-contract",
            ),
        )
    )
    entries.extend(
        _special_entry(
            f"isanlp_rst.ingest.schemas.{filename}",
            "schema",
            schema_id=f"{SCHEMA_BASE}/{filename}",
            compatibility="serialized_contract",
            documentation_anchor="7-persist-and-reload-canonically",
        )
        for filename in sorted(generated_schemas())
    )
    payload = {
        "contract": "isanlp_rst.public_surface",
        "contract_version": "2.0.0",
        "entries": entries,
    }
    return rfc8785.dumps(payload) + b"\n"


def write_public_surface(path: Path = PUBLIC_SURFACE_PATH) -> Path:
    """Write the generated authority to its package resource path."""

    path.write_bytes(generated_public_surface())
    return path


def public_surface_parity(path: Path = PUBLIC_SURFACE_PATH) -> bool:
    """Return whether the committed authority equals current runtime inspection."""

    return path.is_file() and path.read_bytes() == generated_public_surface()


def _root_entry(name: str, value: Any) -> dict[str, Any]:
    return _special_entry(
        f"isanlp_rst.ingest.{name}",
        _entry_kind(value),
        public_import=f"isanlp_rst.ingest:{name}",
        compatibility=(
            "serialized_contract"
            if name in {
                "PersistedContract",
                "ProductionAnalysisOutcome",
                "load_contract",
                "serialize_contract",
            }
            else "semver"
        ),
        documentation_anchor={
            "PreparationOutcome": "4-prepare-and-inspect-complete-evidence",
            "ProductionAnalysisOutcome": "6-analyse-with-an-immutable-model-release",
            "describe_capabilities": "3-discover-capability-without-a-model",
            "load_contract": "7-persist-and-reload-canonically",
            "serialize_contract": "7-persist-and-reload-canonically",
        }.get(name),
    )


def _entry_kind(value: Any) -> str:
    if isinstance(value, EnumType):
        return "enum"
    if inspect.isclass(value):
        if issubclass(value, BaseException):
            return "exception"
        if getattr(value, "_is_protocol", False):
            return "protocol"
        return "class"
    if inspect.isfunction(value):
        return "function"
    return "alias"


def _special_entry(
    qualified_name: str,
    kind: str,
    *,
    public_import: str | None = None,
    schema_id: str | None = None,
    compatibility: str = "semver",
    documentation_anchor: str | None = None,
) -> dict[str, Any]:
    return {
        "qualified_name": qualified_name,
        "public_import": public_import,
        "kind": kind,
        "status": "supported",
        "introduced": "5.0.0",
        "deprecated": None,
        "removal": None,
        "schema_id": schema_id,
        "documentation_anchor": documentation_anchor,
        "compatibility": compatibility,
    }


if __name__ == "__main__":
    print(write_public_surface())


__all__ = [
    "PUBLIC_SURFACE_PATH",
    "generated_public_surface",
    "public_surface_parity",
    "write_public_surface",
]
