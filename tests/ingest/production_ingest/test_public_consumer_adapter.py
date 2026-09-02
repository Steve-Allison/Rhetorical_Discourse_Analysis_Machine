"""Representative downstream consumption through public imports only."""

from rdam.rst.ingest import (
    AnalysedOutcome,
    ProductionIngestor,
    SourceArtifact,
    serialize_contract,
)

from .conftest import ParserBuilder


def test_consumer_explains_result_without_private_imports(
    parser_builder: ParserBuilder,
) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("A claim. Supporting evidence.", source_name="consumer.txt")
    )
    assert isinstance(result, AnalysedOutcome)
    semantic = result.semantic
    assert semantic.analysis is not None
    assert semantic.primary_inference is not None
    assert semantic.analysed_document is not None
    explanation = {
        "source": semantic.preparation.semantic.source.source_name,
        "nodes": len(semantic.analysis.nodes),
        "edges": len(semantic.analysis.primary_edges),
        "decisions": len(semantic.primary_inference.structure_decisions),
        "tokens": len(semantic.analysed_document.tokens),
        "validated": semantic.validation.passed if semantic.validation else False,
        "bytes": len(serialize_contract(result)),
    }
    assert explanation == {
        "source": "consumer.txt",
        "nodes": 3,
        "edges": 2,
        "decisions": 1,
        "tokens": 4,
        "validated": True,
        "bytes": explanation["bytes"],
    }
