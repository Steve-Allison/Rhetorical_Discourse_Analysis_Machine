"""Causal tests for the production/offline boundary authority."""

from pathlib import Path, PurePosixPath
import tarfile
import zipfile

import pytest

from tools.production_boundary.artifacts import inspect_artifact
from tools.production_boundary.authority import OwnershipAuthority, OwnershipClassificationError, validate_ownership
from tools.production_boundary.contracts import OwnershipClass, OwnershipRule, ViolationKind
from tools.production_boundary.dependencies import validate_declared_dependencies
from tools.production_boundary.imports import validate_import_boundary


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_authority_classifies_each_surface() -> None:
    authority = OwnershipAuthority(Path.cwd())
    assert authority.classify("isanlp_rst/parser.py") == OwnershipClass.PRODUCTION
    assert authority.classify("offline_workbench/evaluation/rst/parseval.py") == OwnershipClass.OFFLINE
    assert authority.classify("offline_workbench/training/run.py") == OwnershipClass.OFFLINE
    assert authority.classify("tests/test_parser.py") == OwnershipClass.REPOSITORY
    assert authority.classify("dist/isanlp_rst.whl") == OwnershipClass.GENERATED


def test_unmatched_relevant_path_fails_closed(tmp_path: Path) -> None:
    authority = OwnershipAuthority(tmp_path)
    with pytest.raises(OwnershipClassificationError, match="matched 0 ownership rules"):
        authority.classify("unowned/member.py")


def test_ambiguous_relevant_path_fails_closed(tmp_path: Path) -> None:
    base = OwnershipAuthority(tmp_path)
    overlapping = OwnershipRule(
        rule_id="duplicate-production",
        prefix=PurePosixPath("isanlp_rst"),
        ownership=OwnershipClass.PRODUCTION,
        reason="causal ambiguity fixture",
        publishable=True,
    )
    authority = OwnershipAuthority(tmp_path, rules=(*base.rules, overlapping))
    with pytest.raises(OwnershipClassificationError, match="matched 2 ownership rules"):
        authority.classify("isanlp_rst/parser.py")


def test_gate_reports_unmatched_and_ambiguous_paths(tmp_path: Path) -> None:
    _write(tmp_path / "unowned/member.py")
    unmatched = validate_ownership(OwnershipAuthority(tmp_path))
    assert unmatched[0].kind == ViolationKind.UNMATCHED_OWNERSHIP
    assert unmatched[0].path == ("unowned/member.py",)

    _write(tmp_path / "isanlp_rst/parser.py")
    base = OwnershipAuthority(tmp_path)
    duplicate = OwnershipRule(rule_id="duplicate", prefix=PurePosixPath("isanlp_rst"), ownership=OwnershipClass.PRODUCTION, reason="ambiguity fixture", publishable=True)
    ambiguous = validate_ownership(OwnershipAuthority(tmp_path, rules=(*base.rules, duplicate)))
    assert any(item.kind == ViolationKind.AMBIGUOUS_OWNERSHIP and item.path == ("isanlp_rst/parser.py",) for item in ambiguous)


def test_direct_production_to_offline_import_reports_complete_path(tmp_path: Path) -> None:
    _write(tmp_path / "isanlp_rst/__init__.py", "from offline_workbench import trainer\n")
    _write(tmp_path / "offline_workbench/__init__.py")
    _write(tmp_path / "offline_workbench/trainer.py")
    report = validate_import_boundary(tmp_path)
    assert report.violations[0].kind == ViolationKind.FORBIDDEN_IMPORT
    assert report.violations[0].path == ("isanlp_rst", "offline_workbench")


def test_indirect_production_to_offline_import_reports_complete_path(tmp_path: Path) -> None:
    _write(tmp_path / "isanlp_rst/__init__.py", "from isanlp_rst import bridge\n")
    _write(tmp_path / "isanlp_rst/bridge.py", "from offline_workbench import trainer\n")
    _write(tmp_path / "offline_workbench/__init__.py")
    _write(tmp_path / "offline_workbench/trainer.py")
    report = validate_import_boundary(tmp_path)
    paths = {violation.path for violation in report.violations}
    assert ("isanlp_rst", "isanlp_rst.bridge", "offline_workbench") in paths


def test_new_production_module_needs_no_secondary_allowlist(tmp_path: Path) -> None:
    _write(tmp_path / "isanlp_rst/__init__.py", "from isanlp_rst import new_runtime\n")
    _write(tmp_path / "isanlp_rst/new_runtime.py", "VALUE = 1\n")
    report = validate_import_boundary(tmp_path)
    assert report.valid
    assert report.production_modules == 2


def test_offline_dependency_in_production_set_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", '[project]\nname="fixture"\nversion="1"\ndependencies=["fire>=0.7"]\n')
    violations = validate_declared_dependencies(tmp_path)
    assert len(violations) == 1
    assert violations[0].path == ("project.dependencies", "fire")


def test_forbidden_wheel_member_is_named(tmp_path: Path) -> None:
    wheel = tmp_path / "isanlp_rst-1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("isanlp_rst/__init__.py", "")
        archive.writestr("offline_workbench/trainer.py", "")
        archive.writestr("isanlp_rst-1.dist-info/METADATA", "")
    receipt = inspect_artifact(wheel)
    assert receipt.forbidden_members == ("offline_workbench/trainer.py",)


def test_forbidden_sdist_member_is_named(tmp_path: Path) -> None:
    source = tmp_path / "trainer.py"
    source.write_text("", encoding="utf-8")
    sdist = tmp_path / "isanlp_rst-1.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        archive.add(source, arcname="isanlp_rst-1/offline_workbench/trainer.py")
        metadata = tmp_path / "PKG-INFO"
        metadata.write_text("Metadata-Version: 2.4\nName: isanlp-rst\nVersion: 1\n", encoding="utf-8")
        archive.add(metadata, arcname="isanlp_rst-1/PKG-INFO")
    receipt = inspect_artifact(sdist)
    assert receipt.forbidden_members == ("isanlp_rst-1/offline_workbench/trainer.py",)


def test_artifact_dependencies_are_read_from_metadata(tmp_path: Path) -> None:
    wheel = tmp_path / "isanlp_rst-1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("isanlp_rst/__init__.py", "")
        archive.writestr(
            "isanlp_rst-1.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: isanlp-rst\nVersion: 1\nRequires-Dist: torch>=2\n",
        )
    assert inspect_artifact(wheel).declared_dependencies == ("torch",)
