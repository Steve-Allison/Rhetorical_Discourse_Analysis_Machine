"""Real SDK clients and model adapters; only the external HTTP service is simulated."""

import asyncio
from collections.abc import Callable
import json
from typing import cast, override

from anthropic import AsyncAnthropic
import httpx2
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import models
import pytest

from rdam._llm import LlmError, StructuredAnalyst


class Finding(BaseModel):
    claim: str


class ServiceTransport(httpx2.AsyncBaseTransport):
    """Record real request/close loops and return provider-protocol fixture bytes."""

    def __init__(self, provider: str, *, block: bool = False, status: int = 200) -> None:
        self.provider = provider
        self.block = block
        self.status = status
        self.requests: list[dict[str, object]] = []
        self.request_loops: list[asyncio.AbstractEventLoop] = []
        self.close_loops: list[asyncio.AbstractEventLoop] = []
        self.entered = asyncio.Event()

    @override
    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        self.request_loops.append(asyncio.get_running_loop())
        body = cast(dict[str, object], json.loads(request.content))
        self.requests.append(body)
        self.entered.set()
        if self.block:
            await asyncio.Future[None]()
        if self.status != 200:
            return httpx2.Response(
                self.status, request=request,
                json={"error": {"type": "api_error", "message": "fixture unavailable",
                                "code": self.status, "status": "UNAVAILABLE"}},
            )
        tools = cast(list[dict[str, object]], body["tools"])
        match self.provider:
            case "openai":
                payload = {
                    "id": "resp_fixture", "object": "response", "created_at": 0,
                    "model": "gpt-4.1", "status": "completed",
                    "output": [{"type": "function_call", "id": "fc_fixture", "call_id": "call_fixture",
                                "name": tools[0]["name"], "arguments": '{"claim":"fixture claim"}'}],
                }
            case "anthropic":
                payload = {
                    "id": "msg_fixture", "type": "message", "role": "assistant", "model": "claude-sonnet-4-5",
                    "stop_reason": "tool_use", "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                    "content": [{"type": "tool_use", "id": "tool_fixture", "name": tools[0]["name"],
                                 "input": {"claim": "fixture claim"}}],
                }
            case "google":
                declarations = cast(list[dict[str, object]], tools[0]["functionDeclarations"])
                payload = {
                    "candidates": [{"content": {"role": "model", "parts": [
                        {"functionCall": {"name": declarations[0]["name"], "args": {"claim": "fixture claim"}}}
                    ]}, "finishReason": "STOP"}],
                    "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
                }
            case _:
                raise AssertionError(f"unexpected provider {self.provider}")
        return httpx2.Response(200, json=payload, request=request)

    @override
    async def aclose(self) -> None:
        self.close_loops.append(asyncio.get_running_loop())


def _service(
    monkeypatch: pytest.MonkeyPatch, provider: str, *, block: bool = False, status: int = 200
) -> tuple[list[ServiceTransport], list[httpx2.AsyncClient]]:
    transports: list[ServiceTransport] = []
    clients: list[httpx2.AsyncClient] = []
    real_http_client = httpx2.AsyncClient

    def http_client(timeout: float) -> httpx2.AsyncClient:
        transport = ServiceTransport(provider, block=block, status=status)
        transports.append(transport)
        client = real_http_client(transport=transport, timeout=timeout)
        clients.append(client)
        return client

    def openai_client(*, api_key: str, max_retries: int, timeout: float) -> AsyncOpenAI:
        assert max_retries == 0
        return AsyncOpenAI(api_key=api_key, max_retries=max_retries, http_client=http_client(timeout))

    def anthropic_client(*, api_key: str, max_retries: int, timeout: float) -> AsyncAnthropic:
        assert max_retries == 0
        return AsyncAnthropic(api_key=api_key, max_retries=max_retries, http_client=http_client(timeout))

    class GoogleHTTPClient(real_http_client):
        def __init__(self, *, timeout: float) -> None:
            transport = ServiceTransport(provider, block=block, status=status)
            transports.append(transport)
            super().__init__(transport=transport, timeout=timeout)
            clients.append(self)

    monkeypatch.setenv("OPENAI_API_KEY", "lifecycle-fixture-not-a-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "lifecycle-fixture-not-a-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "lifecycle-fixture-not-a-key")
    monkeypatch.setattr("rdam._llm.AsyncOpenAI", openai_client)
    monkeypatch.setattr("rdam._llm.AsyncAnthropic", anthropic_client)
    if provider == "google":
        monkeypatch.setattr("rdam._llm.AsyncClient", GoogleHTTPClient)
    # The real SDK adapters must execute, but every HTTP client is fixture-owned.
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)
    return transports, clients


def _analyst(
    provider: str, *, source_validator: Callable[[Finding, str], object] | None = None,
    deadline: float = 5.0, transport_retries: int = 0,
) -> StructuredAnalyst[Finding]:
    names = {"openai": "gpt-4.1", "anthropic": "claude-sonnet-4-5", "google": "gemini-2.5-pro"}
    return StructuredAnalyst(
        output_type=Finding, instructions="Return a supported claim.", model=f"{provider}:{names[provider]}",
        source_validator=source_validator, output_retries=2, transport_retries=transport_retries,
        transport_deadline_seconds=deadline,
    )


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_repeated_sync_calls_close_on_owning_loop_after_success_and_validation_failure(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    transports, clients = _service(monkeypatch, provider)

    def validate(output: Finding, source: str) -> None:
        if output.claim != source:
            raise ValueError("claim: offsets [3:16] mismatch; unique literal occurrence [0:13]")

    analyst = _analyst(provider, source_validator=validate)
    assert analyst.agent.model is None, "cached configuration must not retain a loop-bound client"
    assert not clients
    assert analyst.extract("fixture claim").structure.claim == "fixture claim"
    with pytest.raises(LlmError, match="llm_output_failed_validation") as caught:
        analyst.extract("different source")
    assert caught.value.output_attempts == 3
    assert analyst.extract("fixture claim").structure.claim == "fixture claim"
    assert len(transports) == 3
    assert [len(transport.requests) for transport in transports] == [1, 3, 1]
    assert len({transport.request_loops[0] for transport in transports}) == 3
    for transport, client in zip(transports, clients, strict=True):
        assert client.is_closed
        assert transport.close_loops == [transport.request_loops[0]]
        assert all(loop is transport.close_loops[0] for loop in transport.request_loops)
        assert transport.close_loops[0].is_closed()
    retry_payload = json.dumps(transports[1].requests[1])
    assert "claim: offsets [3:16] mismatch; unique literal occurrence [0:13]" in retry_payload


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_deadline_closes_actual_client_before_sync_loop_exits(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    transports, clients = _service(monkeypatch, provider, block=True)
    with pytest.raises(LlmError, match="llm_transport_deadline_exceeded"):
        _analyst(provider, deadline=0.05).extract("fixture claim")
    assert len(transports) == len(clients) == 1
    assert clients[0].is_closed
    assert transports[0].close_loops == transports[0].request_loops


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_external_cancellation_closes_client_and_propagates(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    transports, clients = _service(monkeypatch, provider, block=True)
    analyst = _analyst(provider)

    async def scenario() -> None:
        task = asyncio.create_task(analyst.extract_async("fixture claim"))
        async with asyncio.timeout(5):
            while not transports:
                await asyncio.sleep(0)
            await transports[0].entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert clients[0].is_closed
        assert transports[0].close_loops == [asyncio.get_running_loop()]

    asyncio.run(scenario())


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_transport_retry_exhaustion_closes_every_attempt_client(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    transports, clients = _service(monkeypatch, provider, status=503)
    with pytest.raises(LlmError, match="llm_request_rejected") as caught:
        _analyst(provider, transport_retries=2).extract("fixture claim")
    assert caught.value.transport_attempts == 3
    assert len(transports) == len(clients) == 3
    assert all(client.is_closed for client in clients)
    for transport in transports:
        assert len(transport.requests) == 1, "SDK retries remain disabled"
        assert transport.close_loops == transport.request_loops


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_concurrent_async_calls_do_not_share_client_lifetimes(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    transports, clients = _service(monkeypatch, provider)
    analyst = _analyst(provider)

    async def scenario() -> None:
        results = await asyncio.gather(*(analyst.extract_async("fixture claim") for _ in range(3)))
        assert all(result.structure.claim == "fixture claim" for result in results)
        assert len(clients) == 3
        assert len({id(client) for client in clients}) == 3
        for transport, client in zip(transports, clients, strict=True):
            assert client.is_closed
            assert transport.close_loops == [asyncio.get_running_loop()]

    asyncio.run(scenario())
