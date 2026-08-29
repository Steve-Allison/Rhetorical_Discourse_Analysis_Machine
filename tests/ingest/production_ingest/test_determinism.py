from pathlib import Path, PurePosixPath

from isanlp_rst.contracts import OutputFormalismEnum, RstAnalysis, RstDocument
from isanlp_rst.ingest import CacheStatus, SourceArtifact
from isanlp_rst.ingest.service import ProductionIngestor
from isanlp_rst.model_loading import ModelFile, ModelReleaseIdentity, ParserCapacity


class ImmutableEmptyParser:
    analysis_capacity = ParserCapacity(unit="edu_count", maximum=512, source="test")
    model_release_identity = ModelReleaseIdentity(
        release_id="test-release",
        manifest_sha256="a" * 64,
        runtime_contract="isanlp_rst.parser/test-v1",
        architecture="test",
        files=(
            ModelFile(
                path=PurePosixPath("model.bin"),
                role="weights",
                size_bytes=1,
                sha256="b" * 64,
            ),
        ),
        capacity=analysis_capacity,
    )

    def parse_document(self, document: RstDocument, output: str = "rst_tree") -> RstAnalysis:
        return RstAnalysis(
            document_id=document.document_id,
            formalism=OutputFormalismEnum(output),
            nodes=(),
            primary_edges=(),
        )


def test_ten_cached_and_uncached_runs_have_one_semantic_identity(tmp_path: Path) -> None:
    artifact = SourceArtifact.from_text("", source_name="empty.txt")
    service = ProductionIngestor(parser=ImmutableEmptyParser())
    uncached = [service.analyse(artifact) for _ in range(5)]
    cached = [service.analyse(artifact, cache_dir=tmp_path) for _ in range(5)]
    assert len({result.semantic_digest for result in (*uncached, *cached)}) == 1
    assert cached[0].execution_receipt.cache_status is CacheStatus.WRITTEN
    assert all(result.execution_receipt.cache_status is CacheStatus.HIT for result in cached[1:])
    assert uncached[0].preparation_receipt.cache_fingerprint == cached[0].preparation_receipt.cache_fingerprint
