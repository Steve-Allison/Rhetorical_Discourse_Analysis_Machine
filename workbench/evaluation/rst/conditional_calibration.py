"""Development-only calibration of joint labels at correct predicted gold splits.

This diagnostic conditions on correct structure and gold EDUs. It cannot certify
calibration of arbitrary tree decisions, segmentation, or end-to-end parsing.
Raw joint scores are retained; fitting does not modify a production model.
"""

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import rdam
from rdam._output import OutputDestination
from rdam.rst.contracts import RstDocument
from workbench.erst.rs4 import RS4Reader
from rdam.rst.model_loading import load_model_release
from rdam.rst.parser import Parser
from workbench.evaluation.rst.calibration import TemperatureScaler, compute_calibration_error
from workbench.evaluation.rst.label_projection import gum_coarse_projection
from workbench.evaluation.rst.normalization import binarize_rs4
from workbench.evaluation.rst.parseval import StandardParsevalScorer
from workbench.evaluation.rst.regression import evaluation_source_identities


def runtime_source_identities() -> dict[str, str]:
    root = Path(rdam.__file__).parent
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest() for path in sorted(root.rglob("*.py"))}


def calibration_metrics(logits: list[list[float]], labels: list[int], *, temperature: float, bins: int) -> dict[str, Any]:
    scaler = TemperatureScaler(temperature)
    probabilities = scaler.predict_proba(logits)
    values = np.asarray(logits, dtype=np.float64)
    raw_targets = np.asarray(labels)
    if not np.issubdtype(raw_targets.dtype, np.integer):
        raise ValueError("calibration targets must be integer class indices")
    targets = raw_targets.astype(np.int64)
    if not len(targets) or len(targets) != len(values) or np.any(targets < 0) or np.any(targets >= values.shape[1]):
        raise ValueError("calibration metrics require valid nonempty class targets")
    shifted = (values - values.max(axis=1, keepdims=True)) / temperature
    log_normalizers = np.log(np.exp(shifted).sum(axis=1))
    nll = float(np.mean(log_normalizers - shifted[np.arange(len(targets)), targets]))
    one_hot = np.zeros_like(probabilities)
    one_hot[np.arange(len(targets)), targets] = 1.0
    brier = float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1)))
    confidences = [float(value) for value in probabilities.max(axis=1)]
    correct = [int(value) for value in probabilities.argmax(axis=1) == targets]
    grouped: dict[float, list[int]] = {}
    for confidence, outcome in zip(confidences, correct, strict=True):
        grouped.setdefault(confidence, []).append(outcome)
    retained = errors = 0
    risk_curve: list[dict[str, int | float]] = []
    for threshold in sorted(grouped, reverse=True):
        outcomes = grouped[threshold]
        retained += len(outcomes)
        errors += sum(1 - outcome for outcome in outcomes)
        risk_curve.append({"threshold_at_least": threshold, "retained": retained, "errors": errors,
                           "coverage": retained / len(labels), "error_rate": errors / retained})
    return {"samples": len(labels), "negative_log_likelihood": nll, "multiclass_brier": brier,
            "reliability": asdict(compute_calibration_error(confidences, correct, n_bins=bins)),
            "error_coverage": risk_curve}


def generate(*, fixtures: Path, model_store: Path, release_id: str, output: Path, bins: int, force: bool) -> None:
    if type(bins) is not int or bins < 1:
        raise ValueError("reliability bins must be a positive integer")
    manifest_path = fixtures / "upstream-manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    names = sorted(manifest["fixtures"])
    paths = {name: fixtures / f"{name}.rs4" for name in names}
    raws = {name: path.read_bytes() for name, path in paths.items()}
    destination = OutputDestination(output, force=force, inputs=(manifest_path, *paths.values()))
    destination.validate()
    runtime_sources = runtime_source_identities()
    release = load_model_release(model_store, release_id)
    if Parser.family_for_runtime_contract(release.manifest.runtime_contract) != "dmrst":
        raise ValueError("this diagnostic requires the single-inventory DMRST classifier")
    member = release.one_file_for_role("relation-inventory")
    inventory = (release.path / member.path).read_text().splitlines()
    parser = Parser.from_model_release(model_store, release_id, device="cpu")
    if list(parser.predictor.relation_table) != inventory:
        raise ValueError("runtime class inventory differs from the released member")
    code = {**evaluation_source_identities(), **{
        name: sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
        for name in ("calibration.py", "conditional_calibration.py")}}
    documents: dict[str, Any] = {}
    for name in names:
        fixture = manifest["fixtures"][name]
        split = fixture["split"]
        if split not in {"dev", "test", "test2"} or name not in manifest["splits"][split]:
            raise ValueError(f"calibration source is not in its declared development/test split: {name}")
        digest = sha256(raws[name]).hexdigest()
        if digest != fixture["local_sha256"] or digest != fixture["upstream_sha256"]:
            raise ValueError(f"calibration source differs from pinned upstream: {name}")
        rs4 = RS4Reader.read_string(raws[name].decode())
        document, gold = binarize_rs4(rs4, document_id=name)
        if document.edus is None:
            raise ValueError("gold normalization did not retain EDU boundaries")
        projection = gum_coarse_projection(tuple(rs4.relations), inventory)
        spans = StandardParsevalScorer(label_mapper=projection.__getitem__).extract_spans_from_analysis(gold)
        labels = {(span.start_edu, span.end_edu): (span.relation, span.nuclearity) for span in spans}
        gold_nodes = {node.node_id: node for node in gold.nodes}
        children: dict[int, list[int]] = {}
        for edge in gold.primary_edges:
            children.setdefault(edge.parent_id, []).append(edge.child_id)
        targets: dict[tuple[int, int, int], tuple[str, str]] = {}
        for parent, descendants in children.items():
            left, _ = sorted((gold_nodes[child] for child in descendants), key=lambda node: node.edu_span)
            node = gold_nodes[parent]
            targets[node.edu_span[0] - 1, node.edu_span[1] - 1, left.edu_span[1] - 1] = labels[node.edu_span]
        parser_input = RstDocument.from_edus([edu.text for edu in document.edus], document_id=name)
        if parser_input.text != document.text:
            raise ValueError("calibration input changed the source text")
        result = parser.analyse_document(parser_input)
        predicted_nodes = {node.node_id: node for node in result.analysis.nodes}
        samples: list[dict[str, Any]] = []
        excluded: Counter[str] = Counter()
        for decision in result.semantic.primary_inference.structure_decisions:
            if decision.selected_split is None or len(decision.node_ids) != 1:
                raise ValueError("conditional calibration requires one model-owned binary split per decision")
            node = predicted_nodes[decision.node_ids[0]]
            target = targets.get((node.edu_span[0] - 1, node.edu_span[1] - 1, decision.selected_split))
            if target is None:
                excluded["predicted_structure_differs_from_gold"] += 1
                continue
            joint = decision.joint
            if joint is None:
                raise ValueError("calibration requires captured joint scores")
            expected = f"{target[0]}_{target[1]}"
            classes = tuple(f"{projection[label.rpartition('_')[0].casefold()]}_{label.rpartition('_')[2].upper()}"
                            for label in joint.labels)
            if expected not in classes:
                excluded["gold_joint_class_absent_from_model_inventory"] += 1
                continue
            if len(set(classes)) != len(classes) or list(joint.labels) != inventory:
                raise ValueError("joint class order or identity differs from released inventory")
            if any(value is None or not math.isfinite(value) for value in joint.log_probabilities):
                raise ValueError("single-inventory calibration requires finite joint log probabilities")
            samples.append({"decision_id": decision.decision_id, "log_probabilities": joint.log_probabilities,
                            "gold_class": classes.index(expected)})
        documents[name] = {"split": split, "source_sha256": digest,
                           "input_text_sha256": sha256(document.text.encode()).hexdigest(), "eligible_samples": samples,
                           "excluded": dict(excluded), "predicted_decisions": len(samples) + excluded.total()}
        print(json.dumps({"document": name, "eligible": len(samples), "excluded": dict(excluded)}), flush=True)
    development_texts = {doc["input_text_sha256"] for doc in documents.values() if doc["split"] == "dev"}
    test_texts = {doc["input_text_sha256"] for doc in documents.values() if doc["split"] != "dev"}
    if development_texts & test_texts:
        raise ValueError("development and evaluation contain identical source text")
    fit = [sample for doc in documents.values() if doc["split"] == "dev" for sample in doc["eligible_samples"]]
    scaler = TemperatureScaler()
    temperature = scaler.fit([sample["log_probabilities"] for sample in fit], [sample["gold_class"] for sample in fit])
    metrics = {}
    for split in sorted({doc["split"] for doc in documents.values()}):
        samples = [sample for doc in documents.values() if doc["split"] == split for sample in doc["eligible_samples"]]
        scores, gold_labels = [sample["log_probabilities"] for sample in samples], [sample["gold_class"] for sample in samples]
        metrics[split] = {"before": calibration_metrics(scores, gold_labels, temperature=1.0, bins=bins),
                          "after": calibration_metrics(scores, gold_labels, temperature=temperature, bins=bins)}
    if manifest_path.read_bytes() != manifest_raw or any(paths[name].read_bytes() != raw for name, raw in raws.items()):
        raise ValueError("calibration inputs changed during measurement")
    if any(sha256((Path(__file__).parent / name).read_bytes()).hexdigest() != digest for name, digest in code.items()):
        raise ValueError("calibration evaluation implementation changed during measurement")
    if runtime_source_identities() != runtime_sources:
        raise ValueError("production parser sources changed during calibration measurement")
    artifact = {"schema_version": "rdam.rst.conditional-calibration/v1", "fit_split": "dev", "temperature": temperature,
                "conditions": "gold_edus_and_correct_predicted_binary_split", "production_calibration_changed": False,
                "model_training_overlap": manifest["model_training_overlap"], "upstream_manifest_sha256": sha256(manifest_raw).hexdigest(),
                "model": {"release_id": release_id, "manifest_sha256": release.manifest.manifest_sha256,
                          "inventory": inventory, "inventory_sha256": member.sha256, "device": "cpu"},
                "evaluation_sources": code, "runtime_sources": runtime_sources,
                "documents": documents, "metrics_by_split": metrics,
                "limitations": ["Conditions exclude incorrect structural decisions and absent gold classes.",
                                "These scores do not calibrate entire trees or arbitrary predicted structures.",
                                "Model training overlap is not independently verified; no operating threshold is selected."]}
    destination.publish((json.dumps(artifact, indent=2, allow_nan=False) + "\n").encode())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixtures", "model-store", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--bins", type=int, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    generate(fixtures=args.fixtures, model_store=args.model_store, release_id=args.release_id,
             output=args.output, bins=args.bins, force=args.force)


if __name__ == "__main__":
    main()
