"""Training script for fine-tuning NeuralSecondaryEdgeScorer on GUM eRST treebanks."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader
from transformers import get_cosine_schedule_with_warmup

from isanlp_rst.erst.dataset import (
    GUMSecondaryEdgeDataset,
    load_gum_erst_corpus,
)
from isanlp_rst.erst.neural_scorer import NeuralSecondaryEdgeScorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


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
    model_name: str = "microsoft/deberta-v3-base",
    data_dir: Path | str = "tests/fixtures/gum",
    output_dir: Path | str = "models/erst_scorer",
    batch_size: int = 16,
    learning_rate: float = 3e-5,
    epochs: int = 4,
    device: str = "auto",
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
    all_candidates = load_gum_erst_corpus(data_dir)
    logger.info("Loaded %d pairwise candidates from %s", len(all_candidates), data_dir)

    if not all_candidates:
        logger.warning("No .rs4 candidates found in %s. Using default fallback.", data_dir)
        return {"best_f1": 0.0, "output_dir": str(out_path)}

    # Split train and dev (80 / 20)
    split_idx = int(len(all_candidates) * 0.8)
    train_cands = all_candidates[:split_idx]
    dev_cands = all_candidates[split_idx:] if split_idx < len(all_candidates) else all_candidates

    # 3. Setup Model and Datasets
    model = NeuralSecondaryEdgeScorer(model_name_or_path=model_name, device=dev).to(dev)

    train_dataset = GUMSecondaryEdgeDataset(train_cands, tokenizer=model.tokenizer)
    dev_dataset = GUMSecondaryEdgeDataset(dev_cands, tokenizer=model.tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    dev_loader = DataLoader(dev_dataset, batch_size=batch_size, shuffle=False)

    # 4. Optimizer and Cosine Warmup
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * 0.1)
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    best_f1 = 0.0
    history: list[dict[str, Any]] = []

    # 5. Training Loop
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for step, batch in enumerate(train_loader):
            src_input_ids = batch["src_input_ids"].to(dev)
            src_attention_mask = batch["src_attention_mask"].to(dev)
            tgt_input_ids = batch["tgt_input_ids"].to(dev)
            tgt_attention_mask = batch["tgt_attention_mask"].to(dev)
            struct_features = batch["struct_features"].to(dev)
            edge_label = batch["edge_label"].to(dev)
            rel_label = batch["rel_label"].to(dev)

            optimizer.zero_grad()
            outputs = model(
                src_input_ids=src_input_ids,
                src_attention_mask=src_attention_mask,
                tgt_input_ids=tgt_input_ids,
                tgt_attention_mask=tgt_attention_mask,
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
                logger.info("Epoch %d/%d | Step %d/%d | Loss: %.4f", epoch, epochs, step + 1, len(train_loader), loss.item())

        avg_train_loss = total_loss / len(train_loader)

        # 6. Evaluation Loop
        model.eval()
        all_preds: list[int] = []
        all_targets: list[int] = []

        with torch.inference_mode():
            for batch in dev_loader:
                src_input_ids = batch["src_input_ids"].to(dev)
                src_attention_mask = batch["src_attention_mask"].to(dev)
                tgt_input_ids = batch["tgt_input_ids"].to(dev)
                tgt_attention_mask = batch["tgt_attention_mask"].to(dev)
                struct_features = batch["struct_features"].to(dev)
                edge_label = batch["edge_label"].to(dev)

                outputs = model(
                    src_input_ids=src_input_ids,
                    src_attention_mask=src_attention_mask,
                    tgt_input_ids=tgt_input_ids,
                    tgt_attention_mask=tgt_attention_mask,
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

        if eval_metrics["f1"] > best_f1:
            best_f1 = eval_metrics["f1"]
            logger.info("New best eRST F1 (%.4f)! Saving model weights to %s", best_f1, out_path)
            torch.save(model.state_dict(), out_path / "model.pt")
            model.tokenizer.save_pretrained(out_path)

        epoch_record = {
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "eval_metrics": eval_metrics,
        }
        history.append(epoch_record)

    summary_file = out_path / "training_summary.json"
    summary_file.write_text(json.dumps({"best_f1": best_f1, "history": history}, indent=2), encoding="utf-8")
    logger.info("Training complete! Best eRST F1: %.4f. Saved to %s", best_f1, out_path)

    return {"best_f1": best_f1, "history": history, "output_dir": str(out_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Neural Secondary Edge Scorer on GUM eRST")
    parser.add_argument("--model_name", default="microsoft/deberta-v3-base", type=str)
    parser.add_argument("--data_dir", default="tests/fixtures/gum", type=str)
    parser.add_argument("--output_dir", default="models/erst_scorer", type=str)
    parser.add_argument("--batch_size", default=16, type=int)
    parser.add_argument("--epochs", default=4, type=int)
    parser.add_argument("--lr", default=3e-5, type=float)
    parser.add_argument("--device", default="auto", type=str)

    args = parser.parse_args()
    train_erst_scorer(
        model_name=args.model_name,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.lr,
        device=args.device,
    )
