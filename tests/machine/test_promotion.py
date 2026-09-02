"""PromotionDecision: promote is unconstructible without evidence; withhold and retire always are."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from rdam import (
    BaselineComparison,
    CalibrationEvidence,
    CandidateIdentity,
    CompatibilityEvidence,
    EmpiricalQualityEvidence,
    EvidenceClass,
    FormalQualityEvidence,
    LatencyEvidence,
    LicensingEvidence,
    Measurement,
    PromotionDecision,
    PromotionOutcome,
    ProvenanceEvidence,
    Recommendation,
    Sha256Identity,
    Technique,
    UnmeasuredQuality,
    compare_candidates,
    load_decision,
    load_published_decision,
    serialize_decision,
)
from rdam.promotion import OutputQualityEvidence

ARTIFACT = Sha256Identity(hex_digest="a" * 64)


def _measure(name: str, value: float, partition: str = "test") -> Measurement:
    return Measurement(name=name, value=value, partition=partition, unit="f1")


def _full_empirical(*, exceeds: bool = True) -> EmpiricalQualityEvidence:
    return EmpiricalQualityEvidence(
        gold_data="GUM-12.1.0",
        partitions=("dev", "test"),
        measurements=(_measure("full_f1", 0.5), _measure("full_f1", 0.48, "dev")),
        baselines=(
            BaselineComparison(
                baseline_identity="prior-release",
                baseline_measurements=(_measure("full_f1", 0.4),),
                comparison_basis="Standard Parseval on the same GUM-12.1.0 test partition",
                candidate_exceeds_baseline=exceeds,
            ),
        ),
        uncertainty="bootstrap 95% CI over documents, non-overlapping",
    )


def _decision(
    quality: OutputQualityEvidence,
    outcome: PromotionOutcome,
    *,
    candidate_id: str = "cand-1",
    calibration: CalibrationEvidence | None = None,
    latency: LatencyEvidence | None = None,
    compatibility: CompatibilityEvidence | None = None,
    licensing: LicensingEvidence | None = None,
    replaces: str | None = None,
    technique: Technique = Technique.RST,
) -> PromotionDecision:
    return PromotionDecision(
        decision_id=f"{candidate_id}-{outcome.value}",
        decided_at=datetime(2026, 9, 2, tzinfo=UTC),
        decided_by="test",
        candidate=CandidateIdentity(technique=technique, candidate_id=candidate_id, artifact_identity=ARTIFACT, description="fixture"),
        output_quality=quality,
        calibration=calibration or CalibrationEvidence(state="declared_absent", description="no calibrated scores"),
        latency=latency or LatencyEvidence(state="measured", platform="Apple M-series", measurements=(Measurement(name="p50_ms", value=120.0, partition="test", unit="ms"),)),
        compatibility=compatibility
        or CompatibilityEvidence(state="verified", environment="production-clean-install", import_time_side_effects=False, packaging_declares_dependencies=True, evidence="clean install valid"),
        provenance=ProvenanceEvidence(code_revision="abc123", configuration_identity="hyperparameters v1", model_asset_identity=ARTIFACT, corpus_partitions=("dev", "test")),
        licensing=licensing or LicensingEvidence(licence="Apache-2.0", intended_use="local analysis", permits_intended_use=True, decision_note="permits"),
        outcome=outcome,
        replaces=replaces,
        recommendation=Recommendation(summary="ok", strengths=("beats baseline",), limitations=("one corpus",)),
    )


class TestGate:
    def test_full_evidence_permits_promote(self) -> None:
        decision = _decision(_full_empirical(), PromotionOutcome.PROMOTE)
        assert decision.admissible_outcomes == frozenset(PromotionOutcome)
        assert all(verdict.admissible for verdict in decision.verdicts())

    def test_promote_without_a_baseline_is_unconstructible(self) -> None:
        quality = EmpiricalQualityEvidence(gold_data="GUM", partitions=("test",), measurements=(_measure("full_f1", 0.2),))
        with pytest.raises(ValidationError, match="no baseline comparison"):
            _decision(quality, PromotionOutcome.PROMOTE)
        withheld = _decision(quality, PromotionOutcome.WITHHOLD)
        assert withheld.admissible_outcomes == {PromotionOutcome.WITHHOLD, PromotionOutcome.RETIRE}

    def test_not_exceeding_the_baseline_stays_in_the_workbench(self) -> None:
        with pytest.raises(ValidationError, match="does not exceed any baseline"):
            _decision(_full_empirical(exceeds=False), PromotionOutcome.PROMOTE)

    def test_unmeasured_quality_never_promotes(self) -> None:
        with pytest.raises(ValidationError, match="output quality unmeasured"):
            _decision(UnmeasuredQuality(reason="no evaluation was run"), PromotionOutcome.PROMOTE)
        assert _decision(UnmeasuredQuality(reason="no evaluation was run"), PromotionOutcome.RETIRE).outcome is PromotionOutcome.RETIRE

    def test_formal_technique_needs_arguments_and_property_tests(self) -> None:
        formal = FormalQualityEvidence(correctness_arguments=("grounded extension is unique",), property_tests=("test_grounded_is_unique",))
        decision = _decision(formal, PromotionOutcome.PROMOTE, technique=Technique.DUNG)
        assert decision.outcome is PromotionOutcome.PROMOTE
        with pytest.raises(ValidationError, match="no property tests"):
            _decision(FormalQualityEvidence(correctness_arguments=("x",)), PromotionOutcome.PROMOTE, technique=Technique.DUNG)

    def test_licence_that_forbids_the_use_blocks_promotion(self) -> None:
        licensing = LicensingEvidence(licence="CC-BY-NC-4.0", intended_use="commercial deployment", permits_intended_use=False, decision_note="non-commercial only")
        with pytest.raises(ValidationError, match="does not permit"):
            _decision(_full_empirical(), PromotionOutcome.PROMOTE, licensing=licensing)

    def test_each_class_is_verdicted_separately(self) -> None:
        decision = _decision(
            _full_empirical(),
            PromotionOutcome.WITHHOLD,
            calibration=CalibrationEvidence(state="missing"),
            latency=LatencyEvidence(state="missing"),
        )
        failing = {verdict.evidence_class for verdict in decision.verdicts() if not verdict.admissible}
        assert failing == {EvidenceClass.CALIBRATION, EvidenceClass.LATENCY_RESOURCES}

    def test_replace_names_what_it_replaces(self) -> None:
        with pytest.raises(ValidationError, match="replace names the candidate it replaces"):
            _decision(_full_empirical(), PromotionOutcome.REPLACE)
        assert _decision(_full_empirical(), PromotionOutcome.REPLACE, replaces="cand-0").replaces == "cand-0"

    def test_evaluated_partitions_must_be_in_provenance(self) -> None:
        quality = EmpiricalQualityEvidence(
            gold_data="GUM",
            partitions=("dev", "test", "test2"),
            measurements=(_measure("full_f1", 0.5, "test2"),),
            baselines=_full_empirical().baselines,
            uncertainty="ci",
        )
        with pytest.raises(ValidationError, match="identified in provenance"):
            _decision(quality, PromotionOutcome.PROMOTE)


class TestComparison:
    def test_like_for_like_comparison(self) -> None:
        a = _decision(_full_empirical(), PromotionOutcome.PROMOTE, candidate_id="a")
        b = _decision(_full_empirical(exceeds=False), PromotionOutcome.WITHHOLD, candidate_id="b")
        comparison = compare_candidates([a, b])
        assert [row.candidate_id for row in comparison.rows] == ["a", "b"]
        assert comparison.gold_data == "GUM-12.1.0"

    def test_different_partitions_are_refused(self) -> None:
        a = _decision(_full_empirical(), PromotionOutcome.PROMOTE, candidate_id="a")
        other = EmpiricalQualityEvidence(gold_data="GUM-12.1.0", partitions=("test",), measurements=(_measure("full_f1", 0.3),))
        b = _decision(other, PromotionOutcome.WITHHOLD, candidate_id="b")
        with pytest.raises(ValueError, match="same gold data, partitions, metrics"):
            compare_candidates([a, b])


class TestPersistence:
    def test_round_trip_and_tamper_evidence(self) -> None:
        decision = _decision(_full_empirical(), PromotionOutcome.PROMOTE)
        payload = serialize_decision(decision)
        assert load_decision(payload) == decision
        tampered = payload.replace(b'"outcome":"promote"', b'"outcome":"retire"')
        with pytest.raises(ValueError, match="digest mismatch"):
            load_decision(tampered)

    def test_published_sidecar_is_found_beside_a_release(self, tmp_path: Path) -> None:
        decision = _decision(_full_empirical(), PromotionOutcome.PROMOTE, candidate_id="modernbert-v1-abc")
        assert load_published_decision(tmp_path, "modernbert-v1-abc") is None
        (tmp_path / "modernbert-v1-abc.promotion.json").write_bytes(serialize_decision(decision))
        assert load_published_decision(tmp_path, "modernbert-v1-abc") == decision
