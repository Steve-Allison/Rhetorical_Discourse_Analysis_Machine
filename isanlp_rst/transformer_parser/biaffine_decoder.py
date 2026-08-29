"""Vectorized deep biaffine attention and dynamic CKY discourse tree decoding."""

from dataclasses import dataclass
import math
import torch
from torch import nn


@dataclass(frozen=True, slots=True)
class ParsedRstTreeSpan:
    """A constituent span in the decoded RST discourse tree."""

    start: int
    end: int
    split: int
    nuclearity: str
    relation: str
    score: float


class DeepBiaffineScorer(nn.Module):
    """Deep Biaffine Scoring for span splitting, nuclearity, and rhetorical relations.

    Computes: S(u, v) = u^T W v + U u + V v + b
    """

    def __init__(self, in_features: int, num_classes: int, bias_u: bool = True, bias_v: bool = True) -> None:
        super().__init__()
        self.in_features = in_features
        self.num_classes = num_classes
        self.weight = nn.Parameter(torch.empty(num_classes, in_features, in_features))
        self.bias_u = nn.Parameter(torch.empty(num_classes, in_features)) if bias_u else None
        self.bias_v = nn.Parameter(torch.empty(num_classes, in_features)) if bias_v else None
        self.bias = nn.Parameter(torch.empty(num_classes))
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.weight)
        if self.bias_u is not None:
            nn.init.zeros_(self.bias_u)
        if self.bias_v is not None:
            nn.init.zeros_(self.bias_v)
        nn.init.zeros_(self.bias)

    def forward(self, left_spans: torch.Tensor, right_spans: torch.Tensor) -> torch.Tensor:
        """Score pairs of adjacent spans (left, right).

        Args:
            left_spans: (B, N, D)
            right_spans: (B, N, D)

        Returns:
            (B, N, num_classes) or (B, N) if num_classes == 1
        """
        # left_spans: (B, N, D), right_spans: (B, N, D)
        # Bilinear term: left^T W right -> (B, N, num_classes)
        # Using torch.einsum: 'bni,cij,bnj->bnc'
        bilinear = torch.einsum("bni,cij,bnj->bnc", left_spans, self.weight, right_spans)

        if self.bias_u is not None:
            # left * bias_u^T: (B, N, D) * (num_classes, D) -> (B, N, num_classes)
            bilinear = bilinear + torch.einsum("bni,ci->bnc", left_spans, self.bias_u)

        if self.bias_v is not None:
            # right * bias_v^T: (B, N, D) * (num_classes, D) -> (B, N, num_classes)
            bilinear = bilinear + torch.einsum("bnj,cj->bnc", right_spans, self.bias_v)

        bilinear = bilinear + self.bias.view(1, 1, self.num_classes)

        if self.num_classes == 1:
            return bilinear.squeeze(-1)
        return bilinear


def cky_discourse_tree_decode(
    split_scores: torch.Tensor,
    nuc_scores: torch.Tensor,
    rel_scores: torch.Tensor,
    nuclearity_labels: tuple[str, ...],
    relation_labels: tuple[str, ...],
) -> list[ParsedRstTreeSpan]:
    """Exact CKY dynamic programming chart decoder for hierarchical RST discourse trees.

    Args:
        split_scores: (Num_EDUs, Num_EDUs) pairwise span scores or (Num_EDUs, Num_EDUs, Num_EDUs) 3D split chart
        nuc_scores: (Num_EDUs, Num_EDUs, Num_Nuclearities) nuclearity classification scores
        rel_scores: (Num_EDUs, Num_EDUs, Num_Relations) relation classification scores
        nuclearity_labels: tuple of nuclearity strings (e.g. ('NS', 'SN', 'NN'))
        relation_labels: tuple of raw relation strings

    Returns:
        List of decoded tree spans in top-down hierarchy.
    """
    n = split_scores.shape[0]
    is_2d_split = split_scores.ndim == 2

    # dp_chart[i][j] holds max score for span (i, j)
    dp_chart = torch.full((n, n), -math.inf, device=split_scores.device, dtype=torch.float32)
    split_chart = torch.zeros((n, n), dtype=torch.long, device=split_scores.device)
    nuc_chart = torch.zeros((n, n), dtype=torch.long, device=split_scores.device)
    rel_chart = torch.zeros((n, n), dtype=torch.long, device=split_scores.device)

    # Base cases: spans of length 1 (single EDUs)
    for i in range(n):
        dp_chart[i, i] = 0.0

    # Fill chart by span length (length 2 to n)
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            k = i + length - 1  # end index (inclusive)

            best_score = -math.inf
            best_j = i
            best_nuc = 0
            best_rel = 0

            # Best nuclearity and relation for span (i, k) are invariant to split point j
            nuc_max_idx = int(torch.argmax(nuc_scores[i, k]).item())
            nuc_max_val = float(nuc_scores[i, k, nuc_max_idx].item())

            rel_max_idx = int(torch.argmax(rel_scores[i, k]).item())
            rel_max_val = float(rel_scores[i, k, rel_max_idx].item())

            span_base_score = nuc_max_val + rel_max_val

            # Find best split point j where i <= j < k
            for j in range(i, k):
                left_score = dp_chart[i, j]
                right_score = dp_chart[j + 1, k]
                split_score = (split_scores[i, j] + split_scores[j + 1, k]) if is_2d_split else split_scores[i, j, k]

                total = left_score + right_score + split_score + span_base_score
                if total > best_score:
                    best_score = total
                    best_j = j
                    best_nuc = nuc_max_idx
                    best_rel = rel_max_idx

            dp_chart[i, k] = best_score
            split_chart[i, k] = best_j
            nuc_chart[i, k] = best_nuc
            rel_chart[i, k] = best_rel

    # Reconstruct tree spans top-down
    tree_spans: list[ParsedRstTreeSpan] = []

    def _reconstruct(start: int, end: int) -> None:
        if start >= end:
            return
        split = int(split_chart[start, end].item())
        nuc_idx = int(nuc_chart[start, end].item())
        rel_idx = int(rel_chart[start, end].item())
        score = float(dp_chart[start, end].item())

        tree_spans.append(
            ParsedRstTreeSpan(
                start=start,
                end=end,
                split=split,
                nuclearity=nuclearity_labels[nuc_idx],
                relation=relation_labels[rel_idx],
                score=score,
            )
        )
        _reconstruct(start, split)
        _reconstruct(split + 1, end)

    _reconstruct(0, n - 1)
    return tree_spans
