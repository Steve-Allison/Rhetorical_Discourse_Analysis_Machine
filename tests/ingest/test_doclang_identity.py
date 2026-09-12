"""Shared DocLang implementation dependencies bind public preparation identity."""

from pathlib import Path
from types import ModuleType

import pytest

from rdam.ingest import ProductionIngestor
from rdam.ingest import _classification, _doclang
from rdam.ingest.doclang import decoder, document, loader, text_walker
from tests.ingest.test_doclang_decoder import artifact


@pytest.mark.parametrize("module", (_doclang, _classification, decoder, document, loader, text_walker))
def test_each_implementation_file_changes_public_identity(
    module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert module.__file__ is not None
    original = Path(module.__file__)
    changed = tmp_path / original.name
    changed.write_bytes(original.read_bytes() + b"\n# changed implementation revision\n")
    source = artifact("<text>Stable source</text>")
    before = ProductionIngestor().prepare(source)
    monkeypatch.setattr(module, "__file__", str(changed))
    after = ProductionIngestor().prepare(source)
    assert before.semantic.source_contract.schema_identity != after.semantic.source_contract.schema_identity
    assert before.semantic_digest != after.semantic_digest
    assert before.semantic.prepared_document == after.semantic.prepared_document
    assert before.semantic.source == after.semantic.source


def test_same_document_is_deterministic_without_sharing_a_tree() -> None:
    source = artifact("<text>Stable source</text>")
    first = ProductionIngestor().prepare(source)
    second = ProductionIngestor().prepare(source)
    assert first.semantic == second.semantic
    assert first.execution.execution_id != second.execution.execution_id


def test_changed_decoder_cannot_hit_an_existing_analysis_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from rdam.ingest import CacheStatus
    from tests.ingest.production_ingest.conftest import build_deterministic_parser

    ingestor = ProductionIngestor(parser=build_deterministic_parser())
    source = artifact("<text>First. Second.</text>")
    cache = tmp_path / "cache"
    first = ingestor.analyse(source, cache_directory=cache)
    hit = ingestor.analyse(source, cache_directory=cache)
    assert first.execution.cache_status is CacheStatus.WRITTEN
    assert hit.execution.cache_status is CacheStatus.HIT
    replacement = tmp_path / "decoder.py"
    replacement.write_bytes(Path(decoder.__file__).read_bytes() + b"\n# new decoder revision\n")
    monkeypatch.setattr(decoder, "__file__", str(replacement))
    changed = ingestor.analyse(source, cache_directory=cache)
    assert changed.execution.cache_status is CacheStatus.WRITTEN
    assert changed.semantic.request.semantic_digest != first.semantic.request.semantic_digest
