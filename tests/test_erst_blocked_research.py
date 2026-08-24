"""Mandatory-system retention and no-promotion decision tests."""

from pathlib import Path

from isanlp_rst.contracts.research import (
    MandatoryResearchSystem,
    PromotionDecision,
    PromotionOutcome,
    ResearchProgramDiagnosis,
)
from scripts.record_blocked_erst_research import record_blocked_research
from scripts.reproduce_erst_baseline import diagnose_reproduction_gate


def test_blocked_program_retains_every_system_and_forbids_promotion(tmp_path: Path) -> None:
    authority = Path("config/erst/baseline-authority-gum-v9.2.0.json")
    baseline = diagnose_reproduction_gate(authority, tmp_path)
    research, decision = record_blocked_research(
        authority,
        tmp_path / "baseline-reproduction-diagnosis.json",
        tmp_path,
    )

    assert tuple(item.system for item in research.systems) == tuple(MandatoryResearchSystem)
    assert all(not item.implementation_started for item in research.systems)
    assert not research.test_data_accessed
    assert not research.test2_data_accessed
    assert decision.outcome == PromotionOutcome.NO_PROMOTION
    assert decision.baseline_diagnosis_sha256 == baseline.receipt_sha256
    assert decision.champion_manifest_sha256 is None
    assert decision.canonical_checkpoint_manifest_sha256 is None
    assert not decision.upload_permitted
    assert all(not gate.passed for gate in decision.gates)

    assert ResearchProgramDiagnosis.model_validate_json(
        (tmp_path / "research-program-diagnosis.json").read_text(encoding="utf-8")
    ) == research
    assert PromotionDecision.model_validate_json(
        (tmp_path / "promotion-decision.json").read_text(encoding="utf-8")
    ) == decision
