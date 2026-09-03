"""The machine's one LLM boundary: text in, a validated native structure out.

Four techniques — SDRT, Toulmin, Walton, PDTB — have no classical algorithm that
produces their native structure from raw text, and 006 FR-032 requires them anyway. They
share exactly one semantic contract: *propose a structure with a model, then accept it
only if this technique's own validator accepts it*. That is two proven callers and more,
with unambiguous ownership here, which is what FR-029 requires before a shared production
abstraction may exist.

**The model proposes; the formalism disposes.** Nothing here repairs, coerces, or
back-fills a malformed proposal. The model is asked for a structure typed by the
technique's own Pydantic contract; Pydantic AI validates it against that contract and, on
failure, re-asks the model with the validation error a bounded number of times. If it
still does not validate, that is a typed failure and the technique fails the request — it
never returns a half-structure dressed as an analysis.

**Retryability (006 capability contract §Transient-boundary retry standard).** This is
the machine's first transient boundary, so it is the first place that standard bites. The
two retry classes are kept separate and are never conflated:

- *structured-output validation retries* — the model returned something that is not a
  valid instance of the technique's contract. Bounded by ``output_retries``; Pydantic AI
  carries the validation error back to the model.
- *transport retries* — rate limits, 5xx, network. Bounded by ``transport_retries`` and
  owned by this boundary's explicit backoff/deadline loop; provider SDK retries are
  disabled so every HTTP attempt remains observable.

Every attempt count reaches the caller in the returned :class:`Extraction`, so a result
that retried shows its retries and an exhausted budget yields a typed failure carrying
the reason. Nothing retries silently.
"""

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import random
from threading import Lock
from typing import Final, cast

from anthropic import AsyncAnthropic
from dotenv import dotenv_values
from dotenv import load_dotenv as load_dotenv_file
from openai import AsyncOpenAI
from pydantic import BaseModel, NonNegativeInt
from pydantic_ai import Agent, AgentRunResult
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelName
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIModelName
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from rdam.contracts import Retryability, UnavailableReason

DEFAULT_MODEL: Final = "openai:gpt-5.6-sol"
"""The model the LLM-backed providers call unless ``RDAM_LLM_MODEL`` overrides it.

A Pydantic AI model string, so the provider is part of the identity: swapping to
``anthropic:claude-opus-5`` or ``google:gemini-2.5-pro`` is configuration, not a rewrite.
"""

MODEL_ENV: Final = "RDAM_LLM_MODEL"
DEFAULT_OUTPUT_RETRIES: Final = 2
DEFAULT_TRANSPORT_RETRIES: Final = 2
DEFAULT_TRANSPORT_DEADLINE_SECONDS: Final = 60.0
_INITIAL_RETRY_DELAY_SECONDS: Final = 0.25
_MAX_RETRY_DELAY_SECONDS: Final = 8.0

_PROVIDER_KEY_ENV: Final[Mapping[str, str]] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "google-gla": "GOOGLE_API_KEY",
    "google-vertex": "GOOGLE_API_KEY",
}


class ModelIdentityError(ValueError):
    """A configured identity is malformed or names an unsupported provider."""


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Canonical provider-qualified model identity."""

    provider: str
    model: str

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


def parse_model_identity(model: str) -> ModelIdentity:
    """Parse and normalize a supported identity; bare names mean OpenAI."""

    if not model or model != model.strip() or any(character.isspace() for character in model):
        raise ModelIdentityError("model identity must be a non-empty value without whitespace")
    provider, separator, model_name = model.partition(":")
    if not separator:
        provider, model_name = "openai", provider
    if provider not in _PROVIDER_KEY_ENV:
        raise ModelIdentityError(f"unsupported model provider {provider!r}")
    if not model_name or ":" in model_name:
        raise ModelIdentityError("model identity must be '<provider>:<model>' or a bare model name")
    return ModelIdentity(provider=provider, model=model_name)


def normalize_model_identity(model: str) -> str:
    """Return the provider-qualified canonical spelling of ``model``."""

    return str(parse_model_identity(model))


class LlmError(RuntimeError):
    """A typed failure at the LLM boundary, classified for the caller (never retried here)."""

    def __init__(
        self,
        code: str,
        retryability: Retryability,
        detail: str,
        *,
        output_attempts: NonNegativeInt = 0,
        transport_attempts: NonNegativeInt = 0,
    ) -> None:
        self.code = code
        self.retryability = retryability
        self.detail = detail
        self.output_attempts = output_attempts
        self.transport_attempts = transport_attempts
        super().__init__(f"{code}: {detail}")


def configured_model() -> str:
    """The model string in force: ``RDAM_LLM_MODEL`` if set, else :data:`DEFAULT_MODEL`."""

    configured = os.environ.get(MODEL_ENV) or DEFAULT_MODEL
    try:
        return normalize_model_identity(configured)
    except ModelIdentityError:
        return configured


def resolved_model_identity(model: str | None = None) -> str:
    """Normalize valid explicit/default configuration while retaining invalid input for capability reporting."""

    configured = configured_model() if model is None else model
    try:
        return normalize_model_identity(configured)
    except ModelIdentityError:
        return configured


def _nearest_dotenv(start: Path | None = None) -> Path | None:
    directory = (start or Path.cwd()).resolve()
    for candidate in (directory, *directory.parents):
        env_file = candidate / ".env"
        if env_file.is_file():
            return env_file
    return None


def load_dotenv(start: Path | None = None) -> None:
    """Populate missing API-key variables from the nearest ``.env``, without overwriting.

    One person on one machine keeps keys in a git-ignored ``.env`` (FR-028). Variables
    already present in the environment always win, so an explicit export overrides the
    file and nothing here can silently replace a deliberate setting.
    """

    if env_file := _nearest_dotenv(start):
        load_dotenv_file(env_file, override=False)


def unavailable_reason(model: str | None = None) -> UnavailableReason | None:
    """``None`` when the configured model can be called; a stable reason when it cannot.

    Side-effect-free by the capability contract: it resolves a key, and never opens a
    connection or sends a request.
    """

    resolved = configured_model() if model is None else model
    try:
        identity = parse_model_identity(resolved)
    except ModelIdentityError:
        return UnavailableReason.MODEL_UNAVAILABLE
    variable = _PROVIDER_KEY_ENV[identity.provider]
    if os.environ.get(variable):
        return None
    env_file = _nearest_dotenv()
    file_value = dotenv_values(env_file).get(variable) if env_file is not None else None
    return None if file_value else UnavailableReason.MODEL_UNAVAILABLE


def _model_without_implicit_retries(model: str, *, timeout_seconds: float) -> Model:
    """Build a supported model whose SDK performs one HTTP attempt per agent request.

    ``StructuredAnalyst`` owns retries and evidence. Provider SDK defaults retry twice
    invisibly, which would violate that ownership and make attempt counts false.
    """

    load_dotenv()
    identity = parse_model_identity(model)
    variable = _PROVIDER_KEY_ENV[identity.provider]
    if not (api_key := os.environ.get(variable)):
        raise ValueError(f"model provider {identity.provider!r} is not configured")
    match identity.provider:
        case "openai":
            client = AsyncOpenAI(api_key=api_key, max_retries=0, timeout=timeout_seconds)
            return OpenAIChatModel(
                cast(OpenAIModelName, identity.model),
                provider=OpenAIProvider(openai_client=client),
            )
        case "anthropic":
            client = AsyncAnthropic(api_key=api_key, max_retries=0, timeout=timeout_seconds)
            return AnthropicModel(
                cast(AnthropicModelName, identity.model),
                provider=AnthropicProvider(anthropic_client=client),
            )
        case "google" | "google-gla" | "google-vertex":
            from httpx2 import AsyncClient
            from google.genai.types import HttpRetryOptions
            from pydantic_ai.models.google import GoogleModel, GoogleModelName
            from pydantic_ai.providers.google import GoogleProvider

            return GoogleModel(
                cast(GoogleModelName, identity.model),
                provider=GoogleProvider(
                    api_key=api_key,
                    http_client=AsyncClient(timeout=timeout_seconds),
                    retry_options=HttpRetryOptions(attempts=1),
                ),
            )
        case _:
            raise AssertionError("model identity parser admitted an unsupported provider")


@dataclass(frozen=True, slots=True)
class Extraction[StructureT: BaseModel]:
    """One accepted proposal, with the identity and effort that produced it."""

    structure: StructureT
    model: str
    output_attempts: int
    transport_attempts: int


class StructuredAnalyst[StructureT: BaseModel]:
    """Asks one model for one technique's native structure, typed by that technique.

    ``output_type`` is the technique's own Pydantic contract, so a proposal that is not a
    well-formed instance of the formalism never reaches the provider. Constructing this
    object builds an agent; it does not call the model.
    """

    def __init__(
        self,
        *,
        output_type: type[StructureT],
        instructions: str,
        model: str | None = None,
        output_retries: int = DEFAULT_OUTPUT_RETRIES,
        transport_retries: int = DEFAULT_TRANSPORT_RETRIES,
        transport_deadline_seconds: float = DEFAULT_TRANSPORT_DEADLINE_SECONDS,
    ) -> None:
        if output_retries < 0 or transport_retries < 0:
            raise ValueError("retry counts must be non-negative")
        if transport_deadline_seconds <= 0:
            raise ValueError("transport deadline must be positive")
        self._model = resolved_model_identity(model)
        self._output_type = output_type
        self._output_retries = output_retries
        self._transport_retries = transport_retries
        self._transport_deadline_seconds = transport_deadline_seconds
        self._instructions = instructions
        self._agent: Agent[None, StructureT] | None = None
        self._agent_lock = Lock()

    @property
    def model(self) -> str:
        return self._model

    @property
    def agent(self) -> Agent[None, StructureT]:
        """The configured agent, built on first access.

        Public so tests can drive this boundary through Pydantic AI's own
        ``Agent.override(model=...)`` seam instead of reaching into privates. Building it
        opens no connection.
        """

        return self._built()

    def _built(self) -> Agent[None, StructureT]:
        if self._agent is not None:
            return self._agent
        with self._agent_lock:
            if self._agent is None:
                self._agent = Agent(
                    _model_without_implicit_retries(
                        self._model,
                        timeout_seconds=self._transport_deadline_seconds,
                    ),
                    output_type=self._output_type,
                    instructions=self._instructions,
                    retries=self._output_retries,
                )
        return self._agent

    async def _run(self, text: str) -> AgentRunResult[StructureT]:
        """One agent run. Kept as the causal external-boundary seam for tests."""

        return await self._built().run(text)

    def extract(self, text: str) -> Extraction[StructureT]:
        """Return the validated structure, or raise :class:`LlmError` with its class."""

        return asyncio.run(self.extract_async(text))

    async def extract_async(self, text: str) -> Extraction[StructureT]:
        """Async extraction under one deadline covering requests, validation, and retries."""

        if not text.strip():
            raise LlmError("empty_source_text", Retryability.NOT_RETRYABLE, "no text to analyse")
        transport_attempts = 0
        try:
            async with asyncio.timeout(self._transport_deadline_seconds):
                while True:
                    transport_attempts += 1
                    try:
                        result = await self._run(text)
                        break
                    except UnexpectedModelBehavior as error:
                        output_attempts = self._output_retries + 1
                        raise LlmError(
                            "llm_output_failed_validation",
                            Retryability.NOT_RETRYABLE,
                            f"no valid {self._output_type.__name__} in {output_attempts} attempts: {error}",
                            output_attempts=output_attempts,
                            transport_attempts=transport_attempts - 1 + output_attempts,
                        ) from error
                    except ModelHTTPError as error:
                        retryable = error.status_code in {408, 409, 429} or error.status_code >= 500
                        if retryable and transport_attempts <= self._transport_retries:
                            await self._wait_before_retry(error.retry_after, transport_attempts)
                            continue
                        raise LlmError(
                            "llm_request_rejected",
                            Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
                            f"HTTP {error.status_code}",
                            transport_attempts=transport_attempts,
                        ) from error
                    except UsageLimitExceeded as error:
                        raise LlmError(
                            "llm_usage_limit_exceeded",
                            Retryability.NOT_RETRYABLE,
                            str(error),
                            transport_attempts=transport_attempts,
                        ) from error
                    except ModelAPIError as error:
                        if transport_attempts <= self._transport_retries:
                            await self._wait_before_retry(None, transport_attempts)
                            continue
                        raise LlmError(
                            "llm_transport_failed",
                            Retryability.RETRYABLE,
                            str(error),
                            transport_attempts=transport_attempts,
                        ) from error
                    except AgentRunError as error:
                        raise LlmError(
                            "llm_run_failed",
                            Retryability.UNKNOWN,
                            str(error),
                            transport_attempts=transport_attempts,
                        ) from error
        except TimeoutError as error:
            raise LlmError(
                "llm_transport_deadline_exceeded",
                Retryability.RETRYABLE,
                f"transport deadline {self._transport_deadline_seconds:g}s exhausted",
                transport_attempts=transport_attempts,
            ) from error
        output_attempts = _request_count(result)
        return Extraction(
            structure=result.output,
            model=self._model,
            output_attempts=output_attempts,
            transport_attempts=transport_attempts - 1 + output_attempts,
        )

    async def _wait_before_retry(self, retry_after: float | None, attempt: int) -> None:
        ceiling = min(_INITIAL_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)), _MAX_RETRY_DELAY_SECONDS)
        delay = retry_after if retry_after is not None else random.uniform(0.0, ceiling)
        await asyncio.sleep(delay)


def _request_count(result: object) -> int:
    """How many model requests the run actually made, from Pydantic AI's own usage record."""

    usage = getattr(result, "usage", None)
    requests = getattr(usage() if callable(usage) else usage, "requests", None)
    return requests if isinstance(requests, int) and requests > 0 else 1


__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_OUTPUT_RETRIES",
    "DEFAULT_TRANSPORT_DEADLINE_SECONDS",
    "DEFAULT_TRANSPORT_RETRIES",
    "MODEL_ENV",
    "Extraction",
    "LlmError",
    "ModelIdentity",
    "ModelIdentityError",
    "StructuredAnalyst",
    "configured_model",
    "load_dotenv",
    "normalize_model_identity",
    "parse_model_identity",
    "resolved_model_identity",
    "unavailable_reason",
]
