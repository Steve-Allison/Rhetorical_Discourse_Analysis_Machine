"""Fail-closed, receipt-backed loading for the private GUM/eRST corpus."""

from collections.abc import Iterable
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from lxml import etree
from pydantic import ValidationError

from isanlp_rst.contracts.analysis import RstAnalysis
from isanlp_rst.contracts.enums import NodeKindEnum
from isanlp_rst.contracts.erst import (
    CorpusAuthorityEntry,
    CorpusDocumentReceipt,
    CorpusFailureType,
    CorpusLicenseClass,
    CorpusLoadFailure,
    CorpusLoadReceipt,
    CorpusPartition,
    GumCorpusAuthority,
    SplitManifest,
)
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate, generate_secondary_edge_candidates
from isanlp_rst.erst.converter import rs4_to_document_and_analysis
from isanlp_rst.erst.rs4 import RS4Reader

GUM_CORPUS_REVISION = "22fdf87f9c71c96bcc771461d06e689b1f90020d"
GUM_SPLITS_SHA256 = "7a1b51ab332ae84d9693824ef067ec1dbfad4275111608231eb5e409437ea6d7"
GUM_LICENSE_SHA256 = "54ce03d1784ed081d6e829d811d41d3f25e35041df1afec14417590b18a70257"
GENTLE_LICENSE_REVISION = "fd7a1bfc82896e362c66f59492b5525940f52fa7"

_PARTITION_HEADING = re.compile(r"^##\s+(train|dev|test|test2)\s*$")
_DOCUMENT_BULLET = re.compile(r"^\s*\*\s+((?:GUM|GENTLE)_[a-z0-9]+_[a-z0-9]+)\s*$")
_LICENSE_MARKERS = (
    "Academic:",
    "Biographies:",
    "Court:",
    "Essays:",
    "Fiction:",
    "Letters:",
    "Podcasts:",
    "WikiHow:",
    "WikiVoyage:",
    "Wikinews/interviews:",
    "reddit:",
    "All annotations are licensed under the Creative Commons Attribution (CC-BY) version 4.0",
)
_ATTRIBUTION_GENRES = frozenset({"academic", "court", "interview", "news"})
_SHARE_ALIKE_GENRES = frozenset({"bio", "voyage"})
_NON_COMMERCIAL_GENRES = frozenset({"essay", "fiction", "letter", "podcast", "reddit", "whow"})


@dataclass(frozen=True, slots=True)
class LoadedCorpusDocument:
    """One document's candidates kept intact through partition assignment."""

    receipt: CorpusDocumentReceipt
    candidates: tuple[SecondaryEdgeCandidate, ...]


@dataclass(frozen=True, slots=True)
class LoadedGumCorpus:
    """Document-preserving payload plus serializable evidence boundaries."""

    documents: tuple[LoadedCorpusDocument, ...]
    receipt: CorpusLoadReceipt
    split_manifest: SplitManifest | None

    @property
    def candidates(self) -> tuple[SecondaryEdgeCandidate, ...]:
        """Flatten only after documents already have authoritative partitions."""

        return tuple(candidate for document in self.documents for candidate in document.candidates)


@dataclass(frozen=True, slots=True)
class _PreparedSource:
    path: Path
    relative_path: str
    document_id: str
    content: bytes
    sha256: str
    authority_entry: CorpusAuthorityEntry


class CorpusLoadError(RuntimeError):
    """Fail-closed error retaining a sanitized machine-readable receipt."""

    def __init__(self, receipt: CorpusLoadReceipt) -> None:
        super().__init__("GUM/eRST corpus load failed; inspect the sanitized receipt")
        self.receipt = receipt


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _license_class_for(document_id: str) -> CorpusLicenseClass:
    if document_id.startswith("GENTLE_"):
        return CorpusLicenseClass.NON_COMMERCIAL
    genre = document_id.split("_", maxsplit=2)[1]
    if genre in _ATTRIBUTION_GENRES:
        return CorpusLicenseClass.CC_BY
    if genre in _SHARE_ALIKE_GENRES:
        return CorpusLicenseClass.CC_BY_SA
    if genre in _NON_COMMERCIAL_GENRES:
        return CorpusLicenseClass.NON_COMMERCIAL
    return CorpusLicenseClass.RESTRICTED


def parse_gum_corpus_authority(
    splits_markdown: str,
    license_markdown: str,
    *,
    corpus_revision: str = GUM_CORPUS_REVISION,
    gentle_license_revision: str = GENTLE_LICENSE_REVISION,
) -> GumCorpusAuthority:
    """Parse exact document splits and conservative licence classes from pinned authority text."""

    missing_markers = tuple(marker for marker in _LICENSE_MARKERS if marker not in license_markdown)
    if missing_markers:
        raise ValueError(f"GUM licence inventory is missing required authority markers: {missing_markers!r}")

    current_partition: CorpusPartition | None = None
    seen_partitions: set[CorpusPartition] = set()
    entries: list[CorpusAuthorityEntry] = []
    for line in splits_markdown.splitlines():
        heading_match = _PARTITION_HEADING.fullmatch(line)
        if heading_match:
            current_partition = CorpusPartition(heading_match.group(1))
            seen_partitions.add(current_partition)
            continue
        document_match = _DOCUMENT_BULLET.fullmatch(line)
        if document_match:
            if current_partition is None:
                raise ValueError("GUM split authority names a document before any partition heading")
            document_id = document_match.group(1)
            entries.append(
                CorpusAuthorityEntry(
                    document_id=document_id,
                    partition=current_partition,
                    license_class=_license_class_for(document_id),
                )
            )
    missing_partitions = set(CorpusPartition).difference(seen_partitions)
    if missing_partitions:
        missing = ", ".join(sorted(partition.value for partition in missing_partitions))
        raise ValueError(f"GUM split authority is missing partitions: {missing}")
    return GumCorpusAuthority(
        corpus_revision=corpus_revision,
        splits_sha256=_sha256_bytes(splits_markdown.encode()),
        license_inventory_sha256=_sha256_bytes(license_markdown.encode()),
        gentle_license_revision=gentle_license_revision,
        entries=tuple(entries),
    )


def load_gum_corpus_authority(
    corpus_root: Path | str,
    *,
    verify_pinned_hashes: bool = True,
) -> GumCorpusAuthority:
    """Read and verify the authority files at a private GUM checkout root."""

    root = Path(corpus_root)
    splits_path = root / "splits.md"
    license_path = root / "LICENSE.md"
    splits_markdown = splits_path.read_text(encoding="utf-8")
    license_markdown = license_path.read_text(encoding="utf-8")
    authority = parse_gum_corpus_authority(splits_markdown, license_markdown)
    if verify_pinned_hashes and authority.splits_sha256 != GUM_SPLITS_SHA256:
        raise ValueError("splits.md does not match pinned GUM V12.1.0 authority")
    if verify_pinned_hashes and authority.license_inventory_sha256 != GUM_LICENSE_SHA256:
        raise ValueError("LICENSE.md does not match pinned GUM V12.1.0 authority")
    return authority


def _find_corpus_root(data_dir: Path) -> Path | None:
    candidates = (data_dir, *data_dir.parents)
    return next(
        (
            candidate
            for candidate in candidates
            if (candidate / "splits.md").is_file() and (candidate / "LICENSE.md").is_file()
        ),
        None,
    )


def _source_files(data_dir: Path, corpus_root: Path) -> tuple[Path, ...]:
    canonical_rst = corpus_root / "rst" / "rstweb"
    search_root = canonical_rst if data_dir == corpus_root and canonical_rst.is_dir() else data_dir
    return tuple(sorted(search_root.glob("**/*.rs4")))


def _relative_source_path(path: Path, corpus_root: Path) -> str:
    return path.relative_to(corpus_root).as_posix()


def _root_fingerprint(
    corpus_revision: str,
    sources: Iterable[tuple[str, str]],
) -> str:
    digest = hashlib.sha256()
    digest.update(corpus_revision.encode())
    for source_path, source_hash in sorted(sources):
        digest.update(b"\0")
        digest.update(source_path.encode())
        digest.update(b"\0")
        digest.update(source_hash.encode())
    return digest.hexdigest()


def _failure(
    failure_type: CorpusFailureType,
    *,
    exception_type: str,
    message: str,
    source_path: str | None = None,
    document_id: str | None = None,
) -> CorpusLoadFailure:
    return CorpusLoadFailure(
        source_path=source_path,
        document_id=document_id,
        failure_type=failure_type,
        message=message,
        exception_type=exception_type,
    )


def _document_receipt(
    *,
    source_path: str,
    source_sha256: str,
    authority_entry: CorpusAuthorityEntry,
    analysis: RstAnalysis,
    candidate_count: int,
    corpus_revision: str,
) -> CorpusDocumentReceipt:
    return CorpusDocumentReceipt(
        document_id=analysis.document_id,
        source_path=source_path,
        source_sha256=source_sha256,
        corpus_revision=corpus_revision,
        partition=authority_entry.partition,
        license_class=authority_entry.license_class,
        node_count=len(analysis.nodes),
        edu_count=sum(node.kind == NodeKindEnum.EDU for node in analysis.nodes),
        primary_edge_count=len(analysis.primary_edges),
        candidate_count=candidate_count,
        secondary_edge_count=len(analysis.secondary_edges),
        signal_count=len(analysis.signals),
        raw_relation_inventory=tuple(sorted({edge.relation_raw for edge in analysis.secondary_edges})),
    )


def _load_receipt(
    *,
    authority: GumCorpusAuthority,
    source_identities: list[tuple[str, str]],
    documents: list[CorpusDocumentReceipt],
    failures: list[CorpusLoadFailure],
    fail_on_error: bool,
) -> CorpusLoadReceipt:
    return CorpusLoadReceipt(
        corpus_revision=authority.corpus_revision,
        corpus_root_fingerprint=_root_fingerprint(authority.corpus_revision, source_identities),
        fail_on_error=fail_on_error,
        documents=tuple(documents),
        failures=tuple(failures),
        document_count=len(documents),
        candidate_count=sum(document.candidate_count for document in documents),
        secondary_edge_count=sum(document.secondary_edge_count for document in documents),
        signal_count=sum(document.signal_count for document in documents),
        succeeded=bool(documents) and not failures,
    )


def _empty_failure_receipt(
    *,
    failure: CorpusLoadFailure,
    fail_on_error: bool,
    corpus_revision: str = GUM_CORPUS_REVISION,
) -> CorpusLoadReceipt:
    return CorpusLoadReceipt(
        corpus_revision=corpus_revision,
        corpus_root_fingerprint=_root_fingerprint(corpus_revision, ()),
        fail_on_error=fail_on_error,
        documents=(),
        failures=(failure,),
        document_count=0,
        candidate_count=0,
        secondary_edge_count=0,
        signal_count=0,
        succeeded=False,
    )


def load_gum_erst_corpus_with_receipt(
    data_dir: Path | str,
    *,
    authority: GumCorpusAuthority | None = None,
    fail_on_error: bool = True,
) -> LoadedGumCorpus:
    """Load official documents with hashes, partitions, licences, and fail-closed evidence."""

    data_path = Path(data_dir)
    if not data_path.is_dir():
        receipt = _empty_failure_receipt(
            failure=_failure(
                CorpusFailureType.MISSING_CORPUS,
                exception_type="FileNotFoundError",
                message="Configured GUM/eRST corpus directory does not exist",
            ),
            fail_on_error=fail_on_error,
        )
        if fail_on_error:
            raise CorpusLoadError(receipt)
        return LoadedGumCorpus(documents=(), receipt=receipt, split_manifest=None)

    corpus_root = _find_corpus_root(data_path) or data_path
    if authority is None:
        if corpus_root == data_path and _find_corpus_root(data_path) is None:
            receipt = _empty_failure_receipt(
                failure=_failure(
                    CorpusFailureType.MISSING_AUTHORITY,
                    exception_type="FileNotFoundError",
                    message="GUM corpus root does not contain splits.md and LICENSE.md",
                ),
                fail_on_error=fail_on_error,
            )
            if fail_on_error:
                raise CorpusLoadError(receipt)
            return LoadedGumCorpus(documents=(), receipt=receipt, split_manifest=None)
        try:
            authority = load_gum_corpus_authority(corpus_root)
        except (OSError, UnicodeError, ValueError, ValidationError) as error:
            receipt = _empty_failure_receipt(
                failure=_failure(
                    CorpusFailureType.INVALID_AUTHORITY,
                    exception_type=type(error).__name__,
                    message="GUM split or licence authority failed pinned validation",
                ),
                fail_on_error=fail_on_error,
            )
            if fail_on_error:
                raise CorpusLoadError(receipt) from error
            return LoadedGumCorpus(documents=(), receipt=receipt, split_manifest=None)

    rs4_files = _source_files(data_path, corpus_root)
    if not rs4_files:
        receipt = _empty_failure_receipt(
            failure=_failure(
                CorpusFailureType.MISSING_CORPUS,
                exception_type="FileNotFoundError",
                message="Configured GUM/eRST directory contains no RS4 sources",
            ),
            fail_on_error=fail_on_error,
            corpus_revision=authority.corpus_revision,
        )
        if fail_on_error:
            raise CorpusLoadError(receipt)
        return LoadedGumCorpus(documents=(), receipt=receipt, split_manifest=None)

    loaded_documents: list[LoadedCorpusDocument] = []
    documents: list[CorpusDocumentReceipt] = []
    failures: list[CorpusLoadFailure] = []
    source_identities: list[tuple[str, str]] = []
    prepared_sources: list[_PreparedSource] = []
    seen_document_ids: set[str] = set()
    seen_source_hashes: set[str] = set()
    resolved_root = corpus_root.resolve()

    for source in rs4_files:
        document_id = source.stem
        source_path = _relative_source_path(source, corpus_root)
        if source.is_symlink() or not source.resolve().is_relative_to(resolved_root):
            failures.append(
                _failure(
                    CorpusFailureType.UNSAFE_SOURCE,
                    exception_type="ValueError",
                    message="Corpus source must be a regular file contained by the corpus root",
                    source_path=source_path,
                    document_id=document_id,
                )
            )
            continue
        try:
            source_bytes = source.read_bytes()
        except OSError as error:
            failures.append(
                _failure(
                    CorpusFailureType.INVALID_RS4,
                    exception_type=type(error).__name__,
                    message="RS4 source could not be read",
                    source_path=source_path,
                    document_id=document_id,
                )
            )
            continue
        source_sha256 = _sha256_bytes(source_bytes)
        source_identities.append((source_path, source_sha256))
        if document_id in seen_document_ids:
            failures.append(
                _failure(
                    CorpusFailureType.DUPLICATE_DOCUMENT,
                    exception_type="ValueError",
                    message="Document ID occurs more than once in corpus sources",
                    source_path=source_path,
                    document_id=document_id,
                )
            )
            continue
        seen_document_ids.add(document_id)
        if source_sha256 in seen_source_hashes:
            failures.append(
                _failure(
                    CorpusFailureType.DUPLICATE_SOURCE,
                    exception_type="ValueError",
                    message="Source bytes duplicate a different corpus document",
                    source_path=source_path,
                    document_id=document_id,
                )
            )
            continue
        seen_source_hashes.add(source_sha256)
        authority_entry = authority.entry_for(document_id)
        if authority_entry is None:
            failures.append(
                _failure(
                    CorpusFailureType.UNAUTHORIZED_DOCUMENT,
                    exception_type="ValueError",
                    message="Document ID is absent from the pinned split authority",
                    source_path=source_path,
                    document_id=document_id,
                )
            )
            continue
        prepared_sources.append(
            _PreparedSource(
                path=source,
                relative_path=source_path,
                document_id=document_id,
                content=source_bytes,
                sha256=source_sha256,
                authority_entry=authority_entry,
            )
        )

    if fail_on_error and failures:
        receipt = _load_receipt(
            authority=authority,
            source_identities=source_identities,
            documents=[],
            failures=failures,
            fail_on_error=True,
        )
        raise CorpusLoadError(receipt)

    for prepared in prepared_sources:
        try:
            rs4_document = RS4Reader.read_string(prepared.content.decode("utf-8"))
            document, analysis = rs4_to_document_and_analysis(
                rs4_document,
                document_id=prepared.document_id,
            )
            document_candidates = generate_secondary_edge_candidates(document, analysis)
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError, etree.XMLSyntaxError) as error:
            failures.append(
                _failure(
                    CorpusFailureType.INVALID_RS4,
                    exception_type=type(error).__name__,
                    message="RS4 parsing, validation, or conversion failed",
                    source_path=prepared.relative_path,
                    document_id=prepared.document_id,
                )
            )
            continue
        if not document_candidates:
            failures.append(
                _failure(
                    CorpusFailureType.ZERO_CANDIDATES,
                    exception_type="ValueError",
                    message="Document produced zero signal-sufficient candidates",
                    source_path=prepared.relative_path,
                    document_id=prepared.document_id,
                )
            )
            continue
        document_receipt = _document_receipt(
            source_path=prepared.relative_path,
            source_sha256=prepared.sha256,
            authority_entry=prepared.authority_entry,
            analysis=analysis,
            candidate_count=len(document_candidates),
            corpus_revision=authority.corpus_revision,
        )
        documents.append(document_receipt)
        loaded_documents.append(
            LoadedCorpusDocument(receipt=document_receipt, candidates=document_candidates)
        )

    receipt = _load_receipt(
        authority=authority,
        source_identities=source_identities,
        documents=documents,
        failures=failures,
        fail_on_error=fail_on_error,
    )
    manifest = (
        SplitManifest(
            corpus_revision=authority.corpus_revision,
            split_authority_sha256=authority.splits_sha256,
            documents=tuple(documents),
        )
        if documents
        else None
    )
    result = LoadedGumCorpus(
        documents=tuple(loaded_documents),
        receipt=receipt,
        split_manifest=manifest,
    )
    if fail_on_error and not receipt.succeeded:
        raise CorpusLoadError(receipt)
    return result


def load_gum_erst_corpus(
    data_dir: Path | str,
    *,
    authority: GumCorpusAuthority | None = None,
) -> list[SecondaryEdgeCandidate]:
    """Compatibility list API implemented as a strictly fail-closed wrapper."""

    result = load_gum_erst_corpus_with_receipt(
        data_dir,
        authority=authority,
        fail_on_error=True,
    )
    return list(result.candidates)


__all__ = [
    "GENTLE_LICENSE_REVISION",
    "GUM_CORPUS_REVISION",
    "GUM_LICENSE_SHA256",
    "GUM_SPLITS_SHA256",
    "CorpusLoadError",
    "LoadedCorpusDocument",
    "LoadedGumCorpus",
    "load_gum_corpus_authority",
    "load_gum_erst_corpus",
    "load_gum_erst_corpus_with_receipt",
    "parse_gum_corpus_authority",
]
