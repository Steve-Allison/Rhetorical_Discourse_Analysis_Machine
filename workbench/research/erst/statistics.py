"""Paired document bootstrap and Holm correction for eRST run receipts."""

from collections import defaultdict

import numpy as np

from workbench.research.erst.contracts import (
    ExperimentRunReceipt,
    ExperimentRunStatus,
    MandatoryExperimentSystem,
    StatisticalComparison,
)


def _mean_document_scores(
    receipts: tuple[ExperimentRunReceipt, ...],
    *,
    system: MandatoryExperimentSystem,
) -> tuple[tuple[str, ...], np.ndarray]:
    if not receipts:
        raise ValueError("statistical comparison requires at least one receipt per system")
    scores: dict[str, list[float]] = defaultdict(list)
    expected_ids: tuple[str, ...] | None = None
    protocol_sha256 = receipts[0].protocol_sha256
    candidate_selection_sha256 = receipts[0].candidate_selection_sha256
    for receipt in receipts:
        if receipt.status != ExperimentRunStatus.SUCCEEDED or receipt.system != system:
            raise ValueError("statistical comparison accepts only successful receipts for its system")
        if (
            receipt.protocol_sha256 != protocol_sha256
            or receipt.candidate_selection_sha256 != candidate_selection_sha256
        ):
            raise ValueError("statistical comparison receipts do not share governed inputs")
        document_ids = tuple(score.document_id for score in receipt.document_scores)
        if expected_ids is None:
            expected_ids = document_ids
        elif document_ids != expected_ids:
            raise ValueError("statistical comparison document ordering differs across seeds")
        for score in receipt.document_scores:
            scores[score.document_id].append(score.full_f)
    if expected_ids is None:
        raise ValueError("statistical comparison found no document scores")
    return expected_ids, np.asarray(
        [sum(scores[document_id]) / len(scores[document_id]) for document_id in expected_ids],
        dtype=np.float64,
    )


def compare_systems(
    *,
    candidate_receipts: tuple[ExperimentRunReceipt, ...],
    baseline_receipts: tuple[ExperimentRunReceipt, ...],
    bootstrap_seed: int,
    bootstrap_resamples: int = 10_000,
) -> StatisticalComparison:
    """Compute one unadjusted paired comparison from seed-mean document scores."""

    if bootstrap_resamples != 10_000:
        raise ValueError("canonical comparison requires exactly 10,000 bootstrap resamples")
    candidate_system = candidate_receipts[0].system if candidate_receipts else None
    baseline_system = baseline_receipts[0].system if baseline_receipts else None
    if candidate_system is None or baseline_system is None or candidate_system == baseline_system:
        raise ValueError("comparison requires two different non-empty systems")
    candidate_ids, candidate_scores = _mean_document_scores(
        candidate_receipts,
        system=candidate_system,
    )
    baseline_ids, baseline_scores = _mean_document_scores(
        baseline_receipts,
        system=baseline_system,
    )
    if candidate_ids != baseline_ids:
        raise ValueError("candidate and baseline document identities differ")
    if candidate_receipts[0].protocol_sha256 != baseline_receipts[0].protocol_sha256:
        raise ValueError("candidate and baseline belong to different protocols")
    differences = candidate_scores - baseline_scores
    generator = np.random.Generator(np.random.PCG64(bootstrap_seed))
    indices = generator.integers(
        0,
        len(differences),
        size=(bootstrap_resamples, len(differences)),
    )
    bootstrap_means = differences[indices].mean(axis=1)
    ci_lower, ci_upper = np.quantile(bootstrap_means, (0.025, 0.975), method="linear")
    non_positive = (int(np.count_nonzero(bootstrap_means <= 0.0)) + 1) / (bootstrap_resamples + 1)
    non_negative = (int(np.count_nonzero(bootstrap_means >= 0.0)) + 1) / (bootstrap_resamples + 1)
    raw_p_value = min(1.0, 2.0 * min(non_positive, non_negative))
    return StatisticalComparison(
        protocol_sha256=candidate_receipts[0].protocol_sha256,
        candidate_system=candidate_system,
        baseline_system=baseline_system,
        candidate_run_receipts=tuple(item.receipt_sha256 for item in candidate_receipts),
        baseline_run_receipts=tuple(item.receipt_sha256 for item in baseline_receipts),
        paired_document_ids=candidate_ids,
        paired_differences=tuple(float(value) for value in differences),
        mean_difference=float(np.mean(differences)),
        bootstrap_seed=bootstrap_seed,
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        raw_p_value=raw_p_value,
        holm_adjusted_p_value=raw_p_value,
    )


def holm_correct(comparisons: tuple[StatisticalComparison, ...]) -> tuple[StatisticalComparison, ...]:
    """Apply monotone Holm correction and preserve the caller's comparison order."""

    if not comparisons:
        raise ValueError("Holm correction requires at least one comparison")
    protocol_hashes = {item.protocol_sha256 for item in comparisons}
    if len(protocol_hashes) != 1:
        raise ValueError("Holm family contains multiple experiment protocols")
    ordered = sorted(enumerate(comparisons), key=lambda item: item[1].raw_p_value)
    adjusted_by_index: dict[int, float] = {}
    running = 0.0
    family_size = len(ordered)
    for rank, (original_index, comparison) in enumerate(ordered):
        adjusted = min(1.0, (family_size - rank) * comparison.raw_p_value)
        running = max(running, adjusted)
        adjusted_by_index[original_index] = running
    corrected: list[StatisticalComparison] = []
    for index, comparison in enumerate(comparisons):
        payload = comparison.model_dump(mode="json")
        payload["holm_adjusted_p_value"] = adjusted_by_index[index]
        payload["comparison_sha256"] = ""
        corrected.append(StatisticalComparison.model_validate(payload))
    return tuple(corrected)


__all__ = ["compare_systems", "holm_correct"]
