"""Reproducibly build wheel and sdist from one clean, named Git commit.

``dist/`` is ignored build output, never tracked: a release is a tagged commit, and the
artifacts are rebuilt from it on demand. What is committed is the evidence — the
source-release record and the reproducible-build report — written to the evidence
directory named on the command line. Distribution name, version, and package directory
come from ``pyproject.toml`` (``tools.production_boundary.identity``); nothing here
restates them.
"""

import argparse
from dataclasses import dataclass
from importlib.metadata import version
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid

import rfc8785

from tools.production_boundary.contracts import (
    BuiltArtifactIdentity,
    ReproducibleBuildReport,
    SourceReleaseIdentity,
    SourceReleaseRecord,
    canonical_record_bytes,
    sha256_path,
    write_canonical_record,
)
from tools.production_boundary.identity import ReleaseIdentity, read_release_identity


@dataclass(frozen=True, slots=True)
class BuildRun:
    wheel: Path
    sdist: Path
    report: Path


@dataclass(frozen=True, slots=True)
class ProductionBuild:
    """The published artifact pair and the reproducible-build report describing it."""

    wheel: Path
    sdist: Path
    report: ReproducibleBuildReport


def _git(*arguments: str, repository_root: Path, capture_output: bool = True) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository_root,
        check=True,
        capture_output=capture_output,
        text=True,
    )
    return completed.stdout.strip() if completed.stdout is not None else ""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_clean_source(root: Path) -> tuple[str, str, int]:
    git_root = Path(_git("rev-parse", "--show-toplevel", repository_root=root)).resolve()
    if git_root != root:
        raise RuntimeError(f"repository root mismatch: expected {root}, Git reports {git_root}")
    status = _git(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        repository_root=root,
    )
    if status:
        raise RuntimeError("production artifacts require a completely clean worktree")
    commit = _git("rev-parse", "HEAD", repository_root=root)
    tree = _git("rev-parse", "HEAD^{tree}", repository_root=root)
    source_date_epoch = int(
        _git("show", "-s", "--format=%ct", commit, repository_root=root)
    )
    return commit, tree, source_date_epoch


def _source_tag(root: Path) -> str | None:
    """The tag naming HEAD exactly, if any — a release build is expected to have one."""

    try:
        return _git("describe", "--tags", "--exact-match", "HEAD", repository_root=root)
    except subprocess.CalledProcessError:
        return None


def _archive_commit(root: Path, commit: str, destination: Path) -> str:
    _git(
        "archive",
        "--format=tar",
        f"--output={destination}",
        commit,
        repository_root=root,
        capture_output=False,
    )
    return sha256_path(destination)


def source_release_record(repository_root: Path) -> SourceReleaseRecord:
    """Select and identify the exact clean source revision for a release."""

    root = repository_root.resolve()
    commit, tree, source_date_epoch = _require_clean_source(root)
    with tempfile.TemporaryDirectory(prefix="rdam-source-release-") as temporary:
        archive_sha256 = _archive_commit(root, commit, Path(temporary) / "source.tar")
    return SourceReleaseRecord(
        source=SourceReleaseIdentity(
            commit=commit,
            tree=tree,
            archive_sha256=archive_sha256,
            source_date_epoch=source_date_epoch,
        )
    )


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    with tarfile.open(archive_path, mode="r:") as archive:
        archive.extractall(destination, filter="data")


def _prepare_package_source(export_root: Path) -> None:
    """Remove build-control files that Hatchling always adds to an sdist."""

    (export_root / ".gitignore").unlink(missing_ok=True)


def _provenance_bytes(
    export_root: Path,
    identity: ReleaseIdentity,
    *,
    commit: str,
    tree: str,
    archive_sha256: str,
    source_date_epoch: int,
) -> bytes:
    """The packaged runtime provenance resource — schema 1.0.0, read strictly by
    ``rdam.rst._provenance``. Its field set is fixed; release-level facts such as the
    tag live in the committed ``ReproducibleBuildReport``, not here."""
    pyproject_identity = sha256_path(export_root / "pyproject.toml")
    lock_identity = sha256_path(export_root / "pixi.lock")
    build_input_identity = _sha256_bytes(
        rfc8785.dumps(
            {
                "source_archive_sha256": archive_sha256,
                "pyproject_sha256": pyproject_identity,
                "pixi_lock_sha256": lock_identity,
            }
        )
    )
    return rfc8785.dumps(
        {
            "schema_name": "isanlp_rst.build_provenance",
            "schema_version": "1.0.0",
            "package_name": identity.distribution,
            "package_version": identity.version,
            "production_contract": "isanlp_rst.production",
            "production_contract_version": "2.0.0",
            "source_commit": commit,
            "source_tree": tree,
            "source_archive_sha256": archive_sha256,
            "source_date_epoch": source_date_epoch,
            "build_input_sha256": build_input_identity,
            "build_tool": f"build {version('build')}",
        }
    ) + b"\n"


def _run_build(export_root: Path, run_root: Path, environment: dict[str, str], identity: ReleaseIdentity) -> BuildRun:
    output = run_root / "artifacts"
    report = run_root / "build-report.json"
    output.mkdir(parents=True)
    subprocess.run(
        (
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(output),
            "--report",
            str(report),
            str(export_root),
        ),
        cwd=run_root,
        check=True,
        env=environment,
    )
    wheel = output / identity.wheel_name
    sdist = output / identity.sdist_name
    if not wheel.is_file() or not sdist.is_file():
        found = tuple(sorted(path.name for path in output.iterdir()))
        raise RuntimeError(f"build produced unexpected artifacts: {found}")
    if set(path.name for path in output.iterdir()) != {identity.wheel_name, identity.sdist_name}:
        raise RuntimeError("build output contains files outside the exact wheel/sdist pair")
    json.loads(report.read_text(encoding="utf-8"))
    return BuildRun(wheel=wheel, sdist=sdist, report=report)


def _publish_artifact(source: Path, destination: Path) -> Path:
    """Atomically place one built artifact at its output path."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)
    return destination


def _reset_output_dir(destination: Path, identity: ReleaseIdentity) -> None:
    """Empty the output directory, refusing to touch anything that is not this release's pair."""

    if destination.exists():
        unexpected = sorted(
            path.name for path in destination.iterdir() if path.name not in {identity.wheel_name, identity.sdist_name}
        )
        if unexpected:
            raise RuntimeError(f"output directory holds files that are not this release's artifacts: {unexpected}")
        shutil.rmtree(destination)
    destination.mkdir(parents=True)


def build_production_artifacts(
    repository_root: Path,
    output_dir: Path,
    identity: ReleaseIdentity | None = None,
) -> ProductionBuild:
    """Double-build exact-commit artifacts via sdist and publish identical bytes.

    The output directory is derived, ignored build output: a previous pair there is
    replaced. If HEAD carries a tag it must be ``v<version>``; a tag naming a different
    version is a real error, not a warning.
    """

    root = repository_root.resolve()
    release = identity or read_release_identity(root)
    commit, tree, source_date_epoch = _require_clean_source(root)
    source_tag = _source_tag(root)
    if source_tag is not None and source_tag != release.tag:
        raise RuntimeError(f"HEAD is tagged {source_tag!r} but the package version is {release.version}")
    destination = output_dir.resolve()
    _reset_output_dir(destination, release)

    with tempfile.TemporaryDirectory(prefix="rdam-production-build-") as temporary:
        workspace = Path(temporary)
        archive_path = workspace / "source.tar"
        archive_sha256 = _archive_commit(root, commit, archive_path)
        provenance: bytes | None = None
        runs: list[BuildRun] = []
        environment = os.environ.copy()
        environment.update(
            {
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_INDEX": "1",
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": str(source_date_epoch),
                "TZ": "UTC",
            }
        )
        for index in (1, 2):
            run_root = workspace / f"run-{index}"
            export_root = run_root / "source"
            _extract_archive(archive_path, export_root)
            _prepare_package_source(export_root)
            candidate = _provenance_bytes(
                export_root,
                release,
                commit=commit,
                tree=tree,
                archive_sha256=archive_sha256,
                source_date_epoch=source_date_epoch,
            )
            if provenance is not None and candidate != provenance:
                raise RuntimeError("build provenance changed between independent build roots")
            provenance = candidate
            (export_root / release.package_dir / "build-provenance.json").write_bytes(candidate)
            runs.append(_run_build(export_root, run_root, environment, release))

        first, second = runs
        comparisons = {
            release.wheel_name: (sha256_path(first.wheel), sha256_path(second.wheel)),
            release.sdist_name: (sha256_path(first.sdist), sha256_path(second.sdist)),
        }
        mismatches = {
            name: identities
            for name, identities in comparisons.items()
            if identities[0] != identities[1]
        }
        if mismatches:
            raise RuntimeError(f"independent via-sdist builds were not reproducible: {mismatches}")

        wheel = _publish_artifact(first.wheel, destination / release.wheel_name)
        sdist = _publish_artifact(first.sdist, destination / release.sdist_name)
        report = ReproducibleBuildReport(
            source_commit=commit,
            source_tree=tree,
            source_tag=source_tag,
            source_archive_sha256=archive_sha256,
            source_date_epoch=source_date_epoch,
            build_frontend=f"build {version('build')}",
            build_backend=f"hatchling {version('hatchling')}",
            build_reports=(sha256_path(first.report), sha256_path(second.report)),
            provenance_sha256=_sha256_bytes(provenance or b""),
            artifacts=(
                BuiltArtifactIdentity(filename=wheel.name, sha256=sha256_path(wheel), size_bytes=wheel.stat().st_size),
                BuiltArtifactIdentity(filename=sdist.name, sha256=sha256_path(sdist), size_bytes=sdist.stat().st_size),
            ),
        )
        return ProductionBuild(wheel=wheel, sdist=sdist, report=report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        required=True,
        help="directory receiving source-release.json and reproducible-build.json",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    identity = read_release_identity(root)
    source_record = source_release_record(root)
    build = build_production_artifacts(root, identity.release_dir(root), identity)
    evidence_dir = args.evidence_dir if args.evidence_dir.is_absolute() else root / args.evidence_dir
    write_canonical_record(evidence_dir / "source-release.json", source_record)
    write_canonical_record(evidence_dir / "reproducible-build.json", build.report)
    print(canonical_record_bytes(build.report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ProductionBuild",
    "build_production_artifacts",
    "source_release_record",
]
