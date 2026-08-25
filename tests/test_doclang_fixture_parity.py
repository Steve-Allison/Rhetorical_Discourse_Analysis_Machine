"""Pinned upstream parity and locked-validator tests for DocLang fixtures."""

from hashlib import sha256
from pathlib import Path

import doclang
from lxml import etree
from pydantic import BaseModel, ConfigDict
import pytest


class _UpstreamManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    upstream_commit: str
    files: dict[str, str]


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "doclang"
MANIFEST = _UpstreamManifest.model_validate_json(
    (FIXTURE_DIR / "upstream-manifest.json").read_text(encoding="utf-8")
)
LOCAL_FIXTURES = tuple(sorted(FIXTURE_DIR.glob("*.dclg")))


def test_fixture_names_and_hashes_match_pinned_upstream_manifest() -> None:
    local_by_name = {path.name: path for path in LOCAL_FIXTURES}
    assert local_by_name.keys() == MANIFEST.files.keys()
    mismatches = {
        name: (sha256(path.read_bytes()).hexdigest(), MANIFEST.files[name])
        for name, path in local_by_name.items()
        if sha256(path.read_bytes()).hexdigest() != MANIFEST.files[name]
    }
    assert not mismatches


def test_no_legacy_double_extension_fixture_remains() -> None:
    assert not tuple(FIXTURE_DIR.glob("*.dclg.xml"))


@pytest.mark.parametrize("fixture", LOCAL_FIXTURES, ids=lambda path: path.name)
def test_locked_doclang_validator_accepts_every_upstream_fixture(fixture: Path) -> None:
    root_tag = etree.parse(fixture).getroot().tag
    has_namespace = isinstance(root_tag, str) and root_tag.startswith("{")
    doclang.validate(fixture, allow_empty_namespace=not has_namespace)
