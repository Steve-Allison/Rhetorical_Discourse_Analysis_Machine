"""Exact analysed token, EDU, sentence, paragraph, and source mapping."""

from pathlib import Path
from typing import Literal

import pytest

from rdam.rst.contracts import NodeKindEnum, RstDocument
from rdam.rst.parser import Parser
from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.contracts.analysis import AnalysedDocument

from .conftest import ParserBuilder


def test_analysed_substrate_is_exact_and_lossless(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="substrate.txt")
    )
    document = outcome.semantic.analysed_document
    assert document is not None
    assert document.fidelity.value == "lossless"
    assert document.character_coverage.covered_units == len(document.text)
    assert document.character_coverage.total_units == len(document.text)
    assert {mapping.token_id for mapping in document.mappings} == {
        token.token_id for token in document.tokens
    }
    for token in document.tokens:
        assert document.text[token.character_range.start:token.character_range.end] == token.text
        assert token.source_anchors
    for edu in document.edus:
        assert edu.token_ids
        assert edu.prepared_segment_ids
        assert edu.source_anchors
    assert "mappings" not in document.model_dump()
    restored = AnalysedDocument.model_validate_json(document.model_dump_json())
    assert restored.mappings == document.mappings
    token_owners = {token_id: edu.edu_id for edu in restored.edus for token_id in edu.token_ids}
    assert all(mapping.edu_id == token_owners[mapping.token_id] for mapping in restored.mappings)


@pytest.mark.slow
@pytest.mark.parametrize("release_id", ("gumrrg-eb1d5745f3a1", "unirst-9407970f1d9d"))
@pytest.mark.parametrize("edu_count", (129, 513))
def test_real_parser_preserves_edus_across_obsolete_capacity_boundaries(release_id: str, edu_count: int) -> None:
    parser = Parser.from_model_release(
        Path.home() / ".cache/isanlp_rst/model-releases", release_id, device="cpu",
    )
    document = RstDocument.from_edus(["Word."] * edu_count, document_id=f"uncapped-{edu_count}")
    result = parser.analyse_document(document)
    substrate = result.analysed_document
    assert len(substrate.edus) == edu_count
    assert substrate.text == document.text
    assert len([node for node in result.analysis.nodes if node.kind == NodeKindEnum.EDU]) == edu_count
    assert len(result.semantic.primary_inference.structure_decisions) == edu_count - 1
    assert substrate.edus[0].text == substrate.edus[-1].text == "Word."
    assert substrate.tokens[-1].character_range.end == len(document.text)


@pytest.mark.parametrize("mutation", ("missing_membership", "shared_token", "unknown_token", "duplicate_token"))
def test_canonical_membership_rejects_missing_or_ambiguous_owners(
    parser_builder: ParserBuilder,
    mutation: Literal["missing_membership", "shared_token", "unknown_token", "duplicate_token"],
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="membership.txt")
    )
    document = outcome.semantic.analysed_document
    assert document is not None
    payload = document.model_dump(exclude={"semantic_digest"})
    match mutation:
        case "missing_membership":
            payload["edus"][0]["token_ids"] = document.edus[0].token_ids[1:]
        case "shared_token":
            payload["edus"][0]["token_ids"] += (document.edus[1].token_ids[0],)
        case "unknown_token":
            payload["edus"][0]["token_ids"] += ("token:invented",)
        case "duplicate_token":
            payload["tokens"][1]["token_id"] = document.tokens[0].token_id
    with pytest.raises(ValueError, match="overlaps|cover every|unique"):
        AnalysedDocument.model_validate(payload)
