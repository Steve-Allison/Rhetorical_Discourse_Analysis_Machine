"""Reference-machine preparation performance acceptance."""

from time import perf_counter

import pytest

from isanlp_rst.ingest import ProductionIngestor, SourceArtifact


@pytest.mark.parametrize(
    ("character_count", "threshold_seconds"),
    ((100_000, 2.0), (1_000_000, 15.0)),
)
def test_preparation_meets_reference_threshold_on_every_measured_run(
    character_count: int,
    threshold_seconds: float,
) -> None:
    text = _source_text(character_count)
    artifact = SourceArtifact.from_text(text, source_name=f"{character_count}.txt")
    ingestor = ProductionIngestor()

    warmup = ingestor.prepare(artifact)
    assert warmup.semantic.prepared_document.text == text

    durations: list[float] = []
    for _ in range(5):
        started = perf_counter()
        outcome = ingestor.prepare(artifact)
        durations.append(perf_counter() - started)
        assert outcome.semantic.prepared_document.text == text

    assert all(duration < threshold_seconds for duration in durations), durations


def _source_text(character_count: int) -> str:
    paragraph = "A structurally meaningful paragraph ends here.\n\n"
    return (paragraph * (character_count // len(paragraph) + 1))[:character_count]
