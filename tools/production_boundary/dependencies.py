"""Declared production dependency validation."""

from pathlib import Path
import re
import tomllib

from tools.production_boundary.authority import OwnershipAuthority
from tools.production_boundary.contracts import BoundaryViolation, OwnershipClass, ViolationKind


_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def requirement_name(requirement: str) -> str:
    match = _NAME.match(requirement)
    if match is None:
        raise ValueError(f"cannot determine dependency name from {requirement!r}")
    return match.group(1).casefold().replace("_", "-")


def validate_declared_dependencies(root: Path, authority: OwnershipAuthority | None = None) -> tuple[BoundaryViolation, ...]:
    repository = root.resolve()
    ownership = authority or OwnershipAuthority(repository)
    payload = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]
    requirements = list(project.get("dependencies", ()))
    requirements.extend(project.get("optional-dependencies", {}).get("formats", ()))
    violations: list[BoundaryViolation] = []
    for requirement in requirements:
        name = requirement_name(requirement)
        owner = ownership.dependency_owner(name)
        if owner != OwnershipClass.PRODUCTION:
            violations.append(BoundaryViolation(kind=ViolationKind.FORBIDDEN_DEPENDENCY, root="pyproject.toml", path=("project.dependencies", name), detail=f"production dependency {name} is classified {owner.value}"))
    return tuple(violations)
