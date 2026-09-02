"""Typed eRST signal contracts and overlap-preservation tests."""

from pydantic import ValidationError
import pytest

from rdam.rst.contracts import (
    AnnotationStatusEnum,
    DiscourseSignal,
    DocumentToken,
    RstDocument,
    SignalDetectionMethod,
    SignalDetectorProvenance,
)
from rdam.rst.erst.signals import RuleBasedSignalDetector, SignalPattern


def _detector() -> SignalDetectorProvenance:
    return SignalDetectorProvenance(
        detector_id="gum-rs4-import",
        detector_version="12.1.0",
        method=SignalDetectionMethod.IMPORTED,
        source_revision="22fdf87f9c71c96bcc771461d06e689b1f90020d",
    )


def test_signal_round_trip_preserves_all_typed_evidence() -> None:
    signal = DiscourseSignal(
        signal_id="sig-1",
        edge_id=None,
        signal_type="morphological",
        signal_subtype="tense",
        token_ids=(3, 4),
        char_spans=((12, 18), (19, 24)),
        compatible_relations=("sequence", "context-circumstance"),
        detector=_detector(),
        status=AnnotationStatusEnum.PREDICTED,
        confidence=0.875,
    )
    restored = DiscourseSignal.model_validate_json(signal.model_dump_json())
    assert restored == signal
    assert restored.edge_id is None
    assert restored.detector.source_revision == "22fdf87f9c71c96bcc771461d06e689b1f90020d"


def test_overlapping_signal_spans_and_token_anchors_are_preserved() -> None:
    first = DiscourseSignal(
        signal_id="sig-1",
        edge_id=None,
        signal_type="dm",
        signal_subtype="discourse_marker",
        token_ids=(1, 2),
        char_spans=((4, 15),),
        compatible_relations=("causal-result",),
        detector=_detector(),
        confidence=0.9,
    )
    second = DiscourseSignal(
        signal_id="sig-2",
        edge_id=None,
        signal_type="lexical",
        signal_subtype="indicative_word",
        token_ids=(2,),
        char_spans=((9, 15),),
        compatible_relations=("causal-result",),
        detector=_detector(),
        confidence=0.8,
    )
    assert set(first.token_ids) & set(second.token_ids) == {2}
    assert first.char_spans[0][0] < second.char_spans[0][1]
    assert second.char_spans[0][0] < first.char_spans[0][1]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"token_ids": (-1,)},
        {"char_spans": ((5, 4),)},
        {"confidence": 1.01},
        {"signal_type": ""},
        {"compatible_relations": ("",)},
    ],
)
def test_invalid_signal_evidence_fails_closed(kwargs: dict[str, object]) -> None:
    payload: dict[str, object] = {
        "signal_id": "sig-invalid",
        "edge_id": None,
        "signal_type": "dm",
        "signal_subtype": "discourse_marker",
        "token_ids": (1,),
        "char_spans": ((0, 3),),
        "compatible_relations": ("contrast",),
        "detector": _detector(),
        "confidence": 0.5,
    }
    payload.update(kwargs)
    with pytest.raises(ValidationError):
        DiscourseSignal.model_validate(payload)


def test_detector_emits_orphan_lexical_and_morphosyntactic_signals() -> None:
    document = RstDocument.from_tokens_and_edus(
        text="However this could work.",
        tokens=(
            DocumentToken(token_id=10, text="However", start=0, end=7),
            DocumentToken(token_id=20, text="this", start=8, end=12),
            DocumentToken(token_id=30, text="could", start=13, end=18),
            DocumentToken(token_id=40, text="work.", start=19, end=24),
        ),
        edus=(),
        document_id="signal-doc",
    )
    result = RuleBasedSignalDetector().detect(document)
    assert {signal.signal_type for signal in result.signals} >= {"dm", "reference", "morphological"}
    assert all(signal.edge_id is None for signal in result.signals)
    assert {signal.token_ids for signal in result.signals} >= {(10,), (20,), (30,)}
    assert {signal.char_spans for signal in result.signals} >= {((0, 7),), ((8, 12),), ((13, 18),)}
    assert result.detector.ruleset_digest is not None


def test_detector_preserves_overlapping_pattern_matches() -> None:
    patterns = (
        SignalPattern(
            phrase="as a result",
            signal_type="dm",
            signal_subtype="discourse_marker",
            compatible_relations=("causal-result",),
            confidence=0.9,
        ),
        SignalPattern(
            phrase="result",
            signal_type="lexical",
            signal_subtype="indicative_word",
            compatible_relations=("causal-result",),
            confidence=0.8,
        ),
    )
    document = RstDocument.from_tokens_and_edus(
        text="As a result, it changed.",
        tokens=(
            DocumentToken(token_id=0, text="As", start=0, end=2),
            DocumentToken(token_id=1, text="a", start=3, end=4),
            DocumentToken(token_id=2, text="result,", start=5, end=12),
            DocumentToken(token_id=3, text="it", start=13, end=15),
            DocumentToken(token_id=4, text="changed.", start=16, end=24),
        ),
        edus=(),
        document_id="overlap-doc",
    )
    signals = RuleBasedSignalDetector(patterns).detect(document).signals
    assert len(signals) == 2
    assert signals[0].char_spans == ((0, 11),)
    assert signals[1].char_spans == ((5, 11),)
    assert set(signals[0].token_ids) & set(signals[1].token_ids) == {2}
