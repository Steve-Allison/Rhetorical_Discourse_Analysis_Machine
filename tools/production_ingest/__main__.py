"""Command-line authority for Gold assembly and immutable baseline freeze."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

from tools.production_ingest.assessor import assess_candidate_preparation
from tools.production_ingest.contracts import GoldSetManifest
from tools.production_ingest.freeze import freeze_baseline
from tools.production_ingest.gold import adjudicate_gold_set, assemble_gold_set, verify_gold_set
from tools.production_ingest.inspection import inspect_candidate_outputs, inspection_status_by_id
from tools.production_ingest.report import build_promotion_decision
from tools.production_ingest.runner import run_baseline_gold_analysis, run_candidate_preparation

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = REPOSITORY_ROOT / "specs/002-production-source-ingest/evidence"
DEFAULT_GOLD_ROOT = Path.home() / ".local/share/isanlp-rst/production-ingest-gold/002-v1"
DEFAULT_MODEL_STORE = Path.home() / ".cache/isanlp_rst/model-releases"
DEFAULT_MANIFEST = EVIDENCE_ROOT / "gold-manifest.json"
DEFAULT_FREEZE = EVIDENCE_ROOT / "baseline-freeze.json"


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m tools.production_ingest")
    subparsers = parser.add_subparsers(dest="command", required=True)
    assemble = subparsers.add_parser("assemble")
    assemble.add_argument("--gold-root", type=Path, required=True)
    assemble.add_argument("--real-root", type=Path, required=True)
    assemble.add_argument("--repository-root", type=Path, default=Path.cwd())
    assemble.add_argument("--manifest", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--gold-root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    adjudicate = subparsers.add_parser("adjudicate")
    adjudicate.add_argument("--gold-root", type=Path, required=True)
    adjudicate.add_argument("--manifest", type=Path, required=True)
    adjudicate.add_argument("--inspection-record", type=Path, required=True)
    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    freeze.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    freeze.add_argument("--repository-root", type=Path, default=REPOSITORY_ROOT)
    freeze.add_argument("--model-release", type=Path)
    freeze.add_argument("--baseline-commit")
    freeze.add_argument("--output", type=Path, default=DEFAULT_FREEZE)
    candidate = subparsers.add_parser("candidate")
    candidate.add_argument("--wheel", type=Path)
    candidate.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    candidate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    candidate.add_argument("--output-root", type=Path, default=DEFAULT_GOLD_ROOT / "candidate-final")
    candidate.add_argument("--model-store", type=Path, default=DEFAULT_MODEL_STORE)
    candidate.add_argument("--model-release-id")
    candidate.add_argument("--device", default="cpu")
    candidate.add_argument("--prepare-only", action="store_true")
    candidate.add_argument("--repetitions", type=int, default=1)
    candidate.add_argument("--evidence", type=Path, default=EVIDENCE_ROOT / "candidate-run.json")
    baseline = subparsers.add_parser("baseline")
    baseline.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    baseline.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    baseline.add_argument("--output-root", type=Path, default=DEFAULT_GOLD_ROOT / "baseline-final")
    baseline.add_argument("--model-store", type=Path, default=DEFAULT_MODEL_STORE)
    baseline.add_argument("--model-release-id")
    baseline.add_argument("--baseline-commit")
    baseline.add_argument("--device", default="cpu")
    baseline.add_argument("--evidence", type=Path, default=EVIDENCE_ROOT / "baseline-run.json")
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    inspect.add_argument("--candidate-output-root", type=Path, default=DEFAULT_GOLD_ROOT / "candidate-final")
    inspect.add_argument("--output", type=Path, default=EVIDENCE_ROOT / "inspection-record.json")
    assess = subparsers.add_parser("assess")
    assess.add_argument("--wheel", type=Path)
    assess.add_argument("--gold-root", type=Path, default=DEFAULT_GOLD_ROOT)
    assess.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    assess.add_argument("--candidate-output-root", type=Path, default=DEFAULT_GOLD_ROOT / "candidate-final")
    assess.add_argument("--baseline-output-root", type=Path, default=DEFAULT_GOLD_ROOT / "baseline-final")
    assess.add_argument("--inspection-record", type=Path, default=EVIDENCE_ROOT / "inspection-record.json")
    assess.add_argument("--model-store", type=Path, default=DEFAULT_MODEL_STORE)
    assess.add_argument("--model-release-id")
    assess.add_argument("--output", type=Path, default=EVIDENCE_ROOT / "promotion-report.json")
    clean = subparsers.add_parser("clean-install")
    clean.add_argument("--wheel", type=Path)
    clean.add_argument("--model-store", type=Path, default=DEFAULT_MODEL_STORE)
    clean.add_argument("--device", default="cpu")
    clean.add_argument("--full", action="store_true")
    arguments = parser.parse_args()

    if arguments.command == "assemble":
        manifest = assemble_gold_set(
            arguments.gold_root,
            real_root=arguments.real_root,
            repository_root=arguments.repository_root,
            frozen_at=datetime.now(UTC),
        )
        _write_model(arguments.manifest, manifest)
    elif arguments.command == "verify":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        verify_gold_set(manifest, arguments.gold_root)
    elif arguments.command == "adjudicate":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        updated, record = adjudicate_gold_set(
            manifest,
            arguments.gold_root,
            adjudicated_at=datetime.now(UTC),
        )
        _write_model(arguments.manifest, updated)
        arguments.inspection_record.parent.mkdir(parents=True, exist_ok=True)
        arguments.inspection_record.write_text(
            json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif arguments.command == "freeze":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        prior = json.loads(DEFAULT_FREEZE.read_text(encoding="utf-8")) if DEFAULT_FREEZE.exists() else {}
        baseline_commit = arguments.baseline_commit or prior.get("baseline_commit")
        model_release_id = prior.get("model_release_id")
        model_release = arguments.model_release or (
            DEFAULT_MODEL_STORE / model_release_id if isinstance(model_release_id, str) else None
        )
        if not isinstance(baseline_commit, str) or model_release is None:
            raise ValueError("freeze requires an immutable baseline commit and model release")
        authority = freeze_baseline(
            repository_root=arguments.repository_root,
            gold_root=arguments.gold_root,
            manifest=manifest,
            model_release=model_release,
            baseline_commit=baseline_commit,
        )
        _write_model(arguments.output, authority)
    elif arguments.command == "candidate":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        wheel = arguments.wheel or _only_wheel(REPOSITORY_ROOT / "dist")
        freeze_record = json.loads(DEFAULT_FREEZE.read_text(encoding="utf-8"))
        release_id = arguments.model_release_id or freeze_record["model_release_id"]
        result = run_candidate_preparation(
            wheel=wheel,
            manifest=manifest,
            gold_root=arguments.gold_root,
            output_root=arguments.output_root,
            repository_root=REPOSITORY_ROOT,
            model_store=None if arguments.prepare_only else arguments.model_store,
            model_release_id=None if arguments.prepare_only else release_id,
            device=arguments.device,
            repetitions=arguments.repetitions,
        )
        _write_json(arguments.evidence, result)
    elif arguments.command == "baseline":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        freeze_record = json.loads(DEFAULT_FREEZE.read_text(encoding="utf-8"))
        release_id = arguments.model_release_id or freeze_record["model_release_id"]
        baseline_commit = arguments.baseline_commit or freeze_record["baseline_commit"]
        result = run_baseline_gold_analysis(
            repository_root=REPOSITORY_ROOT,
            baseline_commit=baseline_commit,
            manifest=manifest,
            gold_root=arguments.gold_root,
            output_root=arguments.output_root,
            model_store=arguments.model_store,
            model_release_id=release_id,
            device=arguments.device,
        )
        _write_json(arguments.evidence, result)
    elif arguments.command == "inspect":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        record = inspect_candidate_outputs(
            manifest=manifest,
            candidate_output_root=arguments.candidate_output_root,
        )
        _write_json(arguments.output, record)
        if not record["all_inspected"]:
            raise SystemExit(1)
    elif arguments.command == "assess":
        manifest = GoldSetManifest.model_validate_json(arguments.manifest.read_bytes())
        wheel = arguments.wheel or _only_wheel(REPOSITORY_ROOT / "dist")
        inspection_record = json.loads(arguments.inspection_record.read_text(encoding="utf-8"))
        repository_clean = not bool(_git("status", "--porcelain", "--untracked-files=no"))
        results = assess_candidate_preparation(
            manifest=manifest,
            gold_root=arguments.gold_root,
            candidate_output_root=arguments.candidate_output_root,
            baseline_output_root=arguments.baseline_output_root,
            inspection_by_id=inspection_status_by_id(inspection_record),
            candidate_clean=repository_clean,
        )
        freeze_record = json.loads(DEFAULT_FREEZE.read_text(encoding="utf-8"))
        release_id = arguments.model_release_id or freeze_record["model_release_id"]
        decision = build_promotion_decision(
            repository_root=REPOSITORY_ROOT,
            wheel=wheel,
            model_release=arguments.model_store / release_id,
            source_results=results,
        )
        _write_model(arguments.output, decision)
        if not decision.passed:
            raise SystemExit(1)
    else:
        wheel = arguments.wheel or _only_wheel(REPOSITORY_ROOT / "dist")
        command = [
            sys.executable,
            "-m",
            "tools.production_boundary.clean_install",
            "--wheel",
            str(wheel),
            "--model-store",
            str(arguments.model_store),
            "--device",
            arguments.device,
            "--base-python",
            str(REPOSITORY_ROOT / ".pixi/envs/production/bin/python"),
        ]
        if arguments.full:
            command.append("--full")
        subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def _write_model(path: Path, model: object) -> None:
    from pydantic import BaseModel

    if not isinstance(model, BaseModel):
        raise TypeError("evidence output must be a Pydantic model")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _only_wheel(directory: Path) -> Path:
    wheels = tuple(sorted(directory.rglob("rdam-*.whl")))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one candidate wheel in {directory}, found {len(wheels)}")
    return wheels[0]


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


if __name__ == "__main__":
    main()
