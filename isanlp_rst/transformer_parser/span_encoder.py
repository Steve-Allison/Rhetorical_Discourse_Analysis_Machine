"""Boundary-aware span representations for pure transformer discourse parsing."""

import torch
from torch import nn
import torch.nn.functional as F


class TransformerSpanAttentionPooling(nn.Module):
    """Learned attention pooling over token hidden states within a span."""

    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.query = nn.Linear(hidden_size, 1, bias=False)

    def forward(self, hidden_states: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Pool token representations.

        Args:
            hidden_states: (B, L, D) token embeddings
            mask: (B, L) boolean or binary mask indicating valid tokens

        Returns:
            (B, D) pooled span representations
        """
        scores = self.query(hidden_states).squeeze(-1)
        min_val = torch.finfo(scores.dtype).min
        scores = scores.masked_fill(~mask.bool(), min_val)
        weights = F.softmax(scores, dim=-1).unsqueeze(-1)
        # Clean potential NaNs from all-masked rows
        weights = torch.nan_to_num(weights, nan=0.0)
        return torch.sum(hidden_states * weights, dim=1)


class TransformerBoundarySpanEncoder(nn.Module):
    """Encodes discourse spans using boundary tokens and learned attention pooling.

    Representation: h_span = Proj([h_start; h_end; h_attn; h_end - h_start; h_start * h_end])
    """

    def __init__(self, hidden_size: int, proj_dim: int = 512, dropout: float = 0.1) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.proj_dim = proj_dim
        self.attn_pool = TransformerSpanAttentionPooling(hidden_size)
        self.projection = nn.Sequential(
            nn.Linear(hidden_size * 5, proj_dim),
            nn.LayerNorm(proj_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(proj_dim, proj_dim),
            nn.LayerNorm(proj_dim),
        )

    def encode_spans(
        self,
        sequence_hidden_states: torch.Tensor,
        span_starts: torch.Tensor,
        span_ends: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Encode arbitrary token spans in parallel.

        Args:
            sequence_hidden_states: (B, Seq_Len, Hidden_Dim)
            span_starts: (B, Num_Spans) 0-indexed start token indices
            span_ends: (B, Num_Spans) 0-indexed inclusive end token indices
            attention_mask: (B, Seq_Len) sequence mask

        Returns:
            (B, Num_Spans, Proj_Dim) projected span embeddings
        """
        batch_size, seq_len, hidden_dim = sequence_hidden_states.shape
        num_spans = span_starts.shape[1]

        # Gather start and end vectors
        batch_idx = torch.arange(batch_size, device=sequence_hidden_states.device).unsqueeze(1).expand(-1, num_spans)
        h_start = sequence_hidden_states[batch_idx, span_starts.clamp(0, seq_len - 1)]  # (B, Num_Spans, D)
        h_end = sequence_hidden_states[batch_idx, span_ends.clamp(0, seq_len - 1)]      # (B, Num_Spans, D)

        # Vectorized Span Attention Pooling across all spans
        # Build span token mask: (B, Num_Spans, Seq_Len)
        token_indices = torch.arange(seq_len, device=sequence_hidden_states.device).view(1, 1, seq_len)
        starts = span_starts.unsqueeze(-1)  # (B, Num_Spans, 1)
        ends = span_ends.unsqueeze(-1)      # (B, Num_Spans, 1)
        span_mask = (token_indices >= starts) & (token_indices <= ends) & attention_mask.unsqueeze(1).bool()

        # Compute query scores for all tokens in sequence: (B, Seq_Len) -> (B, 1, Seq_Len)
        scores = self.attn_pool.query(sequence_hidden_states).squeeze(-1).unsqueeze(1)  # (B, 1, Seq_Len)
        scores = scores.expand(-1, num_spans, -1)  # (B, Num_Spans, Seq_Len)

        min_val = torch.finfo(scores.dtype).min
        scores = scores.masked_fill(~span_mask, min_val)
        weights = F.softmax(scores, dim=-1).unsqueeze(-1)  # (B, Num_Spans, Seq_Len, 1)
        weights = torch.nan_to_num(weights, nan=0.0)

        # Weighted sum: (B, Num_Spans, Seq_Len, 1) * (B, 1, Seq_Len, D) -> (B, Num_Spans, D)
        h_attn = torch.sum(weights * sequence_hidden_states.unsqueeze(1), dim=2)

        # Rich multi-relational interaction vector
        h_diff = h_end - h_start
        h_mult = h_start * h_end
        combined = torch.cat([h_start, h_end, h_attn, h_diff, h_mult], dim=-1)  # (B, Num_Spans, 5*D)

        return self.projection(combined)
