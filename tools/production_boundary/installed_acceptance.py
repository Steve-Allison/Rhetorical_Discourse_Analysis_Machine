"""Exercise the installed release contract outside the source checkout.

Runs inside a fresh venv where only the built wheel is installed. The expected version is
passed in by the clean-install driver (read from the wheel's filename), so this script
carries no version literal of its own.
"""

import argparse
from importlib import import_module, resources
from importlib.metadata import PackageNotFoundError, distribution, version
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from typing import cast
import zipfile


# tiktoken is a required OpenAI runtime dependency, not an offline-only package.
OFFLINE_DISTRIBUTIONS = ("fire", "jsonnet", "nltk", "peft", "pytest")
_TEXT = "Because it rained, the match stopped. The crowd left."
_EDUS = ("Because it rained, the match stopped.", "The crowd left.")
_DOCLANG_ARCHIVE_DOCUMENT = b"<doclang><text>Installed archive acceptance.</text></doclang>"


def _required_digest(value: object, label: str) -> str:
    digest = getattr(value, "hex_digest", None)
    if not isinstance(digest, str):
        raise AssertionError(f"{label} has no semantic digest")
    return digest


def _disable_external_network() -> None:
    if os.environ.get("RDAM_NETWORK_DISABLED") != "1":
        raise AssertionError("installed acceptance requires explicit network-disable mode")
    original_connect = socket.socket.connect

    def guarded_connect(instance: socket.socket, address: object) -> None:
        if isinstance(address, tuple):
            endpoint = cast(tuple[object, ...], address)
            if endpoint and isinstance(endpoint[0], str) and endpoint[0] in {"127.0.0.1", "::1", "localhost"}:
                original_connect(instance, endpoint)
                return
        raise OSError("external network access is disabled during installed acceptance")

    socket.socket.connect = guarded_connect


def _assert_offline_distributions_absent() -> None:
    present: list[str] = []
    for name in OFFLINE_DISTRIBUTIONS:
        try:
            distribution(name)
        except PackageNotFoundError:
            continue
        present.append(name)
    if present:
        raise AssertionError(f"offline distributions are available in production: {present}")


def _archive_bytes(document: bytes) -> bytes:
    content_types = b'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Override PartName="/document.xml" ContentType="application/vnd.doclang.document+xml"/>
</Types>'''
    relationships = b'''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://doclang.ai/ns/package/2026/relationships/document" Target="document.xml"/>
</Relationships>'''
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        # Fixed entry timestamps: identical input must give identical archive bytes, so the
        # source identity — and every digest derived from it — is reproducible across runs.
        for name, payload in (
            ("[Content_Types].xml", content_types),
            ("_rels/.rels", relationships),
            ("document.xml", document),
        ):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return output.getvalue()


def _prepare_sources(
    *,
    markdown: Path | None,
    doclang: Path | None,
    docling: Path | None,
) -> dict[str, object]:
    from rdam.ingest import (
        Availability,
        ProductionIngestError,
        ProductionIngestor,
        SafeProductionFailureRecord,
        SourceArtifact,
        SourceForm,
        describe_capabilities,
        load_contract,
        serialize_contract,
    )

    ingestor = ProductionIngestor()
    artifacts = [
        SourceArtifact.from_text(_TEXT, source_name="acceptance.txt"),
        SourceArtifact.from_edus(_EDUS, source_name="acceptance.edus"),
    ]
    if markdown is not None and doclang is not None and docling is not None:
        artifacts.extend(
            (
                SourceArtifact.from_path(markdown),
                SourceArtifact.from_path(docling, source_form=SourceForm.DOCLING_JSON),
                SourceArtifact.from_path(doclang),
                SourceArtifact.from_bytes(
                    _archive_bytes(_DOCLANG_ARCHIVE_DOCUMENT),
                    source_form=SourceForm.DOCLANG_ARCHIVE,
                    source_name="acceptance.dclx",
                    media_type="application/vnd.doclang.archive+zip",
                ),
            )
        )
    results: dict[str, object] = {}
    for artifact in artifacts:
        prepared = ingestor.prepare(artifact)
        encoded = serialize_contract(prepared)
        if serialize_contract(load_contract(encoded)) != encoded:
            raise AssertionError(f"canonical preparation changed for {artifact.source_form.value}")
        results[artifact.source_form.value] = {
            "inventory_items": len(prepared.semantic.inventory),
            "prepared_segments": len(prepared.semantic.prepared_document.segments),
            "semantic_digest": _required_digest(
                prepared.semantic_digest,
                "preparation outcome",
            ),
        }

    capabilities = describe_capabilities()
    availability = {
        item.source_form.value: item.availability.value
        for item in capabilities.semantic.source_forms
    }
    formats_installed = markdown is not None
    if formats_installed and set(availability.values()) != {Availability.AVAILABLE.value}:
        raise AssertionError("formats installation does not advertise all six source forms")
    if not formats_installed:
        optional = {
            SourceForm.MARKDOWN,
            SourceForm.DOCLING_JSON,
            SourceForm.DOCLANG_XML,
            SourceForm.DOCLANG_ARCHIVE,
        }
        advertised = {
            item.source_form
            for item in capabilities.semantic.source_forms
            if item.availability is Availability.UNAVAILABLE
        }
        if advertised != optional:
            raise AssertionError("core capability discovery contradicts optional format availability")
        try:
            ingestor.prepare(
                SourceArtifact.from_bytes(
                    b"# Heading",
                    source_form=SourceForm.MARKDOWN,
                    source_name="unavailable.md",
                    media_type="text/markdown; charset=utf-8",
                )
            )
        except ProductionIngestError as error:
            record = load_contract(serialize_contract(error.failure))
            if not isinstance(record, SafeProductionFailureRecord):
                raise AssertionError(
                    "unavailable format did not yield a safe typed failure"
                ) from error
        else:
            raise AssertionError("core installation unexpectedly prepared Markdown")
    return {
        "capability_identity": _required_digest(
            capabilities.semantic_digest,
            "capabilities",
        ),
        "availability": availability,
        "preparation": results,
    }


def _analyse_with_release(
    *,
    model_store: Path,
    release_id: str,
    erst_checkpoint: Path | None,
    device: str,
) -> dict[str, object]:
    from rdam import AggregateRequest, MachineConfig, ResultOutcome, Technique, production_machine
    from rdam.configuration import LocalRstModel, RstSettings
    from rdam.serialization import load, serialize
    from rdam.rst.output import RstOutput
    from rdam.ingest import (
        AnalysedOutcome,
        ParserAnalysisResult,
    )

    config = MachineConfig(rst=RstSettings(
        model=LocalRstModel(store=model_store, release_id=release_id),
        device=device, erst_checkpoint=erst_checkpoint,
    ))
    machine = production_machine(config=config)
    aggregate = machine.analyse(AggregateRequest.for_text(
        _TEXT, (Technique.RST,), source_name="installed-analysis.txt"
    ))
    result = aggregate.outcome_for(Technique.RST)
    if not isinstance(result, ResultOutcome):
        raise AssertionError("installed RST machine outcome was not successful")
    outcome = RstOutput.model_validate_json(json.dumps(
        result.result.model_dump(mode="json")["payload"]
    )).root
    if not isinstance(outcome, AnalysedOutcome):
        raise AssertionError("non-empty installed analysis did not return AnalysedOutcome")
    parser_result = outcome.semantic.parser_result
    if not isinstance(parser_result, ParserAnalysisResult):
        raise AssertionError("installed analysis omitted the canonical parser result")
    if not parser_result.semantic.loaded_components:
        raise AssertionError("installed analysis omitted loaded-component receipts")
    if not outcome.semantic.validation or not outcome.semantic.validation.passed:
        raise AssertionError("installed analysis did not pass complete validation")
    encoded = serialize(aggregate)
    if serialize(load(encoded)) != encoded:
        raise AssertionError("installed analysis failed canonical round-trip")

    from rdam.rst._version import TOOL_NAME

    with tempfile.TemporaryDirectory(prefix="rdam-cli-acceptance-") as directory:
        output = Path(directory) / "result.json"
        command = [
            str(Path(sys.executable).with_name(TOOL_NAME)),
            "analyse",
            "--techniques",
            "rst",
            "--text",
            _TEXT,
            "--source-name",
            "installed-analysis.txt",
            "--model-store",
            str(model_store),
            "--release-id",
            release_id,
            "--device",
            device,
            "--output",
            str(output),
        ]
        if erst_checkpoint is not None:
            command.extend(("--erst-checkpoint", str(erst_checkpoint)))
        subprocess.run(command, check=True, env=os.environ.copy())
        cli = load(output.read_bytes())
        if getattr(cli, "semantic_digest", None) != aggregate.semantic_digest:
            raise AssertionError("installed CLI semantic result differs from Python API")
    return {
        "outcome_identity": _required_digest(outcome.semantic_digest, "analysis outcome"),
        "parser_result_identity": _required_digest(
            parser_result.semantic_digest,
            "parser result",
        ),
        "loaded_components": len(parser_result.semantic.loaded_components),
        "validation_checks": len(outcome.semantic.validation.checks),
        "cli_semantic_parity": True,
    }


def _machine_interfaces(*, http: bool) -> dict[str, object]:
    """Check the installed machine and both thin transports without model calls."""
    from importlib.util import find_spec
    from rdam import AggregateRequest, ResultOutcome, StructuredInput, Technique, production_machine
    from rdam.serialization import load, schema, schema_models, serialize, serialize_request

    scripts = {point.name for point in distribution("rdam").entry_points if point.group == "console_scripts"}
    if "rdam" not in scripts or "rdam-rst" in scripts:
        raise AssertionError("installed command declarations are not the unified interface")
    if find_spec("rdam.rst.cli") is not None:
        raise AssertionError("obsolete RST-only CLI module remains installed")
    if (find_spec("uvicorn") is not None) != http or (find_spec("starlette") is not None) != http:
        raise AssertionError("HTTP dependency availability contradicts installed extras")
    machine = production_machine()
    if machine.capabilities().http_available != http:
        raise AssertionError("capabilities contradict installed HTTP availability")
    request = AggregateRequest.for_structured((StructuredInput(
        technique=Technique.DUNG, payload={"arguments": ["a", "b"], "attacks": [["a", "b"]]}
    ),), techniques=(Technique.DUNG,))
    result = machine.analyse(request)
    if not isinstance(result.outcome_for(Technique.DUNG), ResultOutcome):
        raise AssertionError("installed Dung did not produce a native result")
    command = str(Path(sys.executable).with_name("rdam"))
    cli = subprocess.run([command, "analyse", "--request", "-"], input=serialize_request(request),
                         capture_output=True, check=True)
    parsed = load(cli.stdout)
    if getattr(parsed, "semantic_digest", None) != result.semantic_digest:
        raise AssertionError("installed Python/CLI analytical identities differ")
    for name in schema_models():
        for mode in ("validation", "serialization"):
            resource = resources.files("rdam.ingest").joinpath("schemas", f"machine-{name}.{mode}.schema.json")
            if json.loads(resource.read_bytes()) != schema(name, mode=mode):
                raise AssertionError(f"installed schema differs from runtime: {name}/{mode}")
    if http:
        import threading
        import time
        import urllib.request
        import uvicorn
        from rdam.http import create_app

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(8)
            port = listener.getsockname()[1]
            server = uvicorn.Server(uvicorn.Config(create_app(machine, port=port),
                loop="asyncio", http="h11", ws="none", log_level="error", access_log=False))
            worker = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
            worker.start()
            try:
                deadline = time.monotonic() + 10
                while not server.started and worker.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.01)
                if not server.started:
                    raise AssertionError("installed HTTP server did not start")
                message = urllib.request.Request(f"http://127.0.0.1:{port}/v1/analyse",
                    data=serialize_request(request), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(message, timeout=10) as response:
                    received = load(response.read())
                if getattr(received, "semantic_digest", None) != result.semantic_digest:
                    raise AssertionError("installed HTTP analytical identity differs")
            finally:
                server.should_exit = True
                worker.join(timeout=15)
                if worker.is_alive():
                    raise AssertionError("installed HTTP server did not stop")
    return {"cli_parity": True, "http_parity": http, "schemas": len(schema_models()) * 2,
            "canonical_roundtrip": serialize(load(serialize(result))) == serialize(result)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-version", required=True, help="the version the installed wheel declares")
    parser.add_argument("--model-store", type=Path, required=True)
    parser.add_argument("--release-id")
    parser.add_argument("--erst-checkpoint", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--formats", action="store_true")
    parser.add_argument("--http", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--doclang", type=Path)
    parser.add_argument("--docling", type=Path)
    args = parser.parse_args()

    _disable_external_network()
    import rdam.rst as rst_package
    from rdam.rst._version import PACKAGE_NAME

    package_file = Path(rst_package.__file__ or "").resolve()
    if package_file.is_relative_to(args.source_root.resolve()):
        raise AssertionError(f"installed acceptance imported the source tree: {package_file}")
    installed_version = version(PACKAGE_NAME)
    if installed_version != args.expected_version or rst_package.__version__ != args.expected_version:
        raise AssertionError(
            f"installed metadata ({installed_version}) and runtime version ({rst_package.__version__}) "
            f"do not agree on the expected {args.expected_version}"
        )
    _assert_offline_distributions_absent()
    surface = json.loads(
        resources.files("rdam.ingest")
        .joinpath("public-surface.json")
        .read_text(encoding="utf-8")
    )
    entries = surface["entries"]
    for entry in entries:
        public_import = entry.get("public_import")
        if public_import is None:
            continue
        module_name, separator, attribute_path = public_import.partition(":")
        if not separator:
            raise AssertionError(f"invalid public import declaration: {public_import}")
        value: object = import_module(module_name)
        for part in attribute_path.split("."):
            value = getattr(value, part)
    forbidden = ("tensor", "embedding", "activation", "workbench", "traininglabel")
    names = {entry["qualified_name"].casefold() for entry in entries}
    if any(marker in name for marker in forbidden for name in names):
        raise AssertionError("installed public surface exposes forbidden scientific internals")

    formats = args.formats
    if formats and (args.markdown is None or args.doclang is None or args.docling is None):
        raise ValueError("formats acceptance requires --markdown, --doclang, and --docling")
    result: dict[str, object] = {
        "package_file": str(package_file),
        "package_version": installed_version,
        "network_disabled": True,
        "offline_distributions_absent": True,
        "public_surface_entries": len(entries),
        "machine_interfaces": _machine_interfaces(http=args.http),
        "source_contract": _prepare_sources(
            markdown=args.markdown if formats else None,
            doclang=args.doclang if formats else None,
            docling=args.docling if formats else None,
        ),
    }
    if args.full:
        if args.release_id is None:
            raise ValueError("full installed acceptance requires --release-id")
        result["analysis"] = _analyse_with_release(
            model_store=args.model_store,
            release_id=args.release_id,
            erst_checkpoint=args.erst_checkpoint,
            device=args.device,
        )
    result["valid"] = True
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
