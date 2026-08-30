"""Pure Transformer Vectorized Discourse Parser (ParsingNetV5)."""

from typing import Any
import torch
from torch import nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer, PretrainedConfig, PreTrainedTokenizerBase

from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION
from isanlp_rst.transformer_parser.span_encoder import TransformerBoundarySpanEncoder
from isanlp_rst.transformer_parser.biaffine_decoder import (
    DeepBiaffineScorer,
    ParsedRstTreeEvidence,
    ParsedRstTreeSpan,
    cky_discourse_tree_decode,
)


class PureTransformerParsingNet(nn.Module):
    """Pure Transformer Vectorized Discourse Tree Parser (ParsingNetV5).

    Eliminates all intermediate BiLSTMs/GRUs and sliding-window RNN decoders.
    Processes full 8,192-token contexts in parallel with hardware-accelerated SDPA/FlashAttention.
    """

    def __init__(
        self,
        model_name_or_path: str = MODERNBERT_BASE_MODEL_ID,
        model_revision: str | None = MODERNBERT_BASE_REVISION,
        raw_relation_inventory: tuple[str, ...] = (),
        nuclearity_labels: tuple[str, ...] = ("NS", "SN", "NN"),
        proj_dim: int = 512,
        device: str | torch.device = "auto",
        torch_dtype: str | torch.dtype = "auto",
        encoder_config: PretrainedConfig | None = None,
        tokenizer: PreTrainedTokenizerBase | None = None,
        local_files_only: bool = False,
    ) -> None:
        super().__init__()
        self.model_name_or_path = model_name_or_path
        self.model_revision = model_revision
        self.raw_relation_inventory = raw_relation_inventory
        self.nuclearity_labels = nuclearity_labels
        self.proj_dim = proj_dim

        # 1. Resolve Device
        if device == "auto":
            if torch.cuda.is_available():
                self.dev = torch.device("cuda")
            elif torch.backends.mps.is_available():
                self.dev = torch.device("mps")
            else:
                self.dev = torch.device("cpu")
        else:
            self.dev = torch.device(device)

        # 2. Resolve Dtype
        if torch_dtype == "auto":
            if self.dev.type in ("cuda", "mps"):
                self.dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            else:
                self.dtype = torch.float32
        elif isinstance(torch_dtype, str):
            dtype_map = {
                "float32": torch.float32,
                "float16": torch.float16,
                "bfloat16": torch.bfloat16,
            }
            self.dtype = dtype_map.get(torch_dtype, torch.float32)
        else:
            self.dtype = torch_dtype

        # 3. Backbone and Tokenizer
        revision_kwargs = {"revision": self.model_revision} if self.model_revision is not None else {}
        loading_kwargs = {
            **revision_kwargs,
            "local_files_only": local_files_only,
        }
        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(
            model_name_or_path,
            use_fast=True,
            **loading_kwargs,
        )
        if encoder_config is None:
            self.encoder = AutoModel.from_pretrained(
                model_name_or_path,
                dtype=self.dtype,
                use_safetensors=True,
                **loading_kwargs,
            ).to(self.dev)
        else:
            self.encoder = AutoModel.from_config(
                encoder_config,
                dtype=self.dtype,
            ).to(self.dev)

        hidden_size = getattr(self.encoder.config, "hidden_size", 768)
        if not isinstance(hidden_size, int) or hidden_size <= 0:
            raise ValueError("encoder config requires a positive integer hidden_size")

        # 4. Boundary Span Encoder
        self.span_encoder = TransformerBoundarySpanEncoder(hidden_size, proj_dim=proj_dim).to(
            device=self.dev, dtype=self.dtype
        )

        # 5. Biaffine Heads for Tree Attachment, Nuclearity, and Relations
        self.split_head = DeepBiaffineScorer(proj_dim, num_classes=1).to(device=self.dev, dtype=self.dtype)
        self.nuc_head = DeepBiaffineScorer(proj_dim, num_classes=len(nuclearity_labels)).to(
            device=self.dev, dtype=self.dtype
        )
        self.rel_head = DeepBiaffineScorer(proj_dim, num_classes=len(raw_relation_inventory)).to(
            device=self.dev, dtype=self.dtype
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        edu_starts: torch.Tensor,
        edu_ends: torch.Tensor,
        gold_splits: torch.Tensor | None = None,
        gold_nucs: torch.Tensor | None = None,
        gold_rels: torch.Tensor | None = None,
    ) -> dict[str, Any]:
        """Compute full discourse tree representations, biaffine scores, and multi-task loss."""
        # 1. Forward through transformer backbone
        hidden_states = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state

        # 2. Encode all EDUs in sequence
        edu_reprs = self.span_encoder.encode_spans(
            hidden_states,
            edu_starts,
            edu_ends,
            attention_mask,
        )  # (B, Num_EDUs, Proj_Dim)

        batch_size, num_edus, _ = edu_reprs.shape

        # 3. Vectorized Pairwise Span Scoring across all (i, j) combinations
        left_expanded = edu_reprs.unsqueeze(2).expand(-1, -1, num_edus, -1).reshape(batch_size, num_edus * num_edus, -1)
        right_expanded = edu_reprs.unsqueeze(1).expand(-1, num_edus, -1, -1).reshape(batch_size, num_edus * num_edus, -1)

        split_scores = self.split_head(left_expanded, right_expanded).view(batch_size, num_edus, num_edus)
        nuc_scores = self.nuc_head(left_expanded, right_expanded).view(batch_size, num_edus, num_edus, len(self.nuclearity_labels))
        rel_scores = self.rel_head(left_expanded, right_expanded).view(batch_size, num_edus, num_edus, len(self.raw_relation_inventory))

        results: dict[str, Any] = {
            "edu_reprs": edu_reprs,
            "split_scores": split_scores,
            "nuc_scores": nuc_scores,
            "rel_scores": rel_scores,
        }

        # 4. Joint Multi-Task Loss Computation if supervision is provided
        if gold_splits is not None and gold_nucs is not None and gold_rels is not None:
            gold_splits = gold_splits.to(device=self.dev)
            gold_nucs = gold_nucs.to(device=self.dev)
            gold_rels = gold_rels.to(device=self.dev)

            # Mask valid constituent spans (i < j)
            mask = torch.triu(torch.ones((num_edus, num_edus), device=self.dev), diagonal=1).bool()
            valid_splits = split_scores[:, mask]
            target_splits = gold_splits[:, mask]
            loss_split = F.binary_cross_entropy_with_logits(valid_splits, target_splits.to(dtype=self.dtype))

            valid_nuc_scores = nuc_scores[:, mask].reshape(-1, len(self.nuclearity_labels))
            target_nucs = gold_nucs[:, mask].reshape(-1)
            loss_nuc = F.cross_entropy(valid_nuc_scores, target_nucs, ignore_index=-100)

            valid_rel_scores = rel_scores[:, mask].reshape(-1, len(self.raw_relation_inventory))
            target_rels = gold_rels[:, mask].reshape(-1)
            loss_rel = F.cross_entropy(valid_rel_scores, target_rels, ignore_index=-100)

            loss_total = loss_split + loss_nuc + (1.2 * loss_rel)
            results["loss"] = loss_total
            results["loss_split"] = loss_split
            results["loss_nuc"] = loss_nuc
            results["loss_rel"] = loss_rel

        return results

    def decode_document_tree(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        edu_starts: torch.Tensor,
        edu_ends: torch.Tensor,
    ) -> list[ParsedRstTreeSpan]:
        """Decode a single document into an optimal projective RST discourse tree."""
        return [item.span for item in self.decode_document_tree_with_evidence(
            input_ids=input_ids,
            attention_mask=attention_mask,
            edu_starts=edu_starts,
            edu_ends=edu_ends,
        )]

    def decode_document_tree_with_evidence(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        edu_starts: torch.Tensor,
        edu_ends: torch.Tensor,
    ) -> list[ParsedRstTreeEvidence]:
        """Decode and retain only scores needed to explain selected decisions."""

        self.eval()
        with torch.inference_mode():
            outputs = self.forward(input_ids, attention_mask, edu_starts, edu_ends)
            split_scores = outputs["split_scores"][0]  # (N, N)
            nuc_scores = outputs["nuc_scores"][0]      # (N, N, Num_Nuc)
            rel_scores = outputs["rel_scores"][0]      # (N, N, Num_Rel)

            tree = cky_discourse_tree_decode(
                split_scores.float(),
                nuc_scores.float(),
                rel_scores.float(),
                self.nuclearity_labels,
                self.raw_relation_inventory,
            )
            evidence: list[ParsedRstTreeEvidence] = []
            for span in tree:
                split_candidates = tuple(range(span.start, span.end))
                split_logits = tuple(
                    float(
                        (
                            split_scores[span.start, split]
                            + split_scores[split + 1, span.end]
                        ).float().item()
                    )
                    for split in split_candidates
                )
                evidence.append(
                    ParsedRstTreeEvidence(
                        span=span,
                        split_candidates=split_candidates,
                        split_logits=split_logits,
                        nuclearity_logits=tuple(
                            float(value) for value in nuc_scores[span.start, span.end].float().tolist()
                        ),
                        relation_logits=tuple(
                            float(value) for value in rel_scores[span.start, span.end].float().tolist()
                        ),
                    )
                )
            return evidence
