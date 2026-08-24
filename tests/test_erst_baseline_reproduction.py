"""Published serialization and baseline-gate diagnosis tests."""

from pathlib import Path

from pydantic import ValidationError
import pytest

from isanlp_rst.contracts.research import (
    BaselineDirection,
    BaselineReproductionDiagnosis,
    BaselineSignalLocation,
    PublishedBaselineExample,
)
from isanlp_rst.erst.baseline import serialize_published_baseline
from scripts.reproduce_erst_baseline import diagnose_reproduction_gate


def test_published_left_direction_serialization_marks_only_target_signal() -> None:
    example = PublishedBaselineExample(
        relation_raw="adversative-antithesis",
        same_path_relation_raw="joint-list",
        direction=BaselineDirection.LEFT,
        head_edu_distance=1,
        source_text="past studies have tended to avoid this task",
        target_text="and have instead used samples of researchers",
        signal_location=BaselineSignalLocation.TARGET,
        signal_start=9,
        signal_end=16,
        label=True,
    )
    assert serialize_published_baseline(example) == (
        "__label__True\tadversative antithesis ( joint-list ) left 1 : "
        "past studies have tended to avoid this task >> and have **instead** used samples of researchers"
    )


def test_published_right_direction_serialization_reorders_spans() -> None:
    example = PublishedBaselineExample(
        relation_raw="causal-result",
        direction=BaselineDirection.RIGHT,
        head_edu_distance=3,
        source_text="so the result followed",
        target_text="the earlier cause",
        signal_location=BaselineSignalLocation.SOURCE,
        signal_start=0,
        signal_end=2,
    )
    assert serialize_published_baseline(example) == (
        "causal result ( _ ) right 3 : the earlier cause << **so** the result followed"
    )


def test_signal_span_must_be_contained_by_selected_text() -> None:
    with pytest.raises(ValidationError, match="contained"):
        PublishedBaselineExample(
            relation_raw="joint-list",
            direction=BaselineDirection.LEFT,
            head_edu_distance=1,
            source_text="one",
            target_text="two",
            signal_location=BaselineSignalLocation.TARGET,
            signal_start=2,
            signal_end=4,
        )


def test_blocked_authority_persists_zero_access_diagnosis(tmp_path: Path) -> None:
    authority_path = Path("config/erst/baseline-authority-gum-v9.2.0.json")
    diagnosis = diagnose_reproduction_gate(authority_path, tmp_path)
    persisted = BaselineReproductionDiagnosis.model_validate_json(
        (tmp_path / "baseline-reproduction-diagnosis.json").read_text(encoding="utf-8")
    )
    assert persisted == diagnosis
    assert diagnosis.runs_started == 0
    assert not diagnosis.training_data_accessed
    assert not diagnosis.test_data_accessed
    assert not diagnosis.architecture_screening_allowed
