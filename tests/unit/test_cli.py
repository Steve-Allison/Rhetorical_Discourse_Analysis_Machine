"""Unified command grammar checks execute the real module entry point."""

from importlib.metadata import version

from tests.interfaces.test_cli import diagnostic, record, run_cli


def test_cli_version_is_stable_json() -> None:
    payload = record(run_cli("version"))
    assert payload["contract"] == "rdam.version"
    assert payload["package"] == "rdam"
    assert payload["version"] == version("rdam")
    assert payload["contracts"]


def test_cli_analyse_requires_explicit_techniques() -> None:
    problem = diagnostic(run_cli("analyse", "--text", "First. Second."))
    assert problem["code"] == "invalid_arguments"


def test_cli_malformed_edus_are_a_safe_typed_failure() -> None:
    problem = diagnostic(run_cli("analyse", "--edus", "not-json", "--techniques", "dung"))
    assert problem["category"] == "invalid_request"
