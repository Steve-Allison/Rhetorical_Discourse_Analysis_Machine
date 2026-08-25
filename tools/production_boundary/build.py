"""Build production artifacts from a clean export of the exact Git commit."""

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


def _git(*arguments: str, repository_root: Path, capture_output: bool = True) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=repository_root,
        check=True,
        capture_output=capture_output,
        text=True,
    )
    return completed.stdout.strip() if completed.stdout is not None else ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_production_artifacts(repository_root: Path, output_dir: Path) -> tuple[Path, Path]:
    """Build one wheel and one sdist without consulting the mutable source tree."""

    root = repository_root.resolve()
    git_root = Path(_git("rev-parse", "--show-toplevel", repository_root=root)).resolve()
    if git_root != root:
        raise RuntimeError(f"repository root mismatch: expected {root}, Git reports {git_root}")
    tracked_status = _git("status", "--porcelain=v1", "--untracked-files=no", repository_root=root)
    if tracked_status:
        raise RuntimeError("production artifacts require a clean tracked worktree")
    commit = _git("rev-parse", "HEAD", repository_root=root)

    with tempfile.TemporaryDirectory(prefix="isanlp-rst-production-build-") as temporary:
        workspace = Path(temporary)
        archive_path = workspace / "source.tar"
        export_root = workspace / "source"
        build_output = workspace / "artifacts"
        export_root.mkdir()
        build_output.mkdir()
        _git(
            "archive",
            "--format=tar",
            f"--output={archive_path}",
            commit,
            repository_root=root,
            capture_output=False,
        )
        with tarfile.open(archive_path, mode="r:") as archive:
            archive.extractall(export_root, filter="data")

        environment = os.environ.copy()
        environment.update({"PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INDEX": "1"})
        subprocess.run(
            (
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--wheel",
                "--sdist",
                "--outdir",
                str(build_output),
            ),
            cwd=export_root,
            check=True,
            env=environment,
        )
        wheels = tuple(build_output.glob("*.whl"))
        sdists = tuple(build_output.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise RuntimeError(
                f"expected one wheel and one sdist, found wheels={len(wheels)}, sdists={len(sdists)}"
            )

        destination = output_dir.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        built_names = {wheels[0].name, sdists[0].name}
        unexpected = sorted(
            path.name
            for path in destination.iterdir()
            if path.is_file()
            and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
            and path.name not in built_names
        )
        if unexpected:
            raise RuntimeError(f"output directory contains unexpected production artifacts: {unexpected}")

        published: list[Path] = []
        for artifact in (*wheels, *sdists):
            final_path = destination / artifact.name
            temporary_path = destination / f".{artifact.name}.{uuid.uuid4().hex}.tmp"
            shutil.copyfile(artifact, temporary_path)
            os.replace(temporary_path, final_path)
            published.append(final_path)

    print(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "source_commit": commit,
                "source_mode": "git_archive",
                "network_dependency_installation": False,
                "artifacts": [
                    {"path": str(path), "sha256": _sha256(path)} for path in published
                ],
            },
            sort_keys=True,
        )
    )
    return published[0], published[1]


def main() -> int:
    build_production_artifacts(Path.cwd(), Path.cwd() / "dist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_production_artifacts"]
