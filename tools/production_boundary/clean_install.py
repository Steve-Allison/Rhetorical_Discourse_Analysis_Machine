"""Create clean core and core+http wheel installs and execute installed acceptance."""

import argparse
from collections import deque
from email.parser import BytesParser
from importlib.metadata import Distribution, distributions
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from typing import Any
import zipfile

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import NormalizedName, canonicalize_name, parse_wheel_filename

from tools.production_boundary.identity import read_release_identity


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {command!r}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def _venv_python(root: Path) -> Path:
    return root / "bin" / "python"


def _venv_purelib(python: Path, cwd: Path) -> Path:
    output = _run(
        [str(python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        cwd=cwd,
    )
    return Path(output)


def _wheel_requirements(wheel: Path) -> list[Requirement]:
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        message = BytesParser().parsebytes(archive.read(metadata_name))
    raw_reqs = message.get_all("Requires-Dist") or []
    return [Requirement(str(item)) for item in raw_reqs]


def _seed_offline_runtime_dependencies(
    *,
    wheel: Path,
    extras: tuple[str, ...],
    base_python: Path,
    target_purelib: Path,
    cwd: Path,
) -> None:
    """Link the exact declared runtime dependency closure from base_python without rdam or offline packages."""
    base_purelib = Path(
        _run(
            [str(base_python), "-I", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
            cwd=cwd,
        )
    )
    if not base_purelib.is_dir():
        base_purelib = Path(sysconfig.get_path("purelib"))

    by_name: dict[NormalizedName, Distribution] = {}
    for dist in distributions(path=[str(base_purelib)]):
        dist_name = dist.metadata["Name"]
        if dist_name:
            by_name[canonicalize_name(dist_name)] = dist

    base_env: dict[str, str] = {key: str(val) for key, val in default_environment().items()}
    visited: set[tuple[NormalizedName, frozenset[str]]] = set()
    queue: deque[tuple[NormalizedName, frozenset[str]]] = deque()

    def enqueue_requirements(reqs: list[Requirement], active_extras: frozenset[str]) -> None:
        contexts: list[dict[str, str]] = [
            {**base_env, "extra": ""},
            *({**base_env, "extra": extra} for extra in sorted(active_extras)),
        ]
        for req in reqs:
            if req.marker is not None and not any(req.marker.evaluate(ctx) for ctx in contexts):
                continue
            target_name = canonicalize_name(req.name)
            if target_name in {canonicalize_name("rdam"), canonicalize_name("pip")}:
                continue
            state = (target_name, frozenset(canonicalize_name(extra) for extra in req.extras))
            if state not in visited:
                visited.add(state)
                queue.append(state)

    enqueue_requirements(_wheel_requirements(wheel), frozenset(extras))

    selected_dists: dict[NormalizedName, Distribution] = {}
    while queue:
        dist_name, dist_extras = queue.popleft()
        dist = by_name.get(dist_name)
        if dist is None:
            raise RuntimeError(f"Offline runtime dependency {dist_name!r} is missing from {base_purelib}")
        selected_dists[dist_name] = dist
        sub_reqs = [Requirement(raw) for raw in (dist.requires or ())]
        enqueue_requirements(sub_reqs, dist_extras)

    entries_to_link: set[str] = set()
    for dist in selected_dists.values():
        for file_path in dist.files or ():
            parts = file_path.parts
            if not parts or parts[0] in {"..", "__pycache__"} or parts[0].endswith(".pth"):
                continue
            entries_to_link.add(parts[0])

    for entry_name in sorted(entries_to_link):
        src = base_purelib / entry_name
        dst = target_purelib / entry_name
        if src.exists() and not dst.exists():
            dst.symlink_to(src, target_is_directory=src.is_dir())


def _build_isolated_worktree_wheel(source_root: Path, workspace: Path) -> Path:
    """Build the rdam wheel from exported package inputs outside AI_Projects+Code without ontology/ access."""
    export_root = workspace / "package-source"
    export_root.mkdir(parents=True)
    shutil.copytree(
        source_root / "rdam",
        export_root / "rdam",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for filename in ("pyproject.toml", "README.md", "LICENSE", "LICENSE_MODELS"):
        source_file = source_root / filename
        if source_file.is_file():
            shutil.copy2(source_file, export_root / filename)
    wheel_dir = workspace / "wheelhouse"
    wheel_dir.mkdir(parents=True)
    env = dict(os.environ)
    env.update(
        {
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INDEX": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    _run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(wheel_dir),
            str(export_root),
        ],
        cwd=workspace,
        environment=env,
    )
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"Expected exactly 1 built wheel, found {wheels}")
    return wheels[0]


def _install_and_run(
    *,
    name: str,
    wheel: Path,
    source_root: Path,
    acceptance: Path,
    model_store: Path,
    doclang_fixture: Path,
    full: bool,
    device: str,
    parity_baseline: Path | None,
    base_python: Path,
    release_id: str | None,
    expected_version: str,
    offline_seed: bool = False,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"rdam-{name}-") as directory:
        root = Path(directory)
        subprocess.run([str(base_python), "-m", "venv", str(root)], check=True)
        python = _venv_python(root)
        extras = ("http",) if "http" in name else ()
        if offline_seed:
            purelib = _venv_purelib(python, root)
            _seed_offline_runtime_dependencies(
                wheel=wheel,
                extras=extras,
                base_python=base_python,
                target_purelib=purelib,
                cwd=root,
            )
            install = [str(python), "-m", "pip", "install", "--no-deps", "--no-index", str(wheel)]
        else:
            requirement = f"{wheel}[{','.join(extras)}]" if extras else str(wheel)
            install = [str(python), "-m", "pip", "install", requirement]
        _run(install, cwd=root)
        command = [
            str(python),
            "-I",
            str(acceptance),
            "--source-root",
            str(source_root),
            "--expected-version",
            expected_version,
            "--model-store",
            str(model_store),
            "--device",
            device,
            "--doclang",
            str(doclang_fixture),
        ]
        if release_id is not None:
            command.extend(("--release-id", release_id))
        if "http" in extras:
            command.append("--http")
        if full:
            command.append("--full")
        acceptance_environment = dict(os.environ)
        acceptance_environment.update(
            {
                "HF_HUB_OFFLINE": "1",
                "RDAM_NETWORK_DISABLED": "1",
                "PIP_NO_INDEX": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
        )
        payload = json.loads(_run(command, cwd=root, environment=acceptance_environment))
        _run([str(python), "-m", "pip", "check"], cwd=root)
        inspection: Any = json.loads(
            _run([str(python), "-m", "pip", "inspect"], cwd=root)
        )
        receipt: dict[str, object] = {
            "environment": name,
            "python": str(python),
            "acceptance": payload,
            "pip_check": "passed",
            "pip_inspect": inspection,
        }
        if parity_baseline is not None and name == "core":
            parity_command = [
                str(python),
                "-I",
                str(source_root / "tools/production_boundary/parity.py"),
                "--device",
                device,
                "--compare",
                str(parity_baseline),
            ]
            receipt["parity"] = json.loads(_run(parity_command, cwd=root))
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel",
        type=Path,
        help="the built wheel; defaults to dist/<version>/<wheel> for the version declared in pyproject.toml",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--model-store", type=Path)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--self-contained-proof", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--parity-baseline", type=Path)
    parser.add_argument("--base-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--release-id")
    args = parser.parse_args()
    if args.full and args.release_id is None:
        raise ValueError("full clean-install certification requires --release-id")
    if not args.self_contained_proof and args.model_store is None:
        raise ValueError("--model-store is required unless --self-contained-proof is set")

    root = args.root.resolve()
    if args.self_contained_proof:
        with tempfile.TemporaryDirectory(prefix="rdam-clean-install-proof-") as temp_dir:
            proof_workspace = Path(temp_dir).resolve()
            wheel = (
                args.wheel.resolve()
                if args.wheel is not None
                else _build_isolated_worktree_wheel(root, proof_workspace)
            )
            _, wheel_version, _, _ = parse_wheel_filename(wheel.name)
            isolated_acceptance = proof_workspace / "installed_acceptance.py"
            shutil.copy2(root / "tools/production_boundary/installed_acceptance.py", isolated_acceptance)
            isolated_doclang = proof_workspace / "mixed.dclg"
            shutil.copy2(root / "tests/fixtures/production_api/retained_content/mixed.dclg", isolated_doclang)
            isolated_store = (
                args.model_store.resolve() if args.model_store is not None else proof_workspace / "empty-model-store"
            )
            isolated_store.mkdir(parents=True, exist_ok=True)
            receipts = tuple(
                _install_and_run(
                    name=name,
                    wheel=wheel,
                    source_root=root,
                    acceptance=isolated_acceptance,
                    model_store=isolated_store,
                    doclang_fixture=isolated_doclang,
                    full=args.full,
                    device=args.device,
                    parity_baseline=args.parity_baseline.resolve() if args.parity_baseline is not None else None,
                    base_python=args.base_python.resolve(),
                    release_id=args.release_id,
                    expected_version=str(wheel_version),
                    offline_seed=True,
                )
                for name in ("core", "core+http")
            )
            summary = {
                "environments": [
                    {
                        "environment": item["environment"],
                        "pip_check": item["pip_check"],
                        "acceptance": item["acceptance"],
                    }
                    for item in receipts
                ],
                "self_contained_proof": True,
                "valid": True,
                "wheel": wheel.name,
            }
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0

    assert args.model_store is not None
    if args.wheel is not None:
        wheel = args.wheel.resolve()
    else:
        identity = read_release_identity(root)
        wheel = identity.release_dir(root) / identity.wheel_name
    _, wheel_version, _, _ = parse_wheel_filename(wheel.name)
    doclang_fixture = root / "tests/fixtures/production_api/retained_content/mixed.dclg"
    acceptance = root / "tools/production_boundary/installed_acceptance.py"
    receipts = tuple(
        _install_and_run(
            name=name,
            wheel=wheel,
            source_root=root,
            acceptance=acceptance,
            model_store=args.model_store.resolve(),
            doclang_fixture=doclang_fixture,
            full=args.full,
            device=args.device,
            parity_baseline=args.parity_baseline.resolve() if args.parity_baseline is not None else None,
            base_python=args.base_python.resolve(),
            release_id=args.release_id,
            expected_version=str(wheel_version),
        )
        for name in ("core", "core+http")
    )
    print(json.dumps({"install_receipts": receipts, "valid": True}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
