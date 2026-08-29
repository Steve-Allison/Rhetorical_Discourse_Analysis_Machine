"""Neural Secondary Edge Scorer with boundary-aware span pooling and asymmetric bilinear attention."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer, PretrainedConfig, PreTrainedTokenizerBase

from isanlp_rst.model_authority import MODERNBERT_BASE_MODEL_ID, MODERNBERT_BASE_REVISION


class AttentionPooling(nn.Module):
    """Learned attention pooling over sequence representations."""

    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.query = nn.Linear(hidden_size, 1, bias=False)

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        # hidden_states: (B, L, D), attention_mask: (B, L)
        scores = self.query(hidden_states).squeeze(-1)  # (B, L)
        min_val = torch.finfo(scores.dtype).min
        scores = scores.masked_fill(attention_mask == 0, min_val)
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

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
        special_tokens_mask: torch.Tensor,
        offset_mapping: torch.Tensor,
    ) -> torch.Tensor:
        batch_size, seq_len, _ = hidden_states.shape
        if attention_mask.shape != (batch_size, seq_len):
            raise ValueError("attention mask shape must match boundary encoder sequence dimensions")
        if special_tokens_mask.shape != (batch_size, seq_len):
            raise ValueError("special-token mask shape must match boundary encoder sequence dimensions")
        if offset_mapping.shape != (batch_size, seq_len, 2):
            raise ValueError("offset mapping shape must be [batch, sequence, 2]")

        lexical_mask = (
            attention_mask.bool()
            & ~special_tokens_mask.bool()
            & (offset_mapping[..., 1] > offset_mapping[..., 0])
        )
        if not bool(torch.all(lexical_mask.any(dim=1)).item()):
            raise ValueError("every encoded span must contain at least one lexical token")
        first_indices = lexical_mask.to(dtype=torch.int64).argmax(dim=1)
        last_indices = seq_len - 1 - lexical_mask.flip(dims=(1,)).to(dtype=torch.int64).argmax(dim=1)
        batch_indices = torch.arange(batch_size, device=hidden_states.device)
        h_start = hidden_states[batch_indices, first_indices]
        h_end = hidden_states[batch_indices, last_indices]

        # 2. Attention pooled representation
        h_attn = self.attn_pool(hidden_states, lexical_mask)

        # 3. Concatenate and project
        h_concat = torch.cat([h_start, h_end, h_attn], dim=-1)
        return self.proj(h_concat)


class NeuralSecondaryEdgeScorer(nn.Module):
    """Joint Multi-Task Neural Scorer for eRST Secondary Discourse Edges.

    Predicts:
    1. Edge existence probability P(edge | u, v) via asymmetric bilinear + MLP scoring.
    2. Raw GUM eRST rhetorical relation distribution.

    The relation inventory is mandatory because the scorer head is a corpus-derived
    contract. Falling back to the historical 18 ontology concepts would silently
    train and decode a different task.
    """

    def __init__(
        self,
        model_name_or_path: str = MODERNBERT_BASE_MODEL_ID,
        model_revision: str | None = None,
        num_struct_features: int = 9,
        proj_dim: int = 256,
        num_relations: int | None = None,
        raw_relation_inventory: tuple[str, ...] | None = None,
        device: str | torch.device = "auto",
        torch_dtype: str | torch.dtype = "auto",
        encoder_config: PretrainedConfig | None = None,
        tokenizer: PreTrainedTokenizerBase | None = None,
        calibration_temperature: float = 1.0,
    ) -> None:
        super().__init__()
        self.model_name_or_path = model_name_or_path
        self.model_revision = (
            MODERNBERT_BASE_REVISION
            if model_revision is None and model_name_or_path == MODERNBERT_BASE_MODEL_ID
            else model_revision
        )
        self.num_struct_features = num_struct_features
        self.proj_dim = proj_dim
        if not calibration_temperature > 0.0:
            raise ValueError("calibration temperature must be positive")
        self.calibration_temperature = calibration_temperature
        if raw_relation_inventory is None:
            raise ValueError("scorer requires an explicit train-derived raw relation inventory")
        self.raw_relation_inventory = raw_relation_inventory
        if not self.raw_relation_inventory or len(self.raw_relation_inventory) != len(
            set(self.raw_relation_inventory)
        ):
            raise ValueError("scorer raw relation inventory must be non-empty and unique")
        resolved_num_relations = (
            len(self.raw_relation_inventory) if num_relations is None else num_relations
        )
        if resolved_num_relations != len(self.raw_relation_inventory):
            raise ValueError("relation head width must match the raw relation inventory")
        self.num_relations = resolved_num_relations

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
        self.tokenizer = tokenizer or AutoTokenizer.from_pretrained(
            model_name_or_path,
            use_fast=True,
            **revision_kwargs,
        )
        if not self.tokenizer.is_fast:
            raise ValueError("eRST scoring requires a verified fast tokenizer artifact")
        if encoder_config is None:
            self.encoder = AutoModel.from_pretrained(
                model_name_or_path,
                dtype=self.dtype,
                use_safetensors=True,
                **revision_kwargs,
            ).to(self.dev)
        else:
            self.encoder = AutoModel.from_config(
                encoder_config,
                dtype=self.dtype,
            ).to(self.dev)
        hidden_size = getattr(self.encoder.config, "hidden_size", None)
        if not isinstance(hidden_size, int) or hidden_size <= 0:
            raise ValueError("eRST encoder config requires a positive integer hidden_size")

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
        self.rel_head = nn.Linear(proj_dim // 2, resolved_num_relations).to(device=self.dev, dtype=self.dtype)

    def set_runtime_device(
        self,
        device: str | torch.device,
        *,
        torch_dtype: torch.dtype | None = None,
    ) -> "NeuralSecondaryEdgeScorer":
        """Move the complete scorer while keeping its runtime contract synchronized."""

        if device == "auto":
            if torch.cuda.is_available():
                resolved_device = torch.device("cuda")
            elif torch.backends.mps.is_available():
                resolved_device = torch.device("mps")
            else:
                resolved_device = torch.device("cpu")
        else:
            resolved_device = torch.device(device)
        resolved_dtype = torch_dtype or self.dtype
        self.to(device=resolved_device, dtype=resolved_dtype)
        self.dev = resolved_device
        self.dtype = resolved_dtype
        return self

    def forward(
        self,
        src_input_ids: torch.Tensor,
        src_attention_mask: torch.Tensor,
        src_special_tokens_mask: torch.Tensor,
        src_offset_mapping: torch.Tensor,
        tgt_input_ids: torch.Tensor,
        tgt_attention_mask: torch.Tensor,
        tgt_special_tokens_mask: torch.Tensor,
        tgt_offset_mapping: torch.Tensor,
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

        h_u = self.span_encoder(
            src_out,
            src_attention_mask,
            src_special_tokens_mask,
            src_offset_mapping,
        )
        h_v = self.span_encoder(
            tgt_out,
            tgt_attention_mask,
            tgt_special_tokens_mask,
            tgt_offset_mapping,
        )

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
        edge_probs = torch.sigmoid(edge_logits / self.calibration_temperature)

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
