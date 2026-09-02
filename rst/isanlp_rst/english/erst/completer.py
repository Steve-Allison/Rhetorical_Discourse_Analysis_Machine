"""eRST graph completer: secondary-edge candidate generation and signal anchoring."""

from dataclasses import dataclass
from typing import Any

from isanlp_rst.contracts.analysis import (
    DiscourseSignal,
    RstAnalysis,
)
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.enums import OutputFormalismEnum
from isanlp_rst.contracts.erst import ErstDecoderConfig
from isanlp_rst.erst.candidates import (
    SecondaryEdgeCandidate,
    generate_secondary_edge_candidates,
    iter_candidate_batches,
    iter_secondary_edge_candidates,
)
from isanlp_rst.erst.signals import RuleBasedSignalDetector
from isanlp_rst.erst.decoder import DecodedErstEdges


@dataclass(frozen=True, slots=True)
class CompleterConfig:
    """Configuration for eRST graph completion and candidate filtering."""

    min_confidence_threshold: float = 0.50
    candidate_batch_size: int = 32


@dataclass(frozen=True, slots=True)
class ErstCompletionTrace:
    """Complete bounded scoring and decoding handoff for one graph completion."""

    analysis: RstAnalysis
    signals: tuple[DiscourseSignal, ...]
    candidates: tuple[SecondaryEdgeCandidate, ...]
    edge_probabilities: tuple[float, ...]
    relation_logits: tuple[tuple[float, ...], ...]
    decoded: DecodedErstEdges


class ErstCompleter:
    """Completes classical RST trees into eRST graphs."""

    def __init__(
        self,
        config: CompleterConfig | None = None,
        signal_detector: RuleBasedSignalDetector | None = None,
        decoder_config: ErstDecoderConfig | None = None,
    ) -> None:
        self.config = config or CompleterConfig()
        self.signal_detector = signal_detector or RuleBasedSignalDetector()
        self.decoder_config = decoder_config

    def generate_secondary_candidates(
        self,
        document: RstDocument,
        analysis: RstAnalysis,
        signals: tuple[DiscourseSignal, ...] | None = None,
    ) -> tuple[SecondaryEdgeCandidate, ...]:
        """Delegate every runtime mode to the canonical complete generator."""

        return generate_secondary_edge_candidates(document, analysis, signals=signals)

    def detect_lexical_signals(
        self,
        document: RstDocument,
        analysis: RstAnalysis,
    ) -> list[DiscourseSignal]:
        """Detect all anchored lexical and morphosyntactic signals as orphans."""

        del analysis
        return list(self.signal_detector.detect(document).signals)

    def complete_graph(
        self,
        document: RstDocument,
        primary_analysis: RstAnalysis,
        neural_scorer: Any | None = None,
    ) -> RstAnalysis:
        """Project the evidence-complete completion trace to its final graph."""

        return self.complete_graph_with_evidence(
            document,
            primary_analysis,
            neural_scorer=neural_scorer,
        ).analysis

    def complete_graph_with_evidence(
        self,
        document: RstDocument,
        primary_analysis: RstAnalysis,
        neural_scorer: Any | None = None,
    ) -> ErstCompletionTrace:
        """Complete a graph while retaining every candidate score and disposition."""

        signals = self.detect_lexical_signals(document, primary_analysis)
        secondary_edges = list(primary_analysis.secondary_edges)
        all_candidates: list[SecondaryEdgeCandidate] = []
        all_edge_probs: list[float] = []
        all_rel_logits: list[list[float]] = []
        streamed_batch_count = 0

        if neural_scorer is not None and primary_analysis.nodes:
            from isanlp_rst.erst.pair_encoding import SecondaryEdgeInferenceDataset
            from isanlp_rst.erst.decoder import ErstSecondaryEdgeDecoder
            from isanlp_rst.erst.relations import resolve_gum_relation_concept

            import torch
            from torch.utils.data import DataLoader

            neural_scorer.eval()
            with torch.inference_mode():
                for candidate_batch in iter_candidate_batches(
                    iter_secondary_edge_candidates(
                        document,
                        primary_analysis,
                        signals=tuple(signals),
                    ),
                    batch_size=self.config.candidate_batch_size,
                ):
                    streamed_batch_count += 1
                    all_candidates.extend(candidate_batch)
                    dataset = SecondaryEdgeInferenceDataset(
                        candidate_batch,
                        tokenizer=neural_scorer.tokenizer,
                    )
                    loader = DataLoader(dataset, batch_size=len(candidate_batch), shuffle=False)
                    for batch in loader:
                        src_input_ids = batch["src_input_ids"].to(neural_scorer.dev)
                        src_attention_mask = batch["src_attention_mask"].to(neural_scorer.dev)
                        src_special_tokens_mask = batch["src_special_tokens_mask"].to(neural_scorer.dev)
                        src_offset_mapping = batch["src_offset_mapping"].to(neural_scorer.dev)
                        tgt_input_ids = batch["tgt_input_ids"].to(neural_scorer.dev)
                        tgt_attention_mask = batch["tgt_attention_mask"].to(neural_scorer.dev)
                        tgt_special_tokens_mask = batch["tgt_special_tokens_mask"].to(neural_scorer.dev)
                        tgt_offset_mapping = batch["tgt_offset_mapping"].to(neural_scorer.dev)
                        struct_features = batch["struct_features"].to(neural_scorer.dev)

                        out = neural_scorer(
                            src_input_ids=src_input_ids,
                            src_attention_mask=src_attention_mask,
                            src_special_tokens_mask=src_special_tokens_mask,
                            src_offset_mapping=src_offset_mapping,
                            tgt_input_ids=tgt_input_ids,
                            tgt_attention_mask=tgt_attention_mask,
                            tgt_special_tokens_mask=tgt_special_tokens_mask,
                            tgt_offset_mapping=tgt_offset_mapping,
                            struct_features=struct_features,
                        )

                        all_edge_probs.extend(out["edge_probs"].cpu().tolist())
                        all_rel_logits.extend(out["rel_logits"].cpu().tolist())

            decoder_config = self.decoder_config or ErstDecoderConfig(
                edge_threshold=self.config.min_confidence_threshold,
                raw_relation_inventory=neural_scorer.raw_relation_inventory,
            )
            if decoder_config.raw_relation_inventory != neural_scorer.raw_relation_inventory:
                raise ValueError("eRST decoder and scorer raw relation inventories differ")
            decoder = ErstSecondaryEdgeDecoder(
                decoder_config,
                ontology_adapter=resolve_gum_relation_concept,
            )
            decoded = decoder.decode_with_receipt(
                primary_analysis,
                all_candidates,
                all_edge_probs,
                all_rel_logits,
                sufficient_signal_ids={signal.signal_id for signal in signals if signal.sufficient},
                streamed_batch_count=streamed_batch_count,
            )
            secondary_edges.extend(decoded.edges)
        else:
            decoder_config = self.decoder_config or ErstDecoderConfig(
                edge_threshold=self.config.min_confidence_threshold,
                raw_relation_inventory=("not_used",),
            )
            from isanlp_rst.erst.decoder import ErstSecondaryEdgeDecoder

            decoded = ErstSecondaryEdgeDecoder(decoder_config).decode_with_receipt(
                primary_analysis,
                (),
                (),
                (),
                sufficient_signal_ids=set(),
                streamed_batch_count=0,
            )

        formalism = OutputFormalismEnum.ERST_GRAPH

        analysis = RstAnalysis(
            document_id=primary_analysis.document_id,
            formalism=formalism,
            nodes=primary_analysis.nodes,
            primary_edges=primary_analysis.primary_edges,
            secondary_edges=tuple(secondary_edges),
            signals=tuple(signals),
            provenance=primary_analysis.provenance,
            timing=primary_analysis.timing,
            warnings=primary_analysis.warnings,
            failure_code=primary_analysis.failure_code,
        )
        return ErstCompletionTrace(
            analysis=analysis,
            signals=tuple(signals),
            candidates=tuple(all_candidates),
            edge_probabilities=tuple(all_edge_probs),
            relation_logits=tuple(tuple(values) for values in all_rel_logits),
            decoded=decoded,
        )


__all__ = ["CompleterConfig", "ErstCompleter", "ErstCompletionTrace"]
