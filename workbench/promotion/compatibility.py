"""Re-declare a stored release's package compatibility without touching the release.

A release manifest is immutable, and its ``compatibility_range`` is the promoter's claim
at promotion time. When a later package version runs the release unchanged — the same
runtime contract, and the equivalence procedure passed — this tool records that finding
beside the release as ``<store>/<release_id>.compatibility.json``, bound to the exact
manifest digest, and proves the release now loads before returning.

Run: ``pixi run redeclare-compatibility --store <store> --release-id <id> --range '<spec>' --reason '...' --basis <evidence> ...``
"""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from rdam.rst.model_loading.release import (
    MODEL_RELEASE_MANIFEST,
    CompatibilityRedeclaration,
    ModelReleaseError,
    ModelReleaseManifest,
    canonical_json_bytes,
    compatibility_redeclaration_path,
    validate_model_release,
)


def redeclare_compatibility(
    store: Path,
    release_id: str,
    *,
    compatibility_range: str,
    declared_by: str,
    reason: str,
    basis: tuple[str, ...],
) -> CompatibilityRedeclaration:
    """Write the re-declaration for one stored release and prove the release loads under it."""

    release = (Path(store).resolve() / release_id).resolve()
    if release.parent != Path(store).resolve():
        raise ModelReleaseError(f"release_id escapes the model store: {release_id!r}")
    manifest_path = release / MODEL_RELEASE_MANIFEST
    if not manifest_path.is_file():
        raise ModelReleaseError(f"no stored release named {release_id!r} in {store}")
    manifest = ModelReleaseManifest.model_validate_json(manifest_path.read_bytes())
    if manifest.release_id != release_id:
        raise ModelReleaseError(f"stored manifest names {manifest.release_id!r}, not {release_id!r}")
    redeclaration = CompatibilityRedeclaration(
        release_id=release_id,
        manifest_sha256=manifest.manifest_sha256,
        compatibility_range=compatibility_range,
        declared_at=datetime.now(UTC),
        declared_by=declared_by,
        reason=reason,
        basis=basis,
    )
    path = compatibility_redeclaration_path(release)
    payload = canonical_json_bytes(redeclaration) + b"\n"
    if path.exists() and path.read_bytes() != payload:
        raise FileExistsError(f"a different compatibility re-declaration already exists: {path}")
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    try:
        validated = validate_model_release(release)
    except ModelReleaseError:
        path.unlink()
        raise
    if validated.redeclaration != redeclaration:
        path.unlink()
        raise ModelReleaseError("the loader did not honour the re-declaration it was given")
    return redeclaration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--store", type=Path, default=Path("models/model-releases"))
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--range", required=True, dest="compatibility_range", help="a Python version specifier, e.g. '>=5.0.0,<7.0.0'")
    parser.add_argument("--declared-by", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--basis", action="append", required=True, help="evidence path or record the re-declaration rests on (repeatable)")
    args = parser.parse_args()
    redeclaration = redeclare_compatibility(
        args.store,
        args.release_id,
        compatibility_range=args.compatibility_range,
        declared_by=args.declared_by,
        reason=args.reason,
        basis=tuple(args.basis),
    )
    print(redeclaration.model_dump_json(indent=2))
    return 0


__all__ = ["redeclare_compatibility"]


if __name__ == "__main__":
    raise SystemExit(main())
