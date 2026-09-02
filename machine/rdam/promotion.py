"""PromotionDecision — the evidence-gated record by which a candidate leaves the workbench.

The 006 promotion-evidence contract, typed: six evidence classes evaluated separately
(FR-021); output-quality rules by technique kind (FR-022); exact provenance (FR-023); an
explicit licensing decision; outcomes ``promote | withhold | replace | retire``; and a
recommendation stating strengths and limitations (US4).

The gate is structural: a ``promote`` or ``replace`` decision **cannot be constructed**
unless every evidence class is admissible. Installation success, a green engineering
test, or the existence of artifacts is never evidence — there is no field for it.

The record lives in the machine package so a promoted artifact's sidecar decision can be
read by production code without importing the workbench that produced it (FR-006).
"""

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from rdam._strict import Sha256Identity, StrictModel, canonical_json_bytes, semantic_sha256
from rdam.frameworks import Technique

PROMOTION_CONTRACT: Literal["rdam.promotion_decision"] = "rdam.promotion_decision"
PROMOTION_CONTRACT_VERSION: Literal["1.0.0"] = "1.0.0"
_SNAKE = r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$"


class PromotionOutcome(StrEnum):
    PROMOTE = "promote"
    WITHHOLD = "withhold"
    REPLACE = "replace"
    RETIRE = "retire"


class EvidenceClass(StrEnum):
    OUTPUT_QUALITY = "output_quality"
    CALIBRATION = "calibration"
    LATENCY_RESOURCES = "latency_resources"
    COMPATIBILITY = "compatibility"
    PROVENANCE = "provenance"
    LICENSING = "licensing"


class Measurement(StrictModel):
    """One named number on one declared partition, in a stated unit."""

    name: str = Field(pattern=_SNAKE)
    value: float
    partition: str = Field(min_length=1)
    unit: str = Field(min_length=1)


class BaselineComparison(StrictModel):
    """The candidate against a relevant baseline on the same declared basis."""

    baseline_identity: str = Field(min_length=1)
    baseline_measurements: tuple[Measurement, ...] = Field(min_length=1)
    comparison_basis: str = Field(min_length=1)
    candidate_exceeds_baseline: bool


class EmpiricalQualityEvidence(StrictModel):
    """FR-022, empirical techniques: gold data, theory-appropriate metrics, baselines, uncertainty."""

    kind: Literal["empirical"] = "empirical"
    gold_data: str = Field(min_length=1)
    partitions: tuple[str, ...] = Field(min_length=1)
    measurements: tuple[Measurement, ...] = Field(min_length=1)
    baselines: tuple[BaselineComparison, ...] = ()
    uncertainty: str | None = None

    @model_validator(mode="after")
    def measurements_are_on_declared_partitions(self) -> Self:
        undeclared = sorted({item.partition for item in self.measurements} - set(self.partitions))
        if undeclared:
            raise ValueError(f"measurements name undeclared partitions: {undeclared}")
        return self

    def deficiencies(self) -> tuple[str, ...]:
        found: list[str] = []
        if not self.baselines:
            found.append("no baseline comparison")
        elif not any(item.candidate_exceeds_baseline for item in self.baselines):
            found.append("candidate does not exceed any baseline")
        if self.uncertainty is None:
            found.append("no uncertainty or statistical comparison")
        return tuple(found)


class FormalQualityEvidence(StrictModel):
    """FR-022, formal techniques: correctness arguments and property tests against the definitions."""

    kind: Literal["formal"] = "formal"
    correctness_arguments: tuple[str, ...] = ()
    property_tests: tuple[str, ...] = ()

    def deficiencies(self) -> tuple[str, ...]:
        found: list[str] = []
        if not self.correctness_arguments:
            found.append("no correctness arguments")
        if not self.property_tests:
            found.append("no property tests")
        return tuple(found)


class UnmeasuredQuality(StrictModel):
    """Quality was not measured. Never admissible; recorded so the gap is explicit."""

    kind: Literal["unmeasured"] = "unmeasured"
    reason: str = Field(min_length=1)

    def deficiencies(self) -> tuple[str, ...]:
        return (f"output quality unmeasured: {self.reason}",)


type OutputQualityEvidence = Annotated[
    EmpiricalQualityEvidence | FormalQualityEvidence | UnmeasuredQuality,
    Field(discriminator="kind"),
]


class CalibrationEvidence(StrictModel):
    """Confidence outputs shown meaningful, or explicitly declared absent."""

    state: Literal["measured", "declared_absent", "missing"]
    description: str | None = None

    def deficiencies(self) -> tuple[str, ...]:
        if self.state == "missing":
            return ("calibration neither measured nor declared absent",)
        if self.state == "measured" and not self.description:
            return ("calibration claimed measured without a description",)
        return ()


class LatencyEvidence(StrictModel):
    """Measured on the supported platform (Apple Silicon first)."""

    state: Literal["measured", "missing"]
    platform: str | None = None
    measurements: tuple[Measurement, ...] = ()

    def deficiencies(self) -> tuple[str, ...]:
        if self.state == "missing":
            return ("latency and resources not measured",)
        found: list[str] = []
        if not self.platform:
            found.append("latency platform not named")
        if not self.measurements:
            found.append("latency claimed measured without measurements")
        return tuple(found)


class CompatibilityEvidence(StrictModel):
    """Runs in the production topology; no import-time work; packaging declares dependencies."""

    state: Literal["verified", "missing"]
    environment: str | None = None
    import_time_side_effects: bool | None = None
    packaging_declares_dependencies: bool | None = None
    evidence: str | None = None

    def deficiencies(self) -> tuple[str, ...]:
        if self.state == "missing":
            return ("runtime and packaging compatibility not verified",)
        found: list[str] = []
        if not self.environment:
            found.append("compatibility environment not named")
        if self.import_time_side_effects is not False:
            found.append("import-time side effects not shown absent")
        if self.packaging_declares_dependencies is not True:
            found.append("packaging metadata not shown to declare dependencies")
        return tuple(found)


class ProvenanceEvidence(StrictModel):
    """Exact evaluated code, configuration, model assets, and corpus partitions (FR-023)."""

    code_revision: str = Field(min_length=1)
    configuration_identity: str = Field(min_length=1)
    model_asset_identity: Sha256Identity | None = None
    corpus_partitions: tuple[str, ...] = ()

    def deficiencies(self) -> tuple[str, ...]:
        return ()


class LicensingEvidence(StrictModel):
    """An explicit decision that the licence permits the intended production use."""

    licence: str = Field(min_length=1)
    intended_use: str = Field(min_length=1)
    permits_intended_use: bool
    decision_note: str = Field(min_length=1)

    def deficiencies(self) -> tuple[str, ...]:
        return () if self.permits_intended_use else (f"licence {self.licence!r} does not permit {self.intended_use!r}",)


class CandidateIdentity(StrictModel):
    technique: Technique
    candidate_id: str = Field(min_length=1)
    artifact_identity: Sha256Identity
    description: str = Field(min_length=1)


class Recommendation(StrictModel):
    summary: str = Field(min_length=1)
    strengths: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = Field(min_length=1)


class EvidenceVerdict(StrictModel):
    evidence_class: EvidenceClass
    admissible: bool
    deficiencies: tuple[str, ...]


class PromotionDecision(StrictModel):
    contract: Literal["rdam.promotion_decision"] = PROMOTION_CONTRACT
    contract_version: Literal["1.0.0"] = PROMOTION_CONTRACT_VERSION
    decision_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    decided_at: datetime
    decided_by: str = Field(min_length=1)
    candidate: CandidateIdentity
    output_quality: OutputQualityEvidence
    calibration: CalibrationEvidence
    latency: LatencyEvidence
    compatibility: CompatibilityEvidence
    provenance: ProvenanceEvidence
    licensing: LicensingEvidence
    outcome: PromotionOutcome
    replaces: str | None = None
    recommendation: Recommendation
    semantic_digest: Sha256Identity | None = None

    def verdicts(self) -> tuple[EvidenceVerdict, ...]:
        """Each class evaluated separately (FR-021)."""

        pairs: tuple[tuple[EvidenceClass, tuple[str, ...]], ...] = (
            (EvidenceClass.OUTPUT_QUALITY, self.output_quality.deficiencies()),
            (EvidenceClass.CALIBRATION, self.calibration.deficiencies()),
            (EvidenceClass.LATENCY_RESOURCES, self.latency.deficiencies()),
            (EvidenceClass.COMPATIBILITY, self.compatibility.deficiencies()),
            (EvidenceClass.PROVENANCE, self.provenance.deficiencies()),
            (EvidenceClass.LICENSING, self.licensing.deficiencies()),
        )
        return tuple(
            EvidenceVerdict(evidence_class=name, admissible=not found, deficiencies=found) for name, found in pairs
        )

    @property
    def admissible_outcomes(self) -> frozenset[PromotionOutcome]:
        """Withhold and retire are always admissible; promote and replace need every class."""

        outcomes = {PromotionOutcome.WITHHOLD, PromotionOutcome.RETIRE}
        if all(verdict.admissible for verdict in self.verdicts()):
            outcomes |= {PromotionOutcome.PROMOTE, PromotionOutcome.REPLACE}
        return frozenset(outcomes)

    @model_validator(mode="after")
    def outcome_is_admissible(self) -> Self:
        if self.outcome not in self.admissible_outcomes:
            failing = "; ".join(
                f"{verdict.evidence_class.value}: {', '.join(verdict.deficiencies)}"
                for verdict in self.verdicts()
                if not verdict.admissible
            )
            raise ValueError(f"outcome {self.outcome.value!r} is not admissible on this evidence — {failing}")
        if (self.outcome is PromotionOutcome.REPLACE) != (self.replaces is not None):
            raise ValueError("replace names the candidate it replaces; no other outcome does")
        if isinstance(self.output_quality, EmpiricalQualityEvidence) and not set(
            self.output_quality.partitions
        ) <= set(self.provenance.corpus_partitions):
            raise ValueError("every evaluated partition must be identified in provenance (FR-023)")
        expected = Sha256Identity(hex_digest=semantic_sha256(self.model_dump(exclude={"semantic_digest"})))
        if self.semantic_digest is not None and self.semantic_digest != expected:
            raise ValueError("promotion decision semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", expected)
        return self


class ComparisonRow(StrictModel):
    candidate_id: str
    outcome: PromotionOutcome
    measurements: tuple[Measurement, ...]


class CandidateComparison(StrictModel):
    """Several candidates for one technique on the same partitions, metrics, and criteria (US4 scenario 2)."""

    technique: Technique
    gold_data: str
    partitions: tuple[str, ...]
    measurement_names: tuple[str, ...]
    intended_use: str
    rows: tuple[ComparisonRow, ...] = Field(min_length=2)


def compare_candidates(decisions: Sequence[PromotionDecision]) -> CandidateComparison:
    """Refuse a comparison that is not like-for-like; otherwise tabulate it."""

    if len(decisions) < 2:
        raise ValueError("a comparison needs at least two candidates")
    first = decisions[0]
    if len({item.candidate.technique for item in decisions}) != 1:
        raise ValueError("candidates must be for one technique")
    qualities = [item.output_quality for item in decisions]
    if not all(isinstance(item, EmpiricalQualityEvidence) for item in qualities):
        raise ValueError("comparison requires empirical quality evidence for every candidate")
    empirical = [item for item in qualities if isinstance(item, EmpiricalQualityEvidence)]
    gold = {item.gold_data for item in empirical}
    partitions = {tuple(sorted(item.partitions)) for item in empirical}
    names = {tuple(sorted(measurement.name for measurement in item.measurements)) for item in empirical}
    uses = {item.licensing.intended_use for item in decisions}
    if len(gold) != 1 or len(partitions) != 1 or len(names) != 1 or len(uses) != 1:
        raise ValueError("candidates must be compared on the same gold data, partitions, metrics, and licensing criteria")
    return CandidateComparison(
        technique=first.candidate.technique,
        gold_data=next(iter(gold)),
        partitions=next(iter(partitions)),
        measurement_names=next(iter(names)),
        intended_use=next(iter(uses)),
        rows=tuple(
            ComparisonRow(candidate_id=item.candidate.candidate_id, outcome=item.outcome, measurements=quality.measurements)
            for item, quality in zip(decisions, empirical, strict=True)
        ),
    )


def serialize_decision(decision: PromotionDecision) -> bytes:
    return canonical_json_bytes(decision)


def load_decision(payload: bytes | str) -> PromotionDecision:
    text = payload if isinstance(payload, str) else payload.decode("utf-8", errors="strict")
    parsed = json.loads(text)
    if not isinstance(parsed, dict) or parsed.get("contract") != PROMOTION_CONTRACT:
        raise ValueError("payload is not a promotion decision")
    decision = PromotionDecision.model_validate_json(text)
    recomputed = semantic_sha256(decision.model_dump(exclude={"semantic_digest"}))
    if decision.semantic_digest is None or decision.semantic_digest.hex_digest != recomputed:
        raise ValueError("promotion decision semantic digest mismatch")
    return decision


def sidecar_path(store: Path, release_id: str) -> Path:
    """Where a published decision for a model-store release lives: beside, never inside, the immutable release."""

    return Path(store) / f"{release_id}.promotion.json"


def load_published_decision(store: Path, release_id: str) -> PromotionDecision | None:
    """The decision published for a store release, or ``None`` when no decision exists."""

    path = sidecar_path(store, release_id)
    if not path.is_file():
        return None
    return load_decision(path.read_bytes())


__all__ = [
    "PROMOTION_CONTRACT",
    "PROMOTION_CONTRACT_VERSION",
    "BaselineComparison",
    "CalibrationEvidence",
    "CandidateComparison",
    "CandidateIdentity",
    "CompatibilityEvidence",
    "ComparisonRow",
    "EmpiricalQualityEvidence",
    "EvidenceClass",
    "EvidenceVerdict",
    "FormalQualityEvidence",
    "LatencyEvidence",
    "LicensingEvidence",
    "Measurement",
    "OutputQualityEvidence",
    "PromotionDecision",
    "PromotionOutcome",
    "ProvenanceEvidence",
    "Recommendation",
    "UnmeasuredQuality",
    "compare_candidates",
    "load_decision",
    "load_published_decision",
    "serialize_decision",
    "sidecar_path",
]
