"""Lexical discourse-cue candidates that never alter primary model decisions."""

from collections.abc import Sequence
from dataclasses import asdict, replace
from functools import cache
import hashlib
import json
import re

from rdam.rst.contracts.analysis import DiscourseSignal, RstAnalysis, SignalDetectorProvenance
from rdam.rst.contracts.document import DocumentToken, RstDocument
from rdam.rst.contracts.enums import AnnotationStatusEnum, SignalDetectionMethod
from rdam.rst.relations.multilingual_markers import MULTILINGUAL_MARKER_RULES, MarkerRule

__all__ = ["DISCOURSE_MARKER_RULES", "DiscourseMarkerPrimer", "MarkerRule"]

DISCOURSE_MARKER_RULES = MULTILINGUAL_MARKER_RULES["en"]


@cache
def _compile_rule_pattern(cue: str) -> re.Pattern[str]:
    """Match original text so Unicode case conversion cannot shift offsets."""
    chinese = any("\u4e00" <= character <= "\u9fff" for character in cue)
    boundary = r"(?:^\s*|[;,.!?，。；、]\s*)"
    word_boundary = "" if chinese else r"\b"
    return re.compile(boundary + word_boundary + "(?P<cue>" + re.escape(cue) + ")" + word_boundary, re.IGNORECASE)


class DiscourseMarkerPrimer:
    """Detect unscored lexical candidates with explicit, provisional attachments."""

    def __init__(self, rules: Sequence[MarkerRule] | None = None, language: str = "en") -> None:
        self.language = language.strip().lower()
        self.rules = tuple(rules) if rules is not None else self._language_rules(self.language)
        self.sorted_rules = sorted(self.rules, key=lambda rule: (-len(rule.cue), rule.cue))

    @staticmethod
    def _language_rules(language: str) -> tuple[MarkerRule, ...]:
        try:
            return MULTILINGUAL_MARKER_RULES[language]
        except KeyError as exc:
            raise ValueError(f"no discourse-marker inventory for language {language!r}") from exc

    @staticmethod
    def _find_cues(text: str, rules: Sequence[MarkerRule]) -> tuple[tuple[MarkerRule, int, int], ...]:
        matches = [
            (rule, *match.span("cue")) for rule in rules for match in _compile_rule_pattern(rule.cue).finditer(text)
        ]
        # Longest lexical match wins at the same occurrence; each source span is
        # emitted once, independently of how many ancestors enclose it.
        matches.sort(key=lambda item: (item[1], -(item[2] - item[1]), item[0].cue))
        selected: list[tuple[MarkerRule, int, int]] = []
        for match in matches:
            if selected and match[1] < selected[-1][2]:
                continue
            selected.append(match)
        return tuple(selected)

    def find_cue_in_text(self, text: str) -> tuple[MarkerRule, int, int] | None:
        """Return the first lexical cue occurrence, without classifying its use."""
        matches = self._find_cues(text, self.sorted_rules)
        return matches[0] if matches else None

    def prime_analysis(
        self,
        analysis: RstAnalysis,
        document: RstDocument,
        *,
        tokens: Sequence[DocumentToken] | None = None,
    ) -> RstAnalysis:
        """Add candidates; nearest-constituent attachment is a heuristic, not proof."""
        language = (document.language or self.language).strip().lower()
        rules = self.rules if language == self.language else self._language_rules(language)
        digest = hashlib.sha256(
            json.dumps(
                [asdict(rule) for rule in rules],
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        detector = SignalDetectorProvenance(
            detector_id="isanlp_rst.marker_primer",
            detector_version="2.0.0",
            method=SignalDetectionMethod.RULE,
            ruleset_digest=digest,
        )
        substrate_tokens = document.tokens if tokens is None else tokens
        node_by_id = {node.node_id: node for node in analysis.nodes}
        signals = list(analysis.signals)
        existing = {signal.signal_id: signal for signal in signals}
        for rule, start, end in self._find_cues(document.text, rules):
            enclosing = [
                edge
                for edge in analysis.primary_edges
                if edge.parent_id in node_by_id
                and edge.child_id in node_by_id
                and node_by_id[edge.child_id].char_span[0] <= start
                and end <= node_by_id[edge.child_id].char_span[1]
            ]
            parent_ids = {edge.parent_id for edge in enclosing}
            if parent_ids:
                smallest = min(
                    node_by_id[parent].char_span[1] - node_by_id[parent].char_span[0] for parent in parent_ids
                )
                parent_ids = {
                    parent
                    for parent in parent_ids
                    if node_by_id[parent].char_span[1] - node_by_id[parent].char_span[0] == smallest
                }
            candidates = tuple(
                sorted(
                    {
                        edge.edge_id
                        for edge in analysis.primary_edges
                        if edge.parent_id in parent_ids
                        and edge.relation_raw.casefold() != "span"
                        and (edge.nuclearity.value != "NN" or edge in enclosing)
                    }
                )
            )
            signal = DiscourseSignal(
                signal_id=f"marker:{start}:{end}",
                edge_id=candidates[0] if len(candidates) == 1 else None,
                signal_type="dm",
                signal_subtype="lexical_candidate",
                token_ids=tuple(
                    token.token_id for token in substrate_tokens or () if token.start < end and start < token.end
                ),
                char_spans=((start, end),),
                compatible_relations=(rule.fine_label,),
                detector=detector,
                sufficient=False,
                status=AnnotationStatusEnum.PREDICTED,
                confidence=None,
                attachment_candidates=candidates,
                attachment_basis="smallest_enclosing_constituent" if candidates else "no_applicable_primary_relation",
            )
            previous = existing.get(signal.signal_id)
            if previous is not None:
                if previous != signal:
                    raise ValueError("marker identity collides with different signal evidence")
                continue
            signals.append(signal)
            existing[signal.signal_id] = signal
        return replace(analysis, signals=tuple(signals))
