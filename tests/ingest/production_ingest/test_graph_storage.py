"""Constituent text resolves from canonical source; distinct native text survives."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.analysis import ParserAnalysisResult, StoredAnalysedEdu, StoredAnalysedToken
from rdam.ingest.contracts.graph import StoredRstGraph
from rdam.ingest.contracts.source import ItemAnchor, TextSpanAnchor
from rdam.rst.parser import Parser

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def parser_result() -> ParserAnalysisResult:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", "gumrrg-eb1d5745f3a1", device="cpu",
    )
    outcome = ProductionIngestor(parser=parser).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="graph-storage.txt"),
    )
    result = outcome.semantic.parser_result
    assert result is not None
    return result


def test_parser_round_trip_stores_ranges_and_preserves_native_graph(parser_result: ParserAnalysisResult) -> None:
    result = parser_result
    encoded = result.model_dump_json()
    nodes = json.loads(encoded)["semantic"]["analysis"]["nodes"]
    assert nodes and all("text" not in node and node["text_override"] is None for node in nodes)
    restored = ParserAnalysisResult.model_validate_json(encoded)
    assert restored.analysis == result.analysis
    assert restored.semantic_digest == result.semantic_digest
    assert restored.semantic.anchors == result.semantic.anchors
    assert restored.analysed_document == result.analysed_document
    substrate = json.loads(encoded)["semantic"]["analysed_document"]
    for item in (*substrate["tokens"], *substrate["edus"]):
        assert "text" not in item and "order" not in item and "source_anchors" not in item
        assert item["text_override"] is None and item["source_anchors_override"] is None


def test_distinct_native_text_is_retained_and_not_relabelled_as_a_quote(parser_result: ParserAnalysisResult) -> None:
    result = parser_result
    graph = replace(result.analysis, nodes=(
        replace(result.analysis.nodes[0], text="Distinct native rendering"), *result.analysis.nodes[1:],
    ))
    stored = StoredRstGraph.capture(graph, result.analysed_document.text)
    assert stored.nodes[0].text_override == "Distinct native rendering"
    assert stored.resolve(result.analysed_document.text) == graph


def test_stored_graph_rejects_out_of_source_ranges_and_redundant_text(parser_result: ParserAnalysisResult) -> None:
    result = parser_result
    text = result.analysed_document.text
    stored = StoredRstGraph.capture(result.analysis, text)
    node = stored.nodes[0]
    outside = node.model_copy(update={"char_span": (0, len(text) + 1)})
    with pytest.raises(ValueError, match="outside"):
        outside.resolve(text)
    redundant = node.model_copy(update={"text_override": text[node.char_span[0]:node.char_span[1]]})
    with pytest.raises(ValueError, match="redundantly"):
        redundant.resolve(text)


def test_substrate_preserves_distinct_native_text_and_external_source_anchors(parser_result: ParserAnalysisResult) -> None:
    document = parser_result.analysed_document
    external = (
        ItemAnchor(artifact_identity="original-artifact", item_identity="paragraph:7"),
        TextSpanAnchor(artifact_identity="original-artifact", start=100, end=110, quote=None),
    )
    token = document.tokens[0].model_copy(update={"text": "native-token-rendering", "source_anchors": external})
    stored_token = StoredAnalysedToken.capture(token, document.text, document.source_anchors)
    assert stored_token.resolve(token.order, document.text, document.source_anchors) == token
    edu = document.edus[0].model_copy(update={"text": "native-edu-rendering", "source_anchors": external})
    stored_edu = StoredAnalysedEdu.capture(edu, document.text, document.source_anchors)
    assert stored_edu.character_range == edu.character_range
    assert stored_edu.resolve(edu.order, document.text, document.source_anchors) == edu


def test_stored_substrate_requires_resolvable_ranges_and_preserves_absent_quotes(parser_result: ParserAnalysisResult) -> None:
    document = parser_result.analysed_document
    token = document.tokens[0]
    stored_token = StoredAnalysedToken.capture(token, document.text, document.source_anchors)
    with pytest.raises(ValueError, match="requires explicit"):
        stored_token.resolve(token.order, document.text, ())
    with pytest.raises(ValueError, match="redundantly"):
        stored_token.model_copy(update={"text_override": token.text}).resolve(
            token.order, document.text, document.source_anchors,
        )
    source_anchor = token.source_anchors[0]
    assert isinstance(source_anchor, TextSpanAnchor)
    unquoted = token.model_copy(update={"source_anchors": (source_anchor.model_copy(update={"quote": None}),)})
    assert StoredAnalysedToken.capture(unquoted, document.text, document.source_anchors).resolve(
        token.order, document.text, document.source_anchors,
    ) == unquoted
    edu = document.edus[0]
    stored_edu = StoredAnalysedEdu.capture(edu, document.text, document.source_anchors)
    with pytest.raises(ValueError, match="requires explicit"):
        stored_edu.resolve(edu.order, document.text, ())
