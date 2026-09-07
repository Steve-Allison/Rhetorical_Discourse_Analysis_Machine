"""Location-only scoring preserves occurrence counts and exposes missing anchors."""

from rdam.rst.contracts.analysis import DiscourseSignal, SignalDetectorProvenance
from rdam.rst.contracts.enums import SignalDetectionMethod
from workbench.evaluation.rst.signal_detection import location_counts


def _signal(*, tokens: tuple[int, ...] = (1, 2), category: str = "dm",
            subtype: str = "marker", edge: str | None = None) -> DiscourseSignal:
    return DiscourseSignal(
        signal_id="synthetic", edge_id=edge, signal_type=category, signal_subtype=subtype,
        token_ids=tokens, detector=SignalDetectorProvenance(
            detector_id="test", detector_version="1", method=SignalDetectionMethod.IMPORTED,
        ),
    )


def test_duplicate_predictions_receive_no_repeated_gold_credit() -> None:
    result = location_counts([_signal()], [_signal(), _signal()])
    assert result["gold_anchored"] == 1
    assert result["predicted_anchored"] == 2
    assert result["matched_location"] == 1
    assert result["matched_location_type_subtype"] == 1


def test_local_edge_ids_do_not_affect_explicit_location_only_metric() -> None:
    result = location_counts([_signal(edge="gold-edge")], [_signal(tokens=(2, 1), edge="other-edge")])
    assert result["matched_location"] == 1


def test_type_and_subtype_disagreement_are_preserved() -> None:
    changed_type = location_counts([_signal()], [_signal(category="lexical")])
    assert changed_type["matched_location"] == 1
    assert changed_type["matched_location_type"] == 0
    changed_subtype = location_counts([_signal()], [_signal(subtype="other")])
    assert changed_subtype["matched_location_type"] == 1
    assert changed_subtype["matched_location_type_subtype"] == 0


def test_unanchored_gold_is_counted_as_excluded_without_false_empty_match() -> None:
    result = location_counts([_signal(tokens=())], [_signal(tokens=())])
    assert result["gold_anchored"] == result["predicted_anchored"] == 0
    assert result["gold_unanchored"] == result["predicted_unanchored"] == 1
    assert result["matched_location"] == 0
