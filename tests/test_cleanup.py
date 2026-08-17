"""Unit tests for ``scripts/cleanup.py`` (stdlib-only project cleaner)."""

import importlib.util
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts" / "cleanup.py"


def _load_cleanup():
    spec = importlib.util.spec_from_file_location("isanlp_rst_cleanup", SCRIPTS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cleanup = _load_cleanup()


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "keep.py").write_text("ok\n", encoding="utf-8")
    pycache = tmp_path / "pkg" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "mod.cpython-312.pyc").write_bytes(b"\0")
    (tmp_path / ".DS_Store").write_bytes(b"ds")
    (tmp_path / "scratch.tmp").write_text("tmp\n", encoding="utf-8")
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref\n", encoding="utf-8")
    (git / "__pycache__").mkdir()
    (git / "__pycache__" / "ignored.pyc").write_bytes(b"\0")
    pixi = tmp_path / ".pixi"
    pixi.mkdir()
    (pixi / "__pycache__").mkdir()
    (pixi / "__pycache__" / "env.pyc").write_bytes(b"\0")
    return tmp_path


def test_collects_bytecode_caches_and_temp_not_source(tree: Path) -> None:
    found = {p.relative_to(tree).as_posix() for p in cleanup.collect_junk(tree)}
    assert "pkg/__pycache__" in found
    assert ".DS_Store" in found
    assert "scratch.tmp" in found
    assert "keep.py" not in found


def test_skips_git_and_pixi_trees(tree: Path) -> None:
    found = {p.relative_to(tree).as_posix() for p in cleanup.collect_junk(tree)}
    assert not any(path.startswith(".git") for path in found)
    assert not any(path.startswith(".pixi") for path in found)


def test_remove_deletes_junk_keeps_source_and_protected(tree: Path) -> None:
    junk = cleanup.collect_junk(tree)
    cleanup.remove_junk(junk, dry_run=False, root=tree)
    assert (tree / "keep.py").is_file()
    assert (tree / ".git" / "HEAD").is_file()
    assert (tree / ".pixi" / "__pycache__" / "env.pyc").is_file()
    assert not (tree / "pkg" / "__pycache__").exists()
    assert not (tree / ".DS_Store").exists()
    assert not (tree / "scratch.tmp").exists()


def test_dry_run_does_not_delete(tree: Path) -> None:
    junk = cleanup.collect_junk(tree)
    cleanup.remove_junk(junk, dry_run=True, root=tree)
    assert (tree / "pkg" / "__pycache__").is_dir()
    assert (tree / ".DS_Store").is_file()
