"""Discourse marker feature priming and relation classification refinement for English RST."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from isanlp_rst.contracts.analysis import (
    DiscourseSignal,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
)
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.enums import (
    AnnotationStatusEnum,
    NuclearityPatternEnum,
)


@dataclass(frozen=True, slots=True)
class MarkerRule:
    """A discourse connective rule mapping lexical cues to canonical relation concepts."""

    cue: str
    coarse_concept: str
    fine_label: str
    default_nuclearity: NuclearityPatternEnum
    is_multiword: bool = False


# Canonical English discourse marker inventory mapped to central.lock.yaml concepts
DISCOURSE_MARKER_RULES: tuple[MarkerRule, ...] = (
    # Contrast / Adversative
    MarkerRule("however", "Contrast", "contrast", NuclearityPatternEnum.NS),
    MarkerRule("nevertheless", "Contrast", "contrast", NuclearityPatternEnum.NS),
    MarkerRule("nonetheless", "Contrast", "contrast", NuclearityPatternEnum.NS),
    MarkerRule("in contrast", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("on the other hand", "Contrast", "contrast", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("on the contrary", "Contrast", "antithesis", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("although", "Contrast", "concession", NuclearityPatternEnum.SN),
    MarkerRule("even though", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("even if", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("despite", "Contrast", "concession", NuclearityPatternEnum.SN),
    MarkerRule("in spite of", "Contrast", "concession", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("whereas", "Contrast", "contrast", NuclearityPatternEnum.NN),
    MarkerRule("while", "Contrast", "contrast", NuclearityPatternEnum.SN),
    MarkerRule("yet", "Contrast", "contrast", NuclearityPatternEnum.NS),
    MarkerRule("but", "Contrast", "contrast", NuclearityPatternEnum.NS),
    MarkerRule("conversely", "Contrast", "contrast", NuclearityPatternEnum.NS),

    # Cause / Causal
    MarkerRule("as a result", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("consequently", "Cause", "result", NuclearityPatternEnum.NS),
    MarkerRule("therefore", "Cause", "result", NuclearityPatternEnum.NS),
    MarkerRule("thus", "Cause", "result", NuclearityPatternEnum.NS),
    MarkerRule("hence", "Cause", "result", NuclearityPatternEnum.NS),
    MarkerRule("because", "Cause", "cause", NuclearityPatternEnum.SN),
    MarkerRule("due to", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("owing to", "Cause", "cause", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("for this reason", "Cause", "result", NuclearityPatternEnum.NS, is_multiword=True),

    # Condition / Contingency
    MarkerRule("if", "Condition", "condition", NuclearityPatternEnum.SN),
    MarkerRule("unless", "Condition", "condition", NuclearityPatternEnum.SN),
    MarkerRule("provided that", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("as long as", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("assuming that", "Condition", "condition", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("in case", "Condition", "contingency", NuclearityPatternEnum.SN, is_multiword=True),
    MarkerRule("otherwise", "Condition", "otherwise", NuclearityPatternEnum.NS),

    # Explanation / Evidence
    MarkerRule("for example", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("for instance", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("specifically", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS),
    MarkerRule("in fact", "Explanation", "evidence", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("indeed", "Explanation", "evidence", NuclearityPatternEnum.NS),
    MarkerRule("namely", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS),
    MarkerRule("that is", "Elaboration", "elaboration-additional", NuclearityPatternEnum.NS, is_multiword=True),

    # Enablement / Purpose
    MarkerRule("in order to", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("so that", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("so as to", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("to that end", "Enablement", "purpose", NuclearityPatternEnum.NS, is_multiword=True),

    # Temporal / Sequence
    MarkerRule("firstly", "Temporal", "sequence", NuclearityPatternEnum.NN),
    MarkerRule("secondly", "Temporal", "sequence", NuclearityPatternEnum.NN),
    MarkerRule("subsequently", "Temporal", "sequence", NuclearityPatternEnum.NN),
    MarkerRule("afterwards", "Temporal", "sequence", NuclearityPatternEnum.NN),
    MarkerRule("after that", "Temporal", "sequence", NuclearityPatternEnum.NN, is_multiword=True),
    MarkerRule("meanwhile", "Temporal", "temporal-same-time", NuclearityPatternEnum.NN),
    MarkerRule("simultaneously", "Temporal", "temporal-same-time", NuclearityPatternEnum.NN),
    MarkerRule("as soon as", "Temporal", "temporal-before", NuclearityPatternEnum.SN, is_multiword=True),

    # Joint / List
    MarkerRule("furthermore", "Joint", "list", NuclearityPatternEnum.NN),
    MarkerRule("moreover", "Joint", "list", NuclearityPatternEnum.NN),
    MarkerRule("in addition", "Joint", "list", NuclearityPatternEnum.NN, is_multiword=True),
    MarkerRule("additionally", "Joint", "list", NuclearityPatternEnum.NN),
    MarkerRule("besides", "Joint", "list", NuclearityPatternEnum.NN),

    # Comparison
    MarkerRule("similarly", "Comparison", "comparison", NuclearityPatternEnum.NN),
    MarkerRule("likewise", "Comparison", "comparison", NuclearityPatternEnum.NN),
    MarkerRule("in the same way", "Comparison", "comparison", NuclearityPatternEnum.NN, is_multiword=True),

    # Summary
    MarkerRule("in conclusion", "Summary", "summary", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("in summary", "Summary", "summary", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("to summarize", "Summary", "summary", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("to sum up", "Summary", "summary", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("in short", "Summary", "summary", NuclearityPatternEnum.NS, is_multiword=True),
    MarkerRule("overall", "Summary", "summary", NuclearityPatternEnum.NS),
)


class DiscourseMarkerPrimer:
    """Detects explicit discourse connectives and primes/refines rhetorical relation labels."""

    def __init__(self, rules: Sequence[MarkerRule] | None = None) -> None:
        self.rules = tuple(rules or DISCOURSE_MARKER_RULES)
        # Sort rules with multiword first so longest cues match first
        self.sorted_rules = sorted(self.rules, key=lambda r: len(r.cue), reverse=True)

    def find_cue_in_text(self, text: str) -> tuple[MarkerRule, int, int] | None:
        """Find matching discourse cue at start of text or following punctuation.

        Returns (MarkerRule, match_start, match_end) or None.
        """
        clean_text = text.lstrip()
        leading_ws = len(text) - len(clean_text)
        text_lower = clean_text.lower()

        for rule in self.sorted_rules:
            cue = rule.cue.lower()
            pattern = r"(?:^|[;,\.]\s*)\b" + re.escape(cue) + r"\b"
            match = re.search(pattern, text_lower)
            if match:
                # Find exact start of cue within matched string
                cue_start_in_match = match.group(0).lower().find(cue)
                start_pos = leading_ws + match.start() + cue_start_in_match
                end_pos = start_pos + len(cue)
                return rule, start_pos, end_pos

        return None

    def prime_analysis(
        self,
        analysis: RstAnalysis,
        document: RstDocument,
        min_model_confidence_to_override: float = 0.90,
    ) -> RstAnalysis:
        """Refine relation labels on primary edges where explicit discourse markers are present.

        If a strong discourse marker (e.g. 'however', 'because') is detected at the start of a child span
        and the model's predicted relation is generic or low-confidence, primes the relation concept
        to the unambiguous marker prior and attaches a DiscourseSignal.
        """
        if not analysis.primary_edges or not analysis.nodes:
            return analysis

        node_map: dict[int, RstNode] = {n.node_id: n for n in analysis.nodes}
        new_edges: list[PrimaryRelationEdge] = []
        new_signals: list[DiscourseSignal] = list(analysis.signals)
        sig_counter = len(new_signals) + 1

        for edge in analysis.primary_edges:
            child_node = node_map.get(edge.child_id)
            if child_node is None:
                new_edges.append(edge)
                continue

            child_text = child_node.text
            cue_match = self.find_cue_in_text(child_text)

            if cue_match is not None:
                rule, cue_local_start, cue_local_end = cue_match
                # Check if current relation matches marker concept
                current_concept = (edge.relation_concept or edge.relation_raw).lower()
                target_concept = rule.coarse_concept.lower()

                # Override if current prediction is generic/mismatched and model confidence is not overwhelmingly high
                should_prime = (
                    current_concept != target_concept
                    and (edge.confidence is None or edge.confidence < min_model_confidence_to_override)
                )

                if should_prime:
                    new_edge = PrimaryRelationEdge(
                        edge_id=edge.edge_id,
                        parent_id=edge.parent_id,
                        child_id=edge.child_id,
                        relation_raw=rule.fine_label,
                        relation_concept=rule.coarse_concept,
                        nuclearity=edge.nuclearity,
                        confidence=0.88,  # Calibrated marker prior confidence
                        calibrated=True,
                    )
                    new_edges.append(new_edge)

                    # Extract token IDs for the cue if document has tokens
                    cue_abs_start = child_node.char_span[0] + cue_local_start
                    cue_abs_end = child_node.char_span[0] + cue_local_end

                    cue_token_ids = tuple(
                        t.token_id
                        for t in document.tokens
                        if (cue_abs_start <= t.start < cue_abs_end) or (cue_abs_start < t.end <= cue_abs_end)
                    )

                    new_signals.append(
                        DiscourseSignal(
                            signal_id=f"sig_{sig_counter}",
                            edge_id=edge.edge_id,
                            signal_type="dm",
                            signal_subtype="dm",
                            token_ids=cue_token_ids,
                            status=AnnotationStatusEnum.PREDICTED,
                            confidence=0.92,
                        )
                    )
                    sig_counter += 1
                else:
                    new_edges.append(edge)
            else:
                new_edges.append(edge)

        return RstAnalysis(
            document_id=analysis.document_id,
            formalism=analysis.formalism,
            nodes=analysis.nodes,
            primary_edges=tuple(new_edges),
            secondary_edges=analysis.secondary_edges,
            signals=tuple(new_signals),
            provenance=analysis.provenance,
            timing=analysis.timing,
            warnings=analysis.warnings,
            failure_code=analysis.failure_code,
        )
