"""Generate an exact-count GUM regression reference; no accuracy acceptance floor.

Run as a module with explicit fixture, model-store, release and output paths.
The reference records mixed official splits and does not claim training isolation.
"""

import argparse
from collections import Counter
from enum import StrEnum
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path

from rdam._output import OutputDestination
from rdam.rst.contracts import NodeKindEnum, RstAnalysis, RstDocument
from workbench.erst.rs4 import RS4Reader
from rdam.rst.model_loading import load_model_release
from workbench.evaluation.rst.label_projection import gum_coarse_projection
from workbench.evaluation.rst.normalization import binarize_rs4
from workbench.evaluation.rst.parseval import ParsevalMetrics, SoftParsevalScorer, StandardParsevalScorer


class SegmentationMode(StrEnum):
    GOLD = "gold-edus"
    PREDICTED = "predicted-edus"


def segmentation_counts(gold: RstAnalysis, prediction: RstAnalysis) -> dict[str, dict[str, int]]:
    """Exact source-character EDU spans and internal end boundaries, without tolerance."""
    gold_spans = sorted(node.char_span for node in gold.nodes if node.kind == NodeKindEnum.EDU)
    predicted_spans = sorted(node.char_span for node in prediction.nodes if node.kind == NodeKindEnum.EDU)
    return {
        "edu_spans": {"gold": len(gold_spans), "predicted": len(predicted_spans),
                      "matched": (Counter(gold_spans) & Counter(predicted_spans)).total()},
        "internal_boundaries": {
            "gold": max(0, len(gold_spans) - 1), "predicted": max(0, len(predicted_spans) - 1),
            "matched": (Counter(end for _, end in gold_spans[:-1])
                        & Counter(end for _, end in predicted_spans[:-1])).total(),
        },
    }


def match_counts(metrics: ParsevalMetrics) -> dict[str, int]:
    """Integer counts are the authority; PRF values are derived from them."""
    return {
        "gold": metrics.gold_spans_count, "predicted": metrics.pred_spans_count,
        "span": metrics.matched_span, "nuclearity": metrics.matched_nuclearity,
        "relation": metrics.matched_relation, "full": metrics.matched_full,
    }


def evaluation_source_identities() -> dict[str, str]:
    """Bind the actual normalization, label projection and scoring implementation."""
    directory = Path(__file__).parent
    return {name: sha256((directory / name).read_bytes()).hexdigest()
            for name in ("normalization.py", "label_projection.py", "parseval.py", "regression.py")}


def generate_reference(
    *, fixtures: Path, model_store: Path, release_id: str, output: Path, force: bool,
    segmentation: SegmentationMode = SegmentationMode.GOLD,
    relinventory: str | None = None,
) -> None:
    from rdam.rst.parser import Parser

    implementation = evaluation_source_identities()
    manifest_path = fixtures / "upstream-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    upstream = json.loads(manifest_raw)
    names = sorted(upstream["fixtures"])
    paths = [fixtures / f"{name}.rs4" for name in names]
    source_bytes = {path: path.read_bytes() for path in paths}
    destination = OutputDestination(output, force=force, inputs=(manifest_path, *paths))
    destination.validate()
    release = load_model_release(model_store, release_id)
    family = Parser.family_for_runtime_contract(release.manifest.runtime_contract)
    if family == "unirst":
        if relinventory is None:
            raise ValueError("UniRST evaluation requires an explicit relation inventory")
        members = [member for member in release.manifest.files
                   if member.role == "relation-inventory" and str(member.path) == f"relation_table_{relinventory}.txt"]
        if len(members) != 1:
            raise ValueError("Selected UniRST inventory is not uniquely identified in the release")
        inventory_member = members[0]
    else:
        if relinventory is not None:
            raise ValueError("DMRST uses its released single inventory")
        inventory_member = release.one_file_for_role("relation-inventory")
    inventory = (release.path / inventory_member.path).read_text(encoding="utf-8").splitlines()
    parser = Parser.from_model_release(model_store, release_id, device="cpu", relinventory=relinventory)
    if list(parser.predictor.relation_table) != inventory:
        raise ValueError("Loaded parser inventory differs from the identified release member")
    documents: dict[str, object] = {}
    totals: dict[str, int] = {}
    split_totals: dict[str, dict[str, int]] = {}
    segmentation_totals: dict[str, dict[str, int]] = {}
    for name, path in zip(names, paths, strict=True):
        fixture = upstream["fixtures"][name]
        digest = sha256(source_bytes[path]).hexdigest()
        if digest != fixture["local_sha256"] or digest != fixture["upstream_sha256"]:
            raise ValueError(f"Fixture differs from pinned upstream: {name}")
        split = fixture["split"]
        if name not in upstream["splits"][split]:
            raise ValueError(f"Fixture split is inconsistent: {name}")
        rs4 = RS4Reader.read_string(source_bytes[path].decode("utf-8"))
        document, gold = binarize_rs4(rs4, document_id=name)
        edus = document.edus
        if edus is None:
            raise ValueError("Gold normalization did not preserve EDUs")
        if segmentation == SegmentationMode.GOLD:
            parser_input = RstDocument.from_edus([edu.text for edu in edus], document_id=name)
        else:
            parser_input = RstDocument.from_text(document.text, document_id=name)
            if parser_input.edus is not None:
                raise ValueError("End-to-end evaluation must not supply gold EDUs")
        if parser_input.text != document.text:
            raise ValueError("Evaluation input changed the source text")
        prediction = parser.parse_document(parser_input)
        # UniRST Appendix B explicitly harmonizes CONDITION and CONTINGENCY:
        # https://aclanthology.org/2025.codi-1.17/ . This is evaluation spelling,
        # not a Central ontology crosswalk or a rewrite of native predictions.
        aliases = {"condition": "contingency"} if relinventory == "eng.erst.gum" else None
        projection = gum_coarse_projection(tuple(rs4.relations), inventory, native_aliases=aliases)
        scorer = (StandardParsevalScorer(label_mapper=projection.__getitem__) if segmentation == SegmentationMode.GOLD
                  else SoftParsevalScorer(label_mapper=projection.__getitem__))
        counts = match_counts(scorer.score(gold, prediction))
        document_result: dict[str, object] = {"fixture_sha256": digest, "split": split, "observed": counts}
        if segmentation == SegmentationMode.PREDICTED:
            segmented = segmentation_counts(gold, prediction)
            document_result["segmentation"] = segmented
            for kind, values in segmented.items():
                kind_totals = segmentation_totals.setdefault(kind, {})
                for key, count in values.items():
                    kind_totals[key] = kind_totals.get(key, 0) + count
        documents[name] = document_result
        per_split = split_totals.setdefault(split, {})
        for metric, count in counts.items():
            totals[metric] = totals.get(metric, 0) + count
            per_split[metric] = per_split.get(metric, 0) + count
    result = {
        "schema_version": ("rdam.rst.gum-quality-baseline/v3" if segmentation == SegmentationMode.GOLD
                           else "rdam.rst.gum-end-to-end-evaluation/v1"),
        "measured_at": datetime.now(UTC).isoformat(),
        "purpose": "exact_regression_reference_not_accuracy_acceptance",
        "evaluation": ("binary_attachment_parseval_gum_coarse_gold_edus" if segmentation == SegmentationMode.GOLD
                       else "exact_character_attachment_parseval_gum_coarse_predicted_edus"),
        "evaluation_sources": implementation,
        "upstream_manifest_sha256": sha256(manifest_raw).hexdigest(),
        "model_training_overlap": upstream["model_training_overlap"],
        "model": {
            "parser": family, "release_id": release.manifest.release_id,
            "manifest_sha256": release.manifest.manifest_sha256,
            "source_model_identity": release.manifest.source_model_identity,
            "source_revision": release.manifest.source_revision,
            "inventory_sha256": inventory_member.sha256,
            "device": "cpu", "gold_edu_boundaries": segmentation == SegmentationMode.GOLD,
        },
        "documents": documents, "micro": totals, "split_micro": split_totals,
    }
    if segmentation == SegmentationMode.PREDICTED:
        result["segmentation_micro"] = segmentation_totals
    if relinventory is not None:
        result["selected_relation_inventory"] = relinventory
        result["label_harmonization"] = {
            "native_to_evaluation": {"condition": "contingency"} if relinventory == "eng.erst.gum" else {},
            "source": "https://aclanthology.org/2025.codi-1.17/", "section": "Appendix B",
        }
    if manifest_path.read_bytes() != manifest_raw or any(path.read_bytes() != raw for path, raw in source_bytes.items()):
        raise ValueError("Evaluation sources changed while inference was running")
    if evaluation_source_identities() != implementation:
        raise ValueError("Evaluation implementation changed while inference was running")
    encoded = (json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    destination.publish(encoded)
    print(json.dumps({"output": str(output.resolve()), "documents": len(documents), "micro": totals}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--model-store", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--relinventory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--segmentation", choices=tuple(SegmentationMode), default=SegmentationMode.GOLD)
    args = parser.parse_args()
    generate_reference(fixtures=args.fixtures, model_store=args.model_store, release_id=args.release_id,
                       output=args.output, force=args.force, segmentation=SegmentationMode(args.segmentation),
                       relinventory=args.relinventory)


if __name__ == "__main__":
    main()
