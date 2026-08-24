"""Deterministic training-only hard-negative selection after official partitioning."""

from dataclasses import dataclass
import hashlib
import heapq
import math

from isanlp_rst.contracts.erst import (
    CandidateDocumentSelection,
    CandidateSelectionReceipt,
    CorpusPartition,
    HardNegativeSamplingConfig,
)
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate
from isanlp_rst.erst.corpus import LoadedGumCorpus


def _candidate_identity(candidate: SecondaryEdgeCandidate) -> tuple[str, int, int, tuple[str, ...]]:
    return (
        candidate.document_id,
        candidate.source_id,
        candidate.target_id,
        candidate.signal_ids,
    )


def candidate_identity_sha256(candidates: tuple[SecondaryEdgeCandidate, ...]) -> str:
    digest = hashlib.sha256()
    for candidate in candidates:
        document_id, source_id, target_id, signal_ids = _candidate_identity(candidate)
        digest.update(document_id.encode())
        digest.update(f"\0{source_id}\0{target_id}\0".encode())
        digest.update("\0".join(signal_ids).encode())
        digest.update(b"\n")
    return digest.hexdigest()


def _hardness_key(
    candidate: SecondaryEdgeCandidate,
    *,
    seed: int,
) -> tuple[int, int, int, int, str]:
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


def _document_selection(
    document_id: str,
    complete: tuple[SecondaryEdgeCandidate, ...],
    selected: tuple[SecondaryEdgeCandidate, ...],
) -> CandidateDocumentSelection:
    complete_positive = sum(candidate.is_gold_edge for candidate in complete)
    selected_positive = sum(candidate.is_gold_edge for candidate in selected)
    return CandidateDocumentSelection(
        document_id=document_id,
        complete_count=len(complete),
        selected_count=len(selected),
        positive_count=complete_positive,
        selected_positive_count=selected_positive,
        negative_count=len(complete) - complete_positive,
        selected_negative_count=len(selected) - selected_positive,
    )


@dataclass(frozen=True, slots=True)
class PartitionedCandidateSelection:
    """Candidate tuples and receipts indexed without test-time resampling."""

    train: tuple[SecondaryEdgeCandidate, ...]
    dev: tuple[SecondaryEdgeCandidate, ...]
    test: tuple[SecondaryEdgeCandidate, ...]
    test2: tuple[SecondaryEdgeCandidate, ...]
    receipts: tuple[CandidateSelectionReceipt, ...]

    def for_partition(self, partition: CorpusPartition) -> tuple[SecondaryEdgeCandidate, ...]:
        """Return one exact partition."""

        return {
            CorpusPartition.TRAIN: self.train,
            CorpusPartition.DEV: self.dev,
            CorpusPartition.TEST: self.test,
            CorpusPartition.TEST2: self.test2,
        }[partition]


def prepare_partition_candidates(
    corpus: LoadedGumCorpus,
    *,
    hard_negative_config: HardNegativeSamplingConfig,
) -> PartitionedCandidateSelection:
    """Assign by document first, sample train only, and retain complete evaluation candidates."""

    if not corpus.receipt.succeeded:
        raise ValueError("candidate partitioning requires a successful corpus load receipt")

    documents_by_partition = {
        partition: tuple(
            document for document in corpus.documents if document.receipt.partition == partition
        )
        for partition in CorpusPartition
    }
    complete_by_partition = {
        partition: tuple(
            candidate
            for document in documents_by_partition[partition]
            for candidate in document.candidates
        )
        for partition in CorpusPartition
    }
    train_complete = complete_by_partition[CorpusPartition.TRAIN]
    if not train_complete:
        raise ValueError("official train partition contains zero candidates")
    positives = tuple(candidate for candidate in train_complete if candidate.is_gold_edge)
    if not positives:
        raise ValueError("official train partition contains zero positive secondary edges")
    negatives = tuple(candidate for candidate in train_complete if not candidate.is_gold_edge)
    maximum_negatives = math.floor(
        len(positives) * hard_negative_config.negative_to_positive_ratio
    )
    chosen_negatives = tuple(
        heapq.nsmallest(
            min(maximum_negatives, len(negatives)),
            negatives,
            key=lambda candidate: _hardness_key(candidate, seed=hard_negative_config.seed),
        )
    )
    selected_identities = {_candidate_identity(candidate) for candidate in (*positives, *chosen_negatives)}
    train_selected = tuple(
        candidate
        for candidate in train_complete
        if _candidate_identity(candidate) in selected_identities
    )
    selected_by_partition = {
        **complete_by_partition,
        CorpusPartition.TRAIN: train_selected,
    }

    receipts: list[CandidateSelectionReceipt] = []
    for partition in CorpusPartition:
        complete = complete_by_partition[partition]
        selected = selected_by_partition[partition]
        per_document = tuple(
            _document_selection(
                document.receipt.document_id,
                document.candidates,
                tuple(
                    candidate
                    for candidate in selected
                    if candidate.document_id == document.receipt.document_id
                ),
            )
            for document in documents_by_partition[partition]
        )
        receipts.append(
            CandidateSelectionReceipt(
                partition=partition,
                sampling_applied=partition == CorpusPartition.TRAIN,
                config_sha256=(
                    hard_negative_config.config_sha256
                    if partition == CorpusPartition.TRAIN
                    else None
                ),
                documents=per_document,
                complete_count=len(complete),
                selected_count=len(selected),
                selected_identity_sha256=candidate_identity_sha256(selected),
            )
        )
    return PartitionedCandidateSelection(
        train=selected_by_partition[CorpusPartition.TRAIN],
        dev=selected_by_partition[CorpusPartition.DEV],
        test=selected_by_partition[CorpusPartition.TEST],
        test2=selected_by_partition[CorpusPartition.TEST2],
        receipts=tuple(receipts),
    )


__all__ = [
    "PartitionedCandidateSelection",
    "candidate_identity_sha256",
    "prepare_partition_candidates",
]
