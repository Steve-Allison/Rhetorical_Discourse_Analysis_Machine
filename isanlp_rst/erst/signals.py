"""Validated, deterministic eRST signal detection with overlap preservation."""

from hashlib import sha256
import json
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from isanlp_rst.contracts.analysis import DiscourseSignal, SignalDetectorProvenance
from isanlp_rst.contracts.document import RstDocument
from isanlp_rst.contracts.enums import AnnotationStatusEnum, SignalDetectionMethod


class SignalPattern(BaseModel):
    """One auditable token-sequence trigger and its raw relation compatibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    phrase: str = Field(min_length=1)
    signal_type: str = Field(min_length=1)
    signal_subtype: str = Field(min_length=1)
    compatible_relations: tuple[str, ...]
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("phrase")
    @classmethod
    def normalize_phrase(cls, value: str) -> str:
        normalized = " ".join(value.casefold().split())
        if not normalized:
            raise ValueError("signal phrase must contain non-whitespace text")
        return normalized

    @field_validator("compatible_relations")
    @classmethod
    def validate_relations(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or any(not relation.strip() for relation in value):
            raise ValueError("signal pattern requires non-empty compatible raw relations")
        if len(value) != len(set(value)):
            raise ValueError("signal pattern compatible relations must be unique")
        return value


class SignalDetectionResult(BaseModel):
    """Typed result boundary for one complete signal-detection pass."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: str
    detector: SignalDetectorProvenance
    signals: tuple[DiscourseSignal, ...]
    token_count: int = Field(ge=0)


def _pattern(
    phrase: str,
    signal_type: str,
    signal_subtype: str,
    *relations: str,
    confidence: float = 0.85,
) -> SignalPattern:
    return SignalPattern(
        phrase=phrase,
        signal_type=signal_type,
        signal_subtype=signal_subtype,
        compatible_relations=relations,
        confidence=confidence,
    )


DEFAULT_SIGNAL_PATTERNS: tuple[SignalPattern, ...] = (
    _pattern("however", "dm", "discourse_marker", "adversative-contrast", "adversative-concession"),
    _pattern("but", "dm", "discourse_marker", "adversative-contrast", "adversative-antithesis"),
    _pattern("although", "dm", "discourse_marker", "adversative-concession"),
    _pattern("even though", "dm", "discourse_marker", "adversative-concession"),
    _pattern("whereas", "dm", "discourse_marker", "adversative-contrast"),
    _pattern("because", "dm", "discourse_marker", "causal-cause", "explanation-justify"),
    _pattern("since", "dm", "discourse_marker", "causal-cause", "context-circumstance"),
    _pattern("therefore", "dm", "discourse_marker", "causal-result"),
    _pattern("as a result", "dm", "discourse_marker", "causal-result"),
    _pattern("consequently", "dm", "discourse_marker", "causal-result"),
    _pattern("if", "dm", "discourse_marker", "contingency-condition"),
    _pattern("unless", "dm", "discourse_marker", "contingency-condition"),
    _pattern("otherwise", "dm", "discourse_marker", "contingency-condition"),
    _pattern("for example", "lexical", "indicative_phrase", "elaboration-example"),
    _pattern("for instance", "lexical", "indicative_phrase", "elaboration-example"),
    _pattern("indeed", "lexical", "indicative_word", "explanation-evidence"),
    _pattern("in addition", "dm", "discourse_marker", "joint-list"),
    _pattern("furthermore", "dm", "discourse_marker", "joint-list"),
    _pattern("moreover", "dm", "discourse_marker", "joint-list"),
    _pattern("meanwhile", "dm", "discourse_marker", "temporal-same-time"),
    _pattern("subsequently", "dm", "discourse_marker", "temporal-after"),
    _pattern("in conclusion", "dm", "discourse_marker", "summary-summary"),
    _pattern("similarly", "dm", "discourse_marker", "adversative-similarity"),
    _pattern("would", "morphological", "mood", "contingency-condition", confidence=0.70),
    _pattern("could", "morphological", "mood", "contingency-condition", confidence=0.70),
    _pattern("should", "morphological", "mood", "contingency-condition", confidence=0.70),
    _pattern("than", "syntactic", "comparative", "adversative-comparison", confidence=0.70),
    _pattern("this", "reference", "demonstrative_reference", "elaboration-additional", confidence=0.65),
    _pattern("these", "reference", "demonstrative_reference", "elaboration-additional", confidence=0.65),
    _pattern("that", "reference", "demonstrative_reference", "elaboration-additional", confidence=0.65),
    _pattern("those", "reference", "demonstrative_reference", "elaboration-additional", confidence=0.65),
)

_EDGE_PUNCTUATION = re.compile(r"^\W+|\W+$", flags=re.UNICODE)


def _normalized_token(token_text: str) -> str:
    return _EDGE_PUNCTUATION.sub("", token_text.casefold())


class RuleBasedSignalDetector:
    """Detect all configured token triggers, including overlaps and orphans."""

    def __init__(
        self,
        patterns: tuple[SignalPattern, ...] = DEFAULT_SIGNAL_PATTERNS,
        *,
        detector_version: str = "1.0.0",
    ) -> None:
        if not patterns:
            raise ValueError("signal detector requires at least one pattern")
        self.patterns = patterns
        canonical = json.dumps(
            [pattern.model_dump(mode="json") for pattern in patterns],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.provenance = SignalDetectorProvenance(
            detector_id="isanlp-rst-rule-signal-detector",
            detector_version=detector_version,
            method=SignalDetectionMethod.RULE,
            ruleset_digest=sha256(canonical).hexdigest(),
        )

    def detect(self, document: RstDocument) -> SignalDetectionResult:
        """Return every match without assigning it to an edge prematurely."""

        normalized_tokens = tuple(_normalized_token(token.text) for token in document.tokens)
        matches: list[tuple[int, int, SignalPattern, tuple[int, ...], tuple[int, int]]] = []
        for pattern in self.patterns:
            phrase_tokens = tuple(pattern.phrase.split())
            width = len(phrase_tokens)
            for start_index in range(len(normalized_tokens) - width + 1):
                if normalized_tokens[start_index : start_index + width] != phrase_tokens:
                    continue
                matched_tokens = document.tokens[start_index : start_index + width]
                first = matched_tokens[0]
                last = matched_tokens[-1]
                first_offset = first.text.casefold().find(phrase_tokens[0])
                last_offset = last.text.casefold().find(phrase_tokens[-1])
                if first_offset < 0 or last_offset < 0:
                    raise RuntimeError("normalized signal token cannot be located in its source token")
                char_span = (
                    first.start + first_offset,
                    last.start + last_offset + len(phrase_tokens[-1]),
                )
                matches.append(
                    (
                        char_span[0],
                        char_span[1],
                        pattern,
                        tuple(token.token_id for token in matched_tokens),
                        char_span,
                    )
                )

        matches.sort(key=lambda item: (item[0], item[1], item[2].signal_type, item[2].signal_subtype, item[2].phrase))
        signals = tuple(
            DiscourseSignal(
                signal_id=f"sig_{index}",
                edge_id=None,
                signal_type=pattern.signal_type,
                signal_subtype=pattern.signal_subtype,
                token_ids=token_ids,
                char_spans=(char_span,),
                compatible_relations=pattern.compatible_relations,
                detector=self.provenance,
                status=AnnotationStatusEnum.PREDICTED,
                confidence=pattern.confidence,
            )
            for index, (_, _, pattern, token_ids, char_span) in enumerate(matches, start=1)
        )
        return SignalDetectionResult(
            document_id=document.document_id,
            detector=self.provenance,
            signals=signals,
            token_count=len(document.tokens),
        )


__all__ = [
    "DEFAULT_SIGNAL_PATTERNS",
    "RuleBasedSignalDetector",
    "SignalDetectionResult",
    "SignalPattern",
]
