"""Reference-machine preparation performance acceptance."""

import pytest

from tools.production_boundary.performance import measure_preparation_case, source_text


@pytest.mark.parametrize(
    ("character_count", "threshold_seconds"),
    ((100_000, 2.0), (1_000_000, 15.0)),
)
def test_preparation_meets_reference_threshold_on_every_measured_run(
    character_count: int,
    threshold_seconds: float,
) -> None:
    measurement = measure_preparation_case(character_count, threshold_seconds)
    assert len(measurement.run_seconds) == 5
    assert measurement.passed, measurement.run_seconds


def test_source_text_has_the_requested_character_count() -> None:
    assert len(source_text(100_000)) == 100_000
