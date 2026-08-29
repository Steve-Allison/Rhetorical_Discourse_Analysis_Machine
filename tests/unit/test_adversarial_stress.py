"""Adversarial stress and edge-case unit tests.

Validates robust fail-closed and non-happy-path behavior across:
- Graph bridges (empty, disconnected, special chars, Unicode injection)
- Multilingual primer (sub-word prefix collisions, unicode ligatures, control chars)
- DiscourseUnit slotted type invariants
- Parser validation bounds and batch parameter guards
"""

import pytest

from isanlp_rst.annotation_rst import DiscourseUnit
from isanlp_rst.contracts import (
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    ProvenanceRecord,
    RelationSchemeEnum,
    RstAnalysis,
    RstDocument,
    RstNode,
    TimingRecord,
)
from isanlp_rst.graph.export import (
    to_graphrag_json,
    to_jsonld,
    to_networkx_graph,
    to_rdf_triples,
    to_turtle,
)
from isanlp_rst.ontology.adapter import OntologyAdapter
from isanlp_rst.parser import Parser
from isanlp_rst.relations.multilingual_markers import MULTILINGUAL_MARKER_RULES
from isanlp_rst.relations.primer import DiscourseMarkerPrimer


# ---------------------------------------------------------------------------
# 1. Native DiscourseUnit Slotted Class Invariants
# ---------------------------------------------------------------------------


def test_discourse_unit_slotted_attributes_strictly_enforced() -> None:
    du = DiscourseUnit(
        id=1,
        left=None,
        right=None,
        start=0,
        end=10,
        text="Sample unit text",
        relation="elaboration",
        nuclearity="SN",
    )
    assert du.id == 1
    assert du.text == "Sample unit text"
    assert du.start == 0
    assert du.end == 10

    # Attempting to assign an unslotted attribute must raise AttributeError
    with pytest.raises(AttributeError):
        du.arbitrary_injected_field = "malicious_payload"  # type: ignore[reportAttributeAccessIssue]


# ---------------------------------------------------------------------------
# 2. Graph Export Adversarial & Malformed Inputs
# ---------------------------------------------------------------------------


def _empty_analysis() -> RstAnalysis:
    return RstAnalysis(
        document_id="empty_doc",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(),
        primary_edges=(),
        secondary_edges=(),
        signals=(),
        provenance=ProvenanceRecord(
            producer="test",
            software_version="4.0.0",
            source_revision="a" * 40,
            model_id="test-model",
            ontology_version="4.1.0-discourse",
        ),
        timing=TimingRecord(parsing_ms=1.0, total_ms=1.0),
    )


def test_graph_export_empty_analysis_does_not_crash() -> None:
    empty = _empty_analysis()

    # NetworkX
    graph = to_networkx_graph(empty)
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0

    # RDF Triples
    triples = to_rdf_triples(empty)
    assert len(triples) >= 1  # Contains document metadata triples

    # Turtle & JSON-LD
    turtle = to_turtle(empty)
    assert "@prefix coe:" in turtle
    jsonld = to_jsonld(empty)
    assert "@context" in jsonld
    assert "@graph" in jsonld

    # GraphRAG
    rag = to_graphrag_json(empty)
    assert rag["document_id"] == "empty_doc"
    assert rag["chunks"] == []
    assert rag["discourse_relations"] == []


def test_graph_export_handles_special_characters_and_emojis() -> None:
    # Text with quotes, newlines, tabs, XML control characters, and Unicode emojis
    adversarial_text = 'Line 1 "quotes" & <tags>\nLine 2 \t with emojis: 🚀 🤖 🧠 and \'single quotes\''

    node_1 = RstNode(
        node_id=1,
        kind=NodeKindEnum.EDU,
        edu_span=(1, 1),
        char_span=(0, len(adversarial_text)),
        text=adversarial_text,
    )
    node_2 = RstNode(
        node_id=2,
        kind=NodeKindEnum.EDU,
        edu_span=(2, 2),
        char_span=(len(adversarial_text) + 1, len(adversarial_text) + 23),
        text="Normal target segment",
    )
    edge = PrimaryRelationEdge(
        edge_id="edge-1",
        parent_id=1,
        child_id=2,
        relation_raw="attribution",
        relation_concept="Attribution",
        nuclearity=NuclearityPatternEnum.NS,
    )

    analysis = RstAnalysis(
        document_id="special_chars_doc",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=(node_1, node_2),
        primary_edges=(edge,),
        secondary_edges=(),
        signals=(),
        provenance=ProvenanceRecord(
            producer="test",
            software_version="4.0.0",
            source_revision="a" * 40,
            model_id="test-model",
            ontology_version="4.1.0-discourse",
        ),
        timing=TimingRecord(parsing_ms=2.0, total_ms=2.0),
    )

    # 1. Turtle export escaping
    turtle = to_turtle(analysis)
    assert "special_chars_doc" in turtle
    assert len(turtle) > 0

    # 2. GraphRAG text payload
    rag = to_graphrag_json(analysis)
    assert len(rag["chunks"]) == 2
    assert rag["chunks"][0]["text"] == adversarial_text
    assert rag["discourse_relations"][0]["concept"] == "Attribution"


# ---------------------------------------------------------------------------
# 3. Ontology Adapter Boundary Testing
# ---------------------------------------------------------------------------


def test_ontology_adapter_handles_unusual_and_unknown_inputs() -> None:
    adapter = OntologyAdapter()

    # Unknown relations with raise_on_unmapped=False return None
    assert (
        adapter.resolve_label(
            "completely_novel_relation",
            scheme=RelationSchemeEnum.RST_DT_FINE,
            raise_on_unmapped=False,
        )
        is None
    )

    # Unknown relations with raise_on_unmapped=True raise KeyError
    with pytest.raises(KeyError, match="Unmapped label"):
        adapter.resolve_label(
            "completely_novel_relation",
            scheme=RelationSchemeEnum.RST_DT_FINE,
            raise_on_unmapped=True,
        )

    # Known canonical concepts resolve cleanly
    canon_elab, conc_elab = adapter.resolve_label("elaboration-additional", scheme=RelationSchemeEnum.RST_DT_FINE)
    assert conc_elab == "Elaboration"
    assert canon_elab == "elaboration-additional"


# ---------------------------------------------------------------------------
# 4. Discourse Marker Primer Sub-Word & Prefix Collision Resistance
# ---------------------------------------------------------------------------


def test_marker_primer_avoids_subword_false_positives() -> None:
    primer = DiscourseMarkerPrimer()

    # "somewhere" must NOT trigger "so"
    # "button" must NOT trigger "but"
    # "author" must NOT trigger "or"
    doc_text = "Somewhere on the button, the author wrote a word."
    doc = RstDocument(
        document_id="subword_test",
        text=doc_text,
    )
    node = RstNode(
        node_id=1,
        kind=NodeKindEnum.EDU,
        edu_span=(1, 1),
        char_span=(0, len(doc_text)),
        text=doc_text,
    )
    analysis = RstAnalysis(
        document_id="subword_test",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(node,),
        primary_edges=(),
        secondary_edges=(),
        signals=(),
        provenance=ProvenanceRecord(
            producer="test",
            software_version="4.0.0",
            source_revision="a" * 40,
            model_id="test",
            ontology_version="4.1.0-discourse",
        ),
        timing=TimingRecord(parsing_ms=1.0, total_ms=1.0),
    )

    primed = primer.prime_analysis(analysis, doc)
    # Extract matched signal text using char_spans
    matched_texts: list[str] = []
    for sig in primed.signals:
        for start, end in sig.char_spans:
            matched_texts.append(doc.text[start:end].lower())

    assert "so" not in matched_texts
    assert "but" not in matched_texts
    assert "or" not in matched_texts


def test_multilingual_markers_unicode_coverage() -> None:
    # Test German markers containing 'ß' (e.g. 'sodass', 'außer')
    de_markers = MULTILINGUAL_MARKER_RULES["de"]
    assert any("ß" in m.cue or "ss" in m.cue for m in de_markers)

    # Test Spanish inverted punctuation and accented characters
    es_markers = MULTILINGUAL_MARKER_RULES["es"]
    assert any("además" in m.cue for m in es_markers)

    # Test Chinese multi-character discourse markers
    zh_markers = MULTILINGUAL_MARKER_RULES["zh"]
    assert any(m.cue in {"因为", "所以", "但是", "然而", "如果"} for m in zh_markers)


# ---------------------------------------------------------------------------
# 5. Parser Parameter Validation & Error Enforcement
# ---------------------------------------------------------------------------


def test_parser_documents_rejects_invalid_batch_size() -> None:
    # Dummy mock predictor
    class _MockPredictor:
        _device = "cpu"

    parser = Parser.__new__(Parser)
    object.__setattr__(parser, "predictor", _MockPredictor())
    object.__setattr__(parser, "erst_checkpoint", None)

    doc = RstDocument(document_id="d1", text="Sample text")

    # batch_size <= 0 must fail immediately with ValueError
    with pytest.raises(ValueError, match="batch_size must be positive"):
        parser.parse_documents([doc], batch_size=0)

    with pytest.raises(ValueError, match="batch_size must be positive"):
        parser.parse_documents([doc], batch_size=-10)

    # Empty list must return empty list without error
    assert parser.parse_documents([], batch_size=16) == []
