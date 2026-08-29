"""Atomic offline promotion into the immutable local production model store."""

import argparse
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile

from isanlp_rst._version import resolve_installed_package_version
from isanlp_rst.model_loading.release import (
    MODEL_RELEASE_MANIFEST,
    ModelFile,
    ModelReleaseError,
    ModelReleaseManifest,
    PromotionReceipt,
    canonical_json_bytes,
    sha256_file,
    validate_model_release,
)


def write_candidate_manifest(
    candidate: Path | str,
    *,
    release_id: str,
    model_task: str,
    architecture: str,
    runtime_contract: str,
    compatibility_range: str,
    source_model_identity: str,
    source_revision: str,
    licence: str,
    use_restrictions: tuple[str, ...],
    roles: dict[PurePosixPath, str],
    evaluation_evidence: str | None = None,
    evaluation_unavailable_reason: str | None = None,
) -> ModelReleaseManifest:
    """Inventory a fully prepared candidate and write its canonical manifest."""

    root = Path(candidate).resolve()
    if not root.is_dir() or root.is_symlink():
        raise ModelReleaseError("candidate must be a real local directory")
    manifest_path = root / MODEL_RELEASE_MANIFEST
    if manifest_path.exists() or manifest_path.is_symlink():
        raise FileExistsError(f"candidate manifest already exists: {manifest_path}")
    actual: set[PurePosixPath] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ModelReleaseError(f"candidate contains a symlink: {path.relative_to(root)}")
        if path.is_file():
            actual.add(PurePosixPath(path.relative_to(root).as_posix()))
    if actual != set(roles):
        missing_roles = sorted(str(path) for path in actual - set(roles))
        missing_files = sorted(str(path) for path in set(roles) - actual)
        raise ModelReleaseError(
            f"candidate role inventory mismatch; missing_roles={missing_roles}, missing_files={missing_files}"
        )
    files = tuple(
        ModelFile(
            path=relative,
            role=roles[relative],
            size_bytes=(root / relative).stat().st_size,
            sha256=sha256_file(root / relative),
        )
        for relative in sorted(actual, key=str)
    )
    manifest = ModelReleaseManifest(
        release_id=release_id,
        model_task=model_task,
        architecture=architecture,
        runtime_contract=runtime_contract,
        compatibility_range=compatibility_range,
        source_model_identity=source_model_identity,
        source_revision=source_revision,
        licence=licence,
        use_restrictions=use_restrictions,
        evaluation_evidence=evaluation_evidence,
        evaluation_unavailable_reason=evaluation_unavailable_reason,
        created_at=datetime.now(UTC),
        producer_version=resolve_installed_package_version(),
        files=files,
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    validate_model_release(root, require_release_name=False)
    return manifest


def copy_release_file(source: Path, target: Path) -> None:
    """Copy one immutable file, using an APFS clone when macOS supports it."""

    target.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        completed = subprocess.run(
            ("/bin/cp", "-c", str(source), str(target)),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return
        if target.exists():
            target.unlink()
    shutil.copy2(source, target)


def promote_model_release(candidate: Path | str, store: Path | str) -> PromotionReceipt:
    """Verify, copy, re-verify, and atomically publish one candidate release."""

    source = Path(candidate).resolve()
    validated_candidate = validate_model_release(source, require_release_name=False)
    production_store = Path(store).resolve()
    production_store.mkdir(parents=True, exist_ok=True)
    if production_store.is_symlink():
        raise ModelReleaseError("production model store cannot be a symlink")
    destination = production_store / validated_candidate.manifest.release_id
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable model release already exists: {destination}")

    temporary = Path(tempfile.mkdtemp(prefix=".promotion-", dir=production_store))
    try:
        for source_path in source.rglob("*"):
            relative = source_path.relative_to(source)
            target = temporary / relative
            if source_path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif source_path.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                copy_release_file(source_path, target)
            else:
                raise ModelReleaseError(f"candidate member is not a regular file: {relative}")
        copied = validate_model_release(temporary, require_release_name=False)
        if copied.manifest.manifest_sha256 != validated_candidate.manifest.manifest_sha256:
            raise ModelReleaseError("candidate and copied manifest hashes differ")
        temporary.rename(destination)
        released = validate_model_release(destination)
        return PromotionReceipt(
            candidate_path=str(source),
            candidate_manifest_sha256=validated_candidate.manifest.manifest_sha256,
            release_path=str(destination),
            release_manifest_sha256=released.manifest.manifest_sha256,
            verified_files=len(released.manifest.files),
            promoted_at=datetime.now(UTC),
            producer_version=resolve_installed_package_version(),
            succeeded=True,
        )
    except BaseException:
        shutil.rmtree(temporary)
        raise


def main() -> int:
    """Promote one already-manifested candidate and print its strict receipt."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    args = parser.parse_args()
    receipt = promote_model_release(args.candidate, args.store)
    print(receipt.model_dump_json(indent=2))
    return 0


__all__ = ["copy_release_file", "promote_model_release", "write_candidate_manifest"]


if __name__ == "__main__":
    raise SystemExit(main())
