"""Pure Transformer Vectorized Discourse Parser package."""

from rdam.rst.transformer_parser.biaffine_decoder import (
    DeepBiaffineScorer,
    ParsedRstTreeSpan,
    cky_discourse_tree_decode,
)
from rdam.rst.transformer_parser.model import PureTransformerParsingNet
from rdam.rst.transformer_parser.predictor import PredictorModernBERT
from rdam.rst.transformer_parser.span_encoder import (
    TransformerBoundarySpanEncoder,
    TransformerSpanAttentionPooling,
)

__all__ = [
    "DeepBiaffineScorer",
    "ParsedRstTreeSpan",
    "PredictorModernBERT",
    "PureTransformerParsingNet",
    "TransformerBoundarySpanEncoder",
    "TransformerSpanAttentionPooling",
    "cky_discourse_tree_decode",
]
