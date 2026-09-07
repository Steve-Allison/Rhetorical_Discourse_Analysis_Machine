"""Measure rule-trigger locations on pinned gold tokens, without attachment claims."""

import argparse
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path

from rdam._output import OutputDestination
from rdam.rst.contracts.analysis import DiscourseSignal
from workbench.erst.converter import rs4_to_document_and_analysis
from workbench.erst.rs4 import RS4Reader
from workbench.erst.signals import RuleBasedSignalDetector


def location_counts(
    gold: Sequence[DiscourseSignal], predicted: Sequence[DiscourseSignal],
) -> dict[str, int]:
    """Exact token-set occurrence counts; caller must supply a shared token table.

    Repeated occurrences retain multiplicity. Unanchored gold signals are recorded
    separately because a lexical location detector cannot identify their location.
    Types and subtypes are compared literally; no taxonomy equivalence is invented.
    """
    anchored_gold = [signal for signal in gold if signal.token_ids]
    anchored_predicted = [signal for signal in predicted if signal.token_ids]
    gold_locations = Counter(tuple(sorted(signal.token_ids)) for signal in anchored_gold)
    predicted_locations = Counter(tuple(sorted(signal.token_ids)) for signal in anchored_predicted)
    gold_types = Counter((tuple(sorted(signal.token_ids)), signal.signal_type) for signal in anchored_gold)
    predicted_types = Counter((tuple(sorted(signal.token_ids)), signal.signal_type) for signal in anchored_predicted)
    gold_subtypes = Counter((tuple(sorted(signal.token_ids)), signal.signal_type, signal.signal_subtype)
                            for signal in anchored_gold)
    predicted_subtypes = Counter((tuple(sorted(signal.token_ids)), signal.signal_type, signal.signal_subtype)
                                 for signal in anchored_predicted)
    return {
        "gold_anchored": len(anchored_gold), "predicted_anchored": len(anchored_predicted),
        "gold_unanchored": len(gold) - len(anchored_gold),
        "predicted_unanchored": len(predicted) - len(anchored_predicted),
        "matched_location": (gold_locations & predicted_locations).total(),
        "matched_location_type": (gold_types & predicted_types).total(),
        "matched_location_type_subtype": (gold_subtypes & predicted_subtypes).total(),
    }


def evaluate(*, fixtures: Path, output: Path, force: bool = False) -> None:
    """Run the unchanged detector on every fixture in the pinned manifest."""
    manifest_path = fixtures / "upstream-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    paths = {name: fixtures / f"{name}.rs4" for name in sorted(manifest["fixtures"])}
    destination = OutputDestination(output, force=force, inputs=(manifest_path, *paths.values()))
    destination.validate()
    implementation_paths = (Path(__file__), Path(RuleBasedSignalDetector.detect.__code__.co_filename),
                            Path(rs4_to_document_and_analysis.__code__.co_filename))
    implementation = {str(path.resolve()): sha256(path.read_bytes()).hexdigest() for path in implementation_paths}
    detector = RuleBasedSignalDetector()
    documents: dict[str, object] = {}
    split_counts: dict[str, dict[str, Counter[str]]] = {}
    for name, path in paths.items():
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        fixture = manifest["fixtures"][name]
        split = fixture["split"]
        if digest != fixture["local_sha256"] or digest != fixture["upstream_sha256"]:
            raise ValueError(f"Fixture differs from the pinned source: {name}")
        if name not in manifest["splits"][split]:
            raise ValueError(f"Fixture split is inconsistent: {name}")
        rs4 = RS4Reader.read_string(raw.decode("utf-8"))
        document, analysis = rs4_to_document_and_analysis(rs4, document_id=name)
        repeated_token_references = 0
        annotation_status = Counter[str]()
        for signal in rs4.signals:
            repeated_token_references += len(signal.tokens) - len(set(signal.tokens))
            annotation_status[signal.status] += 1
            if any(token < 1 or token > len(document.tokens) for token in signal.tokens):
                raise ValueError(f"Gold signal has an out-of-range token: {name}")
        predicted = detector.detect(document).signals
        categories = sorted({signal.signal_type for signal in (*analysis.signals, *predicted)})
        counts = {category: location_counts(
            [signal for signal in analysis.signals if signal.signal_type == category],
            [signal for signal in predicted if signal.signal_type == category],
        ) for category in categories}
        counts["all"] = location_counts(analysis.signals, predicted)
        for category, values in counts.items():
            split_counts.setdefault(split, {}).setdefault(category, Counter()).update(values)
        documents[name] = {"source_sha256": digest, "split": split,
                           "reconstructed_text_sha256": sha256(document.text.encode()).hexdigest(),
                           "token_count": len(document.tokens), "counts": counts,
                           "annotation_status_counts": annotation_status,
                           "repeated_gold_token_references": repeated_token_references}
        if path.read_bytes() != raw:
            raise ValueError(f"Fixture changed during evaluation: {name}")
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Fixture manifest changed during evaluation")
    if any(sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in implementation.items()):
        raise ValueError("Evaluation implementation changed during evaluation")
    result = {
        "schema_version": "rdam.signal-location-evaluation/v1",
        "measured_at": datetime.now(UTC).isoformat(),
        "conditions": {"tokens": "gold_rs4_whitespace_tokens_on_reconstructed_text",
                       "matching": "exact_token_set_occurrences_with_multiplicity",
                       "type_mapping": "literal_native_labels_without_aliases",
                       "annotation_reference": "pinned_corpus_signals_not_independently_adjudicated",
                       "repeated_token_references": "set_membership_with_duplicate_count_recorded",
                       "attachment_evaluated": False, "end_to_end_tokenization_evaluated": False,
                       "unanchored_gold": "excluded_from_location_denominator_and_counted_separately"},
        "manifest_sha256": sha256(manifest_bytes).hexdigest(),
        "implementation_sha256": implementation,
        "detector": detector.provenance.model_dump(mode="json"),
        "documents": documents, "split_micro_counts": split_counts,
    }
    destination.publish((json.dumps(result, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({"output": str(output.resolve()), "documents": len(documents),
                      "split_micro_counts": split_counts}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    evaluate(fixtures=args.fixtures, output=args.output, force=args.force)


if __name__ == "__main__":
    main()
