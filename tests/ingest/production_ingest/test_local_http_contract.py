"""Loopback HTTP parity, capability health, and safe typed failures."""

from dataclasses import dataclass
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import threading

from isanlp_rst.cli import _handler_type
from isanlp_rst.ingest import (
    FailureCategory,
    LifecycleStage,
    ProductionAnalysisOutcome,
    ProductionFailure,
    ProductionIngestError,
    ProductionIngestor,
    Retryability,
    SafeProductionFailureRecord,
    SourceArtifact,
    load_contract,
    serialize_contract,
)

from .conftest import ParserBuilder


@dataclass(slots=True)
class _HttpIngestor:
    delegate: ProductionIngestor
    outcome: ProductionAnalysisOutcome
    fail: bool = False
    calls: int = 0

    def analyse(self, source: SourceArtifact) -> ProductionAnalysisOutcome:
        del source
        self.calls += 1
        if self.fail:
            raise ProductionIngestError(
                ProductionFailure(
                    failed_stage=LifecycleStage.INFERENCE,
                    category=FailureCategory.PROVIDER_UNAVAILABLE,
                    code="parser_unavailable",
                    retryability=Retryability.NOT_RETRYABLE,
                    message_template="parser_is_not_available",
                )
            )
        return self.outcome

    def capabilities(self):
        return self.delegate.capabilities()


def test_local_http_analysis_and_capabilities_match_python_bytes(
    parser_builder: ParserBuilder,
) -> None:
    delegate = ProductionIngestor(parser=parser_builder())
    outcome = delegate.analyse(
        SourceArtifact.from_text("First. Second.", source_name="http-request")
    )
    ingestor = _HttpIngestor(delegate, outcome)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_type(ingestor))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/analyse",
            body=json.dumps({"source_form": "text", "text": "First. Second."}),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        assert response.status == 200
        assert response.read() == serialize_contract(outcome)
        assert ingestor.calls == 1

        connection.request("GET", "/capabilities")
        capability_response = connection.getresponse()
        assert capability_response.status == 200
        assert load_contract(capability_response.read()).kind == "capabilities"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_local_http_failure_is_safe_canonical_contract(
    parser_builder: ParserBuilder,
) -> None:
    delegate = ProductionIngestor(parser=parser_builder())
    outcome = delegate.analyse(
        SourceArtifact.from_text("First. Second.", source_name="http-request")
    )
    ingestor = _HttpIngestor(delegate, outcome, fail=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_type(ingestor))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/analyse",
            body=json.dumps({"source_form": "text", "text": "PRIVATE marker"}),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = response.read()
        assert response.status == 503
        assert load_contract(payload).kind == "safe_production_failure"
        assert b"PRIVATE" not in payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_local_http_malformed_request_is_a_safe_canonical_failure(
    parser_builder: ParserBuilder,
) -> None:
    delegate = ProductionIngestor(parser=parser_builder())
    outcome = delegate.analyse(
        SourceArtifact.from_text("First. Second.", source_name="http-request")
    )
    ingestor = _HttpIngestor(delegate, outcome)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_type(ingestor))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(
            "POST",
            "/analyse",
            body=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        record = load_contract(response.read())
        assert response.status == 400
        assert isinstance(record, SafeProductionFailureRecord)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
