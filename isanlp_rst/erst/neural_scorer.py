"""Neural Secondary Edge Scorer with boundary-aware span pooling and asymmetric bilinear attention."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from isanlp_rst.erst.dataset import COARSE_CONCEPTS


class AttentionPooling(nn.Module):
    """Learned attention pooling over sequence representations."""

    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.query = nn.Linear(hidden_size, 1, bias=False)

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        # hidden_states: (B, L, D), attention_mask: (B, L)
        scores = self.query(hidden_states).squeeze(-1)  # (B, L)
        scores = scores.masked_fill(attention_mask == 0, -1e9)
        weights = F.softmax(scores, dim=-1).unsqueeze(-1)  # (B, L, 1)
        pooled = torch.sum(hidden_states * weights, dim=1)  # (B, D)
        return pooled


class BoundaryAwareSpanEncoder(nn.Module):
    """Encodes a span using boundary tokens (start, end) and learned attention pooling."""

    def __init__(self, hidden_size: int, proj_dim: int = 256) -> None:
        super().__init__()
        self.attn_pool = AttentionPooling(hidden_size)
        self.proj = nn.Sequential(
            nn.Linear(hidden_size * 3, proj_dim),
            nn.LayerNorm(proj_dim),
            nn.GELU(),
            nn.Dropout(0.1),
        )

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        # 1. Extract first and last non-special tokens
        batch_size, seq_len, _ = hidden_states.shape

        # Start token (index 1 if [CLS] is at 0, else 0)
        h_start = hidden_states[:, 1 if seq_len > 1 else 0]

        # End token (last non-padding index)
        lengths = attention_mask.sum(dim=-1).long() - 1
        lengths = torch.clamp(lengths, min=0)
        h_end = hidden_states[torch.arange(batch_size, device=hidden_states.device), lengths]

        # 2. Attention pooled representation
        h_attn = self.attn_pool(hidden_states, attention_mask)

        # 3. Concatenate and project
        h_concat = torch.cat([h_start, h_end, h_attn], dim=-1)
        return self.proj(h_concat)


class NeuralSecondaryEdgeScorer(nn.Module):
    """Joint Multi-Task Neural Scorer for eRST Secondary Discourse Edges.

    Predicts:
    1. Edge existence probability P(edge | u, v) via asymmetric bilinear + MLP scoring.
    2. Coarse rhetorical relation distribution over canonical concepts.
    """

    def __init__(
        self,
        model_name_or_path: str = "microsoft/deberta-v3-base",
        num_struct_features: int = 9,
        proj_dim: int = 256,
        num_relations: int = len(COARSE_CONCEPTS),
        device: str | torch.device = "auto",
        torch_dtype: str | torch.dtype = "auto",
    ) -> None:
        super().__init__()
        self.model_name_or_path = model_name_or_path
        self.num_relations = num_relations

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
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)
        self.encoder = AutoModel.from_pretrained(
            model_name_or_path,
            torch_dtype=self.dtype,
        ).to(self.dev)
        hidden_size = self.encoder.config.hidden_size

        # 4. Boundary-Aware Span Encoder
        self.span_encoder = BoundaryAwareSpanEncoder(hidden_size, proj_dim=proj_dim).to(
            device=self.dev, dtype=self.dtype
        )

        # 5. Asymmetric Bilinear Scorer: h_u^T W h_v
        self.bilinear = nn.Bilinear(proj_dim, proj_dim, 1, bias=False).to(device=self.dev, dtype=self.dtype)

        # 6. Pairwise Deep MLP: [h_u; h_v; h_u * h_v; |h_u - h_v|; f_struct]
        mlp_in_dim = (proj_dim * 4) + num_struct_features
        self.pairwise_mlp = nn.Sequential(
            nn.Linear(mlp_in_dim, proj_dim),
            nn.LayerNorm(proj_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(proj_dim, proj_dim // 2),
            nn.GELU(),
        ).to(device=self.dev, dtype=self.dtype)

        # 7. Multi-Task Output Heads
        self.edge_head = nn.Linear(proj_dim // 2, 1).to(device=self.dev, dtype=self.dtype)
        self.rel_head = nn.Linear(proj_dim // 2, num_relations).to(device=self.dev, dtype=self.dtype)

    def forward(
        self,
        src_input_ids: torch.Tensor,
        src_attention_mask: torch.Tensor,
        tgt_input_ids: torch.Tensor,
        tgt_attention_mask: torch.Tensor,
        struct_features: torch.Tensor,
        edge_label: torch.Tensor | None = None,
        rel_label: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        """Compute existence logit, relation logits, and multi-task loss."""
        # 1. Cast struct_features to model dtype
        struct_features = struct_features.to(device=self.dev, dtype=self.dtype)

        # 2. Encode source and target spans
        src_out = self.encoder(input_ids=src_input_ids, attention_mask=src_attention_mask).last_hidden_state
        tgt_out = self.encoder(input_ids=tgt_input_ids, attention_mask=tgt_attention_mask).last_hidden_state

        h_u = self.span_encoder(src_out, src_attention_mask)  # (B, proj_dim)
        h_v = self.span_encoder(tgt_out, tgt_attention_mask)  # (B, proj_dim)

        # 2. Compute asymmetric bilinear term
        bilinear_score = self.bilinear(h_u, h_v)  # (B, 1)

        # 3. Construct rich pairwise interaction vector
        h_mult = h_u * h_v
        h_diff = torch.abs(h_u - h_v)
        pair_vec = torch.cat([h_u, h_v, h_mult, h_diff, struct_features], dim=-1)

        # 4. Forward through Pairwise MLP
        mlp_repr = self.pairwise_mlp(pair_vec)

        # 5. Predictions
        edge_logits = (bilinear_score + self.edge_head(mlp_repr)).squeeze(-1)  # (B,)
        rel_logits = self.rel_head(mlp_repr)  # (B, num_relations)
        edge_probs = torch.sigmoid(edge_logits)

        result: dict[str, torch.Tensor] = {
            "edge_logits": edge_logits,
            "edge_probs": edge_probs,
            "rel_logits": rel_logits,
        }

        # 6. Joint Loss Computation if labels provided
        if edge_label is not None:
            # Focal Loss for edge existence: FL(p_t) = -alpha * (1 - p_t)^gamma * log(p_t)
            gamma = 2.0
            alpha = 0.75
            bce_loss = F.binary_cross_entropy_with_logits(edge_logits, edge_label, reduction="none")
            p_t = torch.exp(-bce_loss)
            focal_weights = alpha * (1.0 - p_t) ** gamma
            loss_edge = (focal_weights * bce_loss).mean()

            loss_total = loss_edge

            # Masked Cross-Entropy for relation classification on positive pairs
            if rel_label is not None:
                pos_mask = (edge_label == 1.0) & (rel_label != -100)
                if pos_mask.sum() > 0:
                    loss_rel = F.cross_entropy(rel_logits[pos_mask], rel_label[pos_mask])
                    loss_total = loss_edge + (1.2 * loss_rel)
                else:
                    loss_rel = torch.tensor(0.0, device=edge_logits.device)
                result["loss_rel"] = loss_rel

            result["loss_edge"] = loss_edge
            result["loss"] = loss_total

        return result
