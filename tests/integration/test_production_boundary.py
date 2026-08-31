"""Causal tests for the production/offline boundary authority."""

from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import zipfile

import pytest

from tools.production_boundary.artifacts import inspect_artifact
from tools.production_boundary.authority import OwnershipAuthority, OwnershipClassificationError, validate_ownership
from tools.production_boundary.build import _archive_commit, _require_clean_source
from tools.production_boundary.contracts import OwnershipClass, OwnershipRule, ViolationKind
from tools.production_boundary.dependencies import validate_declared_dependencies
from tools.production_boundary.imports import validate_import_boundary


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_authority_classifies_each_surface() -> None:
    authority = OwnershipAuthority(Path.cwd())
    assert authority.classify("isanlp_rst/parser.py") == OwnershipClass.PRODUCTION
    assert authority.classify("workbench/evaluation/rst/parseval.py") == OwnershipClass.OFFLINE
    assert authority.classify("workbench/training/run.py") == OwnershipClass.OFFLINE
    assert authority.classify("tests/test_parser.py") == OwnershipClass.REPOSITORY
    assert authority.classify("models/modernbert_v1/model.safetensors") == OwnershipClass.MODEL
    assert authority.classify("models/model-releases/modernbert-v1-e5ea56cd620f/release-manifest.json") == OwnershipClass.MODEL
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
    _write(tmp_path / "isanlp_rst/__init__.py", "from workbench import trainer\n")
    _write(tmp_path / "workbench/__init__.py")
    _write(tmp_path / "workbench/trainer.py")
    report = validate_import_boundary(tmp_path)
    assert report.violations[0].kind == ViolationKind.FORBIDDEN_IMPORT
    assert report.violations[0].path == ("isanlp_rst", "workbench")


def test_indirect_production_to_offline_import_reports_complete_path(tmp_path: Path) -> None:
    _write(tmp_path / "isanlp_rst/__init__.py", "from isanlp_rst import bridge\n")
    _write(tmp_path / "isanlp_rst/bridge.py", "from workbench import trainer\n")
    _write(tmp_path / "workbench/__init__.py")
    _write(tmp_path / "workbench/trainer.py")
    report = validate_import_boundary(tmp_path)
    paths = {violation.path for violation in report.violations}
    assert ("isanlp_rst", "isanlp_rst.bridge", "workbench") in paths


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
        archive.writestr("workbench/trainer.py", "")
        archive.writestr("isanlp_rst-1.dist-info/METADATA", "")
    receipt = inspect_artifact(wheel)
    assert receipt.forbidden_members == ("workbench/trainer.py",)


def test_forbidden_sdist_member_is_named(tmp_path: Path) -> None:
    source = tmp_path / "trainer.py"
    source.write_text("", encoding="utf-8")
    sdist = tmp_path / "isanlp_rst-1.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        archive.add(source, arcname="isanlp_rst-1/workbench/trainer.py")
        metadata = tmp_path / "PKG-INFO"
        metadata.write_text("Metadata-Version: 2.4\nName: isanlp-rst\nVersion: 1\n", encoding="utf-8")
        archive.add(metadata, arcname="isanlp_rst-1/PKG-INFO")
    receipt = inspect_artifact(sdist)
    assert receipt.forbidden_members == ("isanlp_rst-1/workbench/trainer.py",)


@pytest.mark.parametrize("suffix", (".pt", ".pth", ".safetensors"))
def test_model_weight_members_are_forbidden_from_wheels(tmp_path: Path, suffix: str) -> None:
    wheel = tmp_path / "isanlp_rst-1-py3-none-any.whl"
    member = f"isanlp_rst/models/parser{suffix}"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("isanlp_rst/__init__.py", "")
        archive.writestr(member, b"weight bytes")
        archive.writestr("isanlp_rst-1.dist-info/METADATA", "")
    receipt = inspect_artifact(wheel)
    assert receipt.forbidden_members == (member,)


def test_artifact_dependencies_are_read_from_metadata(tmp_path: Path) -> None:
    wheel = tmp_path / "isanlp_rst-1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("isanlp_rst/__init__.py", "")
        archive.writestr(
            "isanlp_rst-1.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: isanlp-rst\nVersion: 1\nRequires-Dist: torch>=2\n",
        )
    assert inspect_artifact(wheel).declared_dependencies == ("torch",)


def test_commit_export_build_cannot_package_stale_build_tree(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _write(
        repository / "pyproject.toml",
        """[build-system]
requires = ["setuptools>=84,<85"]
build-backend = "setuptools.build_meta"

[project]
name = "clean-build-fixture"
version = "1.0.0"
""",
    )
    _write(repository / "clean_build_fixture/__init__.py", 'VALUE = "committed"\n')
    _write(repository / ".gitignore", "build/\n")
    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(
        (
            "git",
            "-c",
            "user.name=Production Build Test",
            "-c",
            "user.email=production-build@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ),
        cwd=repository,
        check=True,
    )
    _write(repository / "build/lib/clean_build_fixture/stale.py", 'VALUE = "stale"\n')

    commit, _tree, _source_date_epoch = _require_clean_source(repository)
    archive_path = tmp_path / "source.tar"
    _archive_commit(repository, commit, archive_path)

    with tarfile.open(archive_path) as archive:
        assert "clean_build_fixture/__init__.py" in archive.getnames()
        assert "build/lib/clean_build_fixture/stale.py" not in archive.getnames()
