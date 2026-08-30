"""Decision-complete primary inference evidence."""

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact

from .conftest import ParserBuilder


def test_selected_structure_relation_nuclearity_and_scores_link_to_graph(
    parser_builder: ParserBuilder,
) -> None:
    outcome = ProductionIngestor(parser=parser_builder()).analyse(
        SourceArtifact.from_text("First. Second.", source_name="primary.txt")
    )
    analysis = outcome.semantic.analysis
    evidence = outcome.semantic.primary_inference
    assert analysis is not None and evidence is not None
    decision = evidence.structure_decisions[0]
    assert decision.selected_split == 0
    assert decision.nuclearity == "NN"
    assert decision.relation.raw_label == "same-unit"
    assert decision.confidence.confidence_kind.value == "probability"
    assert decision.split_entropy is not None
    assert set(decision.node_ids) <= {node.node_id for node in analysis.nodes}
    assert set(decision.primary_edge_ids) == {
        edge.edge_id for edge in analysis.primary_edges
    }
