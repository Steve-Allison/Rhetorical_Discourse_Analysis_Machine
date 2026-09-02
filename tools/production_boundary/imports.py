"""Static import-closure validation for the production namespace."""

import ast
from collections import deque
from pathlib import Path
import time

from tools.production_boundary.authority import OwnershipAuthority
from tools.production_boundary.contracts import BoundaryReport, BoundaryViolation, OwnershipClass, ViolationKind

BOUNDARY_ROOTS = frozenset({"machine", "rst", "dung", "ibis"})
"""Machine boundary directories. They are never importable packages: the packages inside
carry their own import names (``machine/rdam`` imports as ``rdam``), so the boundary
segment is dropped when naming modules (006 architecture-boundaries §Structural rules 2)."""


def module_name(root: Path, path: Path) -> str:
    parts = list(path.relative_to(root).with_suffix("").parts)
    if len(parts) > 1 and parts[0] in BOUNDARY_ROOTS:
        del parts[0]
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_relative(current: str, level: int, target: str | None) -> str:
    package = current.split(".")[:-1]
    if level > len(package) + 1:
        return target or ""
    prefix = package[: len(package) - level + 1]
    if target:
        prefix.extend(target.split("."))
    return ".".join(prefix)


def imported_modules(path: Path, current: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_relative(current, node.level, node.module) if node.level else (node.module or "")
            if base:
                imports.add(base)
                imports.update(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
    return tuple(sorted(imports))


def _local_target(name: str, modules: dict[str, Path]) -> str | None:
    candidate = name
    while candidate:
        if candidate in modules:
            return candidate
        candidate = candidate.rpartition(".")[0]
    return None


def validate_import_boundary(root: Path, authority: OwnershipAuthority | None = None) -> BoundaryReport:
    started = time.perf_counter()
    repository = root.resolve()
    ownership = authority or OwnershipAuthority(repository)
    # Every production root plus the workbench: the walk from each production module must
    # never reach a workbench module, directly or transitively (FR-006, research D5 check a).
    source_roots = {"isanlp_rst", "workbench", "workbench.research", *BOUNDARY_ROOTS}
    python_files = [
        path
        for path in ownership.iter_relevant_files()
        if path.suffix == ".py" and ownership.relative(path).parts[0] in source_roots
    ]
    modules = {module_name(repository, path): path for path in python_files}
    graph: dict[str, tuple[str, ...]] = {}
    for name, path in modules.items():
        graph[name] = tuple(target for imported in imported_modules(path, name) if (target := _local_target(imported, modules)))

    production = {name for name, path in modules.items() if ownership.classify(ownership.relative(path)) == OwnershipClass.PRODUCTION}
    violations: list[BoundaryViolation] = []
    for root_module in sorted(production):
        queue: deque[tuple[str, tuple[str, ...]]] = deque([(root_module, (root_module,))])
        visited = {root_module}
        while queue:
            current, chain = queue.popleft()
            for target in graph.get(current, ()):
                target_owner = ownership.classify(ownership.relative(modules[target]))
                next_chain = (*chain, target)
                if target_owner != OwnershipClass.PRODUCTION:
                    violations.append(BoundaryViolation(kind=ViolationKind.FORBIDDEN_IMPORT, root=root_module, path=next_chain, detail=f"production reaches {target_owner.value} module {target}"))
                    continue
                if target not in visited:
                    visited.add(target)
                    queue.append((target, next_chain))

    unique = {tuple(item.path): item for item in violations}
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return BoundaryReport(scanned_files=len(python_files), production_modules=len(production), elapsed_ms=elapsed_ms, violations=tuple(unique[key] for key in sorted(unique)))
