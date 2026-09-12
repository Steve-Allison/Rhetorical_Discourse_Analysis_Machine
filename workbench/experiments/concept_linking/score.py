"""Score frozen occurrence annotations using the same deterministic resolver."""
import json
from pathlib import Path
from time import perf_counter

from rdam.concepts import CandidateSpan, ConceptIndex, resolve_candidates
from rdam.ingest.contracts.preparation import ContentInventory


def main() -> None:
    root = Path(__file__).parent
    prepared = json.loads((root / "prepared.json").read_text())
    extracted = json.loads((root / "extracted.json").read_text())
    if prepared["gold_sha256"] != extracted["gold_sha256"]:
        raise ValueError("evaluation inputs differ")
    index = ConceptIndex.load()
    if index.identity.model_dump(mode="json") != prepared["ontology"]:
        raise ValueError("ontology changed during evaluation")
    gold = {}
    methods = {name: {} for name in ("baseline", "terms", "terms_and_names_diagnostic")}
    timings = {name: 0.0 for name in methods}
    for passage, experiment in zip(prepared["passages"], extracted["passages"], strict=True):
        if passage["id"] != experiment["id"]:
            raise ValueError("passage order differs")
        name = passage["id"]
        for expected in passage["annotations"]:
            gold[name, expected["start"], expected["end"]] = expected["target"]
        timings["baseline"] += passage["seconds"]
        for mention in passage["baseline"]["mentions"]:
            methods["baseline"][name, mention["start"], mention["end"]] = [c["resource"]["identifier"] for c in mention["candidates"]]
        inventory = ContentInventory.model_validate_json(json.dumps(passage["inventory"]))
        surface = passage["baseline"]["surfaces"][0]
        for method in ("terms", "terms_and_names_diagnostic"):
            spans = tuple(CandidateSpan(item_id=surface["item_id"], field_pointer=surface["field_pointer"],
                start=item["start"], end=item["end"], quote=item["quote"])
                for item in experiment["occurrences"] if method != "terms" or item["type"] == "term")
            started = perf_counter()
            result = resolve_candidates(inventory, index, spans)
            timings[method] += experiment["seconds"] + perf_counter() - started
            for mention in result.mentions:
                methods[method][name, mention.start, mention.end] = [c.resource.identifier for c in mention.candidates]
    metrics = {}
    canonical_gold = {key for key, target in gold.items() if target is not None}
    for name, predictions in methods.items():
        correct = predictions.keys() & gold.keys()
        candidate_correct = sum(gold[key] in predictions[key] for key in correct if gold[key] is not None)
        metrics[name] = {
            "predicted_mentions": len(predictions), "gold_mentions": len(gold), "true_positive_mentions": len(correct),
            "mention_precision": len(correct) / len(predictions) if predictions else None,
            "mention_recall": len(correct) / len(gold), "canonical_gold_mentions": len(canonical_gold),
            "correct_canonical_candidate_inclusions": candidate_correct,
            "canonical_candidate_recall": candidate_correct / len(canonical_gold),
            "ambiguous_mentions": sum(len(targets) > 1 for targets in predictions.values()),
            "spurious_mentions": len(predictions.keys() - gold.keys()),
            "spurious_canonical_candidates": sum(target != gold.get(key) for key, targets in predictions.items() for target in targets),
            "unmapped_mentions": sum(not targets for targets in predictions.values()),
            "additional_valid_mentions_over_baseline": len(correct - methods["baseline"].keys()),
            "seconds_excluding_initialization": timings[name],
            "occurrences": [{"passage": key[0], "start": key[1], "end": key[2], "candidates": targets,
                              "gold_target": gold.get(key), "gold_occurrence": key in gold}
                             for key, targets in sorted(predictions.items())],
        }
    output = {"gold_sha256": prepared["gold_sha256"], "ontology": prepared["ontology"], "metrics": metrics,
        "peak_rss_bytes": {"baseline_process": prepared["peak_rss_bytes"], "nlp_process": extracted["peak_rss_bytes"]},
        "nlp_initialization_seconds": extracted["initialization_seconds"],
        "offsets": {key: extracted[key] for key in ("verified_byte_offsets", "python_character_offset_counterexamples",
                                                   "position_preserving_whitespace_substitutions")}}
    (root / "metrics.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({name: {key: value for key, value in values.items() if key != "occurrences"}
                      for name, values in metrics.items()}, indent=2))


if __name__ == "__main__":
    main()
