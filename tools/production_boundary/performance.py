"""Deterministic preparation-performance measurement for release evidence."""

from time import perf_counter

from rdam.rst.ingest import ProductionIngestor, SourceArtifact

from tools.production_boundary.contracts import (
    PreparationPerformanceCase,
    PreparationPerformanceEvidence,
)


PREPARATION_CASES = (
    (100_000, 2.0),
    (1_000_000, 15.0),
)
WARMUP_RUNS = 1
MEASURED_RUNS = 5


def source_text(character_count: int) -> str:
    """Build a deterministic source fixture of precisely ``character_count`` characters."""

    paragraph = "A structurally meaningful paragraph ends here.\n\n"
    return (paragraph * (character_count // len(paragraph) + 1))[:character_count]


def measure_preparation_case(
    character_count: int,
    threshold_seconds: float,
) -> PreparationPerformanceCase:
    """Measure exactly one warm-up and five preparation runs for one source size."""

    text = source_text(character_count)
    artifact = SourceArtifact.from_text(text, source_name=f"{character_count}.txt")
    ingestor = ProductionIngestor()

    warmup_started = perf_counter()
    warmup = ingestor.prepare(artifact)
    warmup_seconds = perf_counter() - warmup_started
    if warmup.semantic.prepared_document.text != text:
        raise AssertionError("preparation warm-up changed the source text")

    run_seconds: list[float] = []
    for _ in range(MEASURED_RUNS):
        started = perf_counter()
        outcome = ingestor.prepare(artifact)
        run_seconds.append(perf_counter() - started)
        if outcome.semantic.prepared_document.text != text:
            raise AssertionError("preparation measurement changed the source text")
    if len(run_seconds) != MEASURED_RUNS:
        raise AssertionError("preparation measurement did not retain exactly five runs")

    return PreparationPerformanceCase(
        character_count=character_count,
        threshold_seconds=threshold_seconds,
        warmup_seconds=warmup_seconds,
        run_seconds=(
            run_seconds[0],
            run_seconds[1],
            run_seconds[2],
            run_seconds[3],
            run_seconds[4],
        ),
    )


def measure_preparation() -> PreparationPerformanceEvidence:
    """Return the complete retained measurement set for the release performance gate."""

    return PreparationPerformanceEvidence(
        warmup_runs=WARMUP_RUNS,
        measured_runs=MEASURED_RUNS,
        cases=tuple(
            measure_preparation_case(character_count, threshold_seconds)
            for character_count, threshold_seconds in PREPARATION_CASES
        ),
    )


__all__ = [
    "MEASURED_RUNS",
    "PREPARATION_CASES",
    "WARMUP_RUNS",
    "measure_preparation",
    "measure_preparation_case",
    "source_text",
]
