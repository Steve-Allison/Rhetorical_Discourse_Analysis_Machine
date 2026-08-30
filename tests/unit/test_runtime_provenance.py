"""Installed-version and source-revision provenance boundaries."""

from importlib.metadata import PackageNotFoundError, version
import re
from collections.abc import Iterator

import pytest

from isanlp_rst import _version
from isanlp_rst import _provenance


@pytest.fixture(autouse=True)
def _clear_runtime_caches() -> Iterator[None]:
    _provenance.resolve_package_version.cache_clear()
    _provenance.resolve_source_revision.cache_clear()
    yield
    _provenance.resolve_package_version.cache_clear()
    _provenance.resolve_source_revision.cache_clear()


def test_tool_version_is_installed_distribution_version() -> None:
    assert _provenance.resolve_package_version() == version("isanlp_rst") == "5.0.0"


def test_unknown_is_only_used_when_distribution_metadata_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_: str) -> str:
        raise PackageNotFoundError("isanlp_rst")

    monkeypatch.setattr(_version, "distribution_version", missing)
    assert _provenance.resolve_package_version() == "unknown"


def test_unexpected_metadata_failure_is_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_: str) -> str:
        raise RuntimeError("metadata backend failed")

    monkeypatch.setattr(_version, "distribution_version", broken)
    with pytest.raises(RuntimeError, match="metadata backend failed"):
        _provenance.resolve_package_version()


def test_source_revision_is_separate_from_semantic_version() -> None:
    revision = _provenance.resolve_source_revision()
    assert re.fullmatch(r"[0-9a-f]{40}(?:-dirty)?", revision)
    assert revision != _provenance.resolve_package_version()
