from functools import cache
import re
from collections.abc import Sequence

from rdam.rst.contracts.analysis import (
    DiscourseSignal,
    PrimaryRelationEdge,
    RstAnalysis,
    SignalDetectorProvenance,
)
from rdam.rst.contracts.document import RstDocument
from rdam.rst.contracts.enums import (
    AnnotationStatusEnum,
    SignalDetectionMethod,
)
from rdam.rst.relations.multilingual_markers import (
    MULTILINGUAL_MARKER_RULES,
    MarkerRule,
)

__all__ = ["DISCOURSE_MARKER_RULES", "DiscourseMarkerPrimer", "MarkerRule"]

DISCOURSE_MARKER_RULES = MULTILINGUAL_MARKER_RULES["en"]


@cache
def _compile_rule_pattern(cue: str) -> re.Pattern[str]:
    """Pre-compile regex for a discourse cue."""
    cue_lower = cue.lower()
    if any("\u4e00" <= c <= "\u9fff" for c in cue_lower):
        pattern = r"(?:^|[;,\.，。；、\s]+)" + re.escape(cue_lower)
    else:
        pattern = r"(?:^|[;,\.]\s*)\b" + re.escape(cue_lower) + r"\b"
    return re.compile(pattern)


class DiscourseMarkerPrimer:
    """Detects explicit discourse connectives and primes/refines rhetorical relation labels."""

    def __init__(self, rules: Sequence[MarkerRule] | None = None, language: str = "en") -> None:
        self.language = (language or "en").strip().lower()
        if rules is not None:
            self.rules = tuple(rules)
        else:
            self.rules = MULTILINGUAL_MARKER_RULES.get(self.language, MULTILINGUAL_MARKER_RULES["en"])
        # Sort rules with longest cues first so specific phrases match before sub-words
        self.sorted_rules = sorted(self.rules, key=lambda r: len(r.cue), reverse=True)

    def find_cue_in_text(self, text: str) -> tuple[MarkerRule, int, int] | None:
        """Find matching discourse cue at start of text or following punctuation.

        Returns (MarkerRule, match_start, match_end) or None.
        """
        return self._find_cue(text, self.sorted_rules)

    @staticmethod
    def _find_cue(text: str, rules: Sequence[MarkerRule]) -> tuple[MarkerRule, int, int] | None:
        clean_text = text.lstrip()
        leading_ws = len(text) - len(clean_text)
        text_lower = clean_text.lower()

        for rule in rules:
            cue = rule.cue.lower()
            regex = _compile_rule_pattern(cue)
            match = regex.search(text_lower)
            if match:
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
        """Refine relation labels on primary edges where explicit discourse markers are present."""
        if not analysis.primary_edges or not analysis.nodes:
            return analysis

        # Use document language rules if document specifies a language
        doc_lang = (document.language or self.language).strip().lower()
        primer_rules = (
            self.sorted_rules
            if doc_lang == self.language
            else sorted(
                MULTILINGUAL_MARKER_RULES.get(doc_lang, self.rules),
                key=lambda r: len(r.cue),
                reverse=True,
            )
        )

        detector = SignalDetectorProvenance(
            detector_id="isanlp_rst.marker_primer",
            detector_version="1.0.0",
            method=SignalDetectionMethod.RULE,
            ruleset_digest="discourse_marker_lexicon_v1",
        )

        new_edges: list[PrimaryRelationEdge] = []
        new_signals: list[DiscourseSignal] = list(analysis.signals)
        signal_counter = len(new_signals) + 1

        node_by_id = {node.node_id: node for node in analysis.nodes}

        for edge in analysis.primary_edges:
            child_node = node_by_id.get(edge.child_id)
            if child_node is None:
                new_edges.append(edge)
                continue

            child_text = child_node.text
            match_res = self._find_cue(child_text, primer_rules)

            if match_res is None:
                new_edges.append(edge)
                continue

            rule, cue_local_start, cue_local_end = match_res
            doc_cue_start = child_node.char_span[0] + cue_local_start
            doc_cue_end = child_node.char_span[0] + cue_local_end

            # Find matching document tokens if tokenized
            matched_token_ids: list[int] = []
            if document.tokens:
                matched_token_ids.extend(
                    token.token_id
                    for token in document.tokens
                    if not (token.end <= doc_cue_start or token.start >= doc_cue_end)
                )

            sig = DiscourseSignal(
                signal_id=f"sig_{signal_counter:04d}",
                edge_id=edge.edge_id,
                signal_type="dm",
                signal_subtype="dm",
                token_ids=tuple(matched_token_ids),
                char_spans=((doc_cue_start, doc_cue_end),),
                compatible_relations=tuple(dict.fromkeys((rule.fine_label, rule.coarse_concept.lower()))),
                detector=detector,
                sufficient=True,
                status=AnnotationStatusEnum.PREDICTED,
                confidence=0.92,
            )
            new_signals.append(sig)
            signal_counter += 1

            # Determine whether to update relation concept based on confidence
            should_override = edge.confidence is None or edge.confidence < min_model_confidence_to_override
            if should_override and edge.relation_concept != rule.coarse_concept:
                updated_edge = PrimaryRelationEdge(
                    edge_id=edge.edge_id,
                    parent_id=edge.parent_id,
                    child_id=edge.child_id,
                    relation_raw=rule.fine_label,
                    relation_concept=rule.coarse_concept,
                    nuclearity=rule.default_nuclearity,
                    confidence=0.88,
                    calibrated=True,
                )
                new_edges.append(updated_edge)
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
