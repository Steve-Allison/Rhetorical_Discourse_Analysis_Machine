"""Paired document-bootstrap comparisons of compatible exact-count evaluations.

Resampling keeps each document's gold and predicted denominators together. It
estimates uncertainty over documents, not independent attachment trials. A test
split label does not establish independence from model training.
"""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from rdam._output import OutputDestination


@dataclass(frozen=True, slots=True)
class Counts:
    gold: int
    predicted: int
    matched: int

    def __post_init__(self) -> None:
        if any(type(value) is not int or value < 0 for value in (self.gold, self.predicted, self.matched)):
            raise ValueError("evaluation counts must be nonnegative integers")
        if self.matched > min(self.gold, self.predicted):
            raise ValueError("matched count exceeds an attachment denominator")


def paired_f1(
    reference: tuple[Counts, ...], candidate: tuple[Counts, ...],
    *, confidence: float, resamples: int, seed: int,
) -> dict[str, Any]:
    if not reference or len(reference) != len(candidate):
        raise ValueError("paired evaluation requires matching nonempty document sets")
    if any(left.gold != right.gold for left, right in zip(reference, candidate, strict=True)):
        raise ValueError("paired documents must have identical gold counts")
    if isinstance(confidence, bool) or not math.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between zero and one")
    if type(resamples) is not int or resamples < 2 or type(seed) is not int or seed < 0:
        raise ValueError("resampling requires at least two draws and a nonnegative integer seed")
    if any(item.gold + item.predicted == 0 for item in (*reference, *candidate)):
        raise ValueError("F1 resampling is undefined for a document with no gold or predicted attachments")

    def f1(rows: tuple[Counts, ...]) -> float:
        return 2 * sum(item.matched for item in rows) / sum(item.gold + item.predicted for item in rows)

    left = np.array([(item.matched, item.gold + item.predicted) for item in reference], dtype=np.int64)
    right = np.array([(item.matched, item.gold + item.predicted) for item in candidate], dtype=np.int64)
    rng = np.random.Generator(np.random.PCG64(seed))
    differences = np.empty(resamples, dtype=np.float64)
    for draw in range(resamples):
        indexes = rng.integers(len(reference), size=len(reference))
        left_total, right_total = left[indexes].sum(axis=0), right[indexes].sum(axis=0)
        differences[draw] = 2 * right_total[0] / right_total[1] - 2 * left_total[0] / left_total[1]
    tail = (1.0 - confidence) / 2.0
    lower, upper = np.quantile(differences, (tail, 1.0 - tail), method="linear")
    return {
        "documents": len(reference), "reference_f1": f1(reference), "candidate_f1": f1(candidate),
        "candidate_minus_reference": f1(candidate) - f1(reference),
        "paired_document_percentile_interval": {"lower": float(lower), "upper": float(upper)},
    }


def compare_files(reference: Path, candidate: Path, *, confidence: float, resamples: int, seed: int) -> dict[str, Any]:
    raw = (reference.read_bytes(), candidate.read_bytes())
    before, after = (json.loads(value) for value in raw)
    for key in ("evaluation", "evaluation_sources", "upstream_manifest_sha256"):
        if before[key] != after[key]:
            raise ValueError(f"evaluation conditions differ: {key}")
    if before["model"]["gold_edu_boundaries"] != after["model"]["gold_edu_boundaries"]:
        raise ValueError("gold and predicted segmentation conditions cannot be paired")
    left, right = before["documents"], after["documents"]
    if not left or left.keys() != right.keys():
        raise ValueError("evaluation document identities differ")
    for name in left:
        for key in ("fixture_sha256", "split"):
            if left[name][key] != right[name][key]:
                raise ValueError(f"paired document provenance differs: {name}/{key}")
    splits: dict[str, Any] = {}
    for split in sorted({item["split"] for item in left.values()}):
        names = tuple(sorted(name for name in left if left[name]["split"] == split))
        metrics = {}
        for metric in ("span", "nuclearity", "relation", "full"):
            pairs = tuple(tuple(Counts(item[name]["observed"]["gold"], item[name]["observed"]["predicted"],
                                       item[name]["observed"][metric]) for name in names) for item in (left, right))
            metrics[metric] = paired_f1(*pairs, confidence=confidence, resamples=resamples, seed=seed)
        splits[split] = {"documents": names, "attachment_metrics": metrics}
    return {
        "schema_version": "rdam.rst.paired-comparison/v1", "evaluation": before["evaluation"],
        "inputs": [{"path": str(path.resolve()), "sha256": sha256(value).hexdigest(), "model": data["model"],
                    "model_training_overlap": data["model_training_overlap"]}
                   for path, value, data in zip((reference, candidate), raw, (before, after), strict=True)],
        "resampling": {"unit": "document", "method": "paired_percentile_bootstrap", "confidence": confidence,
                       "resamples": resamples, "seed": seed, "rng": "PCG64", "numpy": np.__version__,
                       "quantile_method": "linear", "comparison_source_sha256": sha256(Path(__file__).read_bytes()).hexdigest()},
        "split_results": splits,
        "limitations": ["Intervals condition on these corpus annotations and fixed model checkpoints.",
                        "They do not measure training-seed variability or establish training isolation."],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confidence", type=float, required=True)
    parser.add_argument("--resamples", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    destination = OutputDestination(args.output, force=args.force, inputs=(args.reference, args.candidate))
    destination.validate()
    result = compare_files(args.reference, args.candidate, confidence=args.confidence,
                           resamples=args.resamples, seed=args.seed)
    destination.publish((json.dumps(result, indent=2, allow_nan=False) + "\n").encode())


if __name__ == "__main__":
    main()
