"""Production assembly is separate from technique-independent orchestration."""

import ast
from pathlib import Path
import subprocess
import sys

from rdam import BOUNDARY_TECHNIQUES, ExecutionPolicy, production_machine
from rdam.composition import production_machine as assemble


def test_production_entry_points_preserve_all_providers_and_policy() -> None:
    policy = ExecutionPolicy(max_workers=1)
    assert production_machine is assemble
    for factory in (production_machine, assemble):
        machine = factory(execution_policy=policy)
        assert tuple(machine.providers) == BOUNDARY_TECHNIQUES
        assert tuple(item.technique for item in machine.capabilities().techniques) == BOUNDARY_TECHNIQUES


def test_orchestration_imports_no_technique_package() -> None:
    root = Path(__file__).resolve().parents[2]
    module = ast.parse((root / "rdam" / "machine.py").read_text(encoding="utf-8"))
    forbidden = tuple(f"rdam.{technique.value}" for technique in BOUNDARY_TECHNIQUES)
    for node in ast.walk(module):
        names = (
            [alias.name for alias in node.names] if isinstance(node, ast.Import)
            else [node.module or ""] if isinstance(node, ast.ImportFrom)
            else []
        )
        assert not any(name == prefix or name.startswith(prefix + ".") for name in names for prefix in forbidden)


def test_importing_machine_does_not_load_provider_implementations() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import sys, rdam; assert not any(name.startswith('rdam.rst') for name in sys.modules)"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
