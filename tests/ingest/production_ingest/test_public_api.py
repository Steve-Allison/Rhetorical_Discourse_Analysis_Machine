"""The canonical ingest package is the only production source-ingest surface."""

from importlib.util import find_spec

import isanlp_rst.doclang as doclang_helpers
import isanlp_rst.ingest as ingest
import isanlp_rst.markdown as markdown_helpers


def _module_exists(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def test_canonical_ingest_exports_complete_public_service() -> None:
    assert ingest.ProductionIngestor is not None
    assert ingest.SourceArtifact is not None
    assert ingest.ProductionAnalysisOutcome is not None
    assert ingest.describe_capabilities is not None
    assert ingest.serialize_contract is not None
    assert ingest.load_contract is not None


def test_obsolete_public_entry_points_are_absent() -> None:
    assert not hasattr(markdown_helpers, "parse_markdown")
    assert not hasattr(doclang_helpers, "parse_doclang")
    assert find_spec("isanlp_rst.docling") is None


def test_obsolete_envelopes_and_entry_modules_are_absent() -> None:
    obsolete_modules = (
        "isanlp_rst.markdown._entry",
        "isanlp_rst.markdown.schema",
        "isanlp_rst.doclang._entry",
        "isanlp_rst.doclang.schema",
        "isanlp_rst.docling._entry",
        "isanlp_rst.ingest.compatibility",
    )
    assert not any(_module_exists(module_name) for module_name in obsolete_modules)
