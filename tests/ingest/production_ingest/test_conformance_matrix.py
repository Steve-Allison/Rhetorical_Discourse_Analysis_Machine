"""Six-source-form analysed/empty and canonical round-trip matrix."""

from collections.abc import Callable
from pathlib import Path

import pytest

from rdam.rst.ingest import (
    AnalysedOutcome,
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
    load_contract,
    serialize_contract,
)

from .conftest import ParserBuilder
from .test_retained_structure import _archive_fixture

_FIXTURES = Path("tests/fixtures/production_api/retained_content")


def _text() -> SourceArtifact:
    return SourceArtifact.from_path(_FIXTURES / "mixed.txt", source_form=SourceForm.TEXT)


def _edus() -> SourceArtifact:
    return SourceArtifact.from_edus(("First.", "Second."), source_name="matrix.edus")


def _markdown() -> SourceArtifact:
    return SourceArtifact.from_path(_FIXTURES / "mixed.md")


def _docling() -> SourceArtifact:
    return SourceArtifact.from_path(_FIXTURES / "mixed.docling.json")


def _doclang() -> SourceArtifact:
    return SourceArtifact.from_path(_FIXTURES / "mixed.dclg")


def _archive() -> SourceArtifact:
    return SourceArtifact.from_bytes(
        _archive_fixture(),
        source_form=SourceForm.DOCLANG_ARCHIVE,
        source_name="matrix.dclx",
        media_type="application/vnd.doclang.archive+zip",
    )


@pytest.mark.parametrize(
    "source_builder",
    (_text, _edus, _markdown, _docling, _doclang, _archive),
    ids=("text", "edus", "markdown", "docling", "doclang", "doclang-archive"),
)
def test_every_source_form_analyses_and_round_trips_canonically(
    source_builder: Callable[[], SourceArtifact],
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(source_builder())
    assert isinstance(outcome, AnalysedOutcome)
    assert outcome.semantic.validation is not None and outcome.semantic.validation.passed
    encoded = serialize_contract(outcome)
    assert serialize_contract(load_contract(encoded)) == encoded
