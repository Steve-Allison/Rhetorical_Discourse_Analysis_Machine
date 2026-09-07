"""Canonical native validation must not require bulk descendant expansion."""

from typing import NoReturn

import pytest

from rdam._strict import canonical_json_bytes
from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.validation import build_analysis_validation_receipt
from rdam.rst.output import RstOutput

from .conftest import ParserBuilder


def test_native_loading_validates_without_materializing_graph_anchors(
    parser_builder: ParserBuilder, monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(SourceArtifact.from_text("First. Second.", source_name="native-validation"))
    payload = result.model_dump_json()

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("native loading expanded graph anchors")

    monkeypatch.setattr("rdam.ingest.parser_result.analysis_anchors", forbidden)
    loaded = RstOutput.model_validate_json(payload)
    assert loaded.root.semantic.analysed_document == result.semantic.analysed_document
    assert loaded.root.model_dump_json() == payload


def test_native_loading_rejects_resealed_self_loop(parser_builder: ParserBuilder) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(SourceArtifact.from_text("First. Second.", source_name="native-validation"))
    data = result.model_dump()
    parser = data["semantic"]["parser_result"]
    edge = parser["semantic"]["analysis"]["primary_edges"][0]
    edge["child_id"] = edge["parent_id"]
    parser["semantic_digest"] = None
    data["semantic_digest"] = None
    with pytest.raises(ValueError, match="primary edge is a self-loop"):
        RstOutput.model_validate_json(canonical_json_bytes(data))


def test_canonical_and_expanded_anchor_validation_receipts_agree(parser_builder: ParserBuilder) -> None:
    result = ProductionIngestor(parser=parser_builder()).analyse(SourceArtifact.from_text("First. Second.", source_name="native-validation"))
    parser = result.semantic.parser_result
    assert parser is not None
    evidence = parser.semantic
    expanded = build_analysis_validation_receipt(
        evidence.analysis, evidence.analysed_document, evidence.primary_inference, evidence.erst_completion,
        evidence.anchors, policy=evidence.policy, composite=evidence.composite_identity,
        recombination=evidence.recombination,
    )
    canonical = build_analysis_validation_receipt(
        evidence.analysis, evidence.analysed_document, evidence.primary_inference, evidence.erst_completion,
        None, policy=evidence.policy, composite=evidence.composite_identity, recombination=evidence.recombination,
    )
    assert canonical == expanded == evidence.validation
