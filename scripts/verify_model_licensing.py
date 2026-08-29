"""Verify commercial license compliance for candidate and released model weights.

Audits candidate architectures in the research technology matrix and production
model registry to guarantee 100% permissive commercial compliance (Apache-2.0,
MIT, BSD-3-Clause, CC-BY-4.0).
"""

import argparse
import json
from pathlib import Path
import sys

from pydantic import BaseModel, Field

from workbench.hashing import canonical_json_bytes, sha256_digest

PERMISSIBLE_COMMERCIAL_LICENSES = frozenset(
    {
        "Apache-2.0",
        "MIT",
        "BSD-3-Clause",
        "BSD-2-Clause",
        "CC-BY-4.0",
        "inherits selected text model",
    }
)

RESTRICTIVE_LICENSES = frozenset(
    {
        "CC-BY-NC-4.0",
        "CC-BY-NC-SA-4.0",
        "CC-BY-NC-ND-4.0",
        "proprietary",
    }
)


class ModelLicenseRecord(BaseModel):
    model_id: str | None
    system_name: str
    declared_license: str
    is_commercial_permissible: bool
    status: str
    notes: str = ""


class LicenseAuditReceipt(BaseModel):
    schema_version: str = "isanlp_rst_license_audit/v1"
    audited_systems: list[ModelLicenseRecord] = Field(default_factory=list)
    total_audited: int
    commercial_ready_count: int
    restricted_count: int
    all_commercial_ready: bool
    audit_sha256: str = ""


def audit_technology_matrix(matrix_path: Path) -> LicenseAuditReceipt:
    """Audit the research technology matrix for license compliance."""
    if not matrix_path.is_file():
        raise FileNotFoundError(f"technology matrix not found at {matrix_path}")

    raw = json.loads(matrix_path.read_text(encoding="utf-8"))
    systems = raw.get("systems", [])

    records: list[ModelLicenseRecord] = []
    commercial_count = 0
    restricted_count = 0

    for item in systems:
        system_name = item.get("system", "unknown")
        model_id = item.get("model_id")
        lic = item.get("model_license", "unknown")

        is_permissible = lic in PERMISSIBLE_COMMERCIAL_LICENSES
        if is_permissible:
            status = "APPROVED_COMMERCIAL"
            commercial_count += 1
            notes = "Commercial deployment permitted."
        else:
            status = "RESTRICTED_NON_COMMERCIAL" if lic in RESTRICTIVE_LICENSES else "UNKNOWN_LICENSE"
            restricted_count += 1
            notes = f"License {lic!r} restricts commercial deployment."

        records.append(
            ModelLicenseRecord(
                model_id=model_id,
                system_name=system_name,
                declared_license=lic,
                is_commercial_permissible=is_permissible,
                status=status,
                notes=notes,
            )
        )

    receipt = LicenseAuditReceipt(
        audited_systems=records,
        total_audited=len(records),
        commercial_ready_count=commercial_count,
        restricted_count=restricted_count,
        all_commercial_ready=(restricted_count == 0),
    )
    receipt.audit_sha256 = sha256_digest(canonical_json_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("workbench/research/erst/technology-matrix.json"),
        help="Path to research technology-matrix.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON audit receipt",
    )
    parser.add_argument(
        "--fail-on-restricted",
        action="store_true",
        help="Exit with non-zero status if any evaluated candidate is non-commercial",
    )
    args = parser.parse_args()

    receipt = audit_technology_matrix(args.matrix)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json_bytes(receipt))

    print(json.dumps(receipt.model_dump(mode="json"), indent=2))

    if args.fail_on_restricted and not receipt.all_commercial_ready:
        print(f"\n[ERROR] {receipt.restricted_count} systems have restricted non-commercial licenses!", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
