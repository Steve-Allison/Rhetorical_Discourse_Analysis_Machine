"""Immutable pre-candidate authority and baseline-wheel preparation freeze."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import tempfile
from io import BytesIO

from rdam.ingest.identity import semantic_sha256, sha256_file
from rdam.rst.model_loading import ParserCapacity, validate_model_release
from tools.production_ingest.contracts import FreezeAuthority, GoldSetManifest
from tools.production_ingest.gold import verify_gold_set


def freeze_baseline(
    *,
    repository_root: Path,
    gold_root: Path,
    manifest: GoldSetManifest,
    model_release: Path,
    baseline_commit: str,
) -> FreezeAuthority:
    """Build the immutable baseline wheel and record isolated legacy prepared inputs."""

    repo = repository_root.resolve()
    verify_gold_set(manifest, gold_root)
    if _git(repo, "rev-parse", baseline_commit) != baseline_commit:
        raise ValueError("baseline_commit is not an exact immutable Git commit")
    with tempfile.TemporaryDirectory(prefix="isanlp-rst-baseline-") as temporary:
        temporary_root = Path(temporary)
        source_root = temporary_root / "source"
        source_root.mkdir()
        archive_bytes = subprocess.run(
            ["git", "archive", "--format=tar", baseline_commit],
            cwd=repo,
            check=True,
            capture_output=True,
        ).stdout
        with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:") as archive:
            archive.extractall(source_root, filter="data")
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(temporary_root / "dist")],
            cwd=source_root,
            check=True,
        )
        wheels = tuple((temporary_root / "dist").glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"baseline build produced {len(wheels)} wheels")
        baseline_wheel = wheels[0]
        baseline_wheel_sha256 = sha256_file(baseline_wheel)
        source_results = _run_isolated_baseline(baseline_wheel, manifest, gold_root, temporary_root)

    release = validate_model_release(model_release, expected_runtime_contract="isanlp_rst.parser/dmrst-v1")
    model_identity = release.analysis_identity(
        ParserCapacity(unit="edu_count", maximum=512, source="isanlp_rst.parser/recursive-v1")
    )
    scorer_files = sorted((repo / "workbench/evaluation/rst").glob("*.py"))
    scorer_digest = semantic_sha256([(path.name, sha256_file(path)) for path in scorer_files])
    return FreezeAuthority(
        frozen_at=datetime.now(UTC),
        gold_manifest_digest=manifest.manifest_digest,
        expectation_digest=manifest.expectation_digest,
        baseline_commit=baseline_commit,
        baseline_wheel_sha256=baseline_wheel_sha256,
        model_release_id=release.manifest.release_id,
        model_digest=model_identity.semantic_digest,
        scorer_digest=scorer_digest,
        pixi_lock_sha256=sha256_file(repo / "pixi.lock"),
        machine=tuple(
            sorted(
                {
                    "machine": platform.machine(),
                    "mac_ver": platform.mac_ver()[0],
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "processor": platform.processor(),
                }.items()
            )
        ),
        source_results=source_results,
    )


def _run_isolated_baseline(
    wheel: Path,
    manifest: GoldSetManifest,
    gold_root: Path,
    temporary_root: Path,
) -> tuple[tuple[str, str], ...]:
    environment_root = temporary_root / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", environment_root], check=True)
    python = environment_root / "bin/python"
    subprocess.run([python, "-m", "pip", "install", "--no-deps", str(wheel)], check=True)
    input_path = temporary_root / "baseline-input.json"
    output_path = temporary_root / "baseline-output.json"
    input_path.write_text(
        json.dumps(
            {
                "root": str(gold_root.resolve()),
                "sources": [source.model_dump(mode="json") for source in manifest.sources],
                "output": str(output_path),
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [python, "-c", _BASELINE_SCRIPT, str(input_path)],
        cwd=temporary_root,
        check=True,
        env={
            **os.environ,
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": "",
            "NO_PROXY": "*",
            "no_proxy": "*",
        },
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {source.source_id for source in manifest.sources}:
        raise RuntimeError("isolated baseline did not produce one result per Gold source")
    return tuple(sorted((key, str(value)) for key, value in payload.items()))


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


_BASELINE_SCRIPT = r'''
import hashlib, json, sys, tempfile
from pathlib import Path

control = json.loads(Path(sys.argv[1]).read_text())
root = Path(control["root"])
results = {}
for source in control["sources"]:
    path = root / source["relative_path"]
    form = source["source_form"]
    try:
        if form == "edus":
            text = " ".join(json.loads(path.read_text(encoding="utf-8"))["edus"])
        elif form == "text":
            text = path.read_text(encoding="utf-8")
        elif form == "markdown":
            from rdam.rst.markdown.harvester import harvest_markdown_text
            from rdam.rst.markdown.loader import load_markdown
            text = harvest_markdown_text(load_markdown(path.read_text(encoding="utf-8"), gfm=True).tokens).full_text
        elif form == "docling_json":
            from docling_core.types.doc import DoclingDocument
            from rdam.rst.docling.harvester import harvest_docling_text
            text = harvest_docling_text(DoclingDocument.load_from_json(path)).full_text
        elif form == "doclang_xml":
            from doclang import validate
            from rdam.rst.doclang.harvester import harvest_doclang_text
            from rdam.rst.doclang.loader import parse_doclang_xml
            validate(path, allow_empty_namespace=True)
            text = harvest_doclang_text(parse_doclang_xml(path)).full_text
        else:
            results[source["source_id"]] = "unsupported:doclang_archive"
            continue
        results[source["source_id"]] = "prepared_sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    except Exception as exc:
        results[source["source_id"]] = "failure:" + type(exc).__name__
Path(control["output"]).write_text(json.dumps(results, sort_keys=True) + "\n")
'''


__all__ = ["freeze_baseline"]
