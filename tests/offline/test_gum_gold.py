"""GUM gold RST fixtures — real documents with human trees to compare against.

The files live in ``tests/fixtures/gum/``. They are official GUM V12.1.0
**test**-split documents whose underlying text is CC BY / CC BY-SA (not
wikiHow, fiction, essays, letters, podcasts, or reddit).
"""

from pathlib import Path

import pytest
from lxml import etree

from isanlp_rst.contracts import NodeKindEnum, OutputFormalismEnum, RstAnalysis
from isanlp_rst.parser import Parser
from .gum_validator import (
    GOLD_FIXTURE_NAMES,
    GUM_FIXTURES_DIR,
    GumGoldValidator,
    GumValidationReport,
)

GOLD_DOCUMENTS: dict[str, int] = {
    "GUM_academic_art": 74,
    "GUM_academic_census": 110,
    "GUM_bio_byron": 91,
    "GUM_bio_dvorak": 71,
    "GUM_bio_emperor": 85,
    "GUM_interview_gaming": 85,
    "GUM_news_nasa": 124,
    "GUM_news_sensitive": 76,
    "GUM_textbook_chemistry": 127,
    "GUM_voyage_oakland": 85,
}

_SECURE_PARSER = etree.XMLParser(
    resolve_entities=False,
    no_network=True,
    dtd_validation=False,
    load_dtd=False,
    huge_tree=False,
)


def _gold_path(doc_id: str) -> Path:
    return GUM_FIXTURES_DIR / f"{doc_id}.rs4"


def gold_edus(path: Path) -> tuple[str, ...]:
    """EDU texts in document order from a GUM ``.rs4`` gold tree."""
    root = etree.parse(path, parser=_SECURE_PARSER).getroot()
    return tuple("".join(seg.itertext()).strip() for seg in root.findall(".//segment"))


@pytest.fixture(scope="module")
def validator() -> GumGoldValidator:
    return GumGoldValidator()


@pytest.fixture(scope="module")
def modernbert_cpu() -> Parser:
    return Parser(family="modernbert", device="cpu")


@pytest.mark.parametrize("doc_id,edu_count", GOLD_DOCUMENTS.items())
def test_gum_gold_fixture_has_expected_edus(doc_id: str, edu_count: int) -> None:
    path = _gold_path(doc_id)
    assert path.is_file(), f"missing GUM gold fixture: {path}"
    edus = gold_edus(path)
    assert len(edus) == edu_count
    assert all(edu for edu in edus)


@pytest.mark.parametrize("doc_id", GOLD_FIXTURE_NAMES)
def test_validator_gold_against_gold_is_perfect_f1(validator: GumGoldValidator, doc_id: str) -> None:
    """Validating gold against itself must produce perfect 1.0 F1 across all metrics."""
    _, gold_analysis, _ = validator.load_gold_fixture(doc_id)
    report = validator.validate_analysis(doc_id, gold_analysis)

    assert report.passed_structural_checks
    assert report.gold_edu_count == report.pred_edu_count
    assert report.standard_parseval.span_f1 == 1.0
    assert report.standard_parseval.nuclearity_f1 == 1.0
    assert report.standard_parseval.relation_f1 == 1.0
    assert report.coarse_parseval.relation_f1 == 1.0
    assert report.standard_parseval.full_f1 == 1.0
    assert report.rst_parseval.span_f1 == 1.0
    assert report.rst_parseval.relation_f1 == 1.0

    if report.secondary_metrics and report.secondary_metrics.gold_count > 0:
        assert report.secondary_metrics.full_f1 == 1.0

    if report.signal_metrics and report.signal_metrics.gold_signals_count > 0:
        assert report.signal_metrics.token_f1 == 1.0

    md = report.summary_markdown()
    assert "Standard Span" in md
    assert "VALID" in md


@pytest.mark.parametrize("doc_id", GOLD_FIXTURE_NAMES)
def test_gum_gold_fixture_structural_soundness(validator: GumGoldValidator, doc_id: str) -> None:
    """Verify structural validity and root reachability of vendored GUM gold fixtures."""
    doc, analysis, rs4 = validator.load_gold_fixture(doc_id)

    assert doc.document_id == doc_id
    assert len(doc.text) > 100
    assert doc.edus is not None and len(doc.edus) == GOLD_DOCUMENTS[doc_id]

    # Verify single root node
    edu_nodes = [n for n in analysis.nodes if n.kind == NodeKindEnum.EDU]
    assert len(edu_nodes) == GOLD_DOCUMENTS[doc_id]

    root = analysis.root_node
    assert root is not None
    assert root.edu_span == (1, len(edu_nodes))

    # Verify primary edges connect children
    child_ids = {e.child_id for e in analysis.primary_edges}
    non_root_nodes = {n.node_id for n in analysis.nodes if n.node_id != root.node_id}
    assert child_ids == non_root_nodes


def test_validator_detects_structural_corruption(validator: GumGoldValidator) -> None:
    """Verify validator flags empty and disconnected predictions."""
    empty_analysis = RstAnalysis(
        document_id="GUM_bio_dvorak",
        formalism=OutputFormalismEnum.RST_TREE,
        nodes=(),
        primary_edges=(),
    )
    report = validator.validate_analysis("GUM_bio_dvorak", empty_analysis)
    assert not report.passed_structural_checks
    assert not report.is_valid_tree
    assert any("no nodes" in err for err in report.structural_errors)


@pytest.mark.slow
@pytest.mark.parametrize("doc_id", GOLD_FIXTURE_NAMES)
def test_modernbert_gold_standard_validation(
    validator: GumGoldValidator,
    modernbert_cpu: Parser,
    doc_id: str,
) -> None:
    """Validate neural parser predictions against GUM gold standards."""
    report: GumValidationReport = validator.validate_document_with_parser(
        gold_doc_id=doc_id,
        parser=modernbert_cpu,
        from_edus=True,
    )

    assert report.passed_structural_checks, f"Structural validation failed: {report.structural_errors}"
    assert report.pred_edu_count > 10
    assert report.is_valid_tree

    md = report.summary_markdown()
    assert doc_id in md
    assert "Standard Span" in md


@pytest.mark.slow
def test_gum_corpus_macro_benchmark(
    validator: GumGoldValidator,
    modernbert_cpu: Parser,
) -> None:
    """Validate the macro-averaged performance of the parser across the full GUM gold corpus."""
    corpus_report = validator.validate_corpus_with_parser(
        parser=modernbert_cpu,
        doc_ids=GOLD_FIXTURE_NAMES,
        from_edus=True,
    )

    assert corpus_report.document_count == len(GOLD_FIXTURE_NAMES)
    assert corpus_report.document_count == 10

    summary_table = corpus_report.summary_table()
    assert "GUM Gold Benchmark Summary" in summary_table
    assert "Macro Average" in summary_table
