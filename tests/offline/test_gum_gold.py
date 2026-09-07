"""GUM gold RST fixtures — real documents with human trees to compare against.

The files live in ``tests/fixtures/gum/``. Their pinned upstream identities
and official train/dev/test assignments are in ``upstream-manifest.json``.
This mixed fixture collection must not be described as a held-out test set.
"""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal, cast

import pytest
from lxml import etree
from pydantic import BaseModel, ConfigDict, Field

from rdam.configuration import DEFAULT_RST_MODEL_VERSION
from rdam.rst.contracts import NodeKindEnum, OutputFormalismEnum, RstAnalysis
from rdam.rst.model_authority import (
    PUBLISHED_RST_REVISIONS,
    XLM_ROBERTA_LARGE_MODEL_ID,
)
from rdam.rst.model_loading import load_model_release
from rdam.rst.parser import Parser
from workbench.evaluation.rst.regression import evaluation_source_identities, match_counts
from .gum_validator import (
    GOLD_FIXTURE_NAMES,
    GUM_FIXTURES_DIR,
    GumCorpusValidationReport,
    GumGoldValidator,
    GumValidationReport,
)


class _QualityMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    gold: int = Field(ge=0)
    predicted: int = Field(ge=0)
    span: int = Field(ge=0)
    nuclearity: int = Field(ge=0)
    relation: int = Field(ge=0)
    full: int = Field(ge=0)


class _QualityPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fixture_sha256: str
    split: Literal["train", "dev", "test"]
    observed: _QualityMetrics


class _QualityModelIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    parser: Literal["dmrst"]
    release_id: str
    manifest_sha256: str
    source_model_identity: str
    source_revision: str
    inventory_sha256: str
    device: Literal["cpu"]
    gold_edu_boundaries: Literal[True]


class _QualityBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["rdam.rst.gum-quality-baseline/v3"]
    measured_at: str
    model: _QualityModelIdentity
    purpose: Literal["exact_regression_reference_not_accuracy_acceptance"]
    evaluation: Literal["binary_attachment_parseval_gum_coarse_gold_edus"]
    evaluation_sources: dict[str, str]
    upstream_manifest_sha256: str
    model_training_overlap: Literal["not_verified"]
    documents: dict[str, _QualityPoint]
    micro: _QualityMetrics
    split_micro: dict[str, _QualityMetrics]

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
MODEL_STORE = Path.home() / ".cache/isanlp_rst/model-releases"
QUALITY_RELEASE_ID = "gumrrg-eb1d5745f3a1"

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
    release = load_model_release(MODEL_STORE, QUALITY_RELEASE_ID)
    member = release.one_file_for_role("relation-inventory")
    inventory = (release.path / member.path).read_text(encoding="utf-8").splitlines()
    return GumGoldValidator(relation_inventory=inventory)


@pytest.fixture(scope="module")
def parser_cpu() -> Parser:
    return Parser.from_model_release(MODEL_STORE, QUALITY_RELEASE_ID, device="cpu")


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
    return _QualityMetrics(**match_counts(report.coarse_parseval))


def _corpus_metrics(report: GumCorpusValidationReport) -> _QualityMetrics:
    totals: dict[str, int] = {}
    for document in report.document_reports:
        for metric, count in match_counts(document.coarse_parseval).items():
            totals[metric] = totals.get(metric, 0) + count
    return _QualityMetrics(**totals)


def _quality_regressions(actual: _QualityMetrics, expected: _QualityMetrics) -> tuple[str, ...]:
    return tuple(
        f"{metric}: observed {actual_value}, reference {getattr(expected, metric)}"
        for metric, actual_value in actual.model_dump().items()
        if actual_value != getattr(expected, metric)
    )


def test_reference_counts_and_split_aggregates_are_consistent() -> None:
    totals: dict[str, int] = {}
    splits: dict[str, dict[str, int]] = {}
    for reference in QUALITY_BASELINE.documents.values():
        counts = reference.observed
        assert counts.full <= min(counts.nuclearity, counts.relation)
        assert max(counts.nuclearity, counts.relation) <= counts.span <= min(counts.gold, counts.predicted)
        split = splits.setdefault(reference.split, {})
        for metric, count in counts.model_dump().items():
            totals[metric] = totals.get(metric, 0) + count
            split[metric] = split.get(metric, 0) + count
    assert totals == QUALITY_BASELINE.micro.model_dump()
    assert splits == {name: counts.model_dump() for name, counts in QUALITY_BASELINE.split_micro.items()}


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
    _, gold_analysis, gold_rs4 = validator.load_gold_fixture(doc_id)
    report = validator.validate_analysis(doc_id, gold_analysis, prediction_rs4=gold_rs4)

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
    doc, analysis, _rs4 = validator.load_gold_fixture(doc_id)

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
@pytest.mark.quality
def test_quality_baseline_is_bound_to_the_default_published_checkpoint() -> None:
    release = load_model_release(MODEL_STORE, QUALITY_RELEASE_ID)
    config_member = release.one_file_for_role("runtime-configuration")
    config = cast(
        dict[str, object],
        json.loads((release.path / config_member.path).read_text(encoding="utf-8")),
    )
    model_config = cast(dict[str, object], config["model"])
    transformer_config = cast(dict[str, object], model_config["transformer"])
    assert QUALITY_BASELINE.documents.keys() == GOLD_DOCUMENTS.keys()
    assert QUALITY_BASELINE.model.release_id == release.manifest.release_id
    assert QUALITY_BASELINE.model.manifest_sha256 == release.manifest.manifest_sha256
    assert QUALITY_BASELINE.model.source_model_identity == release.manifest.source_model_identity
    assert QUALITY_BASELINE.model.source_revision == release.manifest.source_revision
    assert QUALITY_BASELINE.model.source_revision == PUBLISHED_RST_REVISIONS[DEFAULT_RST_MODEL_VERSION]
    assert transformer_config["model_name"] == XLM_ROBERTA_LARGE_MODEL_ID
    inventory_member = release.one_file_for_role("relation-inventory")
    assert QUALITY_BASELINE.model.inventory_sha256 == inventory_member.sha256
    assert QUALITY_BASELINE.evaluation_sources == evaluation_source_identities()
    manifest_path = GUM_FIXTURES_DIR / "upstream-manifest.json"
    assert QUALITY_BASELINE.upstream_manifest_sha256 == sha256(manifest_path.read_bytes()).hexdigest()
    upstream = json.loads(manifest_path.read_bytes())
    for name, reference in QUALITY_BASELINE.documents.items():
        assert reference.fixture_sha256 == sha256(_gold_path(name).read_bytes()).hexdigest()
        assert reference.split == upstream["fixtures"][name]["split"]


def test_quality_gate_rejects_a_structurally_valid_wrong_tree(validator: GumGoldValidator) -> None:
    _, wrong_document_analysis, wrong_rs4 = validator.load_gold_fixture("GUM_bio_dvorak")
    report = validator.validate_analysis(
        "GUM_academic_art",
        replace(wrong_document_analysis, document_id="GUM_academic_art"),
        prediction_rs4=wrong_rs4,
    )
    regressions = _quality_regressions(
        _report_metrics(report),
        QUALITY_BASELINE.documents["GUM_academic_art"].observed,
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
    """Detect any changed match counts under the recorded evaluation conditions."""
    report = next(report for report in parser_quality_report.document_reports if report.doc_id == doc_id)
    regressions = _quality_regressions(_report_metrics(report), QUALITY_BASELINE.documents[doc_id].observed)

    assert report.passed_structural_checks, f"Structural validation failed: {report.structural_errors}"
    assert report.pred_edu_count == report.gold_edu_count
    assert report.is_valid_tree
    assert not regressions, "; ".join(regressions)

    md = report.summary_markdown()
    assert doc_id in md
    assert "Standard Span" in md


@pytest.mark.slow
@pytest.mark.quality
def test_gum_corpus_micro_regression(
    parser_quality_report: GumCorpusValidationReport,
) -> None:
    """Reproduce recorded micro counts without an arbitrary accuracy floor."""
    corpus_report = parser_quality_report
    regressions = _quality_regressions(_corpus_metrics(corpus_report), QUALITY_BASELINE.micro)

    assert corpus_report.document_count == len(GOLD_FIXTURE_NAMES)
    assert not regressions, "; ".join(regressions)

    summary_table = corpus_report.summary_table()
    assert "GUM Gold Benchmark Summary" in summary_table
    assert "Macro Average" in summary_table
