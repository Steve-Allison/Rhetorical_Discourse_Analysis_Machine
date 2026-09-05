"""Create clean core/formats wheel installs and execute installed acceptance."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from packaging.utils import parse_wheel_filename

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


def _install_and_run(
    *,
    name: str,
    wheel: Path,
    source_root: Path,
    acceptance: Path,
    model_store: Path,
    fixtures: tuple[Path, Path, Path],
    full: bool,
    device: str,
    parity_baseline: Path | None,
    base_python: Path,
    release_id: str | None,
    erst_checkpoint: Path | None,
    expected_version: str,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix=f"rdam-{name}-") as directory:
        root = Path(directory)
        subprocess.run([str(base_python), "-m", "venv", str(root)], check=True)
        python = _venv_python(root)
        extras = tuple(extra for extra in ("formats", "http") if extra in name)
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
        ]
        if release_id is not None:
            command.extend(("--release-id", release_id))
        if erst_checkpoint is not None:
            command.extend(("--erst-checkpoint", str(erst_checkpoint)))
        if "http" in extras:
            command.append("--http")
        if "formats" in extras:
            command.extend(
                [
                    "--formats",
                    "--markdown",
                    str(fixtures[0]),
                    "--doclang",
                    str(fixtures[1]),
                    "--docling",
                    str(fixtures[2]),
                ]
            )
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
        if parity_baseline is not None and name == "formats":
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
    parser.add_argument("--model-store", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--parity-baseline", type=Path)
    parser.add_argument("--base-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--release-id")
    parser.add_argument("--erst-checkpoint", type=Path)
    args = parser.parse_args()
    if args.full and args.release_id is None:
        raise ValueError("full clean-install certification requires --release-id")
    root = args.root.resolve()
    if args.wheel is not None:
        wheel = args.wheel.resolve()
    else:
        identity = read_release_identity(root)
        wheel = identity.release_dir(root) / identity.wheel_name
    _, wheel_version, _, _ = parse_wheel_filename(wheel.name)
    fixtures = (
        root / "tests/fixtures/markdown/minimal.md",
        root / "tests/fixtures/doclang/ok_comprehensive.dclg",
        root / "tests/fixtures/docling/markdown.docling.json",
    )
    acceptance = root / "tools/production_boundary/installed_acceptance.py"
    receipts = tuple(
        _install_and_run(
            name=name,
            wheel=wheel,
            source_root=root,
            acceptance=acceptance,
            model_store=args.model_store.resolve(),
            fixtures=fixtures,
            full=args.full,
            device=args.device,
            parity_baseline=args.parity_baseline.resolve() if args.parity_baseline is not None else None,
            base_python=args.base_python.resolve(),
            release_id=args.release_id,
            erst_checkpoint=(
                args.erst_checkpoint.resolve() if args.erst_checkpoint is not None else None
            ),
            expected_version=str(wheel_version),
        )
        for name in ("core", "core+http", "formats", "formats+http")
    )
    print(json.dumps({"install_receipts": receipts, "valid": True}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
