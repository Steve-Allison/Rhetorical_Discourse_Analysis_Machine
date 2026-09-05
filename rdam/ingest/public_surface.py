"""Loader and runtime reconciler for the production public-surface authority."""

from collections.abc import Mapping
from enum import StrEnum
from importlib import import_module, resources
import inspect
import json
from pathlib import Path
import re
from typing import Self, cast

from pydantic import Field, model_validator

from rdam.ingest.contracts.base import StrictContractModel

_RESOURCE = "public-surface.json"


class PublicEntryKind(StrEnum):
    FUNCTION = "function"
    CLASS = "class"
    PROTOCOL = "protocol"
    ENUM = "enum"
    ALIAS = "alias"
    EXCEPTION = "exception"
    SCHEMA = "schema"
    RESOURCE = "resource"
    CONSOLE_COMMAND = "console_command"
    LOCAL_ENDPOINT = "local_endpoint"


class PublicEntryStatus(StrEnum):
    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    INTERNAL = "internal"


class CompatibilityGuarantee(StrEnum):
    SEMVER = "semver"
    SERIALIZED_CONTRACT = "serialized_contract"
    RELEASE_BOUND = "release_bound"
    NONE = "none"


class PublicSurfaceEntry(StrictContractModel):
    qualified_name: str = Field(min_length=1)
    public_import: str | None = None
    kind: PublicEntryKind
    status: PublicEntryStatus
    introduced: str
    deprecated: str | None = None
    removal: str | None = None
    schema_id: str | None = None
    documentation_anchor: str | None = None
    compatibility: CompatibilityGuarantee


class PublicSurfaceInventory(StrictContractModel):
    contract: str
    contract_version: str
    entries: tuple[PublicSurfaceEntry, ...]

    @model_validator(mode="after")
    def unique_coherent_entries(self) -> Self:
        names = [entry.qualified_name for entry in self.entries]
        imports = [entry.public_import for entry in self.entries if entry.public_import is not None]
        if len(names) != len(set(names)):
            raise ValueError("public-surface qualified names must be unique")
        if len(imports) != len(set(imports)):
            raise ValueError("public-surface import paths must be unique")
        for entry in self.entries:
            if entry.status is PublicEntryStatus.DEPRECATED and entry.deprecated is None:
                raise ValueError("deprecated public entries require a deprecation version")
            if entry.status is PublicEntryStatus.SUPPORTED and entry.removal is not None:
                raise ValueError("supported public entries cannot declare removal")
        return self


class PublicSurfaceReconciliation(StrictContractModel):
    missing_exports: tuple[str, ...]
    unclassified_exports: tuple[str, ...]
    signature_mismatches: tuple[str, ...]
    enum_mismatches: tuple[str, ...]
    schema_mismatches: tuple[str, ...]
    documentation_mismatches: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not any(
            (
                self.missing_exports,
                self.unclassified_exports,
                self.signature_mismatches,
                self.enum_mismatches,
                self.schema_mismatches,
                self.documentation_mismatches,
            )
        )


def load_public_surface() -> PublicSurfaceInventory:
    """Load the installed, versioned public-surface resource strictly."""

    payload = resources.files("rdam.ingest").joinpath(_RESOURCE).read_bytes()
    return PublicSurfaceInventory.model_validate_json(payload)


def reconcile_public_surface(
    inventory: PublicSurfaceInventory | None = None,
) -> PublicSurfaceReconciliation:
    """Reconcile declared imports, root exports, schemas, enums, and documentation."""

    authority = inventory or load_public_surface()
    missing: list[str] = []
    signature_mismatches: list[str] = []
    enum_mismatches: list[str] = []
    schema_mismatches: list[str] = []
    documentation_mismatches: list[str] = []
    declared_by_module: dict[str, set[str]] = {}

    for entry in authority.entries:
        if entry.public_import is not None:
            try:
                value, module_name, root_name = _resolve_import(entry.public_import)
            except AttributeError, ImportError, ValueError:
                missing.append(entry.qualified_name)
                continue
            declared_by_module.setdefault(module_name, set()).add(root_name)
            if entry.kind is PublicEntryKind.FUNCTION:
                if not callable(value):
                    signature_mismatches.append(entry.qualified_name)
                    continue
                try:
                    inspect.signature(value)
                except TypeError, ValueError:
                    signature_mismatches.append(entry.qualified_name)
            if entry.kind is PublicEntryKind.ENUM:
                members = getattr(value, "__members__", None)
                if not isinstance(members, Mapping):
                    enum_mismatches.append(entry.qualified_name)
                    continue
                enum_members = cast(Mapping[object, object], members)
                if len(enum_members) != len({getattr(member, "value", object()) for member in enum_members.values()}):
                    enum_mismatches.append(entry.qualified_name)
        if entry.schema_id is not None and not _schema_exists(entry.schema_id):
            schema_mismatches.append(entry.qualified_name)
        if entry.documentation_anchor is not None and not _documentation_anchor_exists(entry.documentation_anchor):
            documentation_mismatches.append(entry.qualified_name)

    unclassified: list[str] = []
    for module_name, declared in declared_by_module.items():
        exported = getattr(import_module(module_name), "__all__", None)
        if exported is None:
            continue
        unclassified.extend(f"{module_name}.{name}" for name in sorted(set(exported) - declared))

    return PublicSurfaceReconciliation(
        missing_exports=tuple(sorted(missing)),
        unclassified_exports=tuple(sorted(unclassified)),
        signature_mismatches=tuple(sorted(signature_mismatches)),
        enum_mismatches=tuple(sorted(enum_mismatches)),
        schema_mismatches=tuple(sorted(schema_mismatches)),
        documentation_mismatches=tuple(sorted(documentation_mismatches)),
    )


def _resolve_import(public_import: str) -> tuple[object, str, str]:
    module_name, separator, path = public_import.partition(":")
    if not separator or not module_name or not path:
        raise ValueError("public imports use module:attribute notation")
    value: object = import_module(module_name)
    parts = path.split(".")
    for part in parts:
        value = getattr(value, part)
    return value, module_name, parts[0]


def _schema_exists(schema_id: str) -> bool:
    for resource in resources.files("rdam.ingest").joinpath("schemas").iterdir():
        if resource.is_file() and resource.name.endswith(".schema.json"):
            document: object = json.loads(resource.read_bytes())
            if isinstance(document, dict) and cast(Mapping[str, object], document).get("$id") == schema_id:
                return True
    return False


def _documentation_anchor_exists(anchor: str) -> bool:
    repository = Path(__file__).resolve().parents[2]
    quickstart = repository / "specs/004-production-api-contract/quickstart.md"
    if not quickstart.is_file():
        return False
    headings = {
        _slug(match.group(1))
        for match in re.finditer(r"^#{1,6}\s+(.+)$", quickstart.read_text(encoding="utf-8"), re.MULTILINE)
    }
    return anchor in headings


def _slug(heading: str) -> str:
    normalized = re.sub(r"[^a-z0-9 -]", "", heading.casefold())
    return re.sub(r"\s+", "-", normalized.strip())


__all__ = [
    "CompatibilityGuarantee",
    "PublicEntryKind",
    "PublicEntryStatus",
    "PublicSurfaceEntry",
    "PublicSurfaceInventory",
    "PublicSurfaceReconciliation",
    "load_public_surface",
    "reconcile_public_surface",
]
