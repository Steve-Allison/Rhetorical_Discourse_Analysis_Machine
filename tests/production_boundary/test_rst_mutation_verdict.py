"""Real pytest subprocesses distinguish causal failures from broken test infrastructure."""

from pathlib import Path
import subprocess
import sys

import pytest

from tools.rst_mutation_test import MUTANTS, causal_failure


@pytest.mark.parametrize(
    ("source", "killed"),
    [
        ("def test_pass():\n    assert True\n", False),
        ("def test_failure():\n    assert 1 == 2\n", True),
        ("raise ImportError('collection is broken')\n", False),
        ("def test_setup(missing_fixture):\n    assert False\n", False),
        ("# no collected tests\n", False),
    ],
)
def test_only_real_test_call_failure_kills_mutant(tmp_path: Path, source: str, killed: bool) -> None:
    (tmp_path / "test_case.py").write_text(source)
    report = tmp_path / "results.xml"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(tmp_path / "test_case.py"), "-q", f"--junitxml={report}"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert causal_failure(result.returncode, report) is killed, result.stdout + result.stderr


def test_all_mutant_sites_are_present_and_unique() -> None:
    for mutant in MUTANTS:
        assert mutant.source.read_text().count(mutant.original) == 1, mutant.name


def test_missing_report_cannot_establish_a_kill(tmp_path: Path) -> None:
    assert not causal_failure(1, tmp_path / "missing.xml")


def test_timeout_is_runner_failure_not_a_mutation_kill(tmp_path: Path) -> None:
    report = tmp_path / 'results.xml'
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=0.05, check=False)
    assert not causal_failure(-15, report)
