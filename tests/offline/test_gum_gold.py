"""GUM gold RST fixtures — real documents with human trees to compare against.

The files live in ``tests/fixtures/gum/``. They are official GUM V12.1.0
**test**-split documents whose underlying text is CC BY / CC BY-SA (not
wikiHow, fiction, essays, letters, podcasts, or reddit).
"""

from dataclasses import replace
from pathlib import Path
from typing import Literal

import pytest
from lxml import etree
from pydantic import BaseModel, ConfigDict, Field

from rdam.rst.contracts import NodeKindEnum, OutputFormalismEnum, RstAnalysis
from rdam.rst.model_authority import DEFAULT_ENCODER_MODEL_ID, DEFAULT_ENCODER_REVISION
from rdam.rst.parser import Parser
from .gum_validator import (
    GOLD_FIXTURE_NAMES,
    GUM_FIXTURES_DIR,
    GumCorpusValidationReport,
    GumGoldValidator,
    GumValidationReport,
)


class _QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    span_f1: float = Field(ge=0.0, le=1.0)
    nuclearity_f1: float = Field(ge=0.0, le=1.0)
    relation_fine_f1: float = Field(ge=0.0, le=1.0)
    relation_coarse_f1: float = Field(ge=0.0, le=1.0)
    full_f1: float = Field(ge=0.0, le=1.0)


class _QualityPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observed: _QualityMetrics
    floors: _QualityMetrics


class _QualityModelIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    parser: Literal["dmrst"]
    hf_model_name: str
    hf_model_version: str
    encoder_model_id: str
    encoder_revision: str
    device: Literal["cpu"]
    gold_edu_boundaries: Literal[True]


class _QualityBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["rdam.rst.gum-quality-baseline/v1"]
    measured_at: str
    model: _QualityModelIdentity
    floor_policy: str
    documents: dict[str, _QualityPoint]
    macro: _QualityPoint

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
QUALITY_BASELINE = _QualityBaseline.model_validate_json(
    (GUM_FIXTURES_DIR / "quality-baseline.json").read_text(encoding="utf-8")
)

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
def parser_cpu() -> Parser:
    return Parser(device="cpu")


@pytest.fixture(scope="module")
def parser_quality_report(
    validator: GumGoldValidator,
    parser_cpu: Parser,
) -> GumCorpusValidationReport:
    return validator.validate_corpus_with_parser(
        parser=parser_cpu,
        doc_ids=GOLD_FIXTURE_NAMES,
        from_edus=True,
    )


def _report_metrics(report: GumValidationReport) -> _QualityMetrics:
    return _QualityMetrics(
        span_f1=report.standard_parseval.span_f1,
        nuclearity_f1=report.standard_parseval.nuclearity_f1,
        relation_fine_f1=report.standard_parseval.relation_f1,
        relation_coarse_f1=report.coarse_parseval.relation_f1,
        full_f1=report.standard_parseval.full_f1,
    )


def _corpus_metrics(report: GumCorpusValidationReport) -> _QualityMetrics:
    return _QualityMetrics(
        span_f1=report.macro_span_f1,
        nuclearity_f1=report.macro_nuclearity_f1,
        relation_fine_f1=report.macro_relation_fine_f1,
        relation_coarse_f1=report.macro_relation_coarse_f1,
        full_f1=report.macro_full_f1,
    )


def _quality_regressions(actual: _QualityMetrics, floors: _QualityMetrics) -> tuple[str, ...]:
    return tuple(
        f"{metric}: {actual_value:.12f} < {floor_value:.12f}"
        for metric, actual_value in actual.model_dump().items()
        if actual_value < getattr(floors, metric)
        for floor_value in (getattr(floors, metric),)
    )


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


def test_quality_baseline_is_bound_to_the_current_default_parser_identity() -> None:
    assert QUALITY_BASELINE.documents.keys() == GOLD_DOCUMENTS.keys()
    assert QUALITY_BASELINE.model.hf_model_name == Parser._DEFAULT_HF_MODEL_NAME
    assert QUALITY_BASELINE.model.hf_model_version == Parser._DEFAULT_HF_MODEL_VERSION
    assert QUALITY_BASELINE.model.encoder_model_id == DEFAULT_ENCODER_MODEL_ID
    assert QUALITY_BASELINE.model.encoder_revision == DEFAULT_ENCODER_REVISION


def test_quality_gate_rejects_a_structurally_valid_wrong_tree(validator: GumGoldValidator) -> None:
    _, wrong_document_analysis, _ = validator.load_gold_fixture("GUM_bio_dvorak")
    report = validator.validate_analysis(
        "GUM_academic_art",
        replace(wrong_document_analysis, document_id="GUM_academic_art"),
    )
    regressions = _quality_regressions(
        _report_metrics(report),
        QUALITY_BASELINE.documents["GUM_academic_art"].floors,
    )
    assert report.passed_structural_checks
    assert regressions


@pytest.mark.slow
@pytest.mark.quality
@pytest.mark.parametrize("doc_id", GOLD_FIXTURE_NAMES)
def test_parser_gold_standard_validation(
    parser_quality_report: GumCorpusValidationReport,
    doc_id: str,
) -> None:
    """Enforce per-document neural quality floors against human gold trees."""
    report = next(report for report in parser_quality_report.document_reports if report.doc_id == doc_id)
    regressions = _quality_regressions(_report_metrics(report), QUALITY_BASELINE.documents[doc_id].floors)

    assert report.passed_structural_checks, f"Structural validation failed: {report.structural_errors}"
    assert report.pred_edu_count > 10
    assert report.is_valid_tree
    assert not regressions, "; ".join(regressions)

    md = report.summary_markdown()
    assert doc_id in md
    assert "Standard Span" in md


@pytest.mark.slow
@pytest.mark.quality
def test_gum_corpus_macro_benchmark(
    parser_quality_report: GumCorpusValidationReport,
) -> None:
    """Enforce macro quality floors across the complete ten-document gold corpus."""
    corpus_report = parser_quality_report
    regressions = _quality_regressions(_corpus_metrics(corpus_report), QUALITY_BASELINE.macro.floors)

    assert corpus_report.document_count == len(GOLD_FIXTURE_NAMES)
    assert corpus_report.document_count == 10
    assert not regressions, "; ".join(regressions)

    summary_table = corpus_report.summary_table()
    assert "GUM Gold Benchmark Summary" in summary_table
    assert "Macro Average" in summary_table
