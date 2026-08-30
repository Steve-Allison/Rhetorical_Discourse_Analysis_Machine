"""Run the one routine production boundary gate."""

import argparse
import json
from pathlib import Path

from tools.production_boundary.artifacts import inspect_artifact, validate_release_directory
from tools.production_boundary.authority import OwnershipAuthority, validate_ownership
from tools.production_boundary.contracts import BoundaryReport, BoundaryViolation, OwnershipClass, ViolationKind
from tools.production_boundary.dependencies import validate_declared_dependencies
from tools.production_boundary.imports import validate_import_boundary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    parser.add_argument("--release-dir", type=Path)
    args = parser.parse_args()
    authority = OwnershipAuthority(args.root)
    imports = validate_import_boundary(args.root, authority)
    ownership_violations = validate_ownership(authority)
    receipts = tuple(inspect_artifact(path) for path in args.artifact)
    artifact_violations: list[BoundaryViolation] = []
    for receipt in receipts:
        artifact_violations.extend(
            BoundaryViolation(
                kind=ViolationKind.FORBIDDEN_ARTIFACT_MEMBER,
                root=receipt.artifact_path,
                path=(member,),
                detail="artifact member is outside the production boundary",
            )
            for member in receipt.forbidden_members
        )
        artifact_violations.extend(
            BoundaryViolation(
                kind=ViolationKind.FORBIDDEN_DEPENDENCY,
                root=receipt.artifact_path,
                path=(dependency,),
                detail="artifact metadata declares an offline or unclassified dependency",
            )
            for dependency in receipt.declared_dependencies
            if authority.dependency_owner(dependency) != OwnershipClass.PRODUCTION
        )
    report = BoundaryReport(
        scanned_files=imports.scanned_files,
        production_modules=imports.production_modules,
        elapsed_ms=imports.elapsed_ms,
        artifact_receipts=receipts,
        violations=(
            imports.violations
            + validate_declared_dependencies(args.root, authority)
            + ownership_violations
            + tuple(artifact_violations)
        ),
    )
    payload = report.model_dump(mode="json")
    payload["valid"] = report.valid
    if args.release_dir is not None:
        payload["promoted_release"] = validate_release_directory(args.release_dir)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
