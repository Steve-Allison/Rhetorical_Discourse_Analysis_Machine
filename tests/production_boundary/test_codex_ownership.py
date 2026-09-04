"""Codex controls are repository tooling, never distributable production code."""

from pathlib import Path

from tools.production_boundary.authority import OwnershipAuthority, validate_ownership
from tools.production_boundary.contracts import OwnershipClass


def test_codex_controls_have_one_non_publishable_repository_owner(tmp_path: Path) -> None:
    control = tmp_path / ".codex" / "skills" / "example" / "SKILL.md"
    control.parent.mkdir(parents=True)
    control.write_text("# Local skill\n", encoding="utf-8")
    authority = OwnershipAuthority(tmp_path)
    assert authority.classify(control) is OwnershipClass.REPOSITORY
    rules = authority.matching_rules(control)
    assert len(rules) == 1
    assert not rules[0].publishable
    assert validate_ownership(authority) == ()
