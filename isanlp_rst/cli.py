"""Canonical command-line and loopback HTTP projections of the production API."""

import argparse
import base64
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from typing import Any, Final, Protocol

import rfc8785

from isanlp_rst import Parser, __version__
from isanlp_rst.ingest import (
    AnalysisPolicy,
    EvidenceDetailPolicy,
    FailureCategory,
    LifecycleStage,
    MarkerRefinementMode,
    OutputFormalism,
    ProductionFailure,
    ProductionIngestError,
    ProductionIngestor,
    ProductionAnalysisOutcome,
    ProductionCapabilities,
    SourceArtifact,
    SourceForm,
    Retryability,
    SafeCause,
    serialize_contract,
)
from isanlp_rst.ingest.service import DEFAULT_ANALYSIS_POLICY

_LOOPBACK_HOSTS: Final = {"127.0.0.1", "::1", "localhost"}
_MEDIA_TYPES: Final = {
    SourceForm.TEXT: "text/plain; charset=utf-8",
    SourceForm.EDUS: "application/vnd.isanlp-rst.edus+json",
    SourceForm.MARKDOWN: "text/markdown; charset=utf-8",
    SourceForm.DOCLING_JSON: "application/vnd.docling.document+json",
    SourceForm.DOCLANG_XML: "application/vnd.doclang+xml",
    SourceForm.DOCLANG_ARCHIVE: "application/vnd.doclang.archive+zip",
}


class _ProductionService(Protocol):
    def analyse(self, source: SourceArtifact) -> ProductionAnalysisOutcome: ...

    def capabilities(self) -> ProductionCapabilities: ...


def cmd_parse(args: argparse.Namespace) -> int:
    """Run one canonical production analysis or emit one safe typed failure."""

    try:
        source = _source_from_cli(args)
        ingestor = _configured_ingestor(args)
        outcome = ingestor.analyse(
            source,
            analysis_policy=_analysis_policy(args),
            cache_directory=Path(args.cache_directory) if args.cache_directory else None,
        )
        payload = _render_outcome(outcome, args.format)
    except ProductionIngestError as exc:
        payload = serialize_contract(exc.failure) + b"\n"
        _write_payload(payload, args.output, stream=sys.stderr.buffer)
        return 2
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        payload = serialize_contract(
            _safe_boundary_failure(
                exc,
                stage=LifecycleStage.ACQUISITION,
                category=FailureCategory.MALFORMED_INPUT,
                code="cli_source_acquisition_failed",
                message_template="cli_source_could_not_be_acquired",
            )
        ) + b"\n"
        _write_payload(payload, args.output, stream=sys.stderr.buffer)
        return 2
    _write_payload(payload, args.output, stream=sys.stdout.buffer)
    return 0


def cmd_capabilities(args: argparse.Namespace) -> int:
    """Emit canonical model-free or configured-parser capability evidence."""

    ingestor = _configured_ingestor(args) if args.release_id else ProductionIngestor()
    _write_payload(
        serialize_contract(ingestor.capabilities()) + b"\n",
        args.output,
        stream=sys.stdout.buffer,
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Serve the exact production contract on a loopback-only HTTP endpoint."""

    if args.host not in _LOOPBACK_HOSTS:
        raise ValueError("the local HTTP service may bind only to a loopback host")
    ingestor = _configured_ingestor(args)
    server = ThreadingHTTPServer((args.host, args.port), _handler_type(ingestor))
    sys.stderr.write(f"isanlp_rst local API: http://{args.host}:{args.port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("server_stopped\n")
    finally:
        server.server_close()
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Emit the installed package version as stable JSON."""

    _write_payload(
        rfc8785.dumps({"package": "isanlp_rst", "version": __version__}) + b"\n",
        args.output,
        stream=sys.stdout.buffer,
    )
    return 0


def _configured_ingestor(args: argparse.Namespace) -> ProductionIngestor:
    if not args.model_store or not args.release_id:
        raise ValueError("analysis requires --model-store and --release-id")
    parser = Parser.from_model_release(
        args.model_store,
        args.release_id,
        family="modernbert",
        device=args.device,
        erst_scorer_checkpoint=args.erst_checkpoint,
    )
    return ProductionIngestor(parser=parser)


def _analysis_policy(args: argparse.Namespace) -> AnalysisPolicy:
    return AnalysisPolicy.model_validate(
        {
            **DEFAULT_ANALYSIS_POLICY.model_dump(exclude={"semantic_digest"}),
            "output_formalism": OutputFormalism(args.output_formalism),
            "evidence_detail": EvidenceDetailPolicy(args.evidence_detail),
            "marker_refinement": (
                MarkerRefinementMode.DISABLED if args.no_marker_refinement else MarkerRefinementMode.EVIDENCE_PRESERVING
            ),
        }
    )


def _source_from_cli(args: argparse.Namespace) -> SourceArtifact:
    if args.text is not None:
        return SourceArtifact.from_text(args.text, source_name=args.source_name or "cli-text")
    if args.edus is not None:
        values = json.loads(args.edus)
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            raise ValueError("--edus must be a JSON array of strings")
        return SourceArtifact.from_edus(tuple(values), source_name=args.source_name or "cli-edus")
    if args.input and args.input != "-":
        source_form = _optional_source_form(args.source_form)
        if source_form is None and Path(args.input).suffix.casefold() in {".txt", ".text"}:
            source_form = SourceForm.TEXT
        return SourceArtifact.from_path(args.input, source_form=source_form)
    payload = sys.stdin.buffer.read()
    source_form = SourceForm(args.source_form or SourceForm.TEXT)
    if source_form is SourceForm.TEXT:
        return SourceArtifact.from_text(
            payload.decode("utf-8", errors="strict"),
            source_name=args.source_name or "stdin",
        )
    return SourceArtifact.from_bytes(
        payload,
        source_form=source_form,
        source_name=args.source_name or "stdin",
        media_type=_MEDIA_TYPES[source_form],
    )


def _source_from_http(data: Mapping[str, Any]) -> SourceArtifact:
    source_form = SourceForm(data.get("source_form", SourceForm.TEXT))
    source_name = str(data.get("source_name", "http-request"))
    if source_form is SourceForm.EDUS:
        edus = data.get("edus")
        if not isinstance(edus, list) or any(not isinstance(item, str) for item in edus):
            raise ValueError("EDU requests require an edus array of strings")
        return SourceArtifact.from_edus(tuple(edus), source_name=source_name)
    if "text" in data:
        text = data["text"]
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        if source_form is SourceForm.TEXT:
            return SourceArtifact.from_text(text, source_name=source_name)
        payload = text.encode("utf-8")
    else:
        encoded = data.get("payload_base64")
        if not isinstance(encoded, str):
            raise ValueError("request requires text, edus, or payload_base64")
        payload = base64.b64decode(encoded, validate=True)
    return SourceArtifact.from_bytes(
        payload,
        source_form=source_form,
        source_name=source_name,
        media_type=str(data.get("media_type", _MEDIA_TYPES[source_form])),
    )


def _handler_type(ingestor: _ProductionService) -> type[BaseHTTPRequestHandler]:
    class ProductionRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/capabilities":
                self._send(HTTPStatus.OK, serialize_contract(ingestor.capabilities()))
                return
            if self.path in {"/", "/health"}:
                capabilities = ingestor.capabilities()
                self._send(
                    HTTPStatus.OK,
                    rfc8785.dumps(
                        {
                            "status": "ok",
                            "contract": capabilities.contract,
                            "contract_version": capabilities.contract_version,
                            "capability_identity": (
                                capabilities.semantic_digest.hex_digest
                                if capabilities.semantic_digest is not None
                                else None
                            ),
                        }
                    ),
                )
                return
            self._send(HTTPStatus.NOT_FOUND, b'{"code":"not_found"}')

        def do_POST(self) -> None:
            if self.path != "/analyse":
                self._send(HTTPStatus.NOT_FOUND, b'{"code":"not_found"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length).decode("utf-8", errors="strict"))
                if not isinstance(data, dict):
                    raise ValueError("request body must be a JSON object")
                outcome = ingestor.analyse(_source_from_http(data))
                self._send(HTTPStatus.OK, serialize_contract(outcome))
            except ProductionIngestError as exc:
                status = (
                    HTTPStatus.SERVICE_UNAVAILABLE
                    if exc.failure.category.value == "provider_unavailable"
                    else HTTPStatus.UNPROCESSABLE_ENTITY
                )
                self._send(
                    status,
                    serialize_contract(exc.failure),
                )
            except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
                self._send(
                    HTTPStatus.BAD_REQUEST,
                    serialize_contract(
                        _safe_boundary_failure(
                            exc,
                            stage=LifecycleStage.ACQUISITION,
                            category=FailureCategory.MALFORMED_INPUT,
                            code="http_request_acquisition_failed",
                            message_template="http_request_could_not_be_acquired",
                        )
                    ),
                )

        def _send(self, status: HTTPStatus, payload: bytes) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return ProductionRequestHandler


def _render_outcome(outcome: Any, output_format: str) -> bytes:
    if output_format == "canonical-json":
        return serialize_contract(outcome) + b"\n"
    analysis = outcome.semantic.analysis
    payload = {
        "projection": "presentation_only",
        "canonical_semantic_identity": outcome.semantic_digest,
        "status": outcome.semantic.status,
        "node_count": len(analysis.nodes) if analysis is not None else 0,
        "primary_edge_count": len(analysis.primary_edges) if analysis is not None else 0,
        "secondary_edge_count": len(analysis.secondary_edges) if analysis is not None else 0,
    }
    return rfc8785.dumps(payload) + b"\n"


def _write_payload(payload: bytes, output: str | None, *, stream: Any) -> None:
    if output is None:
        stream.write(payload)
        stream.flush()
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _optional_source_form(value: str | None) -> SourceForm | None:
    return SourceForm(value) if value is not None else None


def _safe_boundary_failure(
    exc: Exception,
    *,
    stage: LifecycleStage,
    category: FailureCategory,
    code: str,
    message_template: str,
) -> ProductionFailure:
    if isinstance(exc, OSError):
        # An I/O error proves neither malformed input nor a permanent condition:
        # the honest labels are internal-processing with unknown retryability.
        category = FailureCategory.INTERNAL_PROCESSING_FAILURE
        retryability = Retryability.UNKNOWN
    else:
        retryability = Retryability.NOT_RETRYABLE
    return ProductionFailure(
        failed_stage=stage,
        category=category,
        code=code,
        retryability=retryability,
        message_template=message_template,
        cause=SafeCause(
            category=category,
            exception_type=type(exc).__qualname__,
            message_template="underlying_operation_failed",
        ),
    )


def _add_model_arguments(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument("--model-store", required=required)
    parser.add_argument("--release-id", required=required)
    parser.add_argument("--erst-checkpoint")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "mps", "cuda"))


def create_parser() -> argparse.ArgumentParser:
    """Build the stable command grammar."""

    parser = argparse.ArgumentParser(prog="isanlp-rst")
    commands = parser.add_subparsers(dest="command")

    parse = commands.add_parser("parse", help="run canonical production analysis")
    parse.add_argument("input", nargs="?")
    parse.add_argument("--text")
    parse.add_argument("--edus")
    parse.add_argument("--source-name")
    parse.add_argument("--source-form", choices=tuple(item.value for item in SourceForm))
    parse.add_argument("--output")
    parse.add_argument("--format", choices=("canonical-json", "summary"), default="canonical-json")
    parse.add_argument("--output-formalism", choices=tuple(OutputFormalism), default=OutputFormalism.RST_TREE)
    parse.add_argument(
        "--evidence-detail", choices=tuple(EvidenceDetailPolicy), default=EvidenceDetailPolicy.DECISION_COMPLETE
    )
    parse.add_argument("--no-marker-refinement", action="store_true")
    parse.add_argument("--cache-directory")
    _add_model_arguments(parse, required=True)
    parse.set_defaults(func=cmd_parse)

    capabilities = commands.add_parser("capabilities", help="describe installed capability")
    capabilities.add_argument("--output")
    _add_model_arguments(capabilities, required=False)
    capabilities.set_defaults(func=cmd_capabilities)

    serve = commands.add_parser("serve", help="run loopback-only canonical HTTP API")
    serve.add_argument("--host", default="127.0.0.1", choices=tuple(sorted(_LOOPBACK_HOSTS)))
    serve.add_argument("--port", type=int, default=8080)
    _add_model_arguments(serve, required=True)
    serve.set_defaults(func=cmd_serve)

    version = commands.add_parser("version")
    version.add_argument("--output")
    version.set_defaults(func=cmd_version)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one CLI command."""

    parser = create_parser()
    args = parser.parse_args(argv)
    function = getattr(args, "func", None)
    if function is None:
        parser.print_help()
        return 1
    try:
        return int(function(args))
    except (OSError, ValueError) as exc:
        sys.stderr.buffer.write(
            serialize_contract(
                _safe_boundary_failure(
                    exc,
                    stage=LifecycleStage.INFERENCE,
                    category=FailureCategory.PROVIDER_UNAVAILABLE,
                    code="cli_provider_configuration_failed",
                    message_template="configured_parser_could_not_be_created",
                )
            )
            + b"\n"
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
