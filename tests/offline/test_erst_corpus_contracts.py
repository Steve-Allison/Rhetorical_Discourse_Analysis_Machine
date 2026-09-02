"""Pydantic corpus receipt and split-manifest invariant tests."""

from pydantic import ValidationError
import pytest

from rdam.rst.contracts.erst import (
    CorpusDocumentReceipt,
    CorpusFailureType,
    CorpusLicenseClass,
    CorpusLoadFailure,
    CorpusLoadReceipt,
    CorpusPartition,
    SplitManifest,
)


def _document(
    document_id: str,
    source_sha256: str,
    partition: CorpusPartition,
) -> CorpusDocumentReceipt:
    return CorpusDocumentReceipt(
        document_id=document_id,
        source_path=f"rst/{document_id}.rs4",
        source_sha256=source_sha256,
        corpus_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
        partition=partition,
        license_class=CorpusLicenseClass.CC_BY,
        node_count=20,
        edu_count=10,
        primary_edge_count=19,
        candidate_count=12,
        secondary_edge_count=2,
        signal_count=3,
        raw_relation_inventory=("adversative-contrast", "elaboration-additional"),
    )


def test_receipt_round_trip_and_totals_are_validated() -> None:
    document = _document("GUM_academic_example", "a" * 64, CorpusPartition.TRAIN)
    failure = CorpusLoadFailure(
        source_path="rst/GUM_broken.rs4",
        failure_type=CorpusFailureType.INVALID_RS4,
        message="Missing body element",
        exception_type="ValueError",
    )
    receipt = CorpusLoadReceipt(
        corpus_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
        corpus_root_fingerprint="e" * 64,
        fail_on_error=False,
        documents=(document,),
        failures=(failure,),
        document_count=1,
        candidate_count=12,
        secondary_edge_count=2,
        signal_count=3,
        succeeded=False,
    )
    assert CorpusLoadReceipt.model_validate_json(receipt.model_dump_json()) == receipt


def test_split_manifest_rejects_duplicate_document_or_source_hash() -> None:
    first = _document("GUM_academic_one", "a" * 64, CorpusPartition.TRAIN)
    duplicate_hash = _document("GUM_news_two", "a" * 64, CorpusPartition.DEV)
    with pytest.raises(ValidationError, match="source SHA-256"):
        SplitManifest(
            corpus_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
            documents=(first, duplicate_hash),
            split_authority_sha256="f" * 64,
        )

    duplicate_id = _document("GUM_academic_one", "b" * 64, CorpusPartition.TEST)
    with pytest.raises(ValidationError, match="document ID"):
        SplitManifest(
            corpus_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
            documents=(first, duplicate_id),
            split_authority_sha256="f" * 64,
        )


def test_source_paths_must_be_relative_and_sanitized() -> None:
    with pytest.raises(ValidationError, match="relative"):
        CorpusDocumentReceipt(
            document_id="GUM_invalid",
            source_path="/private/corpus/GUM_invalid.rs4",
            source_sha256="c" * 64,
            corpus_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
            partition=CorpusPartition.TRAIN,
            license_class=CorpusLicenseClass.CC_BY,
            node_count=2,
            edu_count=1,
            primary_edge_count=1,
            candidate_count=1,
            secondary_edge_count=0,
            signal_count=1,
            raw_relation_inventory=(),
        )


def test_receipt_rejects_non_reconciling_counts_and_false_success() -> None:
    document = _document("GUM_academic_example", "d" * 64, CorpusPartition.TRAIN)
    with pytest.raises(ValidationError, match="candidate_count"):
        CorpusLoadReceipt(
            corpus_revision=document.corpus_revision,
            corpus_root_fingerprint="e" * 64,
            fail_on_error=True,
            documents=(document,),
            failures=(),
            document_count=1,
            candidate_count=11,
            secondary_edge_count=2,
            signal_count=3,
            succeeded=True,
        )
    with pytest.raises(ValidationError, match="failures"):
        CorpusLoadReceipt(
            corpus_revision=document.corpus_revision,
            corpus_root_fingerprint="e" * 64,
            fail_on_error=True,
            documents=(document,),
            failures=(
                CorpusLoadFailure(
                    source_path="rst/broken.rs4",
                    failure_type=CorpusFailureType.INVALID_RS4,
                    message="bad",
                    exception_type="ValueError",
                ),
            ),
            document_count=1,
            candidate_count=12,
            secondary_edge_count=2,
            signal_count=3,
            succeeded=True,
        )
