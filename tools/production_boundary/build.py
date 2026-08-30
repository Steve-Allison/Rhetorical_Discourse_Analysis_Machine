"""Reproducibly build wheel and sdist from one clean, named Git commit."""

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
from typing import Final
import uuid

import rfc8785

from tools.production_boundary.contracts import sha256_path


PACKAGE_VERSION: Final = "5.0.0"
WHEEL_NAME: Final = f"isanlp_rst-{PACKAGE_VERSION}-py3-none-any.whl"
SDIST_NAME: Final = f"isanlp_rst-{PACKAGE_VERSION}.tar.gz"


@dataclass(frozen=True, slots=True)
class BuildRun:
    wheel: Path
    sdist: Path
    report: Path


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


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    with tarfile.open(archive_path, mode="r:") as archive:
        archive.extractall(destination, filter="data")


def _provenance_bytes(
    export_root: Path,
    *,
    commit: str,
    tree: str,
    archive_sha256: str,
    source_date_epoch: int,
) -> bytes:
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
            "package_name": "isanlp_rst",
            "package_version": PACKAGE_VERSION,
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


def _run_build(export_root: Path, run_root: Path, environment: dict[str, str]) -> BuildRun:
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
    wheel = output / WHEEL_NAME
    sdist = output / SDIST_NAME
    if not wheel.is_file() or not sdist.is_file():
        found = tuple(sorted(path.name for path in output.iterdir()))
        raise RuntimeError(f"build produced unexpected artifacts: {found}")
    if set(path.name for path in output.iterdir()) != {WHEEL_NAME, SDIST_NAME}:
        raise RuntimeError("build output contains files outside the exact wheel/sdist pair")
    json.loads(report.read_text(encoding="utf-8"))
    return BuildRun(wheel=wheel, sdist=sdist, report=report)


def _publish_immutable(source: Path, destination: Path) -> Path:
    if destination.exists():
        raise FileExistsError(f"promoted artifact already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)
    return destination


def build_production_artifacts(repository_root: Path, output_dir: Path) -> tuple[Path, Path]:
    """Double-build exact-commit artifacts via sdist and publish identical bytes."""

    root = repository_root.resolve()
    commit, tree, source_date_epoch = _require_clean_source(root)
    destination = output_dir.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"promoted artifact directory is not empty: {destination}")

    with tempfile.TemporaryDirectory(prefix="isanlp-rst-production-build-") as temporary:
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
            candidate = _provenance_bytes(
                export_root,
                commit=commit,
                tree=tree,
                archive_sha256=archive_sha256,
                source_date_epoch=source_date_epoch,
            )
            if provenance is not None and candidate != provenance:
                raise RuntimeError("build provenance changed between independent build roots")
            provenance = candidate
            (export_root / "isanlp_rst/build-provenance.json").write_bytes(candidate)
            runs.append(_run_build(export_root, run_root, environment))

        first, second = runs
        comparisons = {
            WHEEL_NAME: (sha256_path(first.wheel), sha256_path(second.wheel)),
            SDIST_NAME: (sha256_path(first.sdist), sha256_path(second.sdist)),
        }
        mismatches = {
            name: identities
            for name, identities in comparisons.items()
            if identities[0] != identities[1]
        }
        if mismatches:
            raise RuntimeError(f"independent via-sdist builds were not reproducible: {mismatches}")

        wheel = _publish_immutable(first.wheel, destination / WHEEL_NAME)
        sdist = _publish_immutable(first.sdist, destination / SDIST_NAME)
        report = {
            "schema_name": "isanlp_rst.release_evidence.reproducible_build",
            "schema_version": "1.0.0",
            "source_commit": commit,
            "source_tree": tree,
            "source_archive_sha256": archive_sha256,
            "source_date_epoch": source_date_epoch,
            "build_frontend": f"build {version('build')}",
            "build_backend": f"hatchling {version('hatchling')}",
            "build_reports": [sha256_path(run.report) for run in runs],
            "provenance_sha256": _sha256_bytes(provenance or b""),
            "artifacts": [
                {"path": str(path), "sha256": sha256_path(path)}
                for path in (wheel, sdist)
            ],
            "reproducible": True,
        }
        print(rfc8785.dumps(report).decode("utf-8"))
        return wheel, sdist


def main() -> int:
    root = Path.cwd()
    build_production_artifacts(root, root / "dist" / PACKAGE_VERSION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PACKAGE_VERSION",
    "SDIST_NAME",
    "WHEEL_NAME",
    "build_production_artifacts",
]
