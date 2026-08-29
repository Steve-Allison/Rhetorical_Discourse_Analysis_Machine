"""Training script for fine-tuning Transformer EDU discourse segmenters on GUM/DISRPT."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from transformers import (
    AutoConfig,
    AutoModelForTokenClassification,
    AutoTokenizer,
    get_cosine_schedule_with_warmup,
)

from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from workbench.training.segmentation.dataset import (
    EduSegmentationDataset,
    SegmentedSentence,
    parse_disrpt_tok_file,
    parse_rs4_to_sentences,
)
from scripts.fetch_disrpt_data import download_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_metrics(preds: list[int], targets: list[int]) -> dict[str, float]:
    """Compute precision, recall, and F1 for B-EDU boundary detection."""
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


def train_segmenter(
    model_name: str = MODERNBERT_BASE_MODEL_ID,
    model_revision: str | None = MODERNBERT_BASE_REVISION,
    data_dir: Path | str = "data/disrpt",
    output_dir: Path | str = "models/segmenter_modernbert_base",
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    epochs: int = 4,
    device: str = "auto",
    pos_weight: float = 4.5,
) -> dict[str, Any]:
    """Fine-tune a Transformer model for EDU segmentation."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    data_path = Path(data_dir)

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

    logger.info("Using device: %s for training %s", dev, model_name)

    # 2. Ingest Data
    if not data_path.exists() or not list(data_path.glob("**/*.tok")):
        logger.info("DISRPT data not found in %s. Downloading...", data_path)
        download_dataset(target_dir=data_path)

    train_sentences: list[SegmentedSentence] = []
    dev_sentences: list[SegmentedSentence] = []

    # Ingest DISRPT train files
    for tok_file in data_path.glob("**/*_train.tok"):
        train_sentences.extend(parse_disrpt_tok_file(tok_file))
    for tok_file in data_path.glob("**/*_dev.tok"):
        dev_sentences.extend(parse_disrpt_tok_file(tok_file))

    # Also ingest local GUM fixtures if available
    fixture_dir = Path("tests/fixtures/gum")
    if fixture_dir.exists():
        for rs4_file in fixture_dir.glob("*.rs4"):
            dev_sentences.extend(parse_rs4_to_sentences(rs4_file))

    logger.info("Loaded %d train sentences and %d dev sentences.", len(train_sentences), len(dev_sentences))

    if not train_sentences:
        raise RuntimeError("No training sentences available. Please verify dataset paths.")

    # 3. Setup Tokenizer and Model
    revision_kwargs = {"revision": model_revision} if model_revision is not None else {}
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True, **revision_kwargs)
    if not tokenizer.is_fast:
        raise ValueError("EDU segmenter training requires a native fast tokenizer artifact")
    config = AutoConfig.from_pretrained(model_name, **revision_kwargs)
    config.num_labels = 2
    config.id2label = {0: "I-EDU", 1: "B-EDU"}
    config.label2id = {"I-EDU": 0, "B-EDU": 1}
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        config=config,
        ignore_mismatched_sizes=True,
        use_safetensors=True,
        **revision_kwargs,
    ).to(dev)

    train_dataset = EduSegmentationDataset(train_sentences, tokenizer=tokenizer)
    dev_dataset = EduSegmentationDataset(dev_sentences, tokenizer=tokenizer) if dev_sentences else None

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    dev_loader = DataLoader(dev_dataset, batch_size=batch_size, shuffle=False) if dev_dataset else None

    # 4. Optimizer and Weighted Loss
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * 0.1)
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps
    )

    weight_tensor = torch.tensor([1.0, pos_weight], device=dev)
    loss_fn = nn.CrossEntropyLoss(weight=weight_tensor, ignore_index=-100)

    best_f1 = 0.0
    history: list[dict[str, Any]] = []

    # 5. Training Loop
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(dev)
            attention_mask = batch["attention_mask"].to(dev)
            labels = batch["labels"].to(dev)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits  # (batch, seq_len, 2)

            loss = loss_fn(logits.view(-1, 2), labels.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()

            if (step + 1) % max(1, len(train_loader) // 5) == 0:
                logger.info(
                    "Epoch %d/%d | Step %d/%d | Loss: %.4f", epoch, epochs, step + 1, len(train_loader), loss.item()
                )

        avg_train_loss = total_loss / len(train_loader)

        # 6. Evaluation Loop
        eval_metrics: dict[str, Any] = {}
        if dev_loader:
            model.eval()
            all_preds: list[int] = []
            all_targets: list[int] = []

            with torch.inference_mode():
                for batch in dev_loader:
                    input_ids = batch["input_ids"].to(dev)
                    attention_mask = batch["attention_mask"].to(dev)
                    labels = batch["labels"].to(dev)

                    outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                    preds = torch.argmax(outputs.logits, dim=-1)

                    mask = labels != -100
                    all_preds.extend(preds[mask].cpu().tolist())
                    all_targets.extend(labels[mask].cpu().tolist())

            eval_metrics = compute_metrics(all_preds, all_targets)
            logger.info(
                "Epoch %d Eval -> Precision: %.4f | Recall: %.4f | F1: %.4f",
                epoch,
                eval_metrics["precision"],
                eval_metrics["recall"],
                eval_metrics["f1"],
            )

            if eval_metrics["f1"] > best_f1:
                best_f1 = eval_metrics["f1"]
                logger.info("New best F1 (%.4f)! Saving checkpoint to %s", best_f1, out_path)
                model.save_pretrained(out_path)
                tokenizer.save_pretrained(out_path)

        epoch_record = {
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "eval_metrics": eval_metrics,
        }
        history.append(epoch_record)

    # Save training summary
    summary_file = out_path / "training_summary.json"
    summary_file.write_text(json.dumps({"best_f1": best_f1, "history": history}, indent=2), encoding="utf-8")
    logger.info("Training complete! Best F1: %.4f. Saved to %s", best_f1, out_path)

    return {"best_f1": best_f1, "history": history, "output_dir": str(out_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Transformer EDU Segmenter")
    parser.add_argument("--model_name", default=MODERNBERT_BASE_MODEL_ID, type=str)
    parser.add_argument("--model_revision", default=MODERNBERT_BASE_REVISION, type=str)
    parser.add_argument("--data_dir", default="data/disrpt", type=str)
    parser.add_argument("--output_dir", default="models/segmenter_deberta_large", type=str)
    parser.add_argument("--batch_size", default=16, type=int)
    parser.add_argument("--epochs", default=4, type=int)
    parser.add_argument("--lr", default=2e-5, type=float)
    parser.add_argument("--device", default="auto", type=str)

    args = parser.parse_args()
    train_segmenter(
        model_name=args.model_name,
        model_revision=args.model_revision,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.lr,
        device=args.device,
    )
