from isanlp_rst.contracts import OutputFormalismEnum, RstAnalysis, RstDocument
from isanlp_rst.ingest import AnalysisStatus, SourceArtifact
from isanlp_rst.ingest.service import ProductionIngestor
from isanlp_rst.model_loading import ParserCapacity


class RecordingParser:
    def __init__(self) -> None:
        self.analysis_capacity = ParserCapacity(unit="edu_count", maximum=512, source="test")
        self.model_release_identity = None
        self.documents: list[RstDocument] = []

    def parse_document(self, document: RstDocument, output: str = "rst_tree") -> RstAnalysis:
        self.documents.append(document)
        return RstAnalysis(
            document_id=document.document_id,
            formalism=OutputFormalismEnum(output),
            nodes=(),
            primary_edges=(),
        )


def test_empty_primary_discourse_returns_explicit_status_without_parser_call() -> None:
    parser = RecordingParser()
    result = ProductionIngestor(parser=parser).analyse(SourceArtifact.from_text(" \n", source_name="blank.txt"))
    assert result.analysis_status is AnalysisStatus.EMPTY_PRIMARY_DISCOURSE
    assert result.analysis is None
    assert not parser.documents


def test_analysis_uses_canonical_prepared_document_and_disables_cache_for_mutable_parser() -> None:
    parser = RecordingParser()
    result = ProductionIngestor(parser=parser).analyse(SourceArtifact.from_text("Authored prose.", source_name="input.txt"))
    assert result.analysis_status is AnalysisStatus.ANALYSED
    assert parser.documents[0].text == "Authored prose."
    assert result.preparation_receipt.cache_fingerprint is None
    assert "durable_cache_disabled_without_released_model_identity" in result.preparation_receipt.warnings
