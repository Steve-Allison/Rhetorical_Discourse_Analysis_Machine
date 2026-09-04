"""The shared-runtime mutation gate distinguishes test failures from broken tests."""

from pathlib import Path

import pytest

from tools.shared_runtime_mutation_test import causal_failure


@pytest.mark.parametrize(
    ("returncode", "failures", "errors", "killed"),
    ((1, 1, 0, True), (1, 1, 1, False), (1, 0, 1, False), (0, 0, 0, False), (2, 1, 0, False)),
)
def test_only_causal_failures_count_as_killed(
    tmp_path: Path, returncode: int, failures: int, errors: int, killed: bool,
) -> None:
    report = tmp_path / "results.xml"
    report.write_text(
        f'<testsuites><testsuite failures="{failures}" errors="{errors}" /></testsuites>',
        encoding="utf-8",
    )
    assert causal_failure(returncode, report) is killed


def test_missing_report_is_not_a_killed_mutant(tmp_path: Path) -> None:
    assert not causal_failure(1, tmp_path / "absent.xml")
