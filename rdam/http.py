"""Optional bounded loopback adapter; analysis remains in one configured Machine."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
import math
import re
import socket
import sys
from typing import Literal, cast

from starlette.applications import Starlette
from starlette.requests import ClientDisconnect, Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.types import Scope, Receive, Send
import uvicorn

from rdam._errors import Operation, error, failure
from rdam._strict import canonical_json_bytes
from rdam.contracts import AggregateAnalysis, MachineCapabilities, MachinePreparation, OperationError
from rdam.historical import HistoricalAggregateAnalysis
from rdam.interpretation import select_analysis
from rdam.machine import Machine
from rdam.serialization import load, load_preparation_request, load_request, load_view_request, serialize, version_info
from rdam.summary import summarise

_POST_ROUTES = {"/v1/prepare": "prepare", "/v1/analyse": "analyse", "/v1/view": "view", "/v1/summary": "summary"}
_GET_ROUTES = {"/v1/capabilities": "capabilities", "/v1/version": "version"}
_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def _response(
    payload: bytes, *, status: int = 200, media: str = "application/json", allow: str | None = None
) -> Response:
    headers = dict(_HEADERS)
    if allow is not None:
        headers["Allow"] = allow
    return Response(payload, status_code=status, media_type=media, headers=headers)


def _reject(
    operation: Operation, status: int, code: str = "invalid_http_request", *, allow: str | None = None
) -> Response:
    category = "busy" if code == "busy" else "invalid_request"
    return _response(serialize(failure(operation, category, code)), status=status, allow=allow)


def _perform(machine: Machine, operation: Operation, payload: bytes, schema_name: str | None, mode: str) -> Response:
    try:
        if operation == "capabilities":
            return _response(serialize(machine.capabilities()))
        if operation == "version":
            return _response(serialize(version_info()))
        if operation == "schema":
            from rdam.serialization import schema

            try:
                document = schema(schema_name or "", mode=cast(Literal["validation", "serialization"], mode))
            except ValueError as cause:
                raise error(operation, "invalid_request", "invalid_input") from cause
            return _response(canonical_json_bytes(document))
        try:
            if operation == "prepare":
                decoded = load_preparation_request(payload)
            elif operation == "analyse":
                decoded = load_request(payload)
            elif operation == "view":
                decoded = load_view_request(payload)
            else:
                decoded = load(payload)
                if not isinstance(
                    decoded, (AggregateAnalysis, HistoricalAggregateAnalysis, MachinePreparation, MachineCapabilities)
                ):
                    raise ValueError("unsupported summary record")
        except (ValueError, UnicodeError) as cause:
            raise error(operation, "invalid_request", "invalid_input") from cause
        from rdam.contracts import AggregateRequest, PreparationRequest
        from rdam.interpretation import ViewRequest

        if isinstance(decoded, PreparationRequest):
            return _response(serialize(machine.prepare(decoded)))
        if isinstance(decoded, AggregateRequest):
            return _response(serialize(machine.analyse(decoded)))
        if isinstance(decoded, ViewRequest):
            return _response(serialize(select_analysis(decoded.analysis, techniques=decoded.techniques)))
        return _response((summarise(decoded) + "\n").encode("utf-8"), media="text/plain")
    except OperationError:
        raise
    except Exception as cause:
        # The sole HTTP exception boundary preserves the cause but exposes no raw values.
        raise error(operation, "internal_error", "internal_error") from cause


def _safe_perform(
    machine: Machine, operation: Operation, payload: bytes, schema_name: str | None, mode: str
) -> Response:
    try:
        return _perform(machine, operation, payload, schema_name, mode)
    except OperationError as cause:
        status = {
            "invalid_request": 400,
            "source_unavailable": 422,
            "preparation_failed": 422,
            "dependency_unavailable": 503,
            "busy": 503,
        }.get(cause.failure.category, 500)
        return _response(serialize(cause.failure), status=status)


def create_app(
    machine: Machine,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_request_bytes: int = 64 * 1024 * 1024,
    body_timeout_seconds: float = 30.0,
) -> Starlette:
    _validate_settings(host, port, max_request_bytes, body_timeout_seconds)
    authority = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
    accepted_hosts = {authority, f"localhost:{port}"}
    busy = False
    jobs: set[asyncio.Task[Response]] = set()

    def finished(task: asyncio.Task[Response]) -> None:
        nonlocal busy
        jobs.discard(task)
        busy = False

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncGenerator[None]:
        yield
        if jobs:
            await asyncio.gather(*jobs)

    async def endpoint(request: Request) -> Response:
        nonlocal busy
        operation: Operation = "serve"
        hosts = request.headers.getlist("host")
        if len(hosts) != 1 or hosts[0].lower() not in accepted_hosts:
            return _reject(operation, 403)
        path = request.url.path
        schema_name = path.removeprefix("/v1/schemas/") if path.startswith("/v1/schemas/") else None
        is_schema = schema_name is not None and bool(schema_name) and "/" not in schema_name
        allowed = "POST" if path in _POST_ROUTES else "GET" if path in _GET_ROUTES or is_schema else None
        if allowed is None:
            return _reject(operation, 404)
        if request.method != allowed:
            return _reject(operation, 405, allow=allowed)
        operation = "schema" if is_schema else cast(Operation, {**_GET_ROUTES, **_POST_ROUTES}[path])
        query = request.query_params.multi_items()
        if query and (
            not is_schema
            or len(query) != 1
            or query[0][0] != "mode"
            or query[0][1] not in {"validation", "serialization"}
        ):
            return _reject(operation, 400)
        mode = request.query_params.get("mode", "validation")
        lengths = request.headers.getlist("content-length")
        if request.headers.getlist("transfer-encoding"):
            return _reject(operation, 400)
        if request.method == "GET":
            if lengths and (len(lengths) != 1 or lengths[0] != "0"):
                return _reject(operation, 400)
            return await asyncio.to_thread(_safe_perform, machine, operation, b"", schema_name, mode)
        if request.headers.getlist("origin"):
            return _reject(operation, 403)
        if not lengths:
            return _reject(operation, 411)
        if len(lengths) != 1 or re.fullmatch(r"[0-9]+", lengths[0]) is None:
            return _reject(operation, 400)
        size = int(lengths[0])
        if size > max_request_bytes:
            return _reject(operation, 413, "body_too_large")
        encodings = request.headers.getlist("content-encoding")
        media = request.headers.getlist("content-type")
        if len(encodings) > 1 or len(media) > 1:
            return _reject(operation, 400)
        if (encodings and (len(encodings) != 1 or encodings[0].lower() != "identity")) or len(media) != 1:
            return _reject(operation, 415)
        if (
            re.fullmatch(r'application/json(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?\s*', media[0], re.IGNORECASE)
            is None
        ):
            return _reject(operation, 415)
        if busy:
            return _reject(operation, 503, "busy")
        busy = True
        worker: asyncio.Task[Response] | None = None
        try:
            body = bytearray()
            try:
                async with asyncio.timeout(body_timeout_seconds):
                    async for chunk in request.stream():
                        if len(body) + len(chunk) > max_request_bytes:
                            return _reject(operation, 413, "body_too_large")
                        if len(body) + len(chunk) > size:
                            return _reject(operation, 400)
                        body.extend(chunk)
            except TimeoutError:
                return _reject(operation, 408, "body_timeout")
            except ClientDisconnect:
                return _reject(operation, 400)
            if len(body) != size:
                return _reject(operation, 400)
            worker = asyncio.create_task(
                asyncio.to_thread(_safe_perform, machine, operation, bytes(body), schema_name, mode)
            )
            jobs.add(worker)
            worker.add_done_callback(finished)
            return await asyncio.shield(worker)
        finally:
            if worker is None:
                busy = False

    class Endpoint:
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            response = await endpoint(Request(scope, receive))
            await response(scope, receive, send)

    return Starlette(routes=[Route("/{path:path}", Endpoint())], lifespan=lifespan)


def _validate_settings(host: object, port: object, maximum: object, timeout: object) -> None:
    if (
        host not in {"127.0.0.1", "::1"}
        or isinstance(port, bool)
        or not isinstance(port, int)
        or not 0 <= port <= 65535
    ):
        raise error("serve", "invalid_request", "invalid_arguments")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
        raise error("serve", "invalid_request", "invalid_arguments")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise error("serve", "invalid_request", "invalid_arguments")


class _SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return canonical_json_bytes({"event": "http_server_diagnostic", "level": record.levelname}).decode("utf-8")


def serve(
    machine: Machine,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_request_bytes: int = 64 * 1024 * 1024,
    body_timeout_seconds: float = 30.0,
) -> None:
    _validate_settings(host, port, max_request_bytes, body_timeout_seconds)
    family = socket.AF_INET6 if host == "::1" else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as listener:
        listener.bind((host, port))
        listener.listen(32)
        actual_port = listener.getsockname()[1]
        app = create_app(
            machine,
            host=host,
            port=actual_port,
            max_request_bytes=max_request_bytes,
            body_timeout_seconds=body_timeout_seconds,
        )
        config = uvicorn.Config(
            app,
            host=host,
            port=actual_port,
            loop="asyncio",
            http="h11",
            ws="none",
            proxy_headers=False,
            access_log=False,
            log_config=None,
            limit_concurrency=32,
            h11_max_incomplete_event_size=16384,
            timeout_keep_alive=5,
            server_header=False,
        )
        server = uvicorn.Server(config)
        logger = logging.getLogger("uvicorn.error")
        previous_handlers, previous_propagate = logger.handlers[:], logger.propagate
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_SafeFormatter())
        logger.handlers = [handler]
        logger.propagate = False
        authority = f"[{host}]:{actual_port}" if ":" in host else f"{host}:{actual_port}"

        async def run() -> None:
            task = asyncio.create_task(server.serve(sockets=[listener]))
            while not server.started and not task.done():
                await asyncio.sleep(0.01)
            if server.started:
                sys.stderr.buffer.write(
                    canonical_json_bytes({"event": "listening", "url": f"http://{authority}"}) + b"\n"
                )
                sys.stderr.buffer.flush()
            await task

        try:
            asyncio.run(run())
        finally:
            logger.handlers, logger.propagate = previous_handlers, previous_propagate
