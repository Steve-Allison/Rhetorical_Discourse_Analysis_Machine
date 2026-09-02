"""Knowledge graph export bridges for Rhetorical Structure Theory analyses."""

from typing import Any
import networkx as nx

from rdam.rst.contracts.analysis import RstAnalysis
from rdam.rst.contracts.document import RstDocument
from rdam.rst.contracts.enums import NodeKindEnum


def to_networkx_graph(
    analysis: RstAnalysis,
    document: RstDocument | None = None,
) -> nx.DiGraph:
    """Convert an RstAnalysis tree/graph into a typed NetworkX DiGraph.

    Args:
        analysis: The parsed discourse analysis result.
        document: Optional original RstDocument for additional metadata.

    Returns:
        nx.DiGraph: Directed graph with node and edge attributes.
    """
    g = nx.DiGraph()
    g.graph["document_id"] = analysis.document_id
    g.graph["formalism"] = analysis.formalism.value
    if document is not None and document.language is not None:
        g.graph["language"] = document.language

    # Index signals by edge_id
    signals_by_edge: dict[str, list[dict[str, Any]]] = {}
    for sig in analysis.signals:
        if sig.edge_id:
            signals_by_edge.setdefault(sig.edge_id, []).append(
                {
                    "signal_id": sig.signal_id,
                    "signal_type": sig.signal_type,
                    "signal_subtype": sig.signal_subtype,
                    "char_spans": list(sig.char_spans),
                    "confidence": sig.confidence,
                }
            )

    # Add discourse unit nodes
    for node in analysis.nodes:
        g.add_node(
            node.node_id,
            text=node.text,
            char_span=node.char_span,
            edu_span=node.edu_span,
            kind=node.kind.value,
            confidence=node.confidence,
        )

    # Add primary directed relations
    for edge in analysis.primary_edges:
        g.add_edge(
            edge.parent_id,
            edge.child_id,
            edge_id=edge.edge_id,
            relation_concept=edge.relation_concept,
            relation_raw=edge.relation_raw,
            nuclearity=edge.nuclearity.value,
            edge_kind="primary",
            confidence=edge.confidence,
            calibrated=edge.calibrated,
            signals=signals_by_edge.get(edge.edge_id, []),
        )

    # Add secondary directed relations
    for edge in analysis.secondary_edges:
        g.add_edge(
            edge.source_id,
            edge.target_id,
            edge_id=edge.edge_id,
            relation_concept=edge.relation_concept,
            relation_raw=edge.relation_raw,
            nuclearity=None,
            edge_kind="secondary",
            confidence=edge.confidence,
            calibrated=edge.calibrated,
            signals=signals_by_edge.get(edge.edge_id, []),
        )

    return g


def to_rdf_triples(
    analysis: RstAnalysis,
    document: RstDocument | None = None,
    base_uri: str = "http://example.org/discourse/",
) -> list[tuple[str, str, str]]:
    """Serialize discourse units and relations into formal W3C RDF triples.

    Args:
        analysis: The parsed discourse analysis result.
        document: Optional original RstDocument for metadata.
        base_uri: Base URI prefix for RDF entities.

    Returns:
        list[tuple[str, str, str]]: List of (subject, predicate, object) string triples.
    """
    doc_uri = f"{base_uri}{analysis.document_id}"
    triples: list[tuple[str, str, str]] = []

    triples.append((doc_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/central/ontology/DiscourseDocument"))
    triples.append((doc_uri, "http://example.org/central/ontology/formalism", analysis.formalism.value))

    for node in analysis.nodes:
        node_uri = f"{doc_uri}#node_{node.node_id}"
        kind_class = "ElementaryDiscourseUnit" if node.kind == NodeKindEnum.EDU else "ComplexDiscourseUnit"
        triples.append((node_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", f"http://example.org/central/ontology/{kind_class}"))
        triples.append((node_uri, "http://example.org/central/ontology/partOfDocument", doc_uri))
        triples.append((node_uri, "http://example.org/central/ontology/text", f'"{node.text}"'))
        triples.append((node_uri, "http://example.org/central/ontology/charStart", str(node.char_span[0])))
        triples.append((node_uri, "http://example.org/central/ontology/charEnd", str(node.char_span[1])))
        triples.append((node_uri, "http://example.org/central/ontology/eduStart", str(node.edu_span[0])))
        triples.append((node_uri, "http://example.org/central/ontology/eduEnd", str(node.edu_span[1])))

    for edge in analysis.primary_edges:
        edge_uri = f"{doc_uri}#edge_{edge.edge_id}"
        parent_uri = f"{doc_uri}#node_{edge.parent_id}"
        child_uri = f"{doc_uri}#node_{edge.child_id}"
        triples.append((edge_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/central/ontology/PrimaryDiscourseRelation"))
        triples.append((edge_uri, "http://example.org/central/ontology/hasParent", parent_uri))
        triples.append((edge_uri, "http://example.org/central/ontology/hasChild", child_uri))
        triples.append((edge_uri, "http://example.org/central/ontology/relationConcept", f"http://example.org/central/ontology/DiscourseRelation#{edge.relation_concept}"))
        triples.append((edge_uri, "http://example.org/central/ontology/relationRaw", f'"{edge.relation_raw}"'))
        triples.append((edge_uri, "http://example.org/central/ontology/nuclearity", f"http://example.org/central/ontology/Nuclearity#{edge.nuclearity.name}"))
        if edge.confidence is not None:
            triples.append((edge_uri, "http://example.org/central/ontology/confidence", str(edge.confidence)))
        triples.append((edge_uri, "http://example.org/central/ontology/calibrated", str(edge.calibrated).lower()))

    for edge in analysis.secondary_edges:
        edge_uri = f"{doc_uri}#edge_{edge.edge_id}"
        source_uri = f"{doc_uri}#node_{edge.source_id}"
        target_uri = f"{doc_uri}#node_{edge.target_id}"
        triples.append((edge_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/central/ontology/SecondaryDiscourseRelation"))
        triples.append((edge_uri, "http://example.org/central/ontology/hasSource", source_uri))
        triples.append((edge_uri, "http://example.org/central/ontology/hasTarget", target_uri))
        triples.append((edge_uri, "http://example.org/central/ontology/relationConcept", f"http://example.org/central/ontology/DiscourseRelation#{edge.relation_concept}"))
        triples.append((edge_uri, "http://example.org/central/ontology/relationRaw", f'"{edge.relation_raw}"'))
        if edge.confidence is not None:
            triples.append((edge_uri, "http://example.org/central/ontology/confidence", str(edge.confidence)))
        triples.append((edge_uri, "http://example.org/central/ontology/calibrated", str(edge.calibrated).lower()))

    return triples


def to_turtle(
    analysis: RstAnalysis,
    document: RstDocument | None = None,
    base_uri: str = "http://example.org/discourse/",
) -> str:
    """Serialize discourse analysis to W3C Turtle RDF format."""
    doc_id = analysis.document_id
    lines = [
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix coe: <http://example.org/central/ontology/> .",
        f"@prefix doc: <{base_uri}{doc_id}#> .",
        "",
        f"<{base_uri}{doc_id}> a coe:DiscourseDocument ;",
        f'    coe:formalism "{analysis.formalism.value}" .',
        "",
    ]

    for node in analysis.nodes:
        kind_class = "ElementaryDiscourseUnit" if node.kind == NodeKindEnum.EDU else "ComplexDiscourseUnit"
        escaped_text = node.text.replace('"', '\\"').replace("\n", " ")
        lines.extend(
            [
                f"doc:node_{node.node_id} a coe:{kind_class} ;",
                f'    coe:text "{escaped_text}" ;',
                f"    coe:charStart {node.char_span[0]} ;",
                f"    coe:charEnd {node.char_span[1]} ;",
                f"    coe:eduStart {node.edu_span[0]} ;",
                f"    coe:eduEnd {node.edu_span[1]} .",
                "",
            ]
        )

    for edge in analysis.primary_edges:
        conf_line = f"    coe:confidence {edge.confidence} ;" if edge.confidence is not None else ""
        lines.extend(
            [
                f"doc:edge_{edge.edge_id} a coe:PrimaryDiscourseRelation ;",
                f"    coe:hasParent doc:node_{edge.parent_id} ;",
                f"    coe:hasChild doc:node_{edge.child_id} ;",
                f"    coe:relationConcept coe:{edge.relation_concept} ;",
                f'    coe:relationRaw "{edge.relation_raw}" ;',
                f"    coe:nuclearity coe:{edge.nuclearity.name} ;",
                f"{conf_line}" if conf_line else "",
                f"    coe:calibrated {str(edge.calibrated).lower()} .",
                "",
            ]
        )
        lines = [line for line in lines if line]

    for edge in analysis.secondary_edges:
        conf_line = f"    coe:confidence {edge.confidence} ;" if edge.confidence is not None else ""
        lines.extend(
            [
                f"doc:edge_{edge.edge_id} a coe:SecondaryDiscourseRelation ;",
                f"    coe:hasSource doc:node_{edge.source_id} ;",
                f"    coe:hasTarget doc:node_{edge.target_id} ;",
                f"    coe:relationConcept coe:{edge.relation_concept} ;",
                f'    coe:relationRaw "{edge.relation_raw}" ;',
                f"{conf_line}" if conf_line else "",
                f"    coe:calibrated {str(edge.calibrated).lower()} .",
                "",
            ]
        )
        lines = [line for line in lines if line]

    return "\n".join(lines)


def to_jsonld(
    analysis: RstAnalysis,
    document: RstDocument | None = None,
    base_uri: str = "http://example.org/discourse/",
) -> dict[str, Any]:
    """Serialize discourse analysis to W3C JSON-LD graph structure."""
    doc_id = analysis.document_id
    doc_uri = f"{base_uri}{doc_id}"

    context = {
        "@vocab": "http://example.org/central/ontology/",
        "coe": "http://example.org/central/ontology/",
        "doc": f"{doc_uri}#",
        "node_id": "@id",
        "kind": "@type",
        "hasParent": {"@type": "@id"},
        "hasChild": {"@type": "@id"},
        "hasSource": {"@type": "@id"},
        "hasTarget": {"@type": "@id"},
    }

    graph: list[dict[str, Any]] = [
        {
            "@id": doc_uri,
            "@type": "coe:DiscourseDocument",
            "formalism": analysis.formalism.value,
        }
    ]

    for node in analysis.nodes:
        kind_class = "coe:ElementaryDiscourseUnit" if node.kind == NodeKindEnum.EDU else "coe:ComplexDiscourseUnit"
        graph.append(
            {
                "@id": f"doc:node_{node.node_id}",
                "@type": kind_class,
                "text": node.text,
                "charStart": node.char_span[0],
                "charEnd": node.char_span[1],
                "eduStart": node.edu_span[0],
                "eduEnd": node.edu_span[1],
                "confidence": node.confidence,
            }
        )

    for edge in analysis.primary_edges:
        graph.append(
            {
                "@id": f"doc:edge_{edge.edge_id}",
                "@type": "coe:PrimaryDiscourseRelation",
                "hasParent": f"doc:node_{edge.parent_id}",
                "hasChild": f"doc:node_{edge.child_id}",
                "relationConcept": f"coe:{edge.relation_concept}",
                "relationRaw": edge.relation_raw,
                "nuclearity": f"coe:{edge.nuclearity.name}",
                "confidence": edge.confidence,
                "calibrated": edge.calibrated,
            }
        )

    for edge in analysis.secondary_edges:
        graph.append(
            {
                "@id": f"doc:edge_{edge.edge_id}",
                "@type": "coe:SecondaryDiscourseRelation",
                "hasSource": f"doc:node_{edge.source_id}",
                "hasTarget": f"doc:node_{edge.target_id}",
                "relationConcept": f"coe:{edge.relation_concept}",
                "relationRaw": edge.relation_raw,
                "confidence": edge.confidence,
                "calibrated": edge.calibrated,
            }
        )

    return {
        "@context": context,
        "@graph": graph,
    }


def to_graphrag_json(
    analysis: RstAnalysis,
    document: RstDocument | None = None,
) -> dict[str, Any]:
    """Convert discourse structure into hierarchical semantic chunks for GraphRAG indexing.

    Args:
        analysis: The parsed discourse analysis result.
        document: Optional original RstDocument for full text.

    Returns:
        dict[str, Any]: Semantic chunk hierarchy with relational transitions.
    """
    chunks: list[dict[str, Any]] = []

    # Map children and parents
    parent_map: dict[int, int] = {}
    child_map: dict[int, list[int]] = {}
    for edge in analysis.primary_edges:
        parent_map[edge.child_id] = edge.parent_id
        child_map.setdefault(edge.parent_id, []).append(edge.child_id)

    for node in analysis.nodes:
        chunks.append(
            {
                "chunk_id": f"{analysis.document_id}__node_{node.node_id}",
                "node_id": node.node_id,
                "chunk_type": node.kind.value,
                "text": node.text,
                "char_span": list(node.char_span),
                "edu_span": list(node.edu_span),
                "parent_node_id": parent_map.get(node.node_id),
                "child_node_ids": child_map.get(node.node_id, []),
                "confidence": node.confidence,
            }
        )

    relations: list[dict[str, Any]] = []
    for edge in analysis.primary_edges:
        relations.append(
            {
                "relation_id": edge.edge_id,
                "relation_type": "primary",
                "source_chunk": f"{analysis.document_id}__node_{edge.parent_id}",
                "target_chunk": f"{analysis.document_id}__node_{edge.child_id}",
                "concept": edge.relation_concept,
                "raw_label": edge.relation_raw,
                "nuclearity": edge.nuclearity.value,
                "confidence": edge.confidence,
                "calibrated": edge.calibrated,
            }
        )

    for edge in analysis.secondary_edges:
        relations.append(
            {
                "relation_id": edge.edge_id,
                "relation_type": "secondary",
                "source_chunk": f"{analysis.document_id}__node_{edge.source_id}",
                "target_chunk": f"{analysis.document_id}__node_{edge.target_id}",
                "concept": edge.relation_concept,
                "raw_label": edge.relation_raw,
                "nuclearity": None,
                "confidence": edge.confidence,
                "calibrated": edge.calibrated,
            }
        )

    return {
        "document_id": analysis.document_id,
        "formalism": analysis.formalism.value,
        "text": document.text if document is not None else None,
        "chunks": chunks,
        "discourse_relations": relations,
    }


__all__ = [
    "to_graphrag_json",
    "to_jsonld",
    "to_networkx_graph",
    "to_rdf_triples",
    "to_turtle",
]
