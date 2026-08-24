"""Record the mandatory-system and no-promotion consequences of a blocked baseline."""

import argparse
from pathlib import Path

from isanlp_rst.contracts.research import (
    BaselineReproductionDiagnosis,
    ErstBaselineAuthorityReceipt,
    MandatoryResearchSystem,
    MandatorySystemDisposition,
    PromotionDecision,
    PromotionGateName,
    PromotionGateResult,
    PromotionOutcome,
    ResearchProgramDiagnosis,
)


def record_blocked_research(
    authority_path: Path,
    baseline_diagnosis_path: Path,
    output_dir: Path,
) -> tuple[ResearchProgramDiagnosis, PromotionDecision]:
    """Persist complete blocked-system inventory and a fail-closed promotion decision."""

    authority = ErstBaselineAuthorityReceipt.model_validate_json(authority_path.read_text(encoding="utf-8"))
    baseline = BaselineReproductionDiagnosis.model_validate_json(
        baseline_diagnosis_path.read_text(encoding="utf-8")
    )
    if authority.ready_for_reproduction:
        raise ValueError("blocked-research receipt requires an unavailable baseline authority")
    if baseline.authority_receipt_sha256 != authority.receipt_sha256:
        raise ValueError("baseline diagnosis does not reference the supplied authority receipt")

    research = ResearchProgramDiagnosis(
        authority_receipt_sha256=authority.receipt_sha256,
        baseline_diagnosis_sha256=baseline.receipt_sha256,
        systems=tuple(
            MandatorySystemDisposition(system=system)
            for system in MandatoryResearchSystem
        ),
    )
    reason = "baseline reproduction gate is blocked by unavailable official scorer authority"
    decision = PromotionDecision(
        outcome=PromotionOutcome.NO_PROMOTION,
        authority_receipt_sha256=authority.receipt_sha256,
        baseline_diagnosis_sha256=baseline.receipt_sha256,
        research_diagnosis_sha256=research.receipt_sha256,
        gates=tuple(
            PromotionGateResult(
                gate=gate,
                passed=False,
                evidence_sha256=research.receipt_sha256,
                reason=reason,
            )
            for gate in PromotionGateName
        ),
        test_data_accessed=False,
        test2_data_accessed=False,
        upload_permitted=False,
        allowed_claims=(
            "corrected eRST interfaces",
            "paper-defined scorer adapter",
            "no benchmark reproduction claim",
            "no canonical eRST checkpoint",
        ),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "research-program-diagnosis.json").write_text(
        research.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "promotion-decision.json").write_text(
        decision.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return research, decision


def main() -> None:
    """Generate blocked research/promotion receipts from exact prerequisite evidence."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authority",
        type=Path,
        default=Path("config/erst/baseline-authority-gum-v9.2.0.json"),
    )
    parser.add_argument("--baseline-diagnosis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    research, decision = record_blocked_research(
        args.authority,
        args.baseline_diagnosis,
        args.output_dir,
    )
    print(
        f"mandatory_systems={len(research.systems)} outcome={decision.outcome.value} "
        f"research_sha256={research.receipt_sha256} decision_sha256={decision.receipt_sha256}"
    )


if __name__ == "__main__":
    main()
