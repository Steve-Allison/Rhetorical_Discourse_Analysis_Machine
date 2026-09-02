"""Champion-gated construction of untouched test and test2 candidate shards."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rdam.rst.contracts.analysis import RstAnalysis
from rdam.rst.contracts.document import RstDocument
from rdam.rst.contracts.erst import (
    CorpusPartition,
    PrivateCorpusVerificationReceipt,
    RawRelationInventory,
)
from rdam.rst.erst.candidates import iter_secondary_edge_candidates
from rdam.rst.erst.converter import rs4_to_document_and_analysis
from rdam.rst.erst.rs4 import RS4Reader
from workbench.research.erst.contracts import (
    ChampionManifest,
    ExperimentDataIdentity,
    ExperimentDocumentIdentity,
    ExperimentProtocol,
)
from workbench.research.erst.data import CandidateRecord, CandidateShard, HarnessCandidate, HarnessDocument
from workbench.research.erst.runner import PreparedExperimentData

FINAL_CACHE_SCHEMA_VERSION = "1.0"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FinalEvaluationCacheManifest(BaseModel):
    """Complete test/test2 cache bound to the pre-test champion identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = FINAL_CACHE_SCHEMA_VERSION
    protocol_sha256: str = Field(pattern=_SHA256_PATTERN)
    champion_sha256: str = Field(pattern=_SHA256_PATTERN)
    private_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    raw_relation_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    shards: tuple[CandidateShard, ...] = Field(min_length=1)
    candidate_count: int = Field(gt=0)
    longest_document_id: str = Field(min_length=1)
    manifest_sha256: str = ""

    @model_validator(mode="after")
    def validate_manifest(self) -> "FinalEvaluationCacheManifest":
        if any(shard.partition not in (CorpusPartition.TEST, CorpusPartition.TEST2) for shard in self.shards):
            raise ValueError("final cache may contain only test and test2")
        if {shard.partition for shard in self.shards} != {
            CorpusPartition.TEST,
            CorpusPartition.TEST2,
        }:
            raise ValueError("final cache requires both test and test2 documents")
        if self.candidate_count != sum(shard.candidate_count for shard in self.shards):
            raise ValueError("final cache candidate count does not reconcile")
        longest = max(self.shards, key=lambda shard: (shard.candidate_count, shard.document_id))
        if self.longest_document_id != longest.document_id:
            raise ValueError("final cache longest-document identity is incorrect")
        encoded = json.dumps(
            self.model_dump(mode="json", exclude={"manifest_sha256"}),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        expected = hashlib.sha256(encoded).hexdigest()
        if self.manifest_sha256 and self.manifest_sha256 != expected:
            raise ValueError("final cache manifest hash does not match canonical content")
        object.__setattr__(self, "manifest_sha256", expected)
        return self


@dataclass(frozen=True, slots=True)
class FinalEvaluationCorpusPayload:
    """Test-only payload created after champion freeze, with no train/dev source paths."""

    corpus_root: Path
    cache_root: Path
    manifest: FinalEvaluationCacheManifest
    raw_relation_inventory: RawRelationInventory
    shards: tuple[CandidateShard, ...]

    @property
    def evaluation_shards(self) -> tuple[CandidateShard, ...]:
        return self.shards

    def load_evaluation_document(self, shard: CandidateShard) -> HarnessDocument:
        if shard not in self.shards:
            raise ValueError("requested document is not a governed final-evaluation shard")
        source = (self.corpus_root / shard.source_path).resolve()
        if not source.is_relative_to(self.corpus_root) or source.is_symlink():
            raise ValueError(f"unsafe final-evaluation source: {shard.document_id}")
        source_bytes = source.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != shard.source_sha256:
            raise ValueError(f"final-evaluation source hash changed: {shard.document_id}")
        document, analysis = rs4_to_document_and_analysis(
            RS4Reader.read_string(source_bytes.decode("utf-8")),
            document_id=shard.document_id,
        )
        candidates = _load_candidate_file(self.cache_root / shard.candidate_path)
        if len(candidates) != shard.candidate_count:
            raise ValueError(f"final-evaluation candidate count changed: {shard.document_id}")
        return HarnessDocument(
            shard=shard,
            document=document,
            gold_analysis=analysis,
            candidates=candidates,
        )


def _load_candidate_file(path: Path) -> tuple[HarnessCandidate, ...]:
    records: list[HarnessCandidate] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                records.append(CandidateRecord.model_validate_json(line).to_harness_candidate())
            except ValueError as error:
                raise ValueError(f"invalid final candidate at {path.name}:{line_number}") from error
    return tuple(records)


def _parse_source(
    *,
    corpus_root: Path,
    source_path: str,
    source_sha256: str,
    document_id: str,
) -> tuple[bytes, RstDocument, RstAnalysis]:
    source = (corpus_root / source_path).resolve()
    if not source.is_relative_to(corpus_root) or not source.is_file() or source.is_symlink():
        raise ValueError(f"unsafe private final source: {document_id}")
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
        raise ValueError(f"private final source hash changed: {document_id}")
    document, analysis = rs4_to_document_and_analysis(
        RS4Reader.read_string(source_bytes.decode("utf-8")),
        document_id=document_id,
    )
    return source_bytes, document, analysis


def _build_final_cache(
    *,
    corpus_root: Path,
    cache_root: Path,
    protocol: ExperimentProtocol,
    champion: ChampionManifest,
    verification: PrivateCorpusVerificationReceipt,
    inventory: RawRelationInventory,
) -> FinalEvaluationCacheManifest:
    cache_root.mkdir(parents=True, exist_ok=False)
    sources = tuple(
        source
        for source in verification.sources
        if source.partition in (CorpusPartition.TEST, CorpusPartition.TEST2)
    )
    if not sources:
        raise ValueError("private verification contains no final-evaluation sources")
    shards: list[CandidateShard] = []
    for source in sources:
        _, document, analysis = _parse_source(
            corpus_root=corpus_root,
            source_path=source.source_path,
            source_sha256=source.source_sha256,
            document_id=source.document_id,
        )
        relative_path = f"candidates/{source.partition.value}/{source.document_id}.jsonl"
        candidate_path = cache_root / relative_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = candidate_path.with_suffix(".jsonl.tmp")
        if candidate_path.exists() or temporary.exists():
            raise RuntimeError(f"final candidate cache already exists: {relative_path}")
        signal_spans = {signal.signal_id: signal.char_spans for signal in analysis.signals}
        candidate_count = 0
        positive_count = 0
        with temporary.open("w", encoding="utf-8") as stream:
            for candidate in iter_secondary_edge_candidates(document, analysis):
                spans = tuple(
                    span
                    for signal_id in candidate.signal_ids
                    for span in signal_spans[signal_id]
                )
                stream.write(CandidateRecord.from_candidate(candidate, spans).model_dump_json() + "\n")
                candidate_count += 1
                positive_count += int(candidate.is_gold_edge)
        if candidate_count <= 0:
            temporary.unlink()
            raise ValueError(f"final-evaluation document produced zero candidates: {source.document_id}")
        temporary.replace(candidate_path)
        shards.append(
            CandidateShard(
                document_id=source.document_id,
                partition=source.partition,
                license_class=source.license_class,
                source_path=source.source_path,
                source_sha256=source.source_sha256,
                candidate_path=relative_path,
                candidate_sha256=_sha256_file(candidate_path),
                candidate_count=candidate_count,
                positive_count=positive_count,
                signal_count=len(analysis.signals),
            )
        )
    manifest = FinalEvaluationCacheManifest(
        protocol_sha256=protocol.protocol_sha256,
        champion_sha256=champion.champion_sha256,
        private_receipt_sha256=verification.receipt_sha256,
        raw_relation_inventory_sha256=inventory.inventory_sha256,
        shards=tuple(shards),
        candidate_count=sum(shard.candidate_count for shard in shards),
        longest_document_id=max(
            shards,
            key=lambda shard: (shard.candidate_count, shard.document_id),
        ).document_id,
    )
    (cache_root / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def prepare_final_evaluation_corpus(
    *,
    corpus_root: Path,
    cache_root: Path,
    protocol: ExperimentProtocol,
    champion: ChampionManifest,
    verification_receipt_path: Path,
    relation_inventory_path: Path,
) -> PreparedExperimentData[FinalEvaluationCorpusPayload]:
    """Access test sources only after validating the frozen dev champion."""

    if champion.protocol_sha256 != protocol.protocol_sha256 or champion.test_data_accessed:
        raise ValueError("final corpus access requires a valid pre-test champion")
    verification = PrivateCorpusVerificationReceipt.model_validate_json(
        verification_receipt_path.read_text(encoding="utf-8")
    )
    inventory = RawRelationInventory.model_validate_json(
        relation_inventory_path.read_text(encoding="utf-8")
    )
    if verification.corpus_revision != protocol.corpus_revision:
        raise ValueError("final corpus revision differs from the frozen protocol")
    cache_root = cache_root.resolve()
    manifest_path = cache_root / "manifest.json"
    if manifest_path.exists():
        manifest = FinalEvaluationCacheManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        expected = (
            protocol.protocol_sha256,
            champion.champion_sha256,
            verification.receipt_sha256,
            inventory.inventory_sha256,
        )
        observed = (
            manifest.protocol_sha256,
            manifest.champion_sha256,
            manifest.private_receipt_sha256,
            manifest.raw_relation_inventory_sha256,
        )
        if observed != expected:
            raise ValueError("final cache belongs to different governed inputs")
        for shard in manifest.shards:
            candidate_path = cache_root / shard.candidate_path
            if not candidate_path.is_file() or _sha256_file(candidate_path) != shard.candidate_sha256:
                raise ValueError(f"final candidate cache failed verification: {shard.document_id}")
    elif cache_root.exists():
        raise ValueError("final cache exists without a complete manifest")
    else:
        manifest = _build_final_cache(
            corpus_root=corpus_root.resolve(),
            cache_root=cache_root,
            protocol=protocol,
            champion=champion,
            verification=verification,
            inventory=inventory,
        )
    documents = tuple(
        ExperimentDocumentIdentity(
            document_id=shard.document_id,
            source_sha256=shard.source_sha256,
            partition=shard.partition,
            candidate_count=shard.candidate_count,
        )
        for shard in manifest.shards
    )
    selection_sha256 = hashlib.sha256(
        (manifest.manifest_sha256 + champion.champion_sha256).encode()
    ).hexdigest()
    payload = FinalEvaluationCorpusPayload(
        corpus_root=corpus_root.resolve(),
        cache_root=cache_root,
        manifest=manifest,
        raw_relation_inventory=inventory,
        shards=manifest.shards,
    )
    return PreparedExperimentData(
        identity=ExperimentDataIdentity(
            split_manifest_sha256=protocol.split_manifest_sha256,
            candidate_selection_sha256=selection_sha256,
            partitions=(CorpusPartition.TEST, CorpusPartition.TEST2),
            documents=documents,
            scored_document_ids=tuple(document.document_id for document in documents),
            candidate_count=manifest.candidate_count,
        ),
        payload=payload,
    )


def select_final_partition(
    prepared: PreparedExperimentData[FinalEvaluationCorpusPayload],
    partition: CorpusPartition,
) -> PreparedExperimentData[FinalEvaluationCorpusPayload]:
    """Create an identity-preserving single-partition view of the frozen final cache."""

    if partition not in (CorpusPartition.TEST, CorpusPartition.TEST2):
        raise ValueError("final evaluation partition must be test or test2")
    shards = tuple(
        shard for shard in prepared.payload.manifest.shards if shard.partition == partition
    )
    if not shards:
        raise ValueError(f"final cache has no {partition.value} shards")
    documents = tuple(
        ExperimentDocumentIdentity(
            document_id=shard.document_id,
            source_sha256=shard.source_sha256,
            partition=shard.partition,
            candidate_count=shard.candidate_count,
        )
        for shard in shards
    )
    return PreparedExperimentData(
        identity=ExperimentDataIdentity(
            split_manifest_sha256=prepared.identity.split_manifest_sha256,
            candidate_selection_sha256=hashlib.sha256(
                (prepared.identity.candidate_selection_sha256 + partition.value).encode()
            ).hexdigest(),
            partitions=(partition,),
            documents=documents,
            scored_document_ids=tuple(document.document_id for document in documents),
            candidate_count=sum(document.candidate_count for document in documents),
        ),
        payload=FinalEvaluationCorpusPayload(
            corpus_root=prepared.payload.corpus_root,
            cache_root=prepared.payload.cache_root,
            manifest=prepared.payload.manifest,
            raw_relation_inventory=prepared.payload.raw_relation_inventory,
            shards=shards,
        ),
    )
__all__ = [
    "FINAL_CACHE_SCHEMA_VERSION",
    "FinalEvaluationCacheManifest",
    "FinalEvaluationCorpusPayload",
    "prepare_final_evaluation_corpus",
    "select_final_partition",
]
