"""Run a built production wheel outside the repository over the private Gold Set."""

import json
from io import BytesIO
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

from tools.production_ingest.contracts import GoldSetManifest


def run_candidate_preparation(
    *,
    wheel: Path,
    manifest: GoldSetManifest,
    gold_root: Path,
    output_root: Path,
    repository_root: Path,
    model_store: Path | None = None,
    model_release_id: str | None = None,
    device: str = "cpu",
    repetitions: int = 1,
) -> dict[str, object]:
    """Collect private canonical outputs from an isolated wheel install."""

    if (model_store is None) != (model_release_id is None):
        raise ValueError("model_store and model_release_id must be supplied together")
    if repetitions < 1:
        raise ValueError("repetitions must be at least one")
    if repetitions > 1 and repetitions % 2:
        raise ValueError("repeated candidate evidence requires an even cached/uncached run count")

    candidate_wheel = wheel.resolve()
    if not candidate_wheel.is_file() or candidate_wheel.suffix != ".whl":
        raise FileNotFoundError(f"candidate wheel not found: {candidate_wheel}")
    private_output = output_root.resolve()
    private_output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isanlp-rst-candidate-") as temporary:
        root = Path(temporary)
        environment_root = root / "venv"
        subprocess.run([sys.executable, "-m", "venv", environment_root], check=True)
        python = environment_root / "bin/python"
        subprocess.run([python, "-m", "pip", "install", f"{candidate_wheel}[formats]"], check=True)
        control = root / "control.json"
        report = root / "report.json"
        control.write_text(
            json.dumps(
                {
                    "gold_root": str(gold_root.resolve()),
                    "output_root": str(private_output),
                    "repository_root": str(repository_root.resolve()),
                    "model_store": str(model_store.resolve()) if model_store is not None else None,
                    "model_release_id": model_release_id,
                    "device": device,
                    "repetitions": repetitions,
                    "cache_root": str(root / "cache"),
                    "report": str(report),
                    "sources": [source.model_dump(mode="json") for source in manifest.sources],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [python, "-c", _CANDIDATE_SCRIPT, str(control)],
            cwd=root,
            check=True,
            env={
                **os.environ,
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": "",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "NO_PROXY": "*",
                "no_proxy": "*",
            },
        )
        payload = json.loads(report.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or len(payload.get("sources", ())) != len(manifest.sources):
        raise RuntimeError("candidate wheel did not produce one preparation result per Gold source")
    return payload


def run_baseline_gold_analysis(
    *,
    repository_root: Path,
    baseline_commit: str,
    manifest: GoldSetManifest,
    gold_root: Path,
    output_root: Path,
    model_store: Path,
    model_release_id: str,
    device: str = "cpu",
) -> dict[str, object]:
    """Run the frozen production wheel over every source with RST Gold."""

    repository = repository_root.resolve()
    resolved_commit = _git(repository, "rev-parse", baseline_commit)
    if resolved_commit != baseline_commit:
        raise ValueError("baseline_commit must be a full immutable Git revision")
    private_output = output_root.resolve()
    private_output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isanlp-rst-baseline-analysis-") as temporary:
        root = Path(temporary)
        source_root = root / "source"
        source_root.mkdir()
        archive_bytes = subprocess.run(
            ["git", "archive", "--format=tar", baseline_commit],
            cwd=repository,
            check=True,
            capture_output=True,
        ).stdout
        with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:") as archive:
            archive.extractall(source_root, filter="data")
        dist = root / "dist"
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
            cwd=source_root,
            check=True,
        )
        wheels = tuple(dist.glob("isanlp_rst-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"baseline build produced {len(wheels)} wheels")
        environment_root = root / "venv"
        subprocess.run([sys.executable, "-m", "venv", environment_root], check=True)
        python = environment_root / "bin/python"
        subprocess.run([python, "-m", "pip", "install", str(wheels[0])], check=True)
        control = root / "control.json"
        report = root / "report.json"
        control.write_text(
            json.dumps(
                {
                    "gold_root": str(gold_root.resolve()),
                    "output_root": str(private_output),
                    "repository_root": str(repository),
                    "model_store": str(model_store.resolve()),
                    "model_release_id": model_release_id,
                    "device": device,
                    "report": str(report),
                    "sources": [
                        source.model_dump(mode="json")
                        for source in manifest.sources
                        if source.rst_gold_ref is not None
                    ],
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [python, "-c", _BASELINE_ANALYSIS_SCRIPT, str(control)],
            cwd=root,
            check=True,
            env={
                **os.environ,
                "PYTHONNOUSERSITE": "1",
                "PYTHONPATH": "",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "NO_PROXY": "*",
                "no_proxy": "*",
            },
        )
        payload = json.loads(report.read_text(encoding="utf-8"))
    expected = sum(source.rst_gold_ref is not None for source in manifest.sources)
    if not isinstance(payload, dict) or len(payload.get("sources", ())) != expected:
        raise RuntimeError("baseline wheel did not produce one analysis per RST Gold source")
    return payload


_CANDIDATE_SCRIPT = r'''
import importlib.util, json, sys
from pathlib import Path

control = json.loads(Path(sys.argv[1]).read_text())
repository_root = Path(control["repository_root"]).resolve()
if repository_root == Path.cwd().resolve() or any(Path(entry or ".").resolve() == repository_root for entry in sys.path):
    raise RuntimeError("candidate execution leaked the repository onto sys.path")
def module_exists(name):
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False
if module_exists("workbench") or module_exists("tools.production_ingest"):
    raise RuntimeError("production environment exposes repository-only evaluation modules")

from rdam.rst.ingest import (
    DispositionDecision,
    ProductionIngestor,
    SourceArtifact,
    SourceForm,
    load_contract,
    serialize_contract,
)

model_store = control["model_store"]
repetitions = control["repetitions"]
if model_store is None:
    ingestor = None
else:
    from rdam.rst import Parser
    parser = Parser.from_model_release(
        model_store,
        control["model_release_id"],
        family="modernbert",
        device=control["device"],
    )
    ingestor = ProductionIngestor(parser=parser)

gold_root = Path(control["gold_root"])
output_root = Path(control["output_root"])
records = []
for source in control["sources"]:
    path = gold_root / source["relative_path"]
    form = SourceForm(source["source_form"])
    if form is SourceForm.EDUS:
        artifact = SourceArtifact.from_edus(json.loads(path.read_text(encoding="utf-8"))["edus"], source_name=path.name, original_source=path.as_uri())
    else:
        artifact = SourceArtifact.from_path(path, source_form=form, original_source=path.as_uri())
    preparation_ingestor = ingestor or ProductionIngestor()
    preparation = preparation_ingestor.prepare(
        artifact,
        parser_capacity=(parser.analysis_capacity if ingestor is not None else None),
    )
    semantic = preparation.semantic
    prepared = semantic.prepared_document
    inventory = semantic.inventory
    output = {
        "schema_version": "1.0.0",
        "source": source,
        "preparation_outcome": json.loads(serialize_contract(preparation)),
    }
    result_digest = None
    analysis_status = None
    node_count = 0
    anchor_coverage = None
    determinism = None
    if ingestor is not None:
        uncached_runs = repetitions if repetitions == 1 else repetitions // 2
        results = [
            ingestor.analyse(
                artifact,
                cache_directory=(
                    None
                    if run_index < uncached_runs
                    else Path(control["cache_root"]) / source["source_id"]
                ),
            )
            for run_index in range(repetitions)
        ]
        semantic_digests = [candidate.semantic_digest.hex_digest for candidate in results]
        if len(set(semantic_digests)) != 1:
            raise RuntimeError("repeated candidate analysis changed semantic identity")
        result = results[0]
        determinism = {
            "runs": repetitions,
            "uncached_runs": uncached_runs,
            "cached_runs": repetitions - uncached_runs,
            "unique_semantic_digests": len(set(semantic_digests)),
            "cache_statuses": [candidate.execution.cache_status.value for candidate in results],
        }
        output["determinism"] = determinism
        persisted = serialize_contract(result)
        reloaded = load_contract(persisted)
        if reloaded.semantic_digest != result.semantic_digest:
            raise RuntimeError("persisted production result changed semantic identity")
        output["analysis_result"] = json.loads(persisted)
        result_digest = result.semantic_digest.hex_digest
        analysis_status = result.semantic.status.value
        analysis = result.semantic.analysis
        node_count = len(analysis.nodes) if analysis is not None else 0
        validation = result.semantic.validation
        anchor_coverage = (
            1.0
            if validation is None and result.semantic.status.value == "empty_primary_discourse"
            else validation.anchor_coverage.ratio
            if validation is not None
            else None
        )
    output_path = output_root / f"{source['source_id']}.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    records.append({
        "source_id": source["source_id"],
        "source_form": source["source_form"],
        "output_file": output_path.name,
        "prepared_digest": prepared.semantic_digest.hex_digest,
        "contract_digest": semantic.source_contract.semantic_digest,
        "inventory_count": len(inventory),
        "disposition_count": len(preparation.dispositions),
        "duplicate_count": sum(
            item.disposition.decision is DispositionDecision.DUPLICATE for item in inventory
        ),
        "result_digest": result_digest,
        "analysis_status": analysis_status,
        "node_count": node_count,
        "analysis_anchor_coverage": anchor_coverage,
        "determinism": determinism,
    })
Path(control["report"]).write_text(json.dumps({"schema_version":"1.0.0","sources":records},sort_keys=True)+"\n")
'''


_BASELINE_ANALYSIS_SCRIPT = r'''
import hashlib, importlib.util, json, sys
from pathlib import Path

control = json.loads(Path(sys.argv[1]).read_text())
repository_root = Path(control["repository_root"]).resolve()
if repository_root == Path.cwd().resolve() or any(Path(entry or ".").resolve() == repository_root for entry in sys.path):
    raise RuntimeError("baseline execution leaked the repository onto sys.path")
def module_exists(name):
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False
if module_exists("workbench") or module_exists("tools.production_ingest"):
    raise RuntimeError("baseline production environment exposes repository-only evaluation modules")

from rdam.rst import Parser
from rdam.rst.contracts import RstDocument
from rdam.rst.contracts.serialization import to_dict

parser = Parser.from_model_release(
    control["model_store"],
    control["model_release_id"],
    family="dmrst",
    device=control["device"],
)
gold_root = Path(control["gold_root"])
output_root = Path(control["output_root"])
records = []
for source in control["sources"]:
    path = gold_root / source["relative_path"]
    source_bytes = path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source["sha256"]:
        raise RuntimeError("baseline source digest mismatch: " + source["source_id"])
    if source["source_form"] == "edus":
        document = RstDocument.from_edus(
            json.loads(source_bytes.decode("utf-8"))["edus"],
            document_id=source["source_id"],
        )
        try:
            analysis = parser.parse_document(document)
            input_mode = "exact_presegmented_edus"
        except ValueError as exc:
            if "produced segmentation does not match the provided EDUs" not in str(exc):
                raise
            analysis = parser.parse_document(
                RstDocument.from_text(document.text, document_id=source["source_id"])
            )
            input_mode = "raw_text_after_historical_presegmented_alignment_failure"
    elif source["source_form"] == "text":
        document = RstDocument.from_text(
            source_bytes.decode("utf-8"),
            document_id=source["source_id"],
        )
        analysis = parser.parse_document(document)
        input_mode = "raw_text"
    else:
        raise RuntimeError("RST Gold source has unsupported baseline form: " + source["source_form"])
    output_path = output_root / (source["source_id"] + ".json")
    output_path.write_text(
        json.dumps({"source_id": source["source_id"], "source_sha256": source["sha256"], "input_mode": input_mode, "analysis": to_dict(analysis)}, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    records.append({
        "source_id": source["source_id"],
        "source_form": source["source_form"],
        "input_mode": input_mode,
        "output_file": output_path.name,
        "node_count": len(analysis.nodes),
        "edge_count": len(analysis.primary_edges) + len(analysis.secondary_edges),
    })
Path(control["report"]).write_text(json.dumps({"schema_version":"1.0.0","sources":records},sort_keys=True)+"\n")
'''


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


__all__ = ["run_baseline_gold_analysis", "run_candidate_preparation"]
