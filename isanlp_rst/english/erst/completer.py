"""eRST graph completer: secondary-edge candidate generation and signal anchoring."""

from dataclasses import dataclass

from isanlp_rst.contracts.analysis import (
    DiscourseSignal,
    RstAnalysis,
)
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.enums import (
    AnnotationStatusEnum,
    NodeKindEnum,
    OutputFormalismEnum,
)


@dataclass(frozen=True, slots=True)
class CompleterConfig:
    """Configuration for eRST graph completion and candidate filtering."""

    max_edu_distance: int = 8
    max_candidates_per_document: int = 50
    min_confidence_threshold: float = 0.50


class ErstCompleter:
    """Completes classical RST trees into eRST graphs."""

    def __init__(self, config: CompleterConfig | None = None) -> None:
        self.config = config or CompleterConfig()

    def generate_secondary_candidates(
        self,
        analysis: RstAnalysis,
    ) -> list[tuple[int, int]]:
        """Generate bounded candidate pairs (source_node_id, target_node_id) for secondary relations.

        Applies locality constraints:
        - Must be distinct nodes.
        - Distance in EDU span <= max_edu_distance.
        - Excludes pairs that already have a primary relation edge.
        """
        edu_nodes = [n for n in analysis.nodes if n.kind == NodeKindEnum.EDU]
        if len(edu_nodes) < 2:
            return []

        # Find existing primary connected pairs
        existing_primary_pairs = {
            (edge.parent_id, edge.child_id)
            for edge in analysis.primary_edges
        } | {
            (edge.child_id, edge.parent_id)
            for edge in analysis.primary_edges
        }

        candidates: list[tuple[int, int]] = []
        for i, src in enumerate(edu_nodes):
            src_edu = src.edu_span[0]
            for j, tgt in enumerate(edu_nodes):
                if i == j:
                    continue
                tgt_edu = tgt.edu_span[0]
                if abs(src_edu - tgt_edu) > self.config.max_edu_distance:
                    continue
                if (src.node_id, tgt.node_id) in existing_primary_pairs:
                    continue

                candidates.append((src.node_id, tgt.node_id))
                if len(candidates) >= self.config.max_candidates_per_document:
                    return candidates

        return candidates

    def detect_lexical_signals(
        self,
        document: RstDocument,
        analysis: RstAnalysis,
    ) -> list[DiscourseSignal]:
        """Detect and anchor lexical/discourse marker signals using document tokens."""
        signals: list[DiscourseSignal] = []
        if not document.tokens or not analysis.primary_edges:
            return signals

        # Common discourse marker cues
        dm_cues = {
            "however": ("dm", "dm"),
            "but": ("dm", "dm"),
            "although": ("dm", "dm"),
            "because": ("dm", "dm"),
            "since": ("dm", "dm"),
            "therefore": ("dm", "dm"),
            "furthermore": ("dm", "dm"),
            "in addition": ("dm", "dm"),
            "for example": ("lexical", "indicative_phrase"),
            "for instance": ("lexical", "indicative_phrase"),
        }

        token_text_lower = [t.text.lower() for t in document.tokens]

        sig_counter = 1
        for edge in analysis.primary_edges:
            child_node = analysis.get_node(edge.child_id)
            if child_node is None:
                continue

            child_char_start, child_char_end = child_node.char_span

            # Find tokens within child node span
            node_token_indices = [
                t.token_id
                for t in document.tokens
                if child_char_start <= t.start and t.end <= child_char_end
            ]

            for tok_id in node_token_indices:
                if tok_id < len(token_text_lower):
                    word = token_text_lower[tok_id]
                    if word in dm_cues:
                        sig_type, sig_subtype = dm_cues[word]
                        signals.append(
                            DiscourseSignal(
                                signal_id=f"sig_{sig_counter}",
                                edge_id=edge.edge_id,
                                signal_type=sig_type,
                                signal_subtype=sig_subtype,
                                token_ids=(tok_id,),
                                status=AnnotationStatusEnum.PREDICTED,
                                confidence=0.85,
                            )
                        )
                        sig_counter += 1

        return signals

    def complete_graph(
        self,
        document: RstDocument,
        primary_analysis: RstAnalysis,
    ) -> RstAnalysis:
        """Complete a classical primary tree into an eRST graph with signals."""
        signals = self.detect_lexical_signals(document, primary_analysis)
        formalism = OutputFormalismEnum.ERST_GRAPH if signals or primary_analysis.secondary_edges else primary_analysis.formalism

        return RstAnalysis(
            document_id=primary_analysis.document_id,
            formalism=formalism,
            nodes=primary_analysis.nodes,
            primary_edges=primary_analysis.primary_edges,
            secondary_edges=primary_analysis.secondary_edges,
            signals=tuple(signals),
            provenance=primary_analysis.provenance,
            timing=primary_analysis.timing,
            warnings=primary_analysis.warnings,
            failure_code=primary_analysis.failure_code,
        )
