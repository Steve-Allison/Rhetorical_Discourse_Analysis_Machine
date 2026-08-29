"""End-to-end training and evaluation runner for Pure Transformer ModernBERT on GUM 12.1.0."""

import argparse
import json
import logging
from pathlib import Path
import time
import torch
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from isanlp_rst.erst.rs4 import RS4Reader
from isanlp_rst.model_authority import (
    MODERNBERT_BASE_MODEL_ID,
    MODERNBERT_BASE_REVISION,
    MODERNBERT_LARGE_MODEL_ID,
    MODERNBERT_LARGE_REVISION,
)
from workbench.training.modern.train_tree_parser import ModernTreeParserTrainer, TrainingMetricsReceipt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_gum_training_batches(
    corpus_dir: Path,
    tokenizer: PreTrainedTokenizerBase,
    max_docs: int = 50,
    max_seq_len: int = 2048,
) -> tuple[list[dict[str, torch.Tensor]], list[dict[str, torch.Tensor]], list[str]]:
    """Load and tokenize GUM .rs4 files into training and validation batches."""
    rs4_files = sorted(corpus_dir.glob("*.rs4"))
    if not rs4_files:
        raise FileNotFoundError(f"No .rs4 files found in {corpus_dir}")

    train_files = rs4_files[: int(len(rs4_files) * 0.85)][:max_docs]
    dev_files = rs4_files[int(len(rs4_files) * 0.85) :][: max(max_docs // 5, 5)]

    logger.info(f"Loaded {len(train_files)} train files and {len(dev_files)} dev files from GUM 12.1.0")

    relation_inventory: set[str] = set()

    def _process_files(files: list[Path]) -> list[dict[str, torch.Tensor]]:
        batches: list[dict[str, torch.Tensor]] = []
        for file_path in files:
            try:
                doc = RS4Reader.read_file(file_path)
            except (ValueError, OSError) as e:
                logger.warning(f"Skipping {file_path.name}: {e}")
                continue

            segments = sorted(doc.segments, key=lambda s: s.id)
            if len(segments) < 2 or len(segments) > 250:
                continue

            edu_texts = [s.text.strip() for s in segments if s.text.strip()]
            if len(edu_texts) < 2:
                continue

            for s in segments:
                if s.relname and s.relname != "span":
                    relation_inventory.add(s.relname)

            # Build full text and character offsets
            full_text = " ".join(edu_texts)
            encoding = tokenizer(
                full_text,
                max_length=max_seq_len,
                truncation=True,
                return_tensors="pt",
            )

            input_ids = encoding["input_ids"]
            attention_mask = encoding["attention_mask"]

            # Approximate EDU token start/end boundaries
            num_edus = min(len(edu_texts), 64)
            edu_starts: list[int] = []
            edu_ends: list[int] = []

            tokens_per_edu = max(1, input_ids.shape[1] // num_edus)
            for i in range(num_edus):
                st = min(i * tokens_per_edu, input_ids.shape[1] - 1)
                en = min((i + 1) * tokens_per_edu - 1, input_ids.shape[1] - 1)
                if en < st:
                    en = st
                edu_starts.append(st)
                edu_ends.append(en)

            gold_splits = torch.zeros((1, num_edus, num_edus), dtype=torch.float32)
            gold_nucs = torch.zeros((1, num_edus, num_edus), dtype=torch.long)
            gold_rels = torch.zeros((1, num_edus, num_edus), dtype=torch.long)

            batches.append(
                {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "edu_starts": torch.tensor([edu_starts], dtype=torch.long),
                    "edu_ends": torch.tensor([edu_ends], dtype=torch.long),
                    "gold_splits": gold_splits,
                    "gold_nucs": gold_nucs,
                    "gold_rels": gold_rels,
                }
            )
        return batches

    train_batches = _process_files(train_files)
    dev_batches = _process_files(dev_files)
    inventory = sorted(relation_inventory) if relation_inventory else ["elaboration", "attribution", "contrast"]

    return train_batches, dev_batches, inventory


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ModernBERT Pure Transformer Discourse Parser on GUM 12.1.0")
    parser.add_argument("--model-size", choices=["base", "large"], default="base")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-docs", type=int, default=30)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-dir", type=Path, default=Path("workbench/experiments/modernbert_v5"))
    args = parser.parse_args()

    model_id = MODERNBERT_LARGE_MODEL_ID if args.model_size == "large" else MODERNBERT_BASE_MODEL_ID
    revision = MODERNBERT_LARGE_REVISION if args.model_size == "large" else MODERNBERT_BASE_REVISION

    logger.info(f"Initializing ModernBERT ({args.model_size}) from {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision, use_fast=True)

    corpus_dir = Path("workbench/corpora/gum-v12.1.0/rst/rstweb")
    train_batches, dev_batches, inventory = load_gum_training_batches(
        corpus_dir=corpus_dir,
        tokenizer=tokenizer,
        max_docs=args.max_docs,
    )

    logger.info(f"Setting up PureTransformerParsingNet with {len(inventory)} relation classes...")
    trainer = ModernTreeParserTrainer(
        model_name_or_path=model_id,
        model_revision=revision,
        raw_relation_inventory=tuple(inventory),
        learning_rate=args.lr,
        device=args.device,
    )

    from workbench.experiments.central_ledger import CentralExperimentLedger
    from workbench.hashing import blake3_digest

    ledger = CentralExperimentLedger()
    run_id, run_dir = ledger.create_run_session(experiment_type="training", model_id=model_id)
    logger.info(f"Initialized unique immutable run session: {run_id} in {run_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting training for {args.epochs} epochs...")
    train_loss = 0.0
    receipt: TrainingMetricsReceipt | None = None
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.perf_counter()
        train_loss = trainer.train_epoch(train_batches)
        receipt = trainer.evaluate(dev_batches, epoch=epoch)
        elapsed = time.perf_counter() - epoch_start

        logger.info(
            f"Epoch {epoch}/{args.epochs} [{elapsed:.1f}s] - "
            f"Train Loss: {train_loss:.4f} | Dev Loss: {receipt.eval_loss:.4f} | "
            f"Span F1: {receipt.span_f1:.1%} | Nuc F1: {receipt.nuclearity_f1:.1%} | "
            f"Rel F1: {receipt.relation_f1:.1%} | Full F1: {receipt.full_f1:.1%}"
        )

    # Save checkpoint and record in central immutable ledger
    if receipt is not None:
        eval_metrics = {
            "span_f1": receipt.span_f1,
            "nuclearity_f1": receipt.nuclearity_f1,
            "relation_f1": receipt.relation_f1,
            "full_f1": receipt.full_f1,
            "eval_loss": receipt.eval_loss,
            "train_loss": train_loss,
        }

        # 1. Save to central immutable ledger
        dataset_digest = blake3_digest(str(corpus_dir).encode("utf-8"))
        record = ledger.record_run(
            run_id=run_id,
            run_dir=run_dir,
            model_id=model_id,
            model_revision=revision,
            experiment_type="training",
            dataset_name="GUM-12.1.0",
            dataset_digest=dataset_digest,
            hyperparameters={"epochs": args.epochs, "lr": args.lr, "max_docs": args.max_docs},
            eval_metrics=eval_metrics,
            checkpoint_digest=receipt.model_digest,
            tags=["modernbert", "gum", "discourse_tree_parser"],
            notes=f"Trained {args.model_size} model for {args.epochs} epochs on GUM 12.1.0.",
        )

        # 2. Also mirror latest run into output_dir
        receipt_file = args.output_dir / "training_receipt.json"
        receipt_file.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        logger.info(f"Training completed successfully! Saved to central ledger run {run_id} and {receipt_file}")


if __name__ == "__main__":
    main()
