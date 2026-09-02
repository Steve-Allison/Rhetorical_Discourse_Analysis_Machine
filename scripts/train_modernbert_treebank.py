"""End-to-end training and evaluation runner for Pure Transformer ModernBERT on GUM 12.1.0."""

import argparse
import hashlib
import json
import logging
from pathlib import Path
import time

from transformers import AutoTokenizer

from rdam.rst.model_authority import (
    MODERNBERT_BASE_MODEL_ID,
    MODERNBERT_BASE_REVISION,
    MODERNBERT_LARGE_MODEL_ID,
    MODERNBERT_LARGE_REVISION,
)
from workbench.experiments.central_ledger import CentralExperimentLedger, get_current_git_commit
from workbench.training.modern.gum_dataset import (
    COARSE_RELATIONS,
    GUMTreebankDataset,
)
from workbench.training.modern.train_tree_parser import ModernTreeParserTrainer, TrainingMetricsReceipt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ModernBERT Pure Transformer Discourse Parser on GUM 12.1.0")
    parser.add_argument("--model-size", choices=["base", "large"], default="base")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--encoder-lr", type=float, default=2e-5, help="Learning rate for pretrained ModernBERT backbone")
    parser.add_argument("--head-lr", type=float, default=1e-4, help="Learning rate for randomly initialized biaffine parser heads")
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--split-pos-weight", type=float, default=5.0, help="Positive class weight for split BCE loss")
    parser.add_argument("--warmup-ratio", type=float, default=0.1, help="Linear warmup ratio for cosine schedule")
    parser.add_argument("--max-grad-norm", type=float, default=1.0, help="Max gradient norm for clipping")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--corpus-dir", type=Path, default=Path("workbench/corpora/gum-v12.1.0"))
    parser.add_argument("--splits-file", type=Path, default=Path("workbench/corpora/gum-v12.1.0/splits.md"))
    parser.add_argument("--output-dir", type=Path, default=Path("models/modernbert_v1"))
    args = parser.parse_args()

    model_id = MODERNBERT_LARGE_MODEL_ID if args.model_size == "large" else MODERNBERT_BASE_MODEL_ID
    revision = MODERNBERT_LARGE_REVISION if args.model_size == "large" else MODERNBERT_BASE_REVISION

    logger.info(f"Initializing fast tokenizer for {model_id} (revision: {revision})...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, use_fast=True)

    logger.info(f"Loading authoritative GUM 12.1.0 dataset from {args.corpus_dir}...")
    dataset = GUMTreebankDataset(
        corpus_dir=args.corpus_dir,
        splits_file=args.splits_file,
        tokenizer=tokenizer,
    )

    train_docs = dataset.documents_by_split["train"]
    dev_docs = dataset.documents_by_split["dev"]
    test_docs = dataset.documents_by_split["test"]
    test2_docs = dataset.documents_by_split["test2"]

    logger.info(
        f"Corpus Partitions: Train={len(train_docs)}, Dev={len(dev_docs)}, "
        f"Test={len(test_docs)}, Test2 (GENTLE)={len(test2_docs)}"
    )

    logger.info(
        f"Setting up PureTransformerParsingNet with {len(COARSE_RELATIONS)} relation classes "
        f"(encoder_lr={args.encoder_lr}, head_lr={args.head_lr}, split_pos_weight={args.split_pos_weight})..."
    )
    trainer = ModernTreeParserTrainer(
        model_name_or_path=model_id,
        model_revision=revision,
        raw_relation_inventory=COARSE_RELATIONS,
        encoder_lr=args.encoder_lr,
        head_lr=args.head_lr,
        weight_decay=args.weight_decay,
        gradient_accumulation_steps=args.grad_accum,
        split_pos_weight=args.split_pos_weight,
        max_grad_norm=args.max_grad_norm,
        device=args.device,
    )

    # Setup cosine schedule with warmup across total optimization steps
    steps_per_epoch = (len(train_docs) + args.grad_accum - 1) // args.grad_accum
    total_training_steps = steps_per_epoch * args.epochs
    trainer.setup_scheduler(total_training_steps, warmup_ratio=args.warmup_ratio)
    logger.info(
        f"Configured cosine schedule: {total_training_steps} total steps "
        f"({int(total_training_steps * args.warmup_ratio)} warmup steps, {steps_per_epoch} steps/epoch)"
    )

    ledger = CentralExperimentLedger()
    run_id, run_dir = ledger.create_run_session(experiment_type="training", model_id=model_id)
    logger.info(f"Initialized unique immutable run session: {run_id} in {run_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    best_dev_full_f1 = -1.0
    best_receipt: TrainingMetricsReceipt | None = None
    best_checkpoint_path = args.output_dir / "model.safetensors"

    logger.info(f"Starting training for {args.epochs} epochs...")
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.perf_counter()
        train_loss = trainer.train_epoch(train_docs)
        receipt = trainer.evaluate(dev_docs, epoch=epoch)
        elapsed = time.perf_counter() - epoch_start

        logger.info(
            f"Epoch {epoch}/{args.epochs} [{elapsed:.1f}s] - "
            f"Train Loss: {train_loss:.4f} | Dev Loss: {receipt.eval_loss:.4f} | "
            f"Span F1: {receipt.span_f1:.1%} | Nuc F1: {receipt.nuclearity_f1:.1%} | "
            f"Rel F1: {receipt.relation_f1:.1%} | Full F1: {receipt.full_f1:.1%}"
        )

        if receipt.full_f1 > best_dev_full_f1:
            best_dev_full_f1 = receipt.full_f1
            best_receipt = receipt
            sha256 = trainer.save_checkpoint(best_checkpoint_path)
            logger.info(f"Saved new best model checkpoint to {best_checkpoint_path} (SHA-256: {sha256[:16]}...)")

    # Evaluate on held-out In-Domain Test and Out-of-Domain GENTLE Test2
    logger.info("Evaluating best model on held-out in-domain Test set...")
    test_receipt = trainer.evaluate(test_docs, epoch=0)
    logger.info(
        f"Test Set - Span F1: {test_receipt.span_f1:.1%} | Nuc F1: {test_receipt.nuclearity_f1:.1%} | "
        f"Rel F1: {test_receipt.relation_f1:.1%} | Full F1: {test_receipt.full_f1:.1%}"
    )

    logger.info("Evaluating best model on out-of-domain GENTLE Test2 set...")
    test2_receipt = trainer.evaluate(test2_docs, epoch=0)
    logger.info(
        f"Test2 (GENTLE) - Span F1: {test2_receipt.span_f1:.1%} | Nuc F1: {test2_receipt.nuclearity_f1:.1%} | "
        f"Rel F1: {test2_receipt.relation_f1:.1%} | Full F1: {test2_receipt.full_f1:.1%}"
    )

    # Save relation inventory and tokenizer assets with model
    inventory_path = args.output_dir / "relation_inventory.json"
    inventory_path.write_text(json.dumps(list(COARSE_RELATIONS), indent=2), encoding="utf-8")
    tokenizer.save_pretrained(args.output_dir)
    trainer.model.encoder.config.save_pretrained(args.output_dir)

    # Save comprehensive training receipt
    eval_metrics = {
        "dev_span_f1": best_receipt.span_f1 if best_receipt else 0.0,
        "dev_nuc_f1": best_receipt.nuclearity_f1 if best_receipt else 0.0,
        "dev_rel_f1": best_receipt.relation_f1 if best_receipt else 0.0,
        "dev_full_f1": best_receipt.full_f1 if best_receipt else 0.0,
        "test_span_f1": test_receipt.span_f1,
        "test_nuc_f1": test_receipt.nuclearity_f1,
        "test_rel_f1": test_receipt.relation_f1,
        "test_full_f1": test_receipt.full_f1,
        "test2_span_f1": test2_receipt.span_f1,
        "test2_nuc_f1": test2_receipt.nuclearity_f1,
        "test2_rel_f1": test2_receipt.relation_f1,
        "test2_full_f1": test2_receipt.full_f1,
    }

    final_sha256 = hashlib.sha256(best_checkpoint_path.read_bytes()).hexdigest()
    receipt_data = {
        "run_id": run_id,
        "model_id": model_id,
        "model_revision": revision,
        "dataset_name": "GUM-12.1.0",
        "checkpoint_sha256": final_sha256,
        "eval_metrics": eval_metrics,
        "hyperparameters": {
            "epochs": args.epochs,
            "encoder_lr": args.encoder_lr,
            "head_lr": args.head_lr,
            "weight_decay": args.weight_decay,
            "grad_accum": args.grad_accum,
        },
        "git_commit": get_current_git_commit(),
    }

    receipt_file = args.output_dir / "training_receipt.json"
    receipt_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

    ledger.record_run(
        run_id=run_id,
        run_dir=run_dir,
        model_id=model_id,
        model_revision=revision,
        experiment_type="training",
        dataset_name="GUM-12.1.0",
        dataset_digest=final_sha256[:16],
        hyperparameters=receipt_data["hyperparameters"],
        eval_metrics=eval_metrics,
        checkpoint_digest=final_sha256,
        tags=["modernbert", "gum12", "pure_transformer"],
    )
    logger.info(f"Training successfully completed! Model and receipt written to {args.output_dir}")


if __name__ == "__main__":
    main()
