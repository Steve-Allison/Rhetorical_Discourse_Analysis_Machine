"""Production rejects experimental eRST without importing or loading its runtime."""

import inspect
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from rdam import AggregateRequest, FormalismChoice, Machine, Technique
from rdam.cli import create_parser
from rdam.configuration import RstSettings
from rdam.contracts import OperationError
from rdam.rst import Parser, RstDocument
from rdam.rst.provider import RstProvider
from rdam.serialization import schema_models


def test_production_does_not_import_or_resolve_erst(tmp_path: Path) -> None:
    script = '''
import os, sys
os.environ['ISANLP_RST_ERST_CHECKPOINT'] = sys.argv[1]
from rdam.composition import production_machine
from rdam.rst import Parser
from rdam.rst.provider import RstProvider
assert not hasattr(Parser, 'complete_erst_document')
assert RstProvider().declaration.formalism('erst_graph') is None
assert all(f.formalism_id != 'erst_graph' for t in production_machine().capabilities().techniques for f in t.formalisms)
assert not any(n == 'workbench' or n.startswith('workbench.') for n in sys.modules)
'''
    invalid_bundle = tmp_path / "manifest.json"
    invalid_bundle.write_text("invalid checkpoint must never be read")
    result = subprocess.run([sys.executable, "-c", script, str(invalid_bundle)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_erst_configuration_and_cli_option_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RstSettings.model_validate({"erst_checkpoint": "checkpoint"})
    with pytest.raises(ValidationError):
        RstSettings.model_validate({"default_formalism": "erst_graph"})
    with pytest.raises(OperationError):
        create_parser().parse_args(["capabilities", "--erst-checkpoint", "checkpoint"])
    assert "erst_scorer_checkpoint" not in inspect.signature(Parser).parameters
    assert "erst-result" not in schema_models()


def test_explicit_erst_request_cannot_load_production_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = RstProvider()
    def unexpected_load() -> Parser:
        raise AssertionError("unsupported formalism loaded a parser")
    monkeypatch.setattr(provider, "_load_parser", unexpected_load)
    request = AggregateRequest.for_text("Evidence.", (Technique.RST,),
        formalisms=(FormalismChoice(technique=Technique.RST, formalism_id="erst_graph"),))
    result = Machine((provider,)).analyse(request)
    assert result.status == "unsuccessful"
    parser = Parser.__new__(Parser)
    with pytest.raises(ValueError, match="workbench"):
        parser.parse_document(RstDocument.from_text("Evidence."), output="erst_graph")
