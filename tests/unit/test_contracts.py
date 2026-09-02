"""Unit tests for Python 3.14 contracts and serialization."""

import pytest

from rdam.rst.contracts import (
    AnnotationStatusEnum,
    DiscourseSignal,
    DocumentToken,
    Edu,
    FailureCodeEnum,
    FormatRstAnalysis,
    InputFidelityEnum,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
    PrimaryRelationEdge,
    ProvenanceRecord,
    RstAnalysis,
    RstDocument,
    RstNode,
    SecondaryRelationEdge,
    SignalDetectionMethod,
    SignalDetectorProvenance,
    SourceReference,
    TextSpan,
    TimingRecord,
    analysis_from_json,
    document_from_json,
    format_analysis_from_json,
    to_dict,
    to_json,
)


def test_document_from_text() -> None:
    text = "First sentence. Second sentence."
    doc = RstDocument.from_text(text, document_id="doc-1")
    assert doc.document_id == "doc-1"
    assert doc.text == text
    assert doc.fidelity == InputFidelityEnum.LOSSLESS
    assert doc.edus is None


def test_document_from_edus() -> None:
    edus = ["First sentence.", "Second sentence."]
    src = SourceReference(uri="https://example.com/doc", mime_type="text/plain")
    prov = ProvenanceRecord(producer="test_suite")
    doc = RstDocument.from_edus(edus, document_id="doc-2", source=src, provenance=prov)
    assert doc.document_id == "doc-2"
    assert doc.text == "First sentence. Second sentence."
    assert doc.fidelity == InputFidelityEnum.RECONSTRUCTED
    assert doc.source == src
    assert doc.provenance.producer == "test_suite"
    assert doc.edus is not None
    assert len(doc.edus) == 2
    assert doc.edus[0].text == "First sentence."
    assert doc.edus[0].start == 0
    assert doc.edus[0].end == 15
    assert doc.edus[1].text == "Second sentence."
    assert doc.edus[1].start == 16
    assert doc.edus[1].end == 32

    # Verify dict and json roundtrip for document
    raw_dict = to_dict(doc)
    assert raw_dict["document_id"] == "doc-2"
    json_str = to_json(doc)
    restored = document_from_json(json_str)
    assert restored.document_id == doc.document_id
    assert restored.text == doc.text
    assert restored.fidelity == doc.fidelity


def test_document_from_edus_validation() -> None:
    with pytest.raises(ValueError, match="edus sequence must not be empty"):
        RstDocument.from_edus([])

    with pytest.raises(ValueError, match="must be a non-empty string"):
        RstDocument.from_edus(["valid EDU", "   "])

    with pytest.raises(ValueError, match="must be a non-empty string"):
        RstDocument.from_edus([""])


def test_document_from_tokens_and_edus() -> None:
    text = "Hello world."
    tokens = (
        DocumentToken(token_id=0, text="Hello", start=0, end=5, sentence_id=0),
        DocumentToken(token_id=1, text="world", start=6, end=11, sentence_id=0),
        DocumentToken(token_id=2, text=".", start=11, end=12, sentence_id=0),
    )
    edus = (Edu(edu_id=1, text="Hello world.", start=0, end=12, token_ids=(0, 1, 2)),)
    doc = RstDocument.from_tokens_and_edus(
        text=text,
        tokens=tokens,
        edus=edus,
        sentence_boundaries=[TextSpan(start=0, end=12, text="Hello world.")],
        document_id="doc-3",
        fidelity=InputFidelityEnum.LOSSLESS,
    )
    assert doc.tokens == tokens
    assert doc.edus == edus
    assert doc.fidelity == InputFidelityEnum.LOSSLESS


def test_invalid_span_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid character span"):
        DocumentToken(token_id=0, text="bad", start=10, end=5)

    with pytest.raises(ValueError, match="Invalid character span"):
        Edu(edu_id=1, text="bad", start=-1, end=5)

    with pytest.raises(ValueError, match="Invalid EDU span"):
        RstNode(
            node_id=1,
            kind=NodeKindEnum.EDU,
            edu_span=(5, 2),
            char_span=(0, 10),
            text="bad",
        )


def test_analysis_and_serialization_roundtrip() -> None:
    nodes = (
        RstNode(
            node_id=1,
            kind=NodeKindEnum.EDU,
            edu_span=(1, 1),
            char_span=(0, 5),
            text="Hello",
            confidence=0.95,
        ),
        RstNode(
            node_id=2,
            kind=NodeKindEnum.EDU,
            edu_span=(2, 2),
            char_span=(6, 12),
            text="world.",
            confidence=0.92,
        ),
        RstNode(
            node_id=3,
            kind=NodeKindEnum.ROOT,
            edu_span=(1, 2),
            char_span=(0, 12),
            text="Hello world.",
            confidence=0.98,
        ),
    )
    primary_edges = (
        PrimaryRelationEdge(
            edge_id="e1",
            parent_id=3,
            child_id=2,
            relation_raw="Elaboration",
            relation_concept="Elaboration",
            nuclearity=NuclearityPatternEnum.NS,
            confidence=0.88,
            calibrated=True,
        ),
    )
    secondary_edges = (
        SecondaryRelationEdge(
            edge_id="sec1",
            source_id=1,
            target_id=2,
            relation_raw="Antithesis",
            relation_concept="Contrast",
            confidence=0.75,
            calibrated=False,
        ),
    )
    signals = (
        DiscourseSignal(
            signal_id="sig1",
            edge_id="e1",
            signal_type="dm",
            signal_subtype="dm",
            token_ids=(0, 2),
            char_spans=((0, 5), (6, 12)),
            compatible_relations=("Elaboration",),
            detector=SignalDetectorProvenance(
                detector_id="contract-test",
                detector_version="1.0.0",
                method=SignalDetectionMethod.GOLD,
            ),
            status=AnnotationStatusEnum.GOLD,
            confidence=1.0,
        ),
    )

    analysis = RstAnalysis(
        document_id="doc-3",
        formalism=OutputFormalismEnum.ERST_GRAPH,
        nodes=nodes,
        primary_edges=primary_edges,
        secondary_edges=secondary_edges,
        signals=signals,
        timing=TimingRecord(segmentation_ms=1.2, parsing_ms=15.4, completion_ms=4.1, total_ms=20.7),
        warnings=("sample warning",),
        failure_code=FailureCodeEnum.ALIGNMENT_FAILED,
    )

    assert analysis.root_node is not None
    assert analysis.root_node.node_id == 3
    assert analysis.get_node(2) == nodes[1]
    assert analysis.failure_code == FailureCodeEnum.ALIGNMENT_FAILED

    # JSON serialization round-trip
    json_str = to_json(analysis)
    restored = analysis_from_json(json_str)

    assert restored.document_id == analysis.document_id
    assert restored.formalism == analysis.formalism
    assert restored.failure_code == FailureCodeEnum.ALIGNMENT_FAILED
    assert len(restored.nodes) == len(analysis.nodes)
    assert len(restored.primary_edges) == len(analysis.primary_edges)
    assert len(restored.secondary_edges) == len(analysis.secondary_edges)
    assert len(restored.signals) == len(analysis.signals)
    assert restored.signals[0].token_ids == (0, 2)
    assert restored.timing.total_ms == 20.7


def test_format_analysis_roundtrip() -> None:
    doc_analysis = RstAnalysis(
        document_id="doc-fmt",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(),
        primary_edges=(),
    )
    table_analysis = RstAnalysis(
        document_id="tbl-1",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(),
        primary_edges=(),
    )
    fmt_analysis = FormatRstAnalysis(
        document_analysis=doc_analysis,
        table_analyses={"#/tables/0": table_analysis},
        node_map={"#/texts/0": 1, "#/tables/0": 2},
    )

    json_str = to_json(fmt_analysis)
    restored = format_analysis_from_json(json_str)

    assert restored.document_analysis.document_id == "doc-fmt"
    assert "#/tables/0" in restored.table_analyses
    assert restored.node_map["#/texts/0"] == 1


def test_malformed_json_deserialization_raises() -> None:
    # Non-dict JSON root
    with pytest.raises(ValueError, match="Expected JSON object"):
        document_from_json("[1, 2, 3]")

    with pytest.raises(ValueError, match="Expected JSON object"):
        analysis_from_json('"string"')

    with pytest.raises(ValueError, match="Expected JSON object"):
        format_analysis_from_json("123")
