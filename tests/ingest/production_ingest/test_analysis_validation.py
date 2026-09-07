"""Primary-tree and formal eRST validation invariants."""

from dataclasses import replace

import pytest

from rdam.ingest import ProductionIngestor, SourceArtifact
from rdam.ingest.parser_result import validate_parser_analysis_result
from rdam.rst.contracts import NuclearityPatternEnum, PrimaryRelationEdge, RelationStructureEnum

from .conftest import ParserBuilder


def test_primary_tree_is_connected_acyclic_and_single_rooted(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First claim. Second claim.", source_name="tree.txt")
    )
    parser_result = outcome.semantic.parser_result
    assert parser_result is not None
    validate_parser_analysis_result(parser_result)
    assert len(parser_result.analysis.nodes) == 3
    assert len(parser_result.analysis.primary_edges) == 2

    first_edge = parser_result.analysis.primary_edges[0]
    invalid = replace(
        parser_result.analysis,
        primary_edges=(replace(first_edge, child_id=first_edge.parent_id),),
    )
    invalid_semantic = parser_result.semantic.model_copy(update={"analysis": invalid})
    with pytest.raises(ValueError, match="primary edge is a self-loop"):
        validate_parser_analysis_result(parser_result.model_copy(update={"semantic": invalid_semantic}))


@pytest.mark.parametrize("mutation", ("sibling_nuclearity", "split", "relation", "duplicate_decision"))
def test_primary_semantic_contradictions_fail_before_digest_checks(
    parser_builder: ParserBuilder,
    mutation: str,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(SourceArtifact.from_text("First. Second.", source_name="semantic-mutation"))
    result = outcome.semantic.parser_result
    assert result is not None
    semantic = result.semantic
    if mutation == "sibling_nuclearity":
        first, second = semantic.analysis.primary_edges
        bad_edge = replace(first, nuclearity=NuclearityPatternEnum.NS, relation_structure=None)
        semantic = semantic.model_copy(
            update={"analysis": replace(semantic.analysis, primary_edges=(bad_edge, second))}
        )
        message = "contradictory nuclearity"
    else:
        (decision,) = semantic.primary_inference.structure_decisions
        if mutation == "split":
            changed = (decision.model_copy(update={"selected_split": 1}),)
            message = "split differs"
        elif mutation == "relation":
            changed = (
                decision.model_copy(
                    update={"relation": decision.relation.model_copy(
                        update={"raw_label": "cause"}
                    )}
                ),
            )
            message = "labels contradict"
        else:
            changed = (decision, decision)
            message = "duplicate target identities"
        semantic = semantic.model_copy(
            update={"primary_inference": semantic.primary_inference.model_copy(update={"structure_decisions": changed})}
        )
    with pytest.raises(ValueError, match=message):
        validate_parser_analysis_result(result.model_copy(update={"semantic": semantic}))


def test_structural_span_and_same_unit_have_distinct_semantics() -> None:
    span = PrimaryRelationEdge("span", 3, 1, "span", "span", NuclearityPatternEnum.NS)
    same_unit = PrimaryRelationEdge("same", 3, 2, "same-unit", "same-unit", NuclearityPatternEnum.NN)
    assert span.relation_structure is RelationStructureEnum.STRUCTURAL_PSEUDO
    assert same_unit.relation_structure is RelationStructureEnum.MULTINUCLEAR
    with pytest.raises(ValueError, match="not independently scored"):
        replace(span, confidence=0.9)
    with pytest.raises(ValueError, match="contradicts"):
        replace(span, relation_structure=RelationStructureEnum.MONONUCLEAR)
