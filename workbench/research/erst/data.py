"""Bounded-memory train/dev corpus preparation for the isolated eRST harness."""

from collections.abc import Iterator
from dataclasses import dataclass, replace
import hashlib
import heapq
import json
import math
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isanlp_rst.contracts.analysis import RstAnalysis
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.erst import (
    CorpusLicenseClass,
    CorpusPartition,
    HardNegativeSamplingConfig,
    PrivateCorpusVerificationReceipt,
    RawRelationInventory,
)
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate, iter_secondary_edge_candidates
from isanlp_rst.erst.converter import rs4_to_document_and_analysis
from workbench.corpus.erst.corpus import GUM_SPLITS_SHA256
from isanlp_rst.erst.rs4 import RS4Reader
from workbench.research.erst.contracts import (
    AblationName,
    ExperimentDataIdentity,
    ExperimentDocumentIdentity,
)
from workbench.research.erst.runner import PreparedExperimentData

CORPUS_CACHE_SCHEMA_VERSION = "1.0"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(model: BaseModel, hash_field: str) -> str:
    encoded = json.dumps(
        model.model_dump(mode="json", exclude={hash_field}),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class CandidateRecord(BaseModel):
    """Lossless JSON boundary for a private cached candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    source_id: int
    target_id: int
    source_text: str
    target_text: str
    source_char_span: tuple[int, int]
    target_char_span: tuple[int, int]
    structural_features: tuple[float, ...]
    is_gold_edge: bool
    gold_relation: str | None = None
    gold_concept: str | None = None
    signal_ids: tuple[str, ...]
    signal_types: tuple[str, ...]
    signal_subtypes: tuple[str, ...]
    compatible_relations: tuple[str, ...]
    source_head_id: int
    target_head_id: int
    source_head_text: str
    target_head_text: str
    source_sentence_ids: tuple[int, ...]
    target_sentence_ids: tuple[int, ...]
    direction: str
    edu_distance: int
    existing_primary_relation: str | None = None
    existing_primary_direction: str | None = None
    primary_path: tuple[str, ...]
    signal_char_spans: tuple[tuple[int, int], ...]

    @classmethod
    def from_candidate(
        cls,
        candidate: SecondaryEdgeCandidate,
        signal_char_spans: tuple[tuple[int, int], ...],
    ) -> "CandidateRecord":
        candidate_fields = SecondaryEdgeCandidate.__dataclass_fields__
        return cls(
            **{name: getattr(candidate, name) for name in candidate_fields},
            signal_char_spans=signal_char_spans,
        )

    def to_harness_candidate(self) -> "HarnessCandidate":
        candidate_fields = SecondaryEdgeCandidate.__dataclass_fields__
        return HarnessCandidate(
            candidate=SecondaryEdgeCandidate(
                **{name: getattr(self, name) for name in candidate_fields}
            ),
            signal_char_spans=self.signal_char_spans,
        )


class CandidateShard(BaseModel):
    """Text-free identity for one private document candidate shard."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str = Field(min_length=1)
    partition: CorpusPartition
    license_class: CorpusLicenseClass
    source_path: str
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_path: str
    candidate_sha256: str = Field(pattern=_SHA256_PATTERN)
    candidate_count: int = Field(gt=0)
    positive_count: int = Field(ge=0)
    signal_count: int = Field(gt=0)

    @field_validator("source_path", "candidate_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("corpus cache paths must be relative POSIX paths")
        return value


class ScreeningCorpusCacheManifest(BaseModel):
    """Complete bounded-memory train/dev cache and exact selection evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = CORPUS_CACHE_SCHEMA_VERSION
    private_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    split_manifest_sha256: str = GUM_SPLITS_SHA256
    sampling_config_sha256: str = Field(pattern=_SHA256_PATTERN)
    raw_relation_inventory_sha256: str = Field(pattern=_SHA256_PATTERN)
    shards: tuple[CandidateShard, ...] = Field(min_length=1)
    selected_train_path: str
    selected_train_sha256: str = Field(pattern=_SHA256_PATTERN)
    selected_train_count: int = Field(gt=0)
    selected_train_positive_count: int = Field(gt=0)
    complete_dev_count: int = Field(gt=0)
    manifest_sha256: str = ""

    @field_validator("selected_train_path")
    @classmethod
    def validate_selection_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("selected train path must be relative to the cache root")
        return value

    @model_validator(mode="after")
    def validate_manifest(self) -> "ScreeningCorpusCacheManifest":
        if any(shard.partition not in (CorpusPartition.TRAIN, CorpusPartition.DEV) for shard in self.shards):
            raise ValueError("screening cache cannot contain test or test2 shards")
        if len({shard.document_id for shard in self.shards}) != len(self.shards):
            raise ValueError("screening cache document IDs must be unique")
        expected_dev = sum(
            shard.candidate_count for shard in self.shards if shard.partition == CorpusPartition.DEV
        )
        if self.complete_dev_count != expected_dev:
            raise ValueError("screening cache dev candidate count does not reconcile")
        expected_hash = _canonical_hash(self, "manifest_sha256")
        if self.manifest_sha256 and self.manifest_sha256 != expected_hash:
            raise ValueError("screening cache manifest SHA-256 does not match canonical content")
        object.__setattr__(self, "manifest_sha256", expected_hash)
        return self


@dataclass(frozen=True, slots=True)
class HarnessCandidate:
    """Canonical production candidate plus exact overlapping signal anchors."""

    candidate: SecondaryEdgeCandidate
    signal_char_spans: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class HarnessDocument:
    """One private source parsed only while its shard is actively evaluated."""

    shard: CandidateShard
    document: RstDocument
    gold_analysis: RstAnalysis
    candidates: tuple[HarnessCandidate, ...]


@dataclass(frozen=True, slots=True)
class ScreeningCorpusPayload:
    """Bounded-memory train/dev payload with no test or test2 path."""

    corpus_root: Path
    cache_root: Path
    manifest: ScreeningCorpusCacheManifest
    train_candidates: tuple[HarnessCandidate, ...]
    raw_relation_inventory: RawRelationInventory

    @property
    def development_shards(self) -> tuple[CandidateShard, ...]:
        return tuple(
            shard for shard in self.manifest.shards if shard.partition == CorpusPartition.DEV
        )

    @property
    def training_shards(self) -> tuple[CandidateShard, ...]:
        return tuple(
            shard for shard in self.manifest.shards if shard.partition == CorpusPartition.TRAIN
        )

    def load_document(self, shard: CandidateShard) -> HarnessDocument:
        if shard not in self.manifest.shards:
            raise ValueError("requested document is not a governed screening shard")
        document, analysis = self.load_analysis(shard)
        candidate_path = self.cache_root / shard.candidate_path
        candidates = tuple(_iter_candidate_file(candidate_path))
        if len(candidates) != shard.candidate_count:
            raise ValueError(f"screening candidate count changed: {shard.document_id}")
        return HarnessDocument(
            shard=shard,
            document=document,
            gold_analysis=analysis,
            candidates=candidates,
        )

    def load_analysis(self, shard: CandidateShard) -> tuple[RstDocument, RstAnalysis]:
        if shard not in self.manifest.shards:
            raise ValueError("requested analysis is not a governed screening shard")
        source = (self.corpus_root / shard.source_path).resolve()
        if not source.is_relative_to(self.corpus_root) or source.is_symlink():
            raise ValueError(f"unsafe screening source: {shard.document_id}")
        source_bytes = source.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != shard.source_sha256:
            raise ValueError(f"screening source hash changed: {shard.document_id}")
        document, analysis = rs4_to_document_and_analysis(
            RS4Reader.read_string(source_bytes.decode("utf-8")),
            document_id=shard.document_id,
        )
        return document, analysis

    def load_development_document(self, shard: CandidateShard) -> HarnessDocument:
        if shard.partition != CorpusPartition.DEV or shard not in self.development_shards:
            raise ValueError("requested document is not a governed development shard")
        return self.load_document(shard)

    def load_candidate_shard(self, shard: CandidateShard) -> tuple[HarnessCandidate, ...]:
        if shard not in self.manifest.shards:
            raise ValueError("requested candidate shard is not governed")
        path = self.cache_root / shard.candidate_path
        if not path.is_file() or _sha256_file(path) != shard.candidate_sha256:
            raise ValueError(f"candidate shard hash changed: {shard.document_id}")
        candidates = tuple(_iter_candidate_file(path))
        if len(candidates) != shard.candidate_count:
            raise ValueError(f"candidate shard count changed: {shard.document_id}")
        return candidates

    def for_ablation(self, name: AblationName, *, seed: int) -> "ScreeningCorpusPayload":
        train = (
            self._uniform_train_candidates(seed=seed)
            if name == AblationName.HARD_NEGATIVES
            else self.train_candidates
        )
        return AblatedScreeningCorpusPayload(
            corpus_root=self.corpus_root,
            cache_root=self.cache_root,
            manifest=self.manifest,
            train_candidates=tuple(_ablate_candidate(item, name, self.raw_relation_inventory) for item in train),
            raw_relation_inventory=self.raw_relation_inventory,
            ablation=name,
        )

    def _uniform_train_candidates(self, *, seed: int) -> tuple[HarnessCandidate, ...]:
        positive_limit = self.manifest.selected_train_positive_count
        negative_limit = self.manifest.selected_train_count - positive_limit
        positives: list[HarnessCandidate] = []
        negative_heap: list[_RankedNegative] = []
        for shard in self.training_shards:
            for item in self.load_candidate_shard(shard):
                candidate = item.candidate
                if candidate.is_gold_edge:
                    positives.append(item)
                    continue
                identity = (
                    f"{seed}\0{candidate.document_id}\0{candidate.source_id}\0"
                    f"{candidate.target_id}\0{'|'.join(candidate.signal_ids)}"
                )
                digest = hashlib.sha256(identity.encode()).hexdigest()
                ranked = _RankedNegative(f"{digest}\0{identity}", item)
                if len(negative_heap) < negative_limit:
                    heapq.heappush(negative_heap, ranked)
                elif ranked.key < negative_heap[0].key:
                    heapq.heapreplace(negative_heap, ranked)
        if len(positives) != positive_limit or len(negative_heap) != negative_limit:
            raise ValueError("uniform ablation sample does not reconcile with governed train counts")
        selected = (*positives, *(ranked.item for ranked in negative_heap))
        return tuple(
            sorted(
                selected,
                key=lambda item: (
                    item.candidate.document_id,
                    item.candidate.source_id,
                    item.candidate.target_id,
                    item.candidate.signal_ids,
                ),
            )
        )


@dataclass(frozen=True, slots=True)
class AblatedScreeningCorpusPayload(ScreeningCorpusPayload):
    """Feature-intervened view retaining identical governed candidate membership."""

    ablation: AblationName

    def load_development_document(self, shard: CandidateShard) -> HarnessDocument:
        loaded = super().load_development_document(shard)
        return replace(
            loaded,
            candidates=tuple(
                _ablate_candidate(item, self.ablation, self.raw_relation_inventory)
                for item in loaded.candidates
            ),
        )


@dataclass(frozen=True, slots=True)
class _RankedNegative:
    key: str
    item: HarnessCandidate

    def __lt__(self, other: "_RankedNegative") -> bool:
        return self.key > other.key


def _ablate_candidate(
    item: HarnessCandidate,
    name: AblationName,
    inventory: RawRelationInventory,
) -> HarnessCandidate:
    candidate = item.candidate
    updates: dict[str, object] = {}
    spans = item.signal_char_spans
    if name == AblationName.SIGNAL_MARKING:
        spans = ()
    elif name == AblationName.STRUCTURAL_FEATURES:
        updates["structural_features"] = (0.0,) * len(candidate.structural_features)
    elif name == AblationName.PRIMARY_PATH_ENCODING:
        updates["primary_path"] = ()
    elif name == AblationName.CONTEXT:
        updates.update(
            source_head_text=candidate.source_text,
            target_head_text=candidate.target_text,
            source_sentence_ids=(),
            target_sentence_ids=(),
        )
    elif name == AblationName.RAW_VS_COARSE_LABELS and candidate.gold_concept is not None:
        representatives: dict[str, str] = {}
        for raw_relation in inventory.labels:
            concept = inventory.concept_by_raw[raw_relation]
            current = representatives.get(concept)
            if current is None or (
                inventory.label_counts[raw_relation],
                raw_relation,
            ) > (
                inventory.label_counts[current],
                current,
            ):
                representatives[concept] = raw_relation
        updates["gold_relation"] = representatives[candidate.gold_concept]
    return HarnessCandidate(
        candidate=replace(candidate, **updates),
        signal_char_spans=spans,
    )


@dataclass(frozen=True, slots=True)
class _DescendingHardness:
    key: tuple[int, int, int, int, str]

    def __lt__(self, other: "_DescendingHardness") -> bool:
        return self.key > other.key


def _hardness_key(candidate: SecondaryEdgeCandidate, *, seed: int) -> tuple[int, int, int, int, str]:
    tie_break = hashlib.sha256(
        (
            f"{seed}\0{candidate.document_id}\0{candidate.source_id}\0"
            f"{candidate.target_id}\0{'|'.join(candidate.signal_ids)}"
        ).encode()
    ).hexdigest()
    return (
        0 if candidate.compatible_relations else 1,
        0 if candidate.existing_primary_relation is not None else 1,
        abs(candidate.edu_distance),
        len(candidate.primary_path),
        tie_break,
    )


def _iter_candidate_file(path: Path) -> Iterator[HarnessCandidate]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                yield CandidateRecord.model_validate_json(line).to_harness_candidate()
            except ValueError as error:
                raise ValueError(f"invalid candidate record at {path.name}:{line_number}") from error


def _write_candidate_shard(
    *,
    corpus_root: Path,
    cache_root: Path,
    source_path: str,
    source_sha256: str,
    document_id: str,
    partition: CorpusPartition,
    license_class: CorpusLicenseClass,
    selected_negative_limit: int,
    sampling_seed: int,
    global_order_start: int,
    positive_records: list[tuple[int, HarnessCandidate]],
    negative_heap: list[tuple[_DescendingHardness, int, HarnessCandidate]],
) -> tuple[CandidateShard, int]:
    source = (corpus_root / source_path).resolve()
    if not source.is_relative_to(corpus_root) or not source.is_file() or source.is_symlink():
        raise ValueError(f"unsafe private corpus source: {document_id}")
    source_bytes = source.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source_sha256:
        raise ValueError(f"private corpus source hash changed: {document_id}")
    document, analysis = rs4_to_document_and_analysis(
        RS4Reader.read_string(source_bytes.decode("utf-8")),
        document_id=document_id,
    )
    relative_candidate_path = f"candidates/{partition.value}/{document_id}.jsonl"
    candidate_path = cache_root / relative_candidate_path
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = candidate_path.with_suffix(".jsonl.tmp")
    if candidate_path.exists() or temporary.exists():
        raise RuntimeError(f"candidate cache path already exists: {relative_candidate_path}")
    candidate_count = 0
    positive_count = 0
    current_order = global_order_start
    signal_spans_by_id = {
        signal.signal_id: signal.char_spans for signal in analysis.signals
    }
    with temporary.open("w", encoding="utf-8") as stream:
        for candidate in iter_secondary_edge_candidates(document, analysis):
            signal_char_spans = tuple(
                span
                for signal_id in candidate.signal_ids
                for span in signal_spans_by_id[signal_id]
            )
            harness_candidate = HarnessCandidate(
                candidate=candidate,
                signal_char_spans=signal_char_spans,
            )
            stream.write(
                CandidateRecord.from_candidate(candidate, signal_char_spans).model_dump_json()
                + "\n"
            )
            candidate_count += 1
            if partition == CorpusPartition.TRAIN:
                if candidate.is_gold_edge:
                    positive_records.append((current_order, harness_candidate))
                    positive_count += 1
                else:
                    item = (
                        _DescendingHardness(_hardness_key(candidate, seed=sampling_seed)),
                        current_order,
                        harness_candidate,
                    )
                    if len(negative_heap) < selected_negative_limit:
                        heapq.heappush(negative_heap, item)
                    elif item[0].key < negative_heap[0][0].key:
                        heapq.heapreplace(negative_heap, item)
            current_order += 1
    if candidate_count <= 0:
        temporary.unlink()
        raise ValueError(f"private corpus document produced zero candidates: {document_id}")
    temporary.replace(candidate_path)
    return (
        CandidateShard(
            document_id=document_id,
            partition=partition,
            license_class=license_class,
            source_path=source_path,
            source_sha256=source_sha256,
            candidate_path=relative_candidate_path,
            candidate_sha256=_sha256_file(candidate_path),
            candidate_count=candidate_count,
            positive_count=positive_count,
            signal_count=len(analysis.signals),
        ),
        current_order,
    )


def _write_selected_train(
    *,
    cache_root: Path,
    selected: tuple[HarnessCandidate, ...],
) -> tuple[str, str]:
    relative_path = "selected/train.jsonl"
    path = cache_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".jsonl.tmp")
    if path.exists() or temporary.exists():
        raise RuntimeError("selected train cache already exists")
    with temporary.open("w", encoding="utf-8") as stream:
        for candidate in selected:
            stream.write(
                CandidateRecord.from_candidate(
                    candidate.candidate,
                    candidate.signal_char_spans,
                ).model_dump_json()
                + "\n"
            )
    temporary.replace(path)
    return relative_path, _sha256_file(path)


def _validate_cache_files(cache_root: Path, manifest: ScreeningCorpusCacheManifest) -> None:
    for shard in manifest.shards:
        path = cache_root / shard.candidate_path
        if not path.is_file() or _sha256_file(path) != shard.candidate_sha256:
            raise ValueError(f"candidate cache shard failed hash verification: {shard.document_id}")
    selected = cache_root / manifest.selected_train_path
    if not selected.is_file() or _sha256_file(selected) != manifest.selected_train_sha256:
        raise ValueError("selected train cache failed hash verification")


def _build_cache(
    *,
    corpus_root: Path,
    cache_root: Path,
    verification: PrivateCorpusVerificationReceipt,
    relation_inventory: RawRelationInventory,
    sampling: HardNegativeSamplingConfig,
) -> ScreeningCorpusCacheManifest:
    cache_root.mkdir(parents=True, exist_ok=False)
    allowed_sources = tuple(
        source
        for source in verification.sources
        if source.partition in (CorpusPartition.TRAIN, CorpusPartition.DEV)
    )
    if not allowed_sources:
        raise ValueError("private corpus verification contains no train/dev sources")
    selected_negative_limit = math.floor(
        relation_inventory.edge_count * sampling.negative_to_positive_ratio
    )
    positive_records: list[tuple[int, HarnessCandidate]] = []
    negative_heap: list[tuple[_DescendingHardness, int, HarnessCandidate]] = []
    shards: list[CandidateShard] = []
    global_order = 0
    for source in allowed_sources:
        shard, global_order = _write_candidate_shard(
            corpus_root=corpus_root,
            cache_root=cache_root,
            source_path=source.source_path,
            source_sha256=source.source_sha256,
            document_id=source.document_id,
            partition=source.partition,
            license_class=source.license_class,
            selected_negative_limit=selected_negative_limit,
            sampling_seed=sampling.seed,
            global_order_start=global_order,
            positive_records=positive_records,
            negative_heap=negative_heap,
        )
        shards.append(shard)
    if len(positive_records) != relation_inventory.edge_count:
        raise ValueError(
            "streamed train positives do not reconcile with the raw relation inventory: "
            f"{len(positive_records)} != {relation_inventory.edge_count}"
        )
    selected_records = sorted(
        (*positive_records, *((order, candidate) for _, order, candidate in negative_heap)),
        key=lambda item: item[0],
    )
    selected = tuple(candidate for _, candidate in selected_records)
    selected_path, selected_sha256 = _write_selected_train(cache_root=cache_root, selected=selected)
    manifest = ScreeningCorpusCacheManifest(
        private_receipt_sha256=verification.receipt_sha256,
        sampling_config_sha256=sampling.config_sha256,
        raw_relation_inventory_sha256=relation_inventory.inventory_sha256,
        shards=tuple(shards),
        selected_train_path=selected_path,
        selected_train_sha256=selected_sha256,
        selected_train_count=len(selected),
        selected_train_positive_count=len(positive_records),
        complete_dev_count=sum(
            shard.candidate_count for shard in shards if shard.partition == CorpusPartition.DEV
        ),
    )
    (cache_root / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _data_identity(
    manifest: ScreeningCorpusCacheManifest,
    train_candidates: tuple[HarnessCandidate, ...],
) -> ExperimentDataIdentity:
    selected_train_counts: dict[str, int] = {}
    for harness_candidate in train_candidates:
        document_id = harness_candidate.candidate.document_id
        selected_train_counts[document_id] = selected_train_counts.get(document_id, 0) + 1
    documents = tuple(
        ExperimentDocumentIdentity(
            document_id=shard.document_id,
            source_sha256=shard.source_sha256,
            partition=shard.partition,
            candidate_count=(
                selected_train_counts[shard.document_id]
                if shard.partition == CorpusPartition.TRAIN
                else shard.candidate_count
            ),
        )
        for shard in manifest.shards
        if shard.partition == CorpusPartition.DEV or shard.document_id in selected_train_counts
    )
    scored_document_ids = tuple(
        shard.document_id for shard in manifest.shards if shard.partition == CorpusPartition.DEV
    )
    selection_sha256 = hashlib.sha256(
        (
            manifest.selected_train_sha256
            + "".join(
                shard.candidate_sha256
                for shard in manifest.shards
                if shard.partition == CorpusPartition.DEV
            )
            + manifest.sampling_config_sha256
        ).encode()
    ).hexdigest()
    return ExperimentDataIdentity(
        split_manifest_sha256=manifest.split_manifest_sha256,
        candidate_selection_sha256=selection_sha256,
        partitions=(CorpusPartition.TRAIN, CorpusPartition.DEV),
        documents=documents,
        scored_document_ids=scored_document_ids,
        candidate_count=len(train_candidates) + manifest.complete_dev_count,
    )


def prepare_screening_corpus(
    *,
    corpus_root: Path,
    verification_receipt_path: Path,
    relation_inventory_path: Path,
    cache_root: Path,
    sampling_seed: int = 17,
    negative_to_positive_ratio: float = 4.0,
) -> PreparedExperimentData[ScreeningCorpusPayload]:
    """Build or verify the bounded cache while reading no test/test2 source text."""

    corpus_root = corpus_root.resolve()
    cache_root = cache_root.resolve()
    verification = PrivateCorpusVerificationReceipt.model_validate_json(
        verification_receipt_path.read_text(encoding="utf-8")
    )
    relation_inventory = RawRelationInventory.model_validate_json(
        relation_inventory_path.read_text(encoding="utf-8")
    )
    if relation_inventory.corpus_revision != verification.corpus_revision:
        raise ValueError("raw relation inventory belongs to a different corpus revision")
    sampling = HardNegativeSamplingConfig(
        negative_to_positive_ratio=negative_to_positive_ratio,
        seed=sampling_seed,
    )
    manifest_path = cache_root / "manifest.json"
    if manifest_path.exists():
        manifest = ScreeningCorpusCacheManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        expected = (
            verification.receipt_sha256,
            sampling.config_sha256,
            relation_inventory.inventory_sha256,
        )
        observed = (
            manifest.private_receipt_sha256,
            manifest.sampling_config_sha256,
            manifest.raw_relation_inventory_sha256,
        )
        if observed != expected:
            raise ValueError("screening corpus cache belongs to different governed inputs")
        _validate_cache_files(cache_root, manifest)
    elif cache_root.exists():
        raise ValueError("screening corpus cache exists without a complete manifest")
    else:
        manifest = _build_cache(
            corpus_root=corpus_root,
            cache_root=cache_root,
            verification=verification,
            relation_inventory=relation_inventory,
            sampling=sampling,
        )
    train_candidates = tuple(_iter_candidate_file(cache_root / manifest.selected_train_path))
    if len(train_candidates) != manifest.selected_train_count:
        raise ValueError("selected train candidate count does not match its cache manifest")
    payload = ScreeningCorpusPayload(
        corpus_root=corpus_root,
        cache_root=cache_root,
        manifest=manifest,
        train_candidates=train_candidates,
        raw_relation_inventory=relation_inventory,
    )
    return PreparedExperimentData(
        identity=_data_identity(manifest, train_candidates),
        payload=payload,
    )


__all__ = [
    "CORPUS_CACHE_SCHEMA_VERSION",
    "CandidateRecord",
    "CandidateShard",
    "HarnessCandidate",
    "HarnessDocument",
    "ScreeningCorpusCacheManifest",
    "ScreeningCorpusPayload",
    "prepare_screening_corpus",
]
