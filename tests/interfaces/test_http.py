"""Real-loopback HTTP contract checks using native Dung and IBIS execution."""

from collections.abc import Generator, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPResponse
import json
from pathlib import Path
import selectors
import signal
import socket
import subprocess
import sys
from threading import Event
from time import monotonic
from typing import override
from urllib.parse import urlsplit

import pytest
import uvicorn

from rdam import (
    AggregateRequest,
    Machine,
    NativeTechniqueResult,
    OperationFailure,
    OperationError,
    PreparationRequest,
    ProviderRequest,
    StructuredInput,
    Technique,
    ViewRequest,
    load,
    select_analysis,
    serialize,
    serialize_preparation_request,
    serialize_request,
    serialize_view_request,
    summarise,
    version_info,
    canonical_json_bytes,
)
from rdam.dung import DungProvider
from rdam.http import create_app
from rdam.ibis import IbisProvider
from rdam.ingest.contracts.source import SourceForm
from rdam.serialization import schema


@dataclass(frozen=True, slots=True)
class Reply:
    status: int
    headers: Mapping[str, str]
    body: bytes


def _reply(response: HTTPResponse) -> Reply:
    return Reply(response.status, {key.lower(): value for key, value in response.getheaders()}, response.read())


@dataclass(frozen=True, slots=True)
class Loopback:
    port: int
    host: str = "127.0.0.1"

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Reply:
        connection = HTTPConnection(self.host, self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=dict(headers or {}))
            return _reply(connection.getresponse())
        finally:
            connection.close()

    def post(self, path: str, body: bytes) -> Reply:
        return self.request("POST", path, body, {"Content-Type": "application/json"})

    def connect(self) -> socket.socket:
        return socket.create_connection((self.host, self.port), timeout=5)

    def raw(self, request: bytes) -> Reply:
        with self.connect() as peer:
            peer.sendall(request)
            response = HTTPResponse(peer)
            response.begin()
            return _reply(response)

    def headers(self, path: str, length: int) -> bytes:
        authority = f"[{self.host}]:{self.port}" if ":" in self.host else f"{self.host}:{self.port}"
        return (
            f"POST {path} HTTP/1.1\r\nHost: {authority}\r\n"
            f"Content-Type: application/json\r\nContent-Length: {length}\r\n\r\n"
        ).encode("ascii")


@contextmanager
def running_server(
    machine: Machine,
    *,
    host: str = "127.0.0.1",
    max_request_bytes: int = 67_108_864,
    body_timeout_seconds: float = 30.0,
) -> Generator[Loopback]:
    """Use the external server's real h11 parser, not an in-process ASGI client."""
    family = socket.AF_INET6 if host == "::1" else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as listener:
        listener.bind((host, 0))
        port = listener.getsockname()[1]
        app = create_app(
            machine,
            host=host,
            port=port,
            max_request_bytes=max_request_bytes,
            body_timeout_seconds=body_timeout_seconds,
        )
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            loop="asyncio",
            http="h11",
            ws="none",
            access_log=False,
            log_level="critical",
            proxy_headers=False,
            limit_concurrency=32,
            h11_max_incomplete_event_size=16_384,
            timeout_keep_alive=5,
        )
        server = uvicorn.Server(config)
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="http-test-server") as executor:
            future = executor.submit(server.run, sockets=[listener])
            try:
                deadline = monotonic() + 10
                while not server.started:
                    if future.done():
                        future.result()
                        pytest.fail("Uvicorn stopped before startup")
                    assert monotonic() < deadline, "loopback server did not start"
                    Event().wait(0.01)
                yield Loopback(port, host)
            finally:
                server.should_exit = True
                future.result(timeout=10)


@pytest.fixture
def native_machine() -> Machine:
    return Machine((DungProvider(), IbisProvider()))


@pytest.fixture
def loopback(native_machine: Machine) -> Iterator[Loopback]:
    with running_server(native_machine) as server:
        yield server


def structured_request(*, invalid_dung: bool = False) -> AggregateRequest:
    return AggregateRequest.for_structured((
        StructuredInput(
            technique=Technique.DUNG,
            payload={"arguments": ["a"], "attacks": [["a", "missing"]] if invalid_dung else [["a", "a"]]},
        ),
        StructuredInput(
            technique=Technique.IBIS,
            payload={"nodes": [{"id": "q", "kind": "issue", "text": "Why?"}], "links": []},
        ),
    ), source_name="HTTP native parity")


def assert_json(reply: Reply, status: int) -> None:
    assert reply.status == status, reply.body
    assert reply.headers["content-type"] == "application/json"
    assert int(reply.headers["content-length"]) == len(reply.body)
    assert reply.headers["cache-control"] == "no-store"
    assert reply.headers["x-content-type-options"] == "nosniff"
    assert "access-control-allow-origin" not in reply.headers
    assert "content-encoding" not in reply.headers
    assert not reply.body.endswith(b"\n")


def assert_failure(reply: Reply, status: int) -> OperationFailure:
    assert_json(reply, status)
    record = load(reply.body)
    assert isinstance(record, OperationFailure)
    assert serialize(record) == reply.body
    assert b"PRIVATE_HTTP_MARKER" not in reply.body
    return record


@pytest.mark.parametrize("invalid_dung", (False, True))
def test_analysis_and_view_equal_native_python_bytes(
    loopback: Loopback, native_machine: Machine, invalid_dung: bool,
) -> None:
    request = structured_request(invalid_dung=invalid_dung)
    expected = native_machine.analyse(request)
    assert expected.status == ("partial" if invalid_dung else "complete")
    reply = loopback.post("/v1/analyse", serialize_request(request))
    assert_json(reply, 200)
    assert reply.body == serialize(expected)
    view_request = ViewRequest(analysis=expected, techniques=(Technique.IBIS,))
    view = loopback.post("/v1/view", serialize_view_request(view_request))
    assert_json(view, 200)
    assert view.body == serialize(select_analysis(expected, techniques=(Technique.IBIS,)))


def test_provider_failure_is_an_unsuccessful_aggregate_not_http_error(
    loopback: Loopback, native_machine: Machine,
) -> None:
    request = AggregateRequest.for_structured((StructuredInput(
        technique=Technique.DUNG, payload={"arguments": ["a"], "attacks": [["a", "missing"]]},
    ),))
    expected = native_machine.analyse(request)
    assert expected.status == "unsuccessful"
    reply = loopback.post("/v1/analyse", serialize_request(request))
    assert_json(reply, 200)
    assert reply.body == serialize(expected)


def test_discovery_and_summary_use_shared_records(loopback: Loopback, native_machine: Machine) -> None:
    capabilities = native_machine.capabilities()
    for path, expected in (("/v1/capabilities", capabilities), ("/v1/version", version_info())):
        reply = loopback.request("GET", path)
        assert_json(reply, 200)
        assert reply.body == serialize(expected)
    summary = loopback.post("/v1/summary", serialize(capabilities))
    assert summary.status == 200
    assert summary.headers["content-type"] == "text/plain; charset=utf-8"
    assert summary.body == (summarise(capabilities) + "\n").encode("utf-8")
    assert int(summary.headers["content-length"]) == len(summary.body)


def test_prepare_preserves_materialized_bytes_after_original_file_changes(
    loopback: Loopback, native_machine: Machine, tmp_path: Path,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("Éva: first source 🙂", encoding="utf-8")
    request = PreparationRequest.for_source(source)
    body = serialize_preparation_request(request)
    assert request.source_artifact is not None
    source.write_text("PRIVATE_HTTP_MARKER replacement", encoding="utf-8")
    reply = loopback.post("/v1/prepare", body)
    assert_json(reply, 200)
    assert reply.body == serialize(native_machine.prepare(request))
    assert b"PRIVATE_HTTP_MARKER" not in reply.body


@pytest.mark.parametrize(("method", "path", "status"), (
    ("GET", "/capabilities", 404),
    ("POST", "/analyse", 404),
    ("GET", "/v1/capabilities/", 404),
    ("GET", "/v1/missing", 404),
    ("GET", "/v1/analyse", 405),
    ("POST", "/v1/version", 405),
    ("PUT", "/v1/analyse", 405),
    ("BREW", "/v1/analyse", 405),
    ("GET", "/v1/version?extra=1", 400),
    ("GET", "/v1/version?extra=1&extra=2", 400),
    ("GET", "/v1/schemas/request?mode=validation&mode=serialization", 400),
    ("GET", "/v1/schemas/request?mode=unknown", 400),
    ("GET", "/v1/schemas/request?version=999", 400),
    ("GET", "/v1/schemas/not-a-schema", 400),
))
def test_route_method_and_query_contract(loopback: Loopback, method: str, path: str, status: int) -> None:
    reply = loopback.request(method, path, b"{}" if method == "POST" else None,
                             {"Content-Type": "application/json"})
    assert_failure(reply, status)
    if status == 405:
        assert reply.headers["allow"]
    assert "location" not in reply.headers


@pytest.mark.parametrize("body", (
    b"not-json PRIVATE_HTTP_MARKER",
    b"\xff",
    b'{"contract":"rdam.request","contract":"rdam.request"}',
    b'{"invalid":"\\ud800"}',
    b'{"invalid":NaN}',
    b'{"invalid":1e999}',
    b"{} {}",
    b'"{}"',
    b"[]",
))
def test_invalid_json_is_safe_shared_failure(loopback: Loopback, body: bytes) -> None:
    assert_failure(loopback.post("/v1/analyse", body), 400)


def test_invalid_base64_is_rejected_before_source_preparation(loopback: Loopback) -> None:
    request = PreparationRequest.for_bytes(b"opaque", SourceForm.DOCLANG_ARCHIVE, "PRIVATE_HTTP_MARKER")
    document = json.loads(serialize_preparation_request(request))
    document["source_artifact"]["artifact"]["raw_bytes"] = "%%%"
    assert_failure(loopback.post("/v1/prepare", json.dumps(document).encode("utf-8")), 400)


def test_decoded_request_with_invalid_source_is_a_preparation_failure(loopback: Loopback) -> None:
    request = PreparationRequest.for_bytes(
        b"This is not a ZIP archive: PRIVATE_HTTP_MARKER", SourceForm.DOCLANG_ARCHIVE, "PRIVATE_HTTP_MARKER",
    )
    reply = loopback.post("/v1/prepare", serialize_preparation_request(request))
    assert_failure(reply, 422)


@pytest.mark.parametrize("mode", ("validation", "serialization"))
@pytest.mark.parametrize("record", ("request", "view-request", "dung-input", "ibis-input", "native-result-v1"))
def test_schema_route_matches_shared_generator(loopback: Loopback, mode: str, record: str) -> None:
    reply = loopback.request("GET", f"/v1/schemas/{record}?mode={mode}")
    assert_json(reply, 200)
    if mode == "validation":
        expected = schema(record, mode="validation")
    else:
        expected = schema(record, mode="serialization")
    assert reply.body == canonical_json_bytes(expected)


def test_schema_default_is_validation(loopback: Loopback) -> None:
    implicit = loopback.request("GET", "/v1/schemas/request")
    explicit = loopback.request("GET", "/v1/schemas/request?mode=validation")
    assert_json(implicit, 200)
    assert implicit.body == explicit.body


@pytest.mark.parametrize("origin", ("null", "http://localhost", "http://127.0.0.1", "https://example.com"))
def test_every_post_origin_is_rejected(loopback: Loopback, origin: str) -> None:
    reply = loopback.request("POST", "/v1/analyse", serialize_request(structured_request()),
                             {"Content-Type": "application/json", "Origin": origin})
    assert_failure(reply, 403)


@pytest.mark.parametrize("host", ("example.com", "localhost", "127.0.0.1:1", "localhost:65536"))
def test_unbound_host_is_rejected(loopback: Loopback, host: str) -> None:
    assert_failure(loopback.request("GET", "/v1/version", headers={"Host": host}), 403)


def test_localhost_requires_exact_bound_port(loopback: Loopback) -> None:
    reply = loopback.request("GET", "/v1/version", headers={"Host": f"localhost:{loopback.port}"})
    assert_json(reply, 200)


def test_ipv6_loopback_requires_bracketed_exact_authority(native_machine: Machine) -> None:
    with running_server(native_machine, host="::1") as server:
        reply = server.request("GET", "/v1/version", headers={"Host": f"[::1]:{server.port}"})
        assert_json(reply, 200)
        assert_failure(server.request("GET", "/v1/version", headers={"Host": f"::1:{server.port}"}), 403)
        assert_failure(server.request("GET", "/v1/version", headers={"Host": f"127.0.0.1:{server.port}"}), 403)


@pytest.mark.parametrize("content_type", (
    "text/plain", "application/json; charset=latin-1", "application/json; unknown=x", "multipart/form-data",
))
def test_unsupported_media_is_rejected(loopback: Loopback, content_type: str) -> None:
    assert_failure(loopback.request("POST", "/v1/analyse", b"{}", {"Content-Type": content_type}), 415)


@pytest.mark.parametrize("content_type", ("application/json", "application/json; charset=utf-8"))
def test_supported_media_preserves_output(loopback: Loopback, content_type: str) -> None:
    reply = loopback.request("POST", "/v1/analyse", serialize_request(structured_request()),
                             {"Content-Type": content_type, "Content-Encoding": "identity"})
    assert_json(reply, 200)


def test_content_encoding_is_not_silently_decompressed(loopback: Loopback) -> None:
    reply = loopback.request("POST", "/v1/analyse", b"{}",
                             {"Content-Type": "application/json", "Content-Encoding": "gzip"})
    assert_failure(reply, 415)


def test_conflicting_media_headers_are_an_invalid_request(loopback: Loopback) -> None:
    body = serialize_request(structured_request())
    request = (f"POST /v1/analyse HTTP/1.1\r\nHost: localhost:{loopback.port}\r\n"
               "Content-Type: application/json\r\nContent-Type: text/plain\r\n"
               f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode("ascii") + body
    assert_failure(loopback.raw(request), 400)


def test_get_body_is_rejected(loopback: Loopback) -> None:
    assert_failure(loopback.request("GET", "/v1/version", b"{}"), 400)


def test_post_requires_content_length(loopback: Loopback) -> None:
    request = (f"POST /v1/analyse HTTP/1.1\r\nHost: localhost:{loopback.port}\r\n"
               "Content-Type: application/json\r\nConnection: close\r\n\r\n").encode("ascii")
    assert_failure(loopback.raw(request), 411)


def test_chunked_transfer_is_not_an_application_body_codec(loopback: Loopback) -> None:
    request = (f"POST /v1/analyse HTTP/1.1\r\nHost: localhost:{loopback.port}\r\n"
               "Content-Type: application/json\r\nTransfer-Encoding: chunked\r\n"
               "Connection: close\r\n\r\n2\r\n{}\r\n0\r\n\r\n").encode("ascii")
    assert_failure(loopback.raw(request), 400)


@pytest.mark.parametrize("framing", ("duplicate_host", "conflicting_lengths", "negative_length"))
def test_h11_rejections_are_explicitly_not_promised_rdam_json(loopback: Loopback, framing: str) -> None:
    extra = {
        "duplicate_host": f"Host: localhost:{loopback.port}\r\nContent-Length: 2\r\n",
        "conflicting_lengths": "Content-Length: 2\r\nContent-Length: 3\r\n",
        "negative_length": "Content-Length: -1\r\n",
    }[framing]
    request = (f"POST /v1/analyse HTTP/1.1\r\nHost: localhost:{loopback.port}\r\n"
               f"{extra}Content-Type: application/json\r\nConnection: close\r\n\r\n{{}}").encode("ascii")
    reply = loopback.raw(request)
    assert reply.status == 400
    assert b"PRIVATE_HTTP_MARKER" not in reply.body


def test_encoded_body_limit_is_inclusive(native_machine: Machine) -> None:
    body = serialize_request(structured_request())
    with running_server(native_machine, max_request_bytes=len(body)) as server:
        assert_json(server.post("/v1/analyse", body), 200)
        assert_failure(server.post("/v1/analyse", body + b" "), 413)


def test_slow_body_has_one_total_deadline_and_releases_admission(native_machine: Machine) -> None:
    with running_server(native_machine, body_timeout_seconds=0.3) as server:
        with server.connect() as peer:
            started = monotonic()
            peer.sendall(server.headers("/v1/analyse", 100) + b"{")
            Event().wait(0.18)
            peer.sendall(b" ")
            response = HTTPResponse(peer)
            response.begin()
            assert_failure(_reply(response), 408)
            assert monotonic() - started < 0.46, "body deadline reset after a small chunk"
        assert_json(server.post("/v1/analyse", serialize_request(structured_request())), 200)


class GatedDungProvider(DungProvider):
    """Instrument entry to real native computation; no synthetic native result."""

    def __init__(self) -> None:
        super().__init__()
        self.entered = Event()
        self.release = Event()
        self.completed = Event()

    @override
    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test did not release native execution")
        try:
            return super().analyse(request)
        finally:
            self.completed.set()


def test_disconnect_keeps_running_native_work_admitted_and_get_responsive() -> None:
    provider = GatedDungProvider()
    machine = Machine((provider, IbisProvider()))
    body = serialize_request(structured_request())
    with running_server(machine) as server:
        try:
            with server.connect() as peer:
                peer.sendall(server.headers("/v1/analyse", len(body)) + body)
                assert provider.entered.wait(timeout=3)
            # Closing the requester cannot preempt the Python provider thread.
            assert_json(server.request("GET", "/v1/version"), 200)
            assert_failure(server.post("/v1/prepare", b"{}"), 503)
            assert not provider.completed.is_set()
        finally:
            provider.release.set()
        assert provider.completed.wait(timeout=3)
        deadline = monotonic() + 3
        while True:
            reply = server.post("/v1/analyse", body)
            if reply.status != 503:
                assert_json(reply, 200)
                break
            assert monotonic() < deadline, "admission was not released after native completion"
            Event().wait(0.01)


def test_shutdown_drains_accepted_native_work() -> None:
    provider = GatedDungProvider()
    machine = Machine((provider, IbisProvider()))
    request = structured_request()
    expected = Machine((DungProvider(), IbisProvider())).analyse(request)

    def release_after_shutdown_begins() -> None:
        Event().wait(0.2)
        provider.release.set()

    with ThreadPoolExecutor(max_workers=2) as clients:
        try:
            with running_server(machine) as server:
                response = clients.submit(server.post, "/v1/analyse", serialize_request(request))
                assert provider.entered.wait(timeout=3)
                release = clients.submit(release_after_shutdown_begins)
            assert provider.completed.is_set(), "server returned before accepted native work completed"
            reply = response.result(timeout=3)
            assert_json(reply, 200)
            assert reply.body == serialize(expected)
            release.result(timeout=3)
        finally:
            provider.release.set()


def test_disconnected_incomplete_body_releases_admission(native_machine: Machine) -> None:
    with running_server(native_machine) as server:
        with server.connect() as peer:
            peer.sendall(server.headers("/v1/analyse", 100) + b"{")
        deadline = monotonic() + 3
        while True:
            reply = server.post("/v1/analyse", serialize_request(structured_request()))
            if reply.status != 503:
                assert_json(reply, 200)
                break
            assert monotonic() < deadline, "disconnected body retained admission"
            Event().wait(0.01)


def test_admission_is_taken_before_complete_body_and_shared_across_posts(native_machine: Machine) -> None:
    with running_server(native_machine, body_timeout_seconds=2) as server:
        with server.connect() as peer:
            peer.sendall(server.headers("/v1/analyse", 100) + b"{")
            assert_json(server.request("GET", "/v1/capabilities"), 200)
            for path in ("/v1/analyse", "/v1/prepare", "/v1/view", "/v1/summary"):
                assert_failure(server.post(path, b"{}"), 503)


@pytest.mark.parametrize("host", ("0.0.0.0", "localhost", "example.com", "::"))
def test_startup_accepts_loopback_literals_only(native_machine: Machine, host: str) -> None:
    with pytest.raises(OperationError):
        create_app(native_machine, host=host)


@pytest.mark.parametrize("port", (-1, 65536, True))
def test_startup_rejects_invalid_ports(native_machine: Machine, port: int) -> None:
    with pytest.raises(OperationError):
        create_app(native_machine, port=port)


@pytest.mark.parametrize("maximum", (0, -1, True))
def test_startup_rejects_invalid_body_limits(native_machine: Machine, maximum: int) -> None:
    with pytest.raises(OperationError):
        create_app(native_machine, max_request_bytes=maximum)


@pytest.mark.parametrize("timeout", (0.0, -1.0, float("nan"), float("inf"), True))
def test_startup_rejects_invalid_body_deadlines(native_machine: Machine, timeout: float) -> None:
    with pytest.raises(OperationError):
        create_app(native_machine, body_timeout_seconds=timeout)


@pytest.mark.parametrize("arguments", (("--host", "0.0.0.0"), ("--port", "65536")))
def test_cli_serve_invalid_binding_is_a_safe_startup_failure(arguments: tuple[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "rdam", "serve", *arguments],
        capture_output=True, check=False, timeout=15,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    failure = load(result.stderr)
    assert isinstance(failure, OperationFailure)
    assert failure.category == "invalid_request"
    assert b"Traceback" not in result.stderr


def test_cli_serve_unavailable_port_is_a_safe_startup_failure() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        port = occupied.getsockname()[1]
        result = subprocess.run(
            [sys.executable, "-m", "rdam", "serve", "--port", str(port)],
            capture_output=True, check=False, timeout=15,
        )
    assert result.returncode == 1
    assert result.stdout == b""
    failure = load(result.stderr)
    assert isinstance(failure, OperationFailure)
    assert failure.category == "source_unavailable"
    assert b"Traceback" not in result.stderr


def test_cli_serve_reports_actual_port_and_stops_cleanly_on_interrupt() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "rdam", "serve", "--port", "0"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
    )
    diagnostics: list[bytes] = []
    try:
        assert process.stderr is not None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stderr, selectors.EVENT_READ)
            deadline = monotonic() + 15
            while True:
                remaining = deadline - monotonic()
                assert remaining > 0, "server did not emit its listening event"
                assert selector.select(timeout=remaining), "server startup timed out"
                line = process.stderr.readline()
                assert line, f"server exited before listening: {b''.join(diagnostics)!r}"
                diagnostics.append(line)
                event = json.loads(line)
                if event.get("event") == "listening":
                    url = event["url"]
                    assert isinstance(url, str)
                    address = urlsplit(url)
                    assert address.hostname == "127.0.0.1"
                    assert address.port is not None and address.port > 0
                    server = Loopback(address.port)
                    break
        assert_json(server.request("GET", "/v1/version"), 200)
        assert_failure(server.post("/v1/analyse", b"PRIVATE_HTTP_MARKER"), 400)
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=15)
        diagnostics.extend(stderr.splitlines(keepends=True))
        assert process.returncode == 130
        assert stdout == b""
        assert b"PRIVATE_HTTP_MARKER" not in b"".join(diagnostics)
        assert b"Traceback" not in b"".join(diagnostics)
        for line in diagnostics:
            assert isinstance(json.loads(line), dict)
        interrupted = load(diagnostics[-1])
        assert isinstance(interrupted, OperationFailure)
        assert interrupted.category == "interrupted"
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=10)
