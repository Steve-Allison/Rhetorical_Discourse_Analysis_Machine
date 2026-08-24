"""Fail-closed entry point for the published eRST baseline reproduction gate."""

import argparse
from pathlib import Path

from isanlp_rst.contracts.research import (
    BaselineReproductionDiagnosis,
    ErstBaselineAuthorityReceipt,
)


def diagnose_reproduction_gate(
    authority_path: Path,
    experiment_root: Path,
) -> BaselineReproductionDiagnosis:
    """Validate authority and persist a secret-free no-run diagnosis when blocked."""

    authority = ErstBaselineAuthorityReceipt.model_validate_json(authority_path.read_text(encoding="utf-8"))
    if authority.ready_for_reproduction:
        raise ValueError("authority unexpectedly permits reproduction; use the separately reviewed executable protocol")

    diagnosis = BaselineReproductionDiagnosis(
        authority_receipt_sha256=authority.receipt_sha256,
        blockers=authority.blockers,
    )
    experiment_root.mkdir(parents=True, exist_ok=True)
    output_path = experiment_root / "baseline-reproduction-diagnosis.json"
    output_path.write_text(diagnosis.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return diagnosis


def main() -> None:
    """Persist the current blocked-gate evidence and return a failing process status."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authority",
        type=Path,
        default=Path("config/erst/baseline-authority-gum-v9.2.0.json"),
    )
    parser.add_argument("--experiment-root", type=Path, required=True)
    args = parser.parse_args()

    diagnosis = diagnose_reproduction_gate(args.authority, args.experiment_root)
    parser.exit(
        2,
        "blocked: published eRST baseline reproduction is unauthorized by authority receipt "
        f"{diagnosis.authority_receipt_sha256}; no corpus or test data was accessed\n",
    )


if __name__ == "__main__":
    main()
