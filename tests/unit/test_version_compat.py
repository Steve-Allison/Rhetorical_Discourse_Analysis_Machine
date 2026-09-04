"""Conformance guard: do we still ingest current Docling / DocLang output?

The rest of the suite parses frozen fixtures — that proves we handle files we
captured once, not that those files still match what current Docling / DocLang
emit. These tests pin our fixtures to the *installed* docling-core / doclang, so
a release that moves the schema version, the XML namespace, or the validator
turns the suite red instead of letting current-output breakage pass silently.

Coverage:
- Run against the **locked** packages on every push via `.github/workflows/ci.yml`
  (these are fast / not slow).
- Run against the **latest** packages weekly via `.github/workflows/deps-compat.yml`,
  which `pixi update`s docling-core / doclang first — that is the "check on every
  new version" guarantee.
"""

import json
from pathlib import Path

import doclang
from docling_core.types.doc.document import CURRENT_VERSION, DoclingDocument
from lxml import etree

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact, SourceForm

DOCLING_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "docling"
DOCLANG_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "doclang"


def _root_ns(path: Path) -> str:
    """Return the XML namespace declared on a fixture's root element (or '')."""
    root = etree.parse(str(path)).getroot()
    tag = root.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag.split("}", 1)[0][1:]
    return ""


_DOCLING_JSON = sorted(DOCLING_FIXTURES.glob("*.docling.json"))
_NAMESPACED_DOCLANG = sorted(p for p in DOCLANG_FIXTURES.glob("*.dclg") if _root_ns(p))


def test_compat_fixtures_present() -> None:
    """Guard against the guard silently no-opping if fixtures are moved/renamed —
    an empty parametrize set would pass vacuously, which is the exact silent-green
    failure mode this whole module exists to prevent."""
    assert _DOCLING_JSON, "no docling fixtures found — compat guard would no-op"
    assert _NAMESPACED_DOCLANG, "no namespaced doclang fixtures found — compat guard would no-op"


@pytest.mark.parametrize("fixture", _DOCLING_JSON, ids=lambda p: p.name)
def test_docling_fixtures_match_current_schema(fixture: Path) -> None:
    """Each fixture's declared Docling schema version must equal the installed
    docling-core ``CURRENT_VERSION``. Red => Docling moved its schema; regenerate
    the Docling fixtures from current Docling output and re-verify canonical ingest
    before relying on the new version."""
    declared = json.loads(fixture.read_text(encoding="utf-8")).get("version")
    assert declared == CURRENT_VERSION, (
        f"{fixture.name} declares Docling schema {declared!r}, but installed "
        f"docling-core CURRENT_VERSION is {CURRENT_VERSION!r}. Regenerate the "
        f"Docling fixtures from current Docling and re-verify canonical ingest."
    )


@pytest.mark.parametrize("fixture", _DOCLING_JSON, ids=lambda p: p.name)
def test_docling_current_package_and_canonical_ingest_accept_fixtures(fixture: Path) -> None:
    """Current docling-core and canonical ingest must accept every fixture."""
    assert DoclingDocument.load_from_json(fixture) is not None
    prepared = ProductionIngestor(parser=None).prepare(
        SourceArtifact.from_path(fixture, source_form=SourceForm.DOCLING_JSON)
    )
    assert prepared.semantic.inventory, (
        f"{fixture.name}: canonical ingest produced no inventoried items"
    )


def test_doclang_namespace_is_current() -> None:
    """The installed current validator must accept our namespaced specimen."""
    sample = _NAMESPACED_DOCLANG[0]
    doclang.validate(sample, allow_empty_namespace=True)


@pytest.mark.parametrize("fixture", _NAMESPACED_DOCLANG, ids=lambda p: p.name)
def test_doclang_validator_accepts_namespaced_fixtures(fixture: Path) -> None:
    """Every namespaced fixture we treat as valid must still pass the installed
    doclang validator. Red => doclang tightened or changed its XSD against what we
    consider current DocLang."""
    doclang.validate(fixture, allow_empty_namespace=True)
