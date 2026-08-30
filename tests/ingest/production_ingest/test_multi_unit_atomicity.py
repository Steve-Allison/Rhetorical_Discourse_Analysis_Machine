"""Complete multi-unit execution, recombination, and fail-closed atomicity."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from isanlp_rst.contracts import RstDocument
from isanlp_rst.ingest import (
    AnalysisPolicy,
    CompositeAnalysisIdentity,
    ParserAnalysisResult,
    ParserCapacity,
    ProductionIngestError,
    ProductionIngestor,
    SourceArtifact,
)
from isanlp_rst.model_loading import ModelReleaseIdentity

from .conftest import DeterministicParser, ParserBuilder


@dataclass(slots=True)
class RecordingUnitParser:
    delegate: DeterministicParser
    fail_on_call: int | None = None
    documents: list[RstDocument] = field(default_factory=list)

    @property
    def analysis_capacity(self) -> ParserCapacity:
        return self.delegate.analysis_capacity

    @property
    def model_release_identity(self) -> ModelReleaseIdentity:
        return self.delegate.model_release_identity

    @property
    def predictor(self) -> object:
        return self.delegate.predictor

    @property
    def erst_checkpoint(self) -> None:
        return None

    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult:
        self.documents.append(document)
        if self.fail_on_call == len(self.documents):
            raise RuntimeError("deliberate unit failure")
        return self.delegate.analyse_document(document, analysis_policy=analysis_policy)

    def describe_analysis_identity(
        self,
        *,
        analysis_policy: AnalysisPolicy,
        segmentation_source: str,
    ) -> CompositeAnalysisIdentity:
        return self.delegate.describe_analysis_identity(
            analysis_policy=analysis_policy,
            segmentation_source=segmentation_source,
        )


def test_subdivided_analysis_recombines_every_unit_completely(
    parser_builder: ParserBuilder,
) -> None:
    parser = RecordingUnitParser(parser_builder(maximum=2))
    outcome = ProductionIngestor(parser=parser).analyse(
        SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
    )
    assert len(parser.documents) == 2
    assert sum(len(document.edus or ()) for document in parser.documents) == 3
    parser_result = outcome.semantic.parser_result
    analysed = outcome.semantic.analysed_document
    assert parser_result is not None and analysed is not None
    assert parser_result.semantic.recombination is not None
    assert len(parser_result.execution.unit_executions) == 2
    assert analysed.text == "One. Two. Three."
    assert parser_result.semantic.recombination.node_mappings
    assert parser_result.semantic.recombination.edge_mappings
    assert outcome.semantic.validation is not None and outcome.semantic.validation.passed


def test_one_failed_unit_returns_no_partial_success(
    parser_builder: ParserBuilder,
) -> None:
    parser = RecordingUnitParser(parser_builder(maximum=2), fail_on_call=2)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor(parser=parser).analyse(
            SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus")
        )
    assert raised.value.failure.code == "parser_execution_failed"
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert len(parser.documents) == 2


def test_one_failed_unit_writes_no_partial_cache_entry(
    parser_builder: ParserBuilder,
    tmp_path: Path,
) -> None:
    parser = RecordingUnitParser(parser_builder(maximum=2), fail_on_call=2)
    with pytest.raises(ProductionIngestError) as raised:
        ProductionIngestor(parser=parser).analyse(
            SourceArtifact.from_edus(("One.", "Two.", "Three."), source_name="three.edus"),
            cache_directory=tmp_path,
        )
    assert raised.value.failure.code == "parser_execution_failed"
    assert not tuple(tmp_path.rglob("*.json"))
    assert not tuple(tmp_path.rglob("*.tmp"))
