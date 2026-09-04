"""Model-free, network-free, adapter-import-free capability discovery."""

import sys

from rdam.ingest import describe_capabilities


def test_capability_discovery_imports_no_optional_adapter_or_model() -> None:
    before = set(sys.modules)
    capabilities = describe_capabilities()
    imported = set(sys.modules) - before
    forbidden_prefixes = ("docling_core", "doclang", "markdown_it", "transformers", "torch")
    assert not any(name.startswith(forbidden_prefixes) for name in imported)
    assert capabilities.semantic.model_free_discovery
    assert capabilities.semantic.output_formalisms == ()
    assert capabilities.semantic.evidence_detail_levels == ()
    assert not capabilities.semantic.canonical_parser_result_supported
