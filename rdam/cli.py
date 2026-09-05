"""One strict terminal adapter over the shared machine and persisted contracts."""

import argparse
from collections.abc import Callable, Sequence
from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
from typing import Any, NoReturn, cast

from rdam._errors import Operation, error, failure
from rdam._output import OutputDestination
from rdam._strict import canonical_json_bytes
from rdam.configuration import MachineConfig
from rdam.contracts import (
    AggregateAnalysis,
    AggregateRequest,
    FormalismChoice,
    MachineCapabilities,
    MachinePreparation,
    OperationError,
    PreparationRequest,
    SourceArtifactRef,
    SourceIdentity,
    StructuredInput,
)
from rdam.frameworks import BOUNDARY_TECHNIQUES, Technique
from rdam.historical import HistoricalAggregateAnalysis
from rdam.ingest.contracts.source import SourceArtifact, SourceForm
from rdam.interpretation import select_analysis
from rdam.serialization import (
    decode_object,
    load,
    load_config,
    load_preparation_request,
    load_request,
    serialize,
    version_info,
)
from rdam.summary import summarise


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, allow_abbrev=False, **kwargs)

    def error(self, message: str) -> NoReturn:
        raise error("configuration", "invalid_request", "invalid_arguments")


class _Once(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        seen: set[str] = getattr(namespace, "_seen", set())
        if self.dest in seen:
            parser.error("repeated option")
        seen.add(self.dest)
        namespace._seen = seen
        setattr(namespace, self.dest, self.const if self.nargs == 0 else values)


def _option(parser: argparse.ArgumentParser, *names: str, **kwargs: Any) -> None:
    parser.add_argument(*names, action=_Once, **kwargs)


def create_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="rdam",
        description="One analysis engine. Canonical JSON on stdout; diagnostics on stderr. Analysis exits: 0 complete, 3 partial, 4 unsuccessful.",
    )
    _option(parser, "--version", nargs=0, const=True, help="emit installed version and contracts as JSON")
    commands = parser.add_subparsers(dest="command", parser_class=_Parser)
    descriptions = {
        "capabilities": "Describe all techniques and configured models without inference.",
        "prepare": "Inventory a source without inference; default: no selected projections.",
        "analyse": "Analyse explicit techniques; Dung and IBIS require supplied structures.",
        "summary": "Read a saved result and emit a readable run summary; never analyse again.",
        "view": "Select whole requested techniques from a saved v2 analysis.",
        "schema": "Emit an installed contract schema without resolving configuration.",
        "version": "Emit installed package and contract versions without resolving configuration.",
        "serve": "Serve one configured machine on loopback; requires rdam[http].",
    }
    examples = {
        "capabilities": "rdam capabilities",
        "prepare": 'rdam prepare --text "A short source."',
        "analyse": 'rdam analyse --text "A claim and its reasons." --techniques toulmin,walton',
        "summary": "rdam summary analysis.json",
        "view": "rdam view analysis.json --techniques toulmin",
        "schema": "rdam schema request",
        "version": "rdam version",
        "serve": "rdam serve --port 0",
    }
    for command, description in descriptions.items():
        sub = commands.add_parser(
            command, help=description, description=description, epilog="Example: " + examples[command]
        )
        if command != "serve":
            _option(sub, "-o", "--output", help="literal file path or - for stdout (default)")
            _option(
                sub, "--force", nargs=0, const=True, default=False, help="atomically replace a non-input regular file"
            )
        _option(
            sub, "--diagnostics", choices=("json", "text"), default="json", help="stderr diagnostics (default: json)"
        )
        if command in {"prepare", "analyse"}:
            sub.add_argument(
                "source", nargs="?", help="literal source path or - for stdin; formats require rdam[formats]"
            )
            for name in ("text", "edus", "request", "source-name"):
                _option(sub, "--" + name)
            _option(sub, "--source-form", choices=tuple(form.value for form in SourceForm))
        if command in {"prepare", "analyse", "view"}:
            _option(
                sub,
                "--techniques",
                help="comma-separated explicit boundaries: " + ",".join(t.value for t in BOUNDARY_TECHNIQUES),
            )
        if command == "analyse":
            sub.add_argument("--structured", action="append", default=[], metavar="TECHNIQUE=FILE")
            sub.add_argument("--formalism", action="append", default=[], metavar="TECHNIQUE=FORMALISM")
        if command in {"summary", "view"}:
            sub.add_argument("result", help="saved result path or - for stdin")
        if command == "schema":
            sub.add_argument("record")
            _option(sub, "--mode", choices=("validation", "serialization"), default="validation")
        if command in {"capabilities", "prepare", "analyse", "serve"}:
            _option(sub, "-c", "--config", help="explicit JSON configuration file; relative paths resolve beside it")
            for name in (
                "model",
                "rst-model",
                "model-store",
                "release-id",
                "rst-relinventory",
                "device",
                "erst-checkpoint",
                "cache-directory",
            ):
                _option(sub, "--" + name)
            sub.add_argument("--technique-model", action="append", default=[], metavar="TECHNIQUE=MODEL")
            _option(sub, "--rst-evidence-detail", choices=("decision_complete", "normalized_distributions"))
            _option(sub, "--rst-marker-refinement", choices=("evidence_preserving", "disabled"))
            for name in ("dung-capacity", "max-workers"):
                _option(sub, "--" + name, type=int)
        if command == "serve":
            _option(sub, "--host", default="127.0.0.1")
            _option(sub, "--port", type=int, default=8765)
            _option(sub, "--max-request-bytes", type=int, default=64 * 1024 * 1024)
            _option(sub, "--body-timeout-seconds", type=float, default=30.0)
    return parser


def _techniques(value: str | None, *, required: bool) -> tuple[Technique, ...]:
    if value is None:
        if required:
            raise error("configuration", "invalid_request", "invalid_arguments")
        return ()
    values = tuple(Technique(item.strip()) for item in value.split(","))
    if len(set(values)) != len(values) or any(item not in BOUNDARY_TECHNIQUES for item in values):
        raise error("configuration", "invalid_request", "invalid_arguments")
    return values


def _mapping(values: list[str], allowed: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        key, separator, item = value.partition("=")
        if not separator or not item or key not in allowed or key in result:
            raise error("configuration", "invalid_request", "invalid_arguments")
        result[key] = item
    return result


def _read(path: str) -> bytes:
    return sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()


def _config(args: argparse.Namespace) -> MachineConfig:
    config = load_config(args.config) if args.config else MachineConfig()
    data = config.model_dump(mode="json")
    if args.model is not None:
        data["llm"]["model"] = args.model
    data["technique_models"].update(_mapping(args.technique_model, {"pdtb", "sdrt", "toulmin", "walton"}))
    local = args.model_store is not None or args.release_id is not None
    if local and (args.model_store is None or args.release_id is None or args.rst_model is not None):
        raise error("configuration", "invalid_request", "invalid_arguments")
    if args.rst_model is not None:
        data["rst"]["model"] = {"kind": "published", "version": args.rst_model}
    elif local:
        data["rst"]["model"] = {"kind": "local_release", "store": args.model_store, "release_id": args.release_id}
    for argument, field in (
        ("rst_relinventory", "relinventory"),
        ("device", "device"),
        ("erst_checkpoint", "erst_checkpoint"),
        ("rst_evidence_detail", "evidence_detail"),
        ("rst_marker_refinement", "marker_refinement"),
    ):
        value = getattr(args, argument)
        if value is not None:
            data["rst"][field] = value
    for name in ("max_workers", "cache_directory"):
        value = getattr(args, name)
        if value is not None:
            data["execution"][name] = value
    if args.dung_capacity is not None:
        data["dung_capacity"] = args.dung_capacity
    return MachineConfig.model_validate_json(canonical_json_bytes(data))


def _inputs(args: argparse.Namespace) -> tuple[Path, ...]:
    paths = [getattr(args, name, None) for name in ("source", "request", "result", "config")]
    paths.extend(_mapping(getattr(args, "structured", []), {"dung", "ibis"}).values())
    if getattr(args, "config", None) == "-" or paths.count("-") > 1:
        raise error("configuration", "invalid_request", "invalid_arguments")
    if args.command in {"prepare", "analyse"}:
        modes = sum(getattr(args, name) is not None for name in ("source", "text", "edus", "request"))
        if modes > 1 or (modes == 0 and (args.command == "prepare" or not args.structured)):
            raise error("configuration", "invalid_request", "invalid_arguments")
        if args.request is not None and any(
            (
                args.techniques is not None,
                args.source_form is not None,
                args.source_name is not None,
                bool(getattr(args, "structured", [])),
                bool(getattr(args, "formalism", [])),
            )
        ):
            raise error("configuration", "invalid_request", "invalid_arguments")
        if (args.text is not None or args.edus is not None) and args.source_form is not None:
            raise error("configuration", "invalid_request", "invalid_arguments")
        if args.request is None:
            selected = _techniques(args.techniques, required=args.command == "analyse")
            structures = _mapping(getattr(args, "structured", []), {"dung", "ibis"})
            formalisms = _mapping(getattr(args, "formalism", []), {item.value for item in selected})
            if any(Technique(key) not in selected for key in structures):
                raise error("configuration", "invalid_request", "invalid_arguments")
            for key, value in formalisms.items():
                FormalismChoice(technique=Technique(key), formalism_id=value)
            if modes == 0 and any(item not in {Technique.DUNG, Technique.IBIS} for item in selected):
                raise error("configuration", "invalid_request", "invalid_arguments")
            if modes == 0 and args.source_form is not None:
                raise error("configuration", "invalid_request", "invalid_arguments")
    return tuple(Path(path) for path in paths if path is not None and path != "-")


def _request(args: argparse.Namespace) -> PreparationRequest | AggregateRequest:
    if args.request is not None:
        return (
            load_preparation_request(_read(args.request))
            if args.command == "prepare"
            else load_request(_read(args.request))
        )
    techniques = _techniques(args.techniques, required=args.command == "analyse")
    structures = tuple(
        StructuredInput(technique=Technique(key), payload=decode_object(_read(path)))
        for key, path in _mapping(getattr(args, "structured", []), {"dung", "ibis"}).items()
    )
    formalisms = tuple(
        FormalismChoice(technique=Technique(key), formalism_id=value)
        for key, value in _mapping(getattr(args, "formalism", []), {item.value for item in BOUNDARY_TECHNIQUES}).items()
    )
    if args.text is not None:
        prepared = PreparationRequest.for_text(args.text, techniques, source_name=args.source_name or "cli-text")
    elif args.edus is not None:
        values: object = json.loads(args.edus)
        canonical_json_bytes(values)
        if not isinstance(values, list) or not all(isinstance(item, str) for item in cast(list[object], values)):
            raise ValueError("EDUs require a JSON array of strings")
        prepared = PreparationRequest.for_edus(
            tuple(cast(list[str], values)), techniques, source_name=args.source_name or "cli-edus"
        )
    elif args.source is not None:
        form = SourceForm(args.source_form) if args.source_form is not None else None
        artifact = (
            SourceArtifact.from_bytes(
                _read("-"), source_form=form or SourceForm.TEXT, source_name=args.source_name or "stdin"
            )
            if args.source == "-"
            else SourceArtifact.from_path(Path(args.source), source_form=form)
        )
        if args.source_name is not None and artifact.source_name != args.source_name:
            artifact = SourceArtifact.model_validate(
                {**artifact.model_dump(exclude={"source_id"}), "source_name": args.source_name}
            )
        if artifact.raw_bytes is None and artifact.edus is None:
            raise ValueError("materialized source has no payload")
        if artifact.raw_sha256 is None:
            raise ValueError("materialized source has no digest")
        from rdam._strict import Sha256Identity

        prepared = PreparationRequest(
            source=SourceIdentity(
                source_id=Sha256Identity(hex_digest=artifact.raw_sha256.hex_digest),
                source_name=artifact.source_name,
                media_type=artifact.media_type,
            ),
            source_artifact=SourceArtifactRef(artifact=artifact),
            techniques=techniques,
        )
    else:
        return AggregateRequest.for_structured(
            structures, techniques=techniques, source_name=args.source_name or "structured-input", formalisms=formalisms
        )
    if args.command == "prepare":
        return prepared
    return AggregateRequest(
        source=prepared.source,
        text=prepared.text,
        source_artifact=prepared.source_artifact,
        techniques=techniques,
        structured_inputs=structures,
        formalisms=formalisms,
    )


def _execute(args: argparse.Namespace) -> tuple[bytes, int, object]:
    if args.command == "version":
        record = version_info()
    elif args.command == "schema":
        from rdam.serialization import schema

        return canonical_json_bytes(schema(args.record, mode=args.mode)), 0, None
    elif args.command in {"summary", "view"}:
        saved = load(_read(args.result))
        if args.command == "summary":
            if not isinstance(
                saved, (AggregateAnalysis, HistoricalAggregateAnalysis, MachinePreparation, MachineCapabilities)
            ):
                raise ValueError("unsupported summary record")
            return summarise(saved).encode("utf-8"), 0, saved
        if not isinstance(saved, AggregateAnalysis):
            raise ValueError("view requires a current aggregate")
        record = select_analysis(saved, techniques=_techniques(args.techniques, required=True))
    else:
        config = _config(args)
        request = _request(args) if args.command in {"prepare", "analyse"} else None
        from rdam.composition import production_machine

        machine = production_machine(config=config)
        if args.command == "serve":
            from rdam.http import serve

            serve(
                machine,
                host=args.host,
                port=args.port,
                max_request_bytes=args.max_request_bytes,
                body_timeout_seconds=args.body_timeout_seconds,
            )
            return b"", 0, None
        if isinstance(request, AggregateRequest):
            record = _invoke("analyse", lambda: machine.analyse(request))
        elif isinstance(request, PreparationRequest):
            record = _invoke("prepare", lambda: machine.prepare(request))
        else:
            record = _invoke("capabilities", machine.capabilities)
    exit_code = (
        {"complete": 0, "partial": 3, "unsuccessful": 4}[record.status] if isinstance(record, AggregateAnalysis) else 0
    )
    return serialize(record), exit_code, record


def _invoke[T](operation: Operation, function: Callable[[], T]) -> T:
    try:
        return function()
    except OperationError:
        raise
    except Exception as cause:
        # Only the transport boundary translates unexpected defects; Python Machine still raises natively.
        raise error(operation, "internal_error", "internal_error") from cause


def _safe_execute(args: argparse.Namespace) -> tuple[bytes, int, object]:
    try:
        return _execute(args)
    except ValueError, UnicodeError, OSError, ImportError, OperationError:
        raise
    except Exception as cause:
        raise error(cast(Operation, args.command), "internal_error", "internal_error") from cause


def main(argv: Sequence[str] | None = None) -> int:
    args: argparse.Namespace | None = None
    operation: Operation = "configuration"
    try:
        args = create_parser().parse_args(argv)
        if args.version:
            if args.command is not None:
                raise error(operation, "invalid_request", "invalid_arguments")
            args = create_parser().parse_args(["version"])
        if args.command is None:
            raise error(operation, "invalid_request", "invalid_arguments")
        operation = cast(Operation, args.command)
        inputs = _inputs(args)
        output = getattr(args, "output", None)
        force = getattr(args, "force", False)
        if force and output in {None, "-"}:
            raise error(operation, "invalid_request", "invalid_arguments")
        destination = (
            None if output is None or output == "-" else OutputDestination(Path(output), force=force, inputs=inputs)
        )
        if destination is not None:
            destination.validate()
        with redirect_stdout(sys.stderr):
            payload, status, record = _safe_execute(args)
        if args.command == "serve":
            return status
        if destination is not None:
            destination.publish(payload + b"\n", identity=getattr(record, "semantic_digest", None))
        else:
            sys.stdout.buffer.write(payload + b"\n")
            sys.stdout.buffer.flush()
        return status
    except BrokenPipeError:
        # Prevent the interpreter's final flush from attempting a second write.
        import os

        sink = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(sink, sys.stdout.fileno())
        finally:
            os.close(sink)
        return 141
    except KeyboardInterrupt:
        problem = failure(operation, "interrupted", "interrupted")
        status = 130
    except OperationError as cause:
        problem = cause.failure
        status = 2 if problem.category == "invalid_request" else 1
    except ValueError, UnicodeError:
        problem = failure(operation, "invalid_request", "invalid_input")
        status = 2
    except OSError:
        problem = failure(operation, "source_unavailable", "source_unavailable")
        status = 1
    except ImportError:
        problem = failure(operation, "dependency_unavailable", "dependency_unavailable")
        status = 1
    if args is not None and getattr(args, "diagnostics", "json") == "text":
        sys.stderr.write(f"{problem.code}: {problem.message}\n")
    else:
        sys.stderr.buffer.write(serialize(problem) + b"\n")
    return status
