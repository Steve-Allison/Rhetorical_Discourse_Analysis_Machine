"""Complete, reproducible multi-unit recombination evidence."""

import pytest
from pydantic import ValidationError

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact

from .conftest import ParserBuilder


def test_recombination_receipt_accounts_for_every_local_result_and_mapping(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder(maximum=2)).analyse(
        SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    receipt = parser_result.semantic.recombination
    assert receipt is not None

    assert len(receipt.unit_identities) == 2
    assert len(receipt.local_result_identities) == 2
    assert len(receipt.unit_durations_ms) == 2
    assert len(receipt.segment_mappings) == 2
    assert {mapping.global_id for mapping in receipt.node_mappings} == {
        str(node.node_id)
        for node in parser_result.analysis.nodes
        if node.node_id not in {
            decision.node_ids[0]
            for decision in parser_result.semantic.primary_inference.structure_decisions
            if decision.decision_id.startswith("recombine:")
        }
    }
    local_edge_ids = {mapping.global_id for mapping in receipt.edge_mappings}
    assert local_edge_ids < {edge.edge_id for edge in parser_result.analysis.primary_edges}
    assert receipt.boundary_inputs
    assert len(receipt.nuclear_spine_inputs) == 2
    assert receipt.stitching_decisions
    assert receipt.warnings == ()
    assert receipt.semantic_digest is not None


def test_stitching_decisions_record_every_adjacent_unit_seam(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder(maximum=2)).analyse(
        SourceArtifact.from_edus(
            ("One.", "Two.", "Three.", "Four.", "Five."), source_name="five.edus"
        )
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    receipt = parser_result.semantic.recombination
    assert receipt is not None
    assert len(receipt.unit_identities) == 3
    assert len(receipt.stitching_decisions) == 2
    seams = tuple(
        (decision.predecessor_unit_id, decision.successor_unit_id)
        for decision in receipt.stitching_decisions
    )
    assert seams == (("unit:0000", "unit:0001"), ("unit:0001", "unit:0002"))


def test_recombination_receipt_digest_rejects_semantic_mutation_but_not_timing(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder(maximum=2)).analyse(
        SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None and parser_result.semantic.recombination is not None
    receipt = parser_result.semantic.recombination

    timing_only = receipt.__class__.model_validate(
        {
            **receipt.model_dump(),
            "unit_durations_ms": tuple(value + 1.0 for value in receipt.unit_durations_ms),
        }
    )
    assert timing_only.semantic_digest == receipt.semantic_digest

    with pytest.raises(ValidationError, match="semantic digest mismatch"):
        receipt.__class__.model_validate(
            {
                **receipt.model_dump(),
                "policy": "mutated-policy",
            }
        )
