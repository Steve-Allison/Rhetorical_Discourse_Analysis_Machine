"""Unit tests for NetworkX, RDF, Turtle, JSON-LD, and GraphRAG discourse export bridges."""

from dataclasses import replace
import json
import networkx as nx
import pytest
from rdflib import Graph

from rdam.rst.contracts import (
    AnnotationStatusEnum,
    DiscourseSignal,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    RstAnalysis,
    RstDocument,
    RstNode,
    SecondaryRelationEdge,
    SignalDetectionMethod,
    SignalDetectorProvenance,
)
from rdam.rst.graph import (
    to_graphrag_json,
    to_jsonld,
    to_networkx_graph,
    to_rdf_triples,
    to_turtle,
)


@pytest.fixture
def sample_analysis() -> tuple[RstDocument, RstAnalysis]:
    doc = RstDocument(
        document_id="doc_kg_01",
        text="The team launched the spacecraft. Because weather conditions were ideal.",
        language="en",
    )
    node1 = RstNode(
        node_id=1,
        kind=NodeKindEnum.EDU,
        edu_span=(1, 1),
        char_span=(0, 33),
        text="The team launched the spacecraft.",
        confidence=0.98,
    )
    node2 = RstNode(
        node_id=2,
        kind=NodeKindEnum.EDU,
        edu_span=(2, 2),
        char_span=(34, 71),
        text="Because weather conditions were ideal.",
        confidence=0.96,
    )
    root = RstNode(
        node_id=3,
        kind=NodeKindEnum.ROOT,
        edu_span=(1, 2),
        char_span=(0, 71),
        text=doc.text,
        confidence=0.95,
    )
    p_edge = PrimaryRelationEdge(
        edge_id="e1",
        parent_id=3,
        child_id=2,
        relation_raw="cause",
        relation_concept="Cause",
        nuclearity=NuclearityPatternEnum.SN,
        confidence=0.91,
        calibrated=True,
    )
    s_edge = SecondaryRelationEdge(
        edge_id="e2_sec",
        source_id=2,
        target_id=1,
        relation_raw="explanation",
        relation_concept="Explanation",
        confidence=0.85,
        calibrated=True,
    )
    signal = DiscourseSignal(
        signal_id="sig_001",
        edge_id="e1",
        signal_type="connective",
        signal_subtype="lexical",
        char_spans=((34, 41),),
        compatible_relations=("cause",),
        detector=SignalDetectorProvenance(
            detector_id="marker_detector",
            detector_version="1.0.0",
            method=SignalDetectionMethod.RULE,
        ),
        sufficient=True,
        status=AnnotationStatusEnum.PREDICTED,
        confidence=0.95,
    )
    analysis = RstAnalysis(
        document_id="doc_kg_01",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(node1, node2, root),
        primary_edges=(p_edge,),
        secondary_edges=(s_edge,),
        signals=(signal,),
    )
    return doc, analysis


def test_to_networkx_graph(sample_analysis: tuple[RstDocument, RstAnalysis]):
    doc, analysis = sample_analysis
    g = to_networkx_graph(analysis, doc)

    assert isinstance(g, nx.MultiDiGraph)
    assert g.graph["document_id"] == "doc_kg_01"
    assert g.graph["formalism"] == "erst_graph"
    assert g.graph["language"] == "en"

    assert len(g.nodes) == 3
    assert g.nodes[1]["kind"] == "edu"
    assert g.nodes[1]["confidence"] == 0.98

    assert len(g.edges) == 2
    edge_p = g.edges[3, 2, "e1"]
    assert edge_p["edge_kind"] == "primary"
    assert edge_p["relation_concept"] == "Cause"
    assert edge_p["calibrated"] is True
    assert len(edge_p["signals"]) == 1

    edge_s = g.edges[2, 1, "e2_sec"]
    assert edge_s["edge_kind"] == "secondary"
    assert edge_s["relation_concept"] == "Explanation"


def test_to_rdf_triples_and_turtle(sample_analysis: tuple[RstDocument, RstAnalysis]):
    doc, analysis = sample_analysis
    triples = to_rdf_triples(analysis, doc)

    assert len(triples) > 10
    predicates = {p for _, p, _ in triples}
    assert "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" in predicates
    assert "http://example.org/central/ontology/relationConcept" in predicates

    turtle_text = to_turtle(analysis, doc)
    assert "@prefix coe:" in turtle_text
    assert "doc:node_1 a coe:ElementaryDiscourseUnit" in turtle_text
    assert "coe:relationConcept rel:Cause" in turtle_text
    parsed = Graph().parse(data=turtle_text, format="turtle")
    assert len(parsed) > 0


def test_to_jsonld(sample_analysis: tuple[RstDocument, RstAnalysis]):
    doc, analysis = sample_analysis
    jsonld = to_jsonld(analysis, doc)

    assert "@context" in jsonld
    assert "@graph" in jsonld
    graph_items = jsonld["@graph"]
    assert len(graph_items) == 6  # 1 doc + 3 nodes + 2 edges


def test_turtle_escapes_literals_and_non_prefixed_local_names(
    sample_analysis: tuple[RstDocument, RstAnalysis],
) -> None:
    doc, analysis = sample_analysis
    first_node = replace(analysis.nodes[0], text='A "quoted" line\ncontinues.')
    first_edge = replace(
        analysis.primary_edges[0],
        edge_id="edge with spaces",
        relation_concept="Cause Effect",
        relation_raw='cause "quoted"',
    )
    changed = replace(
        analysis,
        document_id="document with spaces",
        nodes=(first_node, *analysis.nodes[1:]),
        primary_edges=(first_edge,),
    )

    parsed = Graph().parse(data=to_turtle(changed, doc), format="turtle")

    assert len(parsed) > 0


def test_to_graphrag_json(sample_analysis: tuple[RstDocument, RstAnalysis]):
    doc, analysis = sample_analysis
    graphrag = to_graphrag_json(analysis, doc)

    assert graphrag["document_id"] == "doc_kg_01"
    assert len(graphrag["chunks"]) == 3
    assert len(graphrag["discourse_relations"]) == 2

    # Verify JSON serializability
    dumped = json.dumps(graphrag)
    assert "doc_kg_01__node_1" in dumped
    assert "Cause" in dumped
