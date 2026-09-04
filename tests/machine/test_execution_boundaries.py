"""Execution is bounded to local threads; policy rejects non-integer limits."""

import ast
from pathlib import Path
from typing import cast

import pytest

from rdam import ExecutionPolicy


@pytest.mark.parametrize("value", (0, 8, True, 1.5))
def test_execution_workers_are_bounded_integers(value: int | float) -> None:
    with pytest.raises(ValueError):
        ExecutionPolicy(max_workers=cast(int, value))


def test_execution_stays_in_process() -> None:
    source = Path(__file__).parents[2] / "rdam" / "machine.py"
    tree = ast.parse(source.read_text())
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert "concurrent.futures" in imports
    assert not imports.intersection({"multiprocessing", "celery", "rq", "subprocess"})
    assert not any(isinstance(node, ast.Name) and node.id == "ProcessPoolExecutor" for node in ast.walk(tree))
