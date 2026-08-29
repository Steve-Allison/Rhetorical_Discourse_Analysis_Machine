"""GUM Gold Standard Validation Engine.

Provides automated validation of processed files, RST analyses, and tree predictions
against the official GUM gold standard fixtures.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from isanlp_rst.annotation_rst import DiscourseUnit

from isanlp_rst.contracts import (
    NodeKindEnum,
    RstAnalysis,
    RstDocument,
    analysis_from_json,
)
from isanlp_rst.erst.converter import du_to_analysis, rs4_to_document_and_analysis
from isanlp_rst.erst.rs4 import RS4Document, RS4Reader
from offline_workbench.evaluation.rst.erst_scorer import ErstScorer, SecondaryEdgeMetrics, SignalMetrics
from offline_workbench.evaluation.rst.parseval import ParsevalMetrics, SoftParsevalScorer, StandardParsevalScorer
from isanlp_rst.ontology.adapter import OntologyAdapter
from isanlp_rst.parser import Parser

GUM_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "gum"

GOLD_FIXTURE_NAMES: tuple[str, ...] = (
    "GUM_academic_art",
    "GUM_academic_census",
    "GUM_bio_byron",
    "GUM_bio_dvorak",
    "GUM_bio_emperor",
    "GUM_interview_gaming",
    "GUM_news_nasa",
    "GUM_news_sensitive",
    "GUM_textbook_chemistry",
    "GUM_voyage_oakland",
)


@dataclass(frozen=True, slots=True)
class GumValidationReport:
    """Detailed validation metrics of a processed prediction against a GUM gold file."""

    doc_id: str
    gold_edu_count: int
    pred_edu_count: int
    standard_parseval: ParsevalMetrics
    rst_parseval: ParsevalMetrics
    coarse_parseval: ParsevalMetrics
    char_parseval: ParsevalMetrics | None = None
    soft_parseval: ParsevalMetrics | None = None
    secondary_metrics: SecondaryEdgeMetrics | None = None
    signal_metrics: SignalMetrics | None = None
    is_valid_tree: bool = True
    structural_errors: tuple[str, ...] = ()

    @property
    def passed_structural_checks(self) -> bool:
        return self.is_valid_tree and len(self.structural_errors) == 0

    def summary_markdown(self) -> str:
        lines = [
            f"### GUM Gold Validation Report: `{self.doc_id}`",
            f"- **Gold EDUs**: {self.gold_edu_count} | **Pred EDUs**: {self.pred_edu_count}",
            f"- **Structural Integrity**: {'VALID' if self.passed_structural_checks else 'INVALID'}",
        ]
        if self.structural_errors:
            for err in self.structural_errors:
                lines.append(f"  - ⚠️ {err}")

        lines.extend(
            [
                "",
                "| Evaluation Metric | Precision | Recall | F1 | Matched / Gold |",
                "| :--- | :--- | :--- | :--- | :--- |",
                f"| **Standard Span (EDU-exact)** | {self.standard_parseval.span_precision:.3f} | {self.standard_parseval.span_recall:.3f} | {self.standard_parseval.span_f1:.3f} | {self.standard_parseval.matched_span} / {self.standard_parseval.gold_spans_count} |",
                f"| **Standard Nuclearity** | {self.standard_parseval.nuclearity_precision:.3f} | {self.standard_parseval.nuclearity_recall:.3f} | {self.standard_parseval.nuclearity_f1:.3f} | {self.standard_parseval.matched_nuclearity} / {self.standard_parseval.gold_spans_count} |",
                f"| **Standard Relation (Fine)** | {self.standard_parseval.relation_precision:.3f} | {self.standard_parseval.relation_recall:.3f} | {self.standard_parseval.relation_f1:.3f} | {self.standard_parseval.matched_relation} / {self.standard_parseval.gold_spans_count} |",
                f"| **Standard Relation (Coarse-18)** | {self.coarse_parseval.relation_precision:.3f} | {self.coarse_parseval.relation_recall:.3f} | {self.coarse_parseval.relation_f1:.3f} | {self.coarse_parseval.matched_relation} / {self.coarse_parseval.gold_spans_count} |",
                f"| **Standard Full (Span+Nuc+Rel)** | {self.standard_parseval.full_precision:.3f} | {self.standard_parseval.full_recall:.3f} | {self.standard_parseval.full_f1:.3f} | {self.standard_parseval.matched_full} / {self.standard_parseval.gold_spans_count} |",
            ]
        )

        if self.char_parseval is not None:
            lines.append(
                f"| **Char Span (Exact)** | {self.char_parseval.span_precision:.3f} | {self.char_parseval.span_recall:.3f} | {self.char_parseval.span_f1:.3f} | {self.char_parseval.matched_span} / {self.char_parseval.gold_spans_count} |"
            )
        if self.soft_parseval is not None:
            lines.append(
                f"| **Soft Span (IoU>=0.80)** | {self.soft_parseval.span_precision:.3f} | {self.soft_parseval.span_recall:.3f} | {self.soft_parseval.span_f1:.3f} | {self.soft_parseval.matched_span} / {self.soft_parseval.gold_spans_count} |"
            )

        lines.extend(
            [
                f"| **RST-Parseval Span** | {self.rst_parseval.span_precision:.3f} | {self.rst_parseval.span_recall:.3f} | {self.rst_parseval.span_f1:.3f} | {self.rst_parseval.matched_span} / {self.rst_parseval.gold_spans_count} |",
                f"| **RST-Parseval Relation (Fine)** | {self.rst_parseval.relation_precision:.3f} | {self.rst_parseval.relation_recall:.3f} | {self.rst_parseval.relation_f1:.3f} | {self.rst_parseval.matched_relation} / {self.rst_parseval.gold_spans_count} |",
            ]
        )

        if self.secondary_metrics is not None and self.secondary_metrics.gold_count > 0:
            lines.extend(
                [
                    "",
                    "| eRST Secondary Edges | Precision | Recall | F1 | Matched / Gold |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                    f"| **Secondary Edge Span** | {self.secondary_metrics.span_precision:.3f} | {self.secondary_metrics.span_recall:.3f} | {self.secondary_metrics.span_f1:.3f} | {self.secondary_metrics.matched_span} / {self.secondary_metrics.gold_count} |",
                    f"| **Secondary Edge Direction** | {self.secondary_metrics.direction_precision:.3f} | {self.secondary_metrics.direction_recall:.3f} | {self.secondary_metrics.direction_f1:.3f} | {self.secondary_metrics.matched_direction} / {self.secondary_metrics.gold_count} |",
                    f"| **Secondary Edge Relation** | {self.secondary_metrics.relation_precision:.3f} | {self.secondary_metrics.relation_recall:.3f} | {self.secondary_metrics.relation_f1:.3f} | {self.secondary_metrics.matched_relation} / {self.secondary_metrics.gold_count} |",
                    f"| **Secondary Edge Full** | {self.secondary_metrics.full_precision:.3f} | {self.secondary_metrics.full_recall:.3f} | {self.secondary_metrics.full_f1:.3f} | {self.secondary_metrics.matched_full} / {self.secondary_metrics.gold_count} |",
                ]
            )

        if self.signal_metrics is not None and self.signal_metrics.gold_signals_count > 0:
            lines.extend(
                [
                    "",
                    "| eRST Discourse Signals | Precision | Recall | F1 | Matched / Gold |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                    f"| **Signal Detection** | {self.signal_metrics.detection_precision:.3f} | {self.signal_metrics.detection_recall:.3f} | {self.signal_metrics.detection_f1:.3f} | {self.signal_metrics.matched_detection} / {self.signal_metrics.gold_signals_count} |",
                    f"| **Signal Token Match** | {self.signal_metrics.token_precision:.3f} | {self.signal_metrics.token_recall:.3f} | {self.signal_metrics.token_f1:.3f} | Tokens |",
                ]
            )

        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class GumCorpusValidationReport:
    """Macro-averaged validation metrics across a corpus of GUM documents."""

    document_reports: tuple[GumValidationReport, ...]

    @property
    def document_count(self) -> int:
        return len(self.document_reports)

    @property
    def macro_span_f1(self) -> float:
        if not self.document_reports:
            return 0.0
        return sum(r.standard_parseval.span_f1 for r in self.document_reports) / len(self.document_reports)

    @property
    def macro_nuclearity_f1(self) -> float:
        if not self.document_reports:
            return 0.0
        return sum(r.standard_parseval.nuclearity_f1 for r in self.document_reports) / len(self.document_reports)

    @property
    def macro_relation_fine_f1(self) -> float:
        if not self.document_reports:
            return 0.0
        return sum(r.standard_parseval.relation_f1 for r in self.document_reports) / len(self.document_reports)

    @property
    def macro_relation_coarse_f1(self) -> float:
        if not self.document_reports:
            return 0.0
        return sum(r.coarse_parseval.relation_f1 for r in self.document_reports) / len(self.document_reports)

    @property
    def macro_full_f1(self) -> float:
        if not self.document_reports:
            return 0.0
        return sum(r.standard_parseval.full_f1 for r in self.document_reports) / len(self.document_reports)

    def summary_table(self) -> str:
        lines = [
            "### GUM Gold Benchmark Summary (Macro-Averaged)",
            "",
            "| Document ID | EDUs (Gold/Pred) | Span F1 | Nuc F1 | Rel (Fine) F1 | Rel (Coarse) F1 | Full F1 | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in self.document_reports:
            status = "PASS" if r.passed_structural_checks else "FAIL"
            lines.append(
                f"| `{r.doc_id}` | {r.gold_edu_count}/{r.pred_edu_count} | {r.standard_parseval.span_f1:.3f} | {r.standard_parseval.nuclearity_f1:.3f} | {r.standard_parseval.relation_f1:.3f} | {r.coarse_parseval.relation_f1:.3f} | {r.standard_parseval.full_f1:.3f} | {status} |"
            )

        lines.extend(
            [
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
                f"| **Macro Average** | - | **{self.macro_span_f1:.3f}** | **{self.macro_nuclearity_f1:.3f}** | **{self.macro_relation_fine_f1:.3f}** | **{self.macro_relation_coarse_f1:.3f}** | **{self.macro_full_f1:.3f}** | **{len(self.document_reports)} docs** |",
            ]
        )
        return "\n".join(lines)


class GumGoldValidator:
    """Validator that verifies model predictions or processed files against GUM gold standards."""

    def __init__(self, fixtures_dir: Path | str | None = None) -> None:
        self.fixtures_dir = Path(fixtures_dir) if fixtures_dir else GUM_FIXTURES_DIR
        self.ontology_adapter = OntologyAdapter()
        self.standard_scorer = StandardParsevalScorer(include_leaves=False, include_root=False)
        self.rst_parseval_scorer = StandardParsevalScorer(include_leaves=True, include_root=True)
        self.erst_scorer = ErstScorer()

        # Coarse-18 mapper function
        def coarse_mapper(raw_label: str) -> str:
            resolved = self.ontology_adapter.resolve_label(raw_label, raise_on_unmapped=False)
            return resolved[1].lower() if resolved else raw_label.lower()

        self.coarse_scorer = StandardParsevalScorer(
            include_leaves=False,
            include_root=False,
            label_mapper=coarse_mapper,
        )
        self.char_scorer = SoftParsevalScorer(include_leaves=False, include_root=False, min_iou=1.0)
        self.soft_scorer = SoftParsevalScorer(include_leaves=False, include_root=False, min_iou=0.80)

    def get_gold_path(self, doc_id: str) -> Path:
        filename = f"{doc_id}.rs4" if not doc_id.endswith(".rs4") else doc_id
        path = self.fixtures_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"GUM gold fixture not found: {path}")
        return path

    def load_gold_fixture(self, doc_id: str) -> tuple[RstDocument, RstAnalysis, RS4Document]:
        path = self.get_gold_path(doc_id)
        reader = RS4Reader()
        rs4_doc = reader.read_file(path)
        doc, analysis = rs4_to_document_and_analysis(rs4_doc, document_id=doc_id)
        return doc, analysis, rs4_doc

    def validate_analysis(
        self,
        gold_doc_id: str,
        predicted_analysis: RstAnalysis,
    ) -> GumValidationReport:
        """Validate an RstAnalysis against a GUM gold fixture."""
        _, gold_analysis, _ = self.load_gold_fixture(gold_doc_id)

        gold_edu_count = len([n for n in gold_analysis.nodes if n.kind == NodeKindEnum.EDU])
        pred_edu_count = len([n for n in predicted_analysis.nodes if n.kind == NodeKindEnum.EDU])

        # Structural checks
        structural_errors: list[str] = []
        is_valid = True

        if not predicted_analysis.nodes:
            is_valid = False
            structural_errors.append("Predicted analysis contains no nodes.")

        root = predicted_analysis.root_node
        if root is None and len(predicted_analysis.nodes) > 1:
            is_valid = False
            structural_errors.append("Missing root node in non-empty tree.")

        # Compute Parseval metrics
        std_metrics = self.standard_scorer.score(gold_analysis, predicted_analysis)
        rst_metrics = self.rst_parseval_scorer.score(gold_analysis, predicted_analysis)
        coarse_metrics = self.coarse_scorer.score(gold_analysis, predicted_analysis)
        char_metrics = self.char_scorer.score(gold_analysis, predicted_analysis)
        soft_metrics = self.soft_scorer.score(gold_analysis, predicted_analysis)

        # eRST metrics if present
        sec_metrics: SecondaryEdgeMetrics | None = None
        if gold_analysis.secondary_edges or predicted_analysis.secondary_edges:
            sec_metrics = self.erst_scorer.score_secondary_edges(
                gold_analysis,
                predicted_analysis,
            )

        sig_metrics: SignalMetrics | None = None
        if gold_analysis.signals or predicted_analysis.signals:
            sig_metrics = self.erst_scorer.score_signals(
                gold_analysis.signals,
                predicted_analysis.signals,
            )

        return GumValidationReport(
            doc_id=gold_doc_id,
            gold_edu_count=gold_edu_count,
            pred_edu_count=pred_edu_count,
            standard_parseval=std_metrics,
            rst_parseval=rst_metrics,
            coarse_parseval=coarse_metrics,
            char_parseval=char_metrics,
            soft_parseval=soft_metrics,
            secondary_metrics=sec_metrics,
            signal_metrics=sig_metrics,
            is_valid_tree=is_valid,
            structural_errors=tuple(structural_errors),
        )

    def validate_tree(
        self,
        gold_doc_id: str,
        tree: DiscourseUnit,
    ) -> GumValidationReport:
        """Validate a legacy DiscourseUnit tree against a GUM gold fixture."""
        pred_analysis = du_to_analysis(tree, document_id=gold_doc_id)
        return self.validate_analysis(gold_doc_id, pred_analysis)

    def validate_file(
        self,
        gold_doc_id: str,
        processed_file_path: Path | str,
    ) -> GumValidationReport:
        """Validate a processed JSON or RS4 file against a GUM gold fixture."""
        path = Path(processed_file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Processed file not found: {path}")

        if path.suffix.lower() == ".json":
            json_text = path.read_text(encoding="utf-8")
            pred_analysis = analysis_from_json(json_text)
        elif path.suffix.lower() == ".rs4":
            reader = RS4Reader()
            rs4 = reader.read_file(path)
            _, pred_analysis = rs4_to_document_and_analysis(rs4, document_id=gold_doc_id)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix} (expected .json or .rs4)")

        return self.validate_analysis(gold_doc_id, pred_analysis)

    def validate_document_with_parser(
        self,
        gold_doc_id: str,
        parser: Parser,
        from_edus: bool = True,
    ) -> GumValidationReport:
        """Run the neural parser against a GUM gold document and validate results."""
        gold_doc, _, _ = self.load_gold_fixture(gold_doc_id)

        if from_edus and gold_doc.edus:
            # Use gold segment boundaries for exact span evaluation
            edu_texts = [e.text for e in gold_doc.edus]
            pred_doc = RstDocument.from_edus(edu_texts, document_id=gold_doc_id)
            pred_analysis = parser.parse_document(pred_doc)
        else:
            # Run end-to-end segmentation and parsing on raw text
            pred_doc = RstDocument.from_text(gold_doc.text, document_id=gold_doc_id)
            pred_analysis = parser.parse_document(pred_doc)

        return self.validate_analysis(gold_doc_id, pred_analysis)

    def validate_corpus_with_parser(
        self,
        parser: Parser,
        doc_ids: Sequence[str] = GOLD_FIXTURE_NAMES,
        from_edus: bool = True,
    ) -> GumCorpusValidationReport:
        """Validate all GUM gold fixture documents with a neural parser."""
        reports = tuple(self.validate_document_with_parser(doc_id, parser, from_edus=from_edus) for doc_id in doc_ids)
        return GumCorpusValidationReport(document_reports=reports)
