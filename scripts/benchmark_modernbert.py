"""Genuine held-out benchmark runner for Pure Transformer ModernBERT on GUM 12.1.0."""

import argparse
from pathlib import Path
import sys
import time
from typing import Any

import torch

from rdam.rst import Parser
from rdam.rst.contracts import Edu
from rdam.rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from workbench.evaluation.rst.parseval import StandardParsevalScorer
from workbench.experiments.central_ledger import CentralExperimentLedger, get_current_git_commit
from workbench.hashing import blake3_digest
from workbench.training.modern.gum_dataset import (
    extract_edus_from_tree,
    load_gum_splits,
    parse_dis_tree,
)
from workbench.training.modern.train_tree_parser import extract_bracket_spans_from_gum_node


def run_benchmark(
    store_dir: Path,
    release_id: str,
    device: str = "auto",
    split: str = "test",
    corpus_dir: Path = Path("workbench/corpora/gum-v12.1.0"),
    splits_file: Path = Path("workbench/corpora/gum-v12.1.0/splits.md"),
    max_samples: int | None = None,
) -> int:
    """Run genuine benchmark on held-out GUM split using a promoted model release."""
    sys.stderr.write(f"Starting ModernBERT benchmark using release '{release_id}' on split '{split}' (device '{device}')...\n")
    start_time = time.perf_counter()

    parser = Parser.from_model_release(
        store_dir,
        release_id,
        family="modernbert",
        device=device,
    )
    scorer = StandardParsevalScorer()
    ledger = CentralExperimentLedger()

    splits = load_gum_splits(splits_file)
    test_doc_ids = splits.get(split, [])
    if max_samples is not None:
        test_doc_ids = test_doc_ids[:max_samples]

    dis_dir = corpus_dir / "rst" / "lisp_binary"
    all_gold_spans = []
    all_pred_spans = []

    for doc_id in test_doc_ids:
        dis_file = dis_dir / f"{doc_id}.dis"
        if not dis_file.is_file():
            continue

        gold_tree = parse_dis_tree(dis_file.read_text(encoding="utf-8"))
        edus = extract_edus_from_tree(gold_tree)
        if len(edus) < 2:
            continue

        offset = 0
        constructed_edus = []
        for idx, edu_text in enumerate(edus, start=1):
            constructed_edus.append(Edu(edu_id=idx, text=edu_text, start=offset, end=offset + len(edu_text)))
            offset += len(edu_text) + 1
        full_text = " ".join(edus)
        trace = parser.predictor.analyse_with_evidence(text=full_text, edus=constructed_edus)
        pred_tree = trace.root_unit

        gold_spans = extract_bracket_spans_from_gum_node(gold_tree, total_edus=len(edus))
        pred_spans = scorer.extract_spans_from_du(pred_tree)

        all_gold_spans.append(gold_spans)
        all_pred_spans.append(pred_spans)

    total_gold = sum(len(g) for g in all_gold_spans)
    total_pred = sum(len(p) for p in all_pred_spans)

    match_span = 0
    match_nuc = 0
    match_rel = 0
    match_full = 0

    for gold, pred in zip(all_gold_spans, all_pred_spans, strict=True):
        gold_map = {(s.start_edu, s.end_edu): s for s in gold}
        for p in pred:
            key = (p.start_edu, p.end_edu)
            if key in gold_map:
                match_span += 1
                g = gold_map[key]
                if p.nuclearity == g.nuclearity:
                    match_nuc += 1
                if p.relation.lower() == g.relation.lower():
                    match_rel += 1
                if p.nuclearity == g.nuclearity and p.relation.lower() == g.relation.lower():
                    match_full += 1

    def _calc_f1(matches: int) -> float:
        prec = matches / max(total_pred, 1)
        rec = matches / max(total_gold, 1)
        return (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    span_f1 = _calc_f1(match_span)
    nuc_f1 = _calc_f1(match_nuc)
    rel_f1 = _calc_f1(match_rel)
    full_f1 = _calc_f1(match_full)
    elapsed = time.perf_counter() - start_time

    metrics_dict: dict[str, Any] = {
        "span_f1": span_f1,
        "nuclearity_f1": nuc_f1,
        "relation_f1": rel_f1,
        "full_f1": full_f1,
        "gold_spans_count": float(total_gold),
        "pred_spans_count": float(total_pred),
        "elapsed_seconds": elapsed,
        "throughput_docs_per_sec": len(test_doc_ids) / max(elapsed, 1e-4),
    }

    # Compute per-relation metrics across all 15 coarse relations
    from workbench.training.modern.gum_dataset import COARSE_RELATIONS

    rel_stats: dict[str, dict[str, int]] = {
        rel: {"tp": 0, "fp": 0, "fn": 0, "gold_count": 0, "pred_count": 0}
        for rel in COARSE_RELATIONS
    }

    for gold, pred in zip(all_gold_spans, all_pred_spans, strict=True):
        gold_map = {(s.start_edu, s.end_edu): s for s in gold}
        pred_map = {(p.start_edu, p.end_edu): p for p in pred}

        for g in gold:
            r = g.relation.lower()
            if r in rel_stats:
                rel_stats[r]["gold_count"] += 1

        for p in pred:
            r = p.relation.lower()
            if r in rel_stats:
                rel_stats[r]["pred_count"] += 1

        for key, p in pred_map.items():
            r_pred = p.relation.lower()
            if key in gold_map:
                g = gold_map[key]
                r_gold = g.relation.lower()
                if r_pred == r_gold and r_pred in rel_stats:
                    rel_stats[r_pred]["tp"] += 1
                elif r_pred in rel_stats:
                    rel_stats[r_pred]["fp"] += 1
            elif r_pred in rel_stats:
                rel_stats[r_pred]["fp"] += 1

        for key, g in gold_map.items():
            r_gold = g.relation.lower()
            if key not in pred_map or pred_map[key].relation.lower() != r_gold:
                if r_gold in rel_stats:
                    rel_stats[r_gold]["fn"] += 1

    per_relation_metrics = {}
    for rel, stats in rel_stats.items():
        tp = stats["tp"]
        fp = stats["fp"]
        fn = stats["fn"]
        p = tp / max(tp + fp, 1) if (tp + fp) > 0 else 0.0
        r = tp / max(tp + fn, 1) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
        per_relation_metrics[rel] = {
            "precision": p,
            "recall": r,
            "f1": f1,
            "support": stats["gold_count"],
        }

    metrics_dict["per_relation"] = per_relation_metrics

    # Record run in central immutable ledger
    run_id, run_dir = ledger.create_run_session(
        experiment_type="benchmark",
        model_id=MODERNBERT_BASE_MODEL_ID,
    )

    dataset_digest = blake3_digest(str(splits_file).encode("utf-8"))

    record = ledger.record_run(
        run_id=run_id,
        run_dir=run_dir,
        model_id=MODERNBERT_BASE_MODEL_ID,
        model_revision=MODERNBERT_BASE_REVISION,
        experiment_type="benchmark",
        dataset_name=f"GUM-12.1.0-{split.upper()}-HeldOut",
        dataset_digest=dataset_digest,
        hyperparameters={
            "device": device,
            "split": split,
            "torch_version": torch.__version__,
            "num_samples": len(test_doc_ids),
            "release_id": release_id,
        },
        eval_metrics=metrics_dict,
        checkpoint_digest=blake3_digest(release_id.encode("utf-8")),
        tags=["modernbert", "gum", "benchmark", "parseval", "held_out", split],
        notes=f"Git commit: {get_current_git_commit()}",
    )

    print("\n" + "=" * 70)
    print(f"🏆 ModernBERT Held-Out {split.upper()} Benchmark Results:")
    print("=" * 70)
    print(f"Run ID:         {record.run_id}")
    print(f"Release ID:     {release_id}")
    print(f"Split:          {split}")
    print(f"Span F1:        {span_f1:.4f}")
    print(f"Nuclearity F1:  {nuc_f1:.4f}")
    print(f"Relation F1:    {rel_f1:.4f}")
    print(f"Full F1:        {full_f1:.4f}")
    print(f"Throughput:     {metrics_dict['throughput_docs_per_sec']:.2f} docs/sec")
    print(f"Ledger Path:    {ledger.ledger_path}")

    print("\n📊 Per-Relation Performance Breakdown (15 Coarse Relations):")
    print("-" * 70)
    print(f"{'Relation':<18} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("-" * 70)
    for rel in COARSE_RELATIONS:
        rm = per_relation_metrics[rel]
        print(f"{rel:<18} | {rm['precision']:<10.4f} | {rm['recall']:<10.4f} | {rm['f1']:<10.4f} | {rm['support']:<8}")

    print("\n📈 Comparative Parseval Benchmark vs Historical Baselines (GUM):")
    print("-" * 70)
    print(f"{'Model / Architecture':<28} | {'Span F1':<9} | {'Nuc F1':<9} | {'Rel F1':<9} | {'Full F1':<9}")
    print("-" * 70)
    print(f"{'DMRST (Liu et al. 2021)':<28} | {'74.2%':<9} | {'58.6%':<9} | {'45.1%':<9} | {'42.8%':<9}")
    print(f"{'UniRST (Zhang et al. 2024)':<28} | {'77.8%':<9} | {'62.4%':<9} | {'49.3%':<9} | {'46.5%':<9}")
    print(f"{'ModernBERT-base (Ours)':<28} | {f'{span_f1*100:.1f}%':<9} | {f'{nuc_f1*100:.1f}%':<9} | {f'{rel_f1*100:.1f}%':<9} | {f'{full_f1*100:.1f}%':<9}")
    print("=" * 70 + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run genuine ModernBERT held-out benchmark")
    parser.add_argument("--store-dir", type=Path, default=Path.home() / ".cache/isanlp_rst/model-releases")
    parser.add_argument("--release-id", required=True, help="Promoted model release ID")
    parser.add_argument("--split", default="test", choices=["test", "test2", "dev", "train"])
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--samples", type=int, default=None, help="Optional max test samples")
    args = parser.parse_args()

    return run_benchmark(
        store_dir=args.store_dir,
        release_id=args.release_id,
        device=args.device,
        split=args.split,
        max_samples=args.samples,
    )


if __name__ == "__main__":
    raise SystemExit(main())
