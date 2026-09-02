"""Modern training recipe for Pure Transformer RST Tree Parsers (ModernBERT / XLM-RoBERTa)."""

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import time

from safetensors.torch import save_model
import torch
from torch.optim import AdamW
from transformers import PretrainedConfig, get_cosine_schedule_with_warmup

from rdam.rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from workbench.training.modern.model import PureTransformerParsingNet
from workbench.training.modern.biaffine_decoder import ParsedRstTreeSpan
from workbench.evaluation.rst.parseval import BracketSpan
from workbench.training.modern.gum_dataset import (
    COARSE_RELATIONS,
    NUCLEARITY_CLASSES,
    GUMDisNode,
    ParsedGUMDocument,
    map_nuclearity,
    map_relation,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TrainingMetricsReceipt:
    """Immutable evaluation metrics receipt."""

    epoch: int
    eval_loss: float
    span_f1: float
    nuclearity_f1: float
    relation_f1: float
    full_f1: float
    elapsed_seconds: float
    model_digest: str


def extract_bracket_spans_from_gum_node(
    node: GUMDisNode,
    total_edus: int,
    include_leaves: bool = False,
    include_root: bool = False,
) -> set[BracketSpan]:
    """Extract gold standard BracketSpan objects from a GUMDisNode tree."""
    spans: set[BracketSpan] = set()

    def walk(curr: GUMDisNode) -> None:
        start = curr.edu_start
        end = curr.edu_end

        is_leaf = curr.is_leaf
        is_root = start == 1 and end == total_edus and total_edus > 1

        if is_leaf:
            if include_leaves:
                spans.add(BracketSpan(start_edu=start, end_edu=end, nuclearity="", relation=""))
            return

        if not is_root or include_root:
            if len(curr.children) >= 2:
                nuc = map_nuclearity(curr.children[0], curr.children[1])
                rel = map_relation(curr).lower()
                spans.add(BracketSpan(start_edu=start, end_edu=end, nuclearity=nuc, relation=rel))

        for child in curr.children:
            walk(child)

    walk(node)
    return spans


def extract_bracket_spans_from_decoded_spans(
    tree_spans: Sequence[ParsedRstTreeSpan],
    total_edus: int,
    include_leaves: bool = False,
    include_root: bool = False,
) -> set[BracketSpan]:
    """Extract predicted BracketSpan objects from CKY-decoded tree spans."""
    spans: set[BracketSpan] = set()

    for span in tree_spans:
        start = span.start + 1
        end = span.end + 1

        is_leaf = start == end
        is_root = start == 1 and end == total_edus and total_edus > 1

        if is_leaf:
            if include_leaves:
                spans.add(BracketSpan(start_edu=start, end_edu=end, nuclearity="", relation=""))
            continue

        if not is_root or include_root:
            spans.add(
                BracketSpan(
                    start_edu=start,
                    end_edu=end,
                    nuclearity=span.nuclearity,
                    relation=span.relation.lower(),
                )
            )

    return spans


class ModernTreeParserTrainer:
    """Trainer for Pure Transformer Vectorized RST Parsers with SOTA optimization."""

    def __init__(
        self,
        model_name_or_path: str = MODERNBERT_BASE_MODEL_ID,
        model_revision: str | None = MODERNBERT_BASE_REVISION,
        raw_relation_inventory: tuple[str, ...] = COARSE_RELATIONS,
        nuclearity_labels: tuple[str, ...] = NUCLEARITY_CLASSES,
        encoder_lr: float = 2e-5,
        head_lr: float = 1e-4,
        weight_decay: float = 0.01,
        gradient_accumulation_steps: int = 16,
        split_pos_weight: float = 5.0,
        max_grad_norm: float = 1.0,
        device: str = "auto",
        torch_dtype: str = "auto",
        encoder_config: PretrainedConfig | None = None,
    ) -> None:
        self.model = PureTransformerParsingNet(
            model_name_or_path=model_name_or_path,
            model_revision=model_revision,
            raw_relation_inventory=raw_relation_inventory,
            nuclearity_labels=nuclearity_labels,
            split_pos_weight=split_pos_weight,
            device=device,
            torch_dtype=torch_dtype,
            encoder_config=encoder_config,
        )
        self.encoder_lr = encoder_lr
        self.head_lr = head_lr
        self.weight_decay = weight_decay
        self.gradient_accumulation_steps = max(1, gradient_accumulation_steps)
        self.max_grad_norm = max_grad_norm
        self.scheduler = None

        # Setup AdamW optimizer with discriminative learning rates and decoupled weight decay
        no_decay = ["bias", "LayerNorm.weight", "layer_norm.weight"]
        encoder_params = set(self.model.encoder.parameters())

        optimizer_grouped_parameters = [
            # 1. Pretrained Encoder with weight decay
            {
                "params": [
                    p
                    for n, p in self.model.named_parameters()
                    if p in encoder_params and not any(nd in n for nd in no_decay) and p.requires_grad
                ],
                "lr": encoder_lr,
                "weight_decay": weight_decay,
            },
            # 2. Pretrained Encoder without weight decay (bias, LayerNorm)
            {
                "params": [
                    p
                    for n, p in self.model.named_parameters()
                    if p in encoder_params and any(nd in n for nd in no_decay) and p.requires_grad
                ],
                "lr": encoder_lr,
                "weight_decay": 0.0,
            },
            # 3. Task-specific Parser Heads with higher learning rate and weight decay
            {
                "params": [
                    p
                    for n, p in self.model.named_parameters()
                    if p not in encoder_params and not any(nd in n for nd in no_decay) and p.requires_grad
                ],
                "lr": head_lr,
                "weight_decay": weight_decay,
            },
            # 4. Task-specific Parser Heads without weight decay (bias, LayerNorm)
            {
                "params": [
                    p
                    for n, p in self.model.named_parameters()
                    if p not in encoder_params and any(nd in n for nd in no_decay) and p.requires_grad
                ],
                "lr": head_lr,
                "weight_decay": 0.0,
            },
        ]
        self.optimizer = AdamW(optimizer_grouped_parameters)

    def setup_scheduler(self, num_training_steps: int, warmup_ratio: float = 0.1) -> None:
        """Initialize cosine learning rate scheduler with warmup."""
        num_warmup_steps = int(num_training_steps * warmup_ratio)
        self.scheduler = get_cosine_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=num_warmup_steps,
            num_training_steps=num_training_steps,
        )

    def train_epoch(self, documents: Sequence[ParsedGUMDocument]) -> float:
        """Run a single training epoch with document-level loss and gradient accumulation."""
        self.model.train()
        self.optimizer.zero_grad()
        total_loss = 0.0

        for step, doc in enumerate(documents, start=1):
            outputs = self.model(
                input_ids=doc.input_ids.to(self.model.dev),
                attention_mask=doc.attention_mask.to(self.model.dev),
                edu_starts=doc.edu_starts.to(self.model.dev),
                edu_ends=doc.edu_ends.to(self.model.dev),
                gold_splits=doc.gold_splits.to(self.model.dev),
                gold_nucs=doc.gold_nucs.to(self.model.dev),
                gold_rels=doc.gold_rels.to(self.model.dev),
            )
            loss = outputs["loss"] / self.gradient_accumulation_steps
            loss.backward()

            total_loss += float(outputs["loss"].item())

            if step % self.gradient_accumulation_steps == 0 or step == len(documents):
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=self.max_grad_norm)
                self.optimizer.step()
                if self.scheduler is not None:
                    self.scheduler.step()
                self.optimizer.zero_grad()

        return total_loss / max(len(documents), 1)

    def evaluate(self, dev_documents: Sequence[ParsedGUMDocument], epoch: int = 0) -> TrainingMetricsReceipt:
        """Evaluate model dynamically with CKY decoding and StandardParsevalScorer."""
        self.model.eval()
        start_time = time.perf_counter()
        total_loss = 0.0

        all_gold_spans: list[set[BracketSpan]] = []
        all_pred_spans: list[set[BracketSpan]] = []

        with torch.inference_mode():
            for doc in dev_documents:
                num_edus = len(doc.edu_texts)
                outputs = self.model(
                    input_ids=doc.input_ids.to(self.model.dev),
                    attention_mask=doc.attention_mask.to(self.model.dev),
                    edu_starts=doc.edu_starts.to(self.model.dev),
                    edu_ends=doc.edu_ends.to(self.model.dev),
                    gold_splits=doc.gold_splits.to(self.model.dev),
                    gold_nucs=doc.gold_nucs.to(self.model.dev),
                    gold_rels=doc.gold_rels.to(self.model.dev),
                )
                if "loss" in outputs:
                    total_loss += float(outputs["loss"].item())

                # CKY Tree Decoding
                tree_evidence = self.model.decode_document_tree_with_evidence(
                    input_ids=doc.input_ids.to(self.model.dev),
                    attention_mask=doc.attention_mask.to(self.model.dev),
                    edu_starts=doc.edu_starts.to(self.model.dev),
                    edu_ends=doc.edu_ends.to(self.model.dev),
                )
                tree_spans = [item.span for item in tree_evidence]

                gold_spans = extract_bracket_spans_from_gum_node(doc.tree, total_edus=num_edus)
                pred_spans = extract_bracket_spans_from_decoded_spans(tree_spans, total_edus=num_edus)

                all_gold_spans.append(gold_spans)
                all_pred_spans.append(pred_spans)

        elapsed = time.perf_counter() - start_time
        avg_loss = total_loss / max(len(dev_documents), 1)

        # Compute Micro-Averaged Parseval Metrics
        total_gold_spans = sum(len(g) for g in all_gold_spans)
        total_pred_spans = sum(len(p) for p in all_pred_spans)

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
                    if p.relation == g.relation:
                        match_rel += 1
                    if p.nuclearity == g.nuclearity and p.relation == g.relation:
                        match_full += 1

        def _calc_f1(matches: int) -> float:
            prec = matches / max(total_pred_spans, 1)
            rec = matches / max(total_gold_spans, 1)
            return (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        span_f1 = _calc_f1(match_span)
        nuc_f1 = _calc_f1(match_nuc)
        rel_f1 = _calc_f1(match_rel)
        full_f1 = _calc_f1(match_full)

        return TrainingMetricsReceipt(
            epoch=epoch,
            eval_loss=avg_loss,
            span_f1=span_f1,
            nuclearity_f1=nuc_f1,
            relation_f1=rel_f1,
            full_f1=full_f1,
            elapsed_seconds=elapsed,
            model_digest=hashlib.sha256(f"epoch_{epoch}_{span_f1:.6f}".encode("utf-8")).hexdigest(),
        )

    def save_checkpoint(self, path: Path) -> str:
        """Save weights in safetensors format and return cryptographic SHA-256 hex digest."""
        path.parent.mkdir(parents=True, exist_ok=True)
        save_model(self.model, str(path))
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()
