from dataclasses import dataclass, field

from rdam.rst.contracts import RstDocument
from rdam.rst.ingest import AnalysisPolicy, AnalysisStatus, CacheStatus, ParserAnalysisResult, SourceArtifact
from rdam.rst.ingest.service import ProductionIngestor

from .conftest import DeterministicParser, ParserBuilder


@dataclass
class RecordingParser:
    delegate: DeterministicParser
    documents: list[RstDocument] = field(default_factory=list)

    @property
    def analysis_capacity(self):
        return self.delegate.analysis_capacity

    @property
    def model_release_identity(self):
        return self.delegate.model_release_identity

    def analyse_document(
        self,
        document: RstDocument,
        *,
        analysis_policy: AnalysisPolicy | None = None,
    ) -> ParserAnalysisResult:
        self.documents.append(document)
        return self.delegate.analyse_document(
            document,
            analysis_policy=analysis_policy,
        )


def test_empty_primary_discourse_returns_explicit_status_without_parser_call(
    parser_builder: ParserBuilder,
) -> None:
    parser = RecordingParser(parser_builder())
    result = ProductionIngestor(parser=parser).analyse(SourceArtifact.from_text(" \n", source_name="blank.txt"))
    assert result.status is AnalysisStatus.EMPTY_PRIMARY_DISCOURSE
    assert result.semantic.analysis is None
    assert not parser.documents


def test_analysis_uses_canonical_prepared_document_and_bypasses_absent_cache(
    parser_builder: ParserBuilder,
) -> None:
    parser = RecordingParser(parser_builder())
    result = ProductionIngestor(parser=parser).analyse(
        SourceArtifact.from_text("Authored prose.", source_name="input.txt")
    )
    assert result.status is AnalysisStatus.ANALYSED
    assert parser.documents[0].text == "Authored prose."
    assert result.execution.cache_status is CacheStatus.BYPASS
