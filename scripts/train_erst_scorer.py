"""Training script for fine-tuning NeuralSecondaryEdgeScorer on GUM eRST treebanks."""

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader
from safetensors import safe_open
from safetensors.torch import save_model
from transformers import get_cosine_schedule_with_warmup

from isanlp_rst.contracts.erst import HardNegativeSamplingConfig
from isanlp_rst.erst.dataset import (
    GUMSecondaryEdgeDataset,
)
from isanlp_rst.erst.corpus import load_gum_erst_corpus_with_receipt
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer
from isanlp_rst.erst.relations import derive_raw_relation_inventory
from isanlp_rst.erst.sampling import prepare_partition_candidates
from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def require_positive_training_steps(total_steps: int) -> None:
    """Reject zero-step runs before a scheduler or success receipt can exist."""

    if total_steps <= 0:
        raise ValueError("eRST training requires at least one optimization step")


def epoch_improves(metric: float, best_metric: float | None) -> bool:
    """Treat the first finite metric as the baseline, including an exact zero."""

    if not math.isfinite(metric):
        raise ValueError("eRST development metric must be finite")
    return best_metric is None or metric > best_metric


def require_checkpoint(checkpoint_path: Path) -> None:
    """Reject absent, empty, pickle-capable, or unreadable training state."""

    if checkpoint_path.suffix != ".safetensors":
        raise ValueError("eRST training state must use the safetensors format")
    if not checkpoint_path.is_file() or checkpoint_path.stat().st_size == 0:
        raise FileNotFoundError("eRST training completed without a non-empty checkpoint")
    try:
        with safe_open(checkpoint_path, framework="pt", device="cpu") as tensors:
            if not list(tensors.keys()):
                raise ValueError("eRST training state contains no tensors")
    except Exception as error:
        raise ValueError("eRST training state is not a valid safetensors file") from error


def compute_edge_metrics(preds: list[int], targets: list[int]) -> dict[str, float]:
    """Compute binary precision, recall, and F1 for secondary edge detection."""
    tp = sum(1 for p, t in zip(preds, targets, strict=True) if p == 1 and t == 1)
    fp = sum(1 for p, t in zip(preds, targets, strict=True) if p == 1 and t == 0)
    fn = sum(1 for p, t in zip(preds, targets, strict=True) if p == 0 and t == 1)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def train_erst_scorer(
    model_name: str = MODERNBERT_BASE_MODEL_ID,
    model_revision: str | None = MODERNBERT_BASE_REVISION,
    data_dir: Path | str = "tests/fixtures/gum",
    output_dir: Path | str = "models/erst_scorer",
    batch_size: int = 16,
    learning_rate: float = 3e-5,
    epochs: int = 4,
    device: str = "auto",
    hard_negative_ratio: float = 4.0,
    seed: int = 17,
) -> dict[str, Any]:
    """Fine-tune NeuralSecondaryEdgeScorer on GUM eRST dataset."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Resolve Device
    if device == "auto":
        if torch.cuda.is_available():
            dev = torch.device("cuda")
        elif torch.backends.mps.is_available():
            dev = torch.device("mps")
        else:
            dev = torch.device("cpu")
    else:
        dev = torch.device(device)

    logger.info("Using device: %s for training eRST Scorer (%s)", dev, model_name)

    # 2. Ingest Candidates
    corpus = load_gum_erst_corpus_with_receipt(data_dir)
    partitioned = prepare_partition_candidates(
        corpus,
        hard_negative_config=HardNegativeSamplingConfig(
            negative_to_positive_ratio=hard_negative_ratio,
            seed=seed,
        ),
    )
    relation_inventory = derive_raw_relation_inventory(corpus)
    train_cands = partitioned.train
    dev_cands = partitioned.dev
    if not dev_cands:
        raise ValueError("official dev partition contains zero candidates")
    logger.info(
        "Loaded %d sampled train and %d complete dev candidates under corpus receipt %s",
        len(train_cands),
        len(dev_cands),
        corpus.receipt.receipt_sha256,
    )

    # 3. Setup Model and Datasets
    model = NeuralSecondaryEdgeScorer(
        model_name_or_path=model_name,
        model_revision=model_revision,
        raw_relation_inventory=relation_inventory.labels,
        device=dev,
    ).to(dev)

    train_dataset = GUMSecondaryEdgeDataset(
        train_cands,
        tokenizer=model.tokenizer,
        raw_relation_inventory=relation_inventory.labels,
    )
    dev_dataset = GUMSecondaryEdgeDataset(
        dev_cands,
        tokenizer=model.tokenizer,
        raw_relation_inventory=relation_inventory.labels,
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    dev_loader = DataLoader(dev_dataset, batch_size=batch_size, shuffle=False)

    # 4. Optimizer and Cosine Warmup
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    require_positive_training_steps(total_steps)
    warmup_steps = int(total_steps * 0.1)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    best_f1: float | None = None
    history: list[dict[str, Any]] = []

    # 5. Training Loop
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for step, batch in enumerate(train_loader):
            src_input_ids = batch["src_input_ids"].to(dev)
            src_attention_mask = batch["src_attention_mask"].to(dev)
            src_special_tokens_mask = batch["src_special_tokens_mask"].to(dev)
            src_offset_mapping = batch["src_offset_mapping"].to(dev)
            tgt_input_ids = batch["tgt_input_ids"].to(dev)
            tgt_attention_mask = batch["tgt_attention_mask"].to(dev)
            tgt_special_tokens_mask = batch["tgt_special_tokens_mask"].to(dev)
            tgt_offset_mapping = batch["tgt_offset_mapping"].to(dev)
            struct_features = batch["struct_features"].to(dev)
            edge_label = batch["edge_label"].to(dev)
            rel_label = batch["rel_label"].to(dev)

            optimizer.zero_grad()
            outputs = model(
                src_input_ids=src_input_ids,
                src_attention_mask=src_attention_mask,
                src_special_tokens_mask=src_special_tokens_mask,
                src_offset_mapping=src_offset_mapping,
                tgt_input_ids=tgt_input_ids,
                tgt_attention_mask=tgt_attention_mask,
                tgt_special_tokens_mask=tgt_special_tokens_mask,
                tgt_offset_mapping=tgt_offset_mapping,
                struct_features=struct_features,
                edge_label=edge_label,
                rel_label=rel_label,
            )

            loss = outputs["loss"]
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()

            if (step + 1) % max(1, len(train_loader) // 4) == 0:
                logger.info(
                    "Epoch %d/%d | Step %d/%d | Loss: %.4f", epoch, epochs, step + 1, len(train_loader), loss.item()
                )

        avg_train_loss = total_loss / len(train_loader)

        # 6. Evaluation Loop
        model.eval()
        all_preds: list[int] = []
        all_targets: list[int] = []

        with torch.inference_mode():
            for batch in dev_loader:
                src_input_ids = batch["src_input_ids"].to(dev)
                src_attention_mask = batch["src_attention_mask"].to(dev)
                src_special_tokens_mask = batch["src_special_tokens_mask"].to(dev)
                src_offset_mapping = batch["src_offset_mapping"].to(dev)
                tgt_input_ids = batch["tgt_input_ids"].to(dev)
                tgt_attention_mask = batch["tgt_attention_mask"].to(dev)
                tgt_special_tokens_mask = batch["tgt_special_tokens_mask"].to(dev)
                tgt_offset_mapping = batch["tgt_offset_mapping"].to(dev)
                struct_features = batch["struct_features"].to(dev)
                edge_label = batch["edge_label"].to(dev)

                outputs = model(
                    src_input_ids=src_input_ids,
                    src_attention_mask=src_attention_mask,
                    src_special_tokens_mask=src_special_tokens_mask,
                    src_offset_mapping=src_offset_mapping,
                    tgt_input_ids=tgt_input_ids,
                    tgt_attention_mask=tgt_attention_mask,
                    tgt_special_tokens_mask=tgt_special_tokens_mask,
                    tgt_offset_mapping=tgt_offset_mapping,
                    struct_features=struct_features,
                )

                preds = (outputs["edge_probs"] >= 0.50).long().cpu().tolist()
                targets = edge_label.long().cpu().tolist()

                all_preds.extend(preds)
                all_targets.extend(targets)

        eval_metrics = compute_edge_metrics(all_preds, all_targets)
        logger.info(
            "Epoch %d Eval -> Precision: %.4f | Recall: %.4f | F1: %.4f",
            epoch,
            eval_metrics["precision"],
            eval_metrics["recall"],
            eval_metrics["f1"],
        )

        if epoch_improves(eval_metrics["f1"], best_f1):
            best_f1 = eval_metrics["f1"]
            logger.info("New best eRST F1 (%.4f)! Saving model weights to %s", best_f1, out_path)
            save_model(
                model,
                str(out_path / "training_state.safetensors"),
                metadata={"format": "pt", "purpose": "private_intermediate_training_state"},
            )
            model.tokenizer.save_pretrained(out_path)

        epoch_record = {
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "eval_metrics": eval_metrics,
        }
        history.append(epoch_record)

    checkpoint_path = out_path / "training_state.safetensors"
    require_checkpoint(checkpoint_path)
    if best_f1 is None:
        raise RuntimeError("eRST training completed without a development evaluation")
    summary_file = out_path / "training_summary.json"
    summary_file.write_text(json.dumps({"best_f1": best_f1, "history": history}, indent=2), encoding="utf-8")
    logger.info("Training complete! Best eRST F1: %.4f. Saved to %s", best_f1, out_path)

    return {"best_f1": best_f1, "history": history, "output_dir": str(out_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Neural Secondary Edge Scorer on GUM eRST")
    parser.add_argument("--model_name", default=MODERNBERT_BASE_MODEL_ID, type=str)
    parser.add_argument("--model_revision", default=MODERNBERT_BASE_REVISION, type=str)
    parser.add_argument("--data_dir", default="tests/fixtures/gum", type=str)
    parser.add_argument("--output_dir", default="models/erst_scorer", type=str)
    parser.add_argument("--batch_size", default=16, type=int)
    parser.add_argument("--epochs", default=4, type=int)
    parser.add_argument("--lr", default=3e-5, type=float)
    parser.add_argument("--device", default="auto", type=str)
    parser.add_argument("--hard-negative-ratio", default=4.0, type=float)
    parser.add_argument("--seed", default=17, type=int)

    args = parser.parse_args()
    train_erst_scorer(
        model_name=args.model_name,
        model_revision=args.model_revision,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.lr,
        device=args.device,
        hard_negative_ratio=args.hard_negative_ratio,
        seed=args.seed,
    )
