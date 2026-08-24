"""eRST-compliant secondary-edge decoding with formal constraints only."""

from collections import Counter
from collections.abc import Callable, Sequence, Set
from dataclasses import dataclass
import math

from isanlp_rst.contracts.analysis import RstAnalysis, SecondaryRelationEdge
from isanlp_rst.contracts.erst import (
    DecodeRejectionReason,
    ErstDecodeReceipt,
    ErstDecoderConfig,
)
from isanlp_rst.erst.candidates import SecondaryEdgeCandidate


@dataclass(frozen=True, slots=True)
class _ScoredCandidate:
    candidate: SecondaryEdgeCandidate
    edge_probability: float
    relation_raw: str
    relation_probability: float
    joint_score: float


@dataclass(frozen=True, slots=True)
class DecodedErstEdges:
    """Decoded edges and their serializable proof receipt."""

    edges: tuple[SecondaryRelationEdge, ...]
    receipt: ErstDecodeReceipt


def _softmax_best(logits: Sequence[float]) -> tuple[int, float]:
    if not logits:
        raise ValueError("each eRST candidate requires raw-relation logits")
    if any(not math.isfinite(logit) for logit in logits):
        raise ValueError("eRST relation logits must be finite")
    maximum = max(logits)
    exponentials = tuple(math.exp(logit - maximum) for logit in logits)
    denominator = sum(exponentials)
    best_index = max(range(len(logits)), key=exponentials.__getitem__)
    return best_index, exponentials[best_index] / denominator


class ErstSecondaryEdgeDecoder:
    """Apply calibrated selection plus only the four formal eRST constraints."""

    def __init__(
        self,
        config: ErstDecoderConfig,
        *,
        ontology_adapter: Callable[[str], str] | None = None,
    ) -> None:
        self.config = config
        self.ontology_adapter = ontology_adapter or (lambda raw_relation: raw_relation)

    def decode_with_receipt(
        self,
        analysis: RstAnalysis,
        candidates: Sequence[SecondaryEdgeCandidate],
        edge_probabilities: Sequence[float],
        relation_logits: Sequence[Sequence[float]],
        *,
        sufficient_signal_ids: Set[str],
        streamed_batch_count: int | None = None,
    ) -> DecodedErstEdges:
        """Decode scores while permitting cycles, crossings, overlap, and unrestricted degree."""

        if not (len(candidates) == len(edge_probabilities) == len(relation_logits)):
            raise ValueError("candidate, edge-probability, and relation-logit counts must match")
        relation_inventory = self.config.raw_relation_inventory
        scored: list[_ScoredCandidate] = []
        below_threshold_count = 0
        for candidate, edge_probability, logits in zip(
            candidates,
            edge_probabilities,
            relation_logits,
            strict=True,
        ):
            if candidate.document_id != analysis.document_id:
                raise ValueError("candidate document identity does not match the analysis")
            if not math.isfinite(edge_probability) or not 0.0 <= edge_probability <= 1.0:
                raise ValueError("eRST edge probabilities must be finite values in [0, 1]")
            if len(logits) != len(relation_inventory):
                raise ValueError("relation-logit width does not match the raw relation inventory")
            relation_index, relation_probability = _softmax_best(logits)
            if edge_probability < self.config.edge_threshold:
                below_threshold_count += 1
                continue
            scored.append(
                _ScoredCandidate(
                    candidate=candidate,
                    edge_probability=edge_probability,
                    relation_raw=relation_inventory[relation_index],
                    relation_probability=relation_probability,
                    joint_score=edge_probability * relation_probability,
                )
            )
        scored.sort(
            key=lambda item: (
                -item.joint_score,
                item.candidate.document_id,
                item.candidate.source_id,
                item.candidate.target_id,
            )
        )

        node_ids = {node.node_id for node in analysis.nodes}
        seen_pairs = {(edge.source_id, edge.target_id) for edge in analysis.secondary_edges}
        rejection_counts: Counter[DecodeRejectionReason] = Counter(
            {reason: 0 for reason in DecodeRejectionReason}
        )
        accepted: list[SecondaryRelationEdge] = []
        for scored_candidate in scored:
            candidate = scored_candidate.candidate
            pair = (candidate.source_id, candidate.target_id)
            reason: DecodeRejectionReason | None = None
            if not any(signal_id in sufficient_signal_ids for signal_id in candidate.signal_ids):
                reason = DecodeRejectionReason.INSUFFICIENT_SIGNAL
            elif candidate.source_id == candidate.target_id:
                reason = DecodeRejectionReason.SELF_LOOP
            elif candidate.source_id not in node_ids or candidate.target_id not in node_ids:
                reason = DecodeRejectionReason.INVENTED_NODE
            elif pair in seen_pairs:
                reason = DecodeRejectionReason.DUPLICATE_DIRECTED_PAIR
            if reason is not None:
                rejection_counts[reason] += 1
                continue
            seen_pairs.add(pair)
            relation_concept = self.ontology_adapter(scored_candidate.relation_raw)
            accepted.append(
                SecondaryRelationEdge(
                    edge_id=f"se_pred_{candidate.source_id}_{candidate.target_id}",
                    source_id=candidate.source_id,
                    target_id=candidate.target_id,
                    relation_raw=scored_candidate.relation_raw,
                    relation_concept=relation_concept,
                    confidence=scored_candidate.edge_probability,
                    calibrated=True,
                )
            )

        batch_count = streamed_batch_count
        if batch_count is None:
            batch_count = 1 if candidates else 0
        receipt = ErstDecodeReceipt(
            candidate_count=len(candidates),
            streamed_batch_count=batch_count,
            below_threshold_count=below_threshold_count,
            accepted_count=len(accepted),
            formal_rejections=dict(rejection_counts),
            output_edge_ids=tuple(edge.edge_id for edge in accepted),
            decoder_config_sha256=self.config.config_sha256,
        )
        return DecodedErstEdges(edges=tuple(accepted), receipt=receipt)

    def decode(
        self,
        analysis: RstAnalysis,
        candidates: Sequence[SecondaryEdgeCandidate],
        edge_probabilities: Sequence[float],
        relation_logits: Sequence[Sequence[float]],
        *,
        sufficient_signal_ids: Set[str],
        streamed_batch_count: int | None = None,
    ) -> tuple[SecondaryRelationEdge, ...]:
        """Return decoded edges for callers that do not persist the receipt themselves."""

        return self.decode_with_receipt(
            analysis,
            candidates,
            edge_probabilities,
            relation_logits,
            sufficient_signal_ids=sufficient_signal_ids,
            streamed_batch_count=streamed_batch_count,
        ).edges


__all__ = [
    "DecodedErstEdges",
    "ErstSecondaryEdgeDecoder",
]
