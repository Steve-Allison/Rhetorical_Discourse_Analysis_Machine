"""Shared ingest has one explicit owner; provider imports belong to composition."""

from pathlib import Path

from tools.production_boundary.authority import OwnershipAuthority, validate_ownership
from tools.production_boundary.imports import validate_import_boundary


def test_shared_ingest_has_exactly_one_machine_owned_production_rule(tmp_path: Path) -> None:
    source = tmp_path / "rdam" / "ingest" / "source.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    authority = OwnershipAuthority(tmp_path)
    rules = authority.matching_rules(source)
    assert len(rules) == 1
    assert rules[0].rule_id == "rdam-ingest"
    assert rules[0].publishable
    assert validate_ownership(authority) == ()


def test_boundary_rejects_direct_technique_import_in_orchestration(tmp_path: Path) -> None:
    package = tmp_path / "rdam"
    package.mkdir()
    machine = package / "machine.py"
    machine.write_text("from .rst import Parser\n", encoding="utf-8")
    report = validate_import_boundary(tmp_path)
    assert not report.valid
    assert any(violation.path == ("rdam.machine", "rdam.rst") for violation in report.violations)
    machine.write_text("from .composition import production_machine\n", encoding="utf-8")
    (package / "composition.py").write_text("from .rst import Parser\n", encoding="utf-8")
    assert validate_import_boundary(tmp_path).valid
