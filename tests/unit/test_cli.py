"""Unit checks for installed command grammar that do not run inference."""

import json

import pytest

from rdam.rst import __version__
from rdam.rst.cli import main
from rdam.ingest import SafeProductionFailureRecord, load_contract


def test_cli_version_is_stable_json(capsysbinary: pytest.CaptureFixture[bytes]) -> None:
    assert main(["version"]) == 0
    payload = json.loads(capsysbinary.readouterr().out)
    assert payload == {"package": "rdam", "version": __version__}


def test_cli_parse_requires_an_immutable_release_configuration(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["parse", "--text", "First. Second."])
    assert raised.value.code == 2
    assert b"--model-store" in capsysbinary.readouterr().err


def test_cli_malformed_edus_are_a_safe_typed_failure(
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    assert main(
        [
            "parse",
            "--edus",
            "not-json",
            "--model-store",
            "/model-store",
            "--release-id",
            "release",
        ]
    ) == 2
    record = load_contract(capsysbinary.readouterr().err)
    assert isinstance(record, SafeProductionFailureRecord)
