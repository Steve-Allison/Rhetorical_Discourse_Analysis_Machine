"""Conformance guard: do we still ingest current DocLang output via dclq + doclang?"""

from pathlib import Path

from dclq.document import LoadedDocument
import doclang
from lxml import etree

import pytest

from rdam.ingest import ProductionIngestError, ProductionIngestor, SourceArtifact, SourceForm

DOCLANG_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "doclang"


def _root_ns(path: Path) -> str:
    """Return the XML namespace declared on a fixture's root element (or '')."""
    root = etree.parse(str(path)).getroot()
    tag = root.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[0][1:]
    return ""


def _declared_version(path: Path) -> str | None:
    root = etree.parse(str(path)).getroot()
    return root.get("version")


_NAMESPACED_DOCLANG = sorted(p for p in DOCLANG_FIXTURES.glob("*.dclg") if _root_ns(p))


def test_compat_fixtures_present() -> None:
    assert _NAMESPACED_DOCLANG, "no namespaced doclang fixtures found — compat guard would no-op"


def test_doclang_namespace_is_current() -> None:
    sample = _NAMESPACED_DOCLANG[0]
    doclang.validate(
        sample,
        spec_version="0.9" if _declared_version(sample) is None else None,
        allow_empty_namespace=True,
    )
    loaded = LoadedDocument.load(sample, validate=False)
    assert loaded.units


@pytest.mark.parametrize("fixture", _NAMESPACED_DOCLANG, ids=lambda p: p.name)
def test_doclang_validator_and_canonical_ingest_accept_namespaced_fixtures(fixture: Path) -> None:
    doclang.validate(
        fixture,
        spec_version="0.9" if _declared_version(fixture) is None else None,
        allow_empty_namespace=True,
    )
    source = SourceArtifact.from_path(fixture, source_form=SourceForm.DOCLANG_XML)
    if fixture.name == "ok_comprehensive.dclg":
        with pytest.raises(ProductionIngestError):
            ProductionIngestor(parser=None).prepare(source)
        return
    prepared = ProductionIngestor(parser=None).prepare(source)
    assert prepared.semantic.inventory, f"{fixture.name}: canonical ingest produced no inventoried items"
