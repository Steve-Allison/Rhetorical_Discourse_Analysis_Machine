"""Unit tests for RS4 XML I/O and converter."""

from pathlib import Path

import pytest

from rdam.rst.contracts import OutputFormalismEnum
from rdam.rst.erst import (
    RS4Document,
    RS4Group,
    RS4Reader,
    RS4SecEdge,
    RS4Segment,
    RS4Signal,
    RS4Writer,
    analysis_to_rs4,
    rs4_to_document_and_analysis,
)
from scripts.extract_rs4_headers import extract_headers_from_path

GUM_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "gum"


@pytest.mark.parametrize(
    "filename,expected_segments",
    [
        ("GUM_bio_dvorak.rs4", 71),
        ("GUM_news_sensitive.rs4", 76),
        ("GUM_voyage_oakland.rs4", 85),
    ],
)
def test_read_gum_rs4_fixtures(filename: str, expected_segments: int) -> None:
    path = GUM_FIXTURES / filename
    assert path.is_file()
    doc = RS4Reader.read_file(path)

    assert len(doc.segments) == expected_segments
    assert len(doc.relations) == 32
    assert "adversative-antithesis" in doc.relations
    assert len(doc.sigtypes) == 10
    assert "dm" in doc.sigtypes

    # Round trip string serialization
    xml_out = RS4Writer.to_string(doc)
    doc_reparsed = RS4Reader.read_string(xml_out)

    assert len(doc_reparsed.segments) == len(doc.segments)
    assert len(doc_reparsed.groups) == len(doc.groups)
    assert len(doc_reparsed.secedges) == len(doc.secedges)
    assert len(doc_reparsed.signals) == len(doc.signals)
    assert doc_reparsed.relations == doc.relations
    assert doc_reparsed.sigtypes == doc.sigtypes


def test_rs4_converter_roundtrip() -> None:
    path = GUM_FIXTURES / "GUM_bio_dvorak.rs4"
    rs4_doc = RS4Reader.read_file(path)

    rst_doc, analysis = rs4_to_document_and_analysis(rs4_doc, document_id="GUM_bio_dvorak")

    assert rst_doc.document_id == "GUM_bio_dvorak"
    assert rst_doc.edus is not None
    assert len(rst_doc.edus) == len(rs4_doc.segments)
    assert analysis.formalism == OutputFormalismEnum.ERST_GRAPH
    assert len(analysis.secondary_edges) == len(rs4_doc.secedges)
    assert len(analysis.signals) == len(rs4_doc.signals)

    # Check signal token coordinate conversion (RS4 1-based -> internal 0-based)
    assert len(rs4_doc.signals) > 1 and len(rs4_doc.signals[1].tokens) > 0
    orig_first_tok = rs4_doc.signals[1].tokens[0]
    conv_first_tok = analysis.signals[1].token_ids[0]
    assert conv_first_tok == orig_first_tok - 1

    # Convert back to RS4
    rs4_converted = analysis_to_rs4(
        rst_doc,
        analysis,
        relations_header=rs4_doc.relations,
        sigtypes_header=rs4_doc.sigtypes,
    )

    assert len(rs4_converted.segments) == len(rs4_doc.segments)
    assert len(rs4_converted.groups) == len(rs4_doc.groups)
    assert len(rs4_converted.secedges) == len(rs4_doc.secedges)
    assert len(rs4_converted.signals) == len(rs4_doc.signals)

    # Check tokens converted back to 1-based
    assert len(rs4_converted.signals) > 1 and len(rs4_converted.signals[1].tokens) > 0
    assert rs4_converted.signals[1].tokens[0] == orig_first_tok
    assert rs4_converted.signals[1].source == rs4_doc.signals[1].source



def test_extract_rs4_headers() -> None:
    headers = extract_headers_from_path(GUM_FIXTURES)
    assert "relations" in headers
    assert "rst" in headers["relations"]
    assert "multinuc" in headers["relations"]
    assert "signal_types" in headers
    assert "dm" in headers["signal_types"]
    assert "graphical" in headers["signal_types"]


def test_synthetic_rs4_creation() -> None:
    doc = RS4Document(
        relations={"elaboration-additional": "rst", "joint-list": "multinuc"},
        sigtypes={"dm": ("dm",), "lexical": ("indicative_word",)},
        segments=(
            RS4Segment(id=1, text="Unit 1", parent=3, relname="span"),
            RS4Segment(id=2, text="Unit 2", parent=1, relname="elaboration-additional"),
        ),
        groups=(RS4Group(id=3, type="span", parent=None, relname="span"),),
        secedges=(RS4SecEdge(id="1-2", source=1, target=2, relname="joint-list"),),
        signals=(RS4Signal(source="2", type="dm", subtype="dm", tokens=(1,), status="gold"),),
    )

    xml_str = RS4Writer.to_string(doc)
    reloaded = RS4Reader.read_string(xml_str)
    assert len(reloaded.segments) == 2
    assert len(reloaded.groups) == 1
    assert len(reloaded.secedges) == 1
    assert len(reloaded.signals) == 1


def test_converter_normalizes_overlapping_token_ranges_within_one_signal() -> None:
    rs4 = RS4Document(
        segments=(RS4Segment(id=1, text="One two", parent=None, relname="span"),),
        signals=(
            RS4Signal(
                source="1",
                type="syntactic",
                subtype="indicative_phrase",
                tokens=(1, 1, 2, 2),
                status="gold",
            ),
        ),
    )
    _, analysis = rs4_to_document_and_analysis(rs4, document_id="overlapping-token-ranges")
    assert analysis.signals[0].token_ids == (0, 1)
    assert analysis.signals[0].char_spans == ((0, 3), (4, 7))


def test_rs4_reader_malformed_xml_raises() -> None:
    with pytest.raises(ValueError, match="Expected root element <rst>"):
        RS4Reader.read_string("<notrst><header/></notrst>")

    with pytest.raises(ValueError, match="Missing <header>"):
        RS4Reader.read_string("<rst><body/></rst>")

    with pytest.raises(ValueError, match="Missing <body>"):
        RS4Reader.read_string("<rst><header/></rst>")
