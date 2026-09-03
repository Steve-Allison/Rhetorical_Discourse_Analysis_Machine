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

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import random
import time
from typing import Final, cast

from anthropic import AsyncAnthropic
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

    return os.environ.get(MODEL_ENV) or DEFAULT_MODEL


def _provider_of(model: str) -> str:
    return model.split(":", 1)[0] if ":" in model else "openai"


def load_dotenv(start: Path | None = None) -> None:
    """Populate missing API-key variables from the nearest ``.env``, without overwriting.

    One person on one machine keeps keys in a git-ignored ``.env`` (FR-028). Variables
    already present in the environment always win, so an explicit export overrides the
    file and nothing here can silently replace a deliberate setting.
    """

    directory = (start or Path.cwd()).resolve()
    wanted = set(_PROVIDER_KEY_ENV.values())
    for candidate in (directory, *directory.parents):
        env_file = candidate / ".env"
        if not env_file.is_file():
            continue
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip().removeprefix("export ").strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, _, raw = stripped.partition("=")
            name = name.strip()
            if name in wanted and name not in os.environ:
                os.environ[name] = raw.strip().strip("'\"")
        return


def unavailable_reason(model: str | None = None) -> UnavailableReason | None:
    """``None`` when the configured model can be called; a stable reason when it cannot.

    Side-effect-free by the capability contract: it resolves a key, and never opens a
    connection or sends a request.
    """

    resolved = model or configured_model()
    variable = _PROVIDER_KEY_ENV.get(_provider_of(resolved))
    if variable is None:
        return UnavailableReason.MODEL_UNAVAILABLE
    if not os.environ.get(variable):
        load_dotenv()
    return None if os.environ.get(variable) else UnavailableReason.MODEL_UNAVAILABLE


def _model_without_implicit_retries(model: str) -> Model:
    """Build a supported model whose SDK performs one HTTP attempt per agent request.

    ``StructuredAnalyst`` owns retries and evidence. Provider SDK defaults retry twice
    invisibly, which would violate that ownership and make attempt counts false.
    """

    load_dotenv()
    provider_name, separator, model_name = model.partition(":")
    if not separator or not model_name:
        raise ValueError("model identity must be '<provider>:<model>'")
    variable = _PROVIDER_KEY_ENV.get(provider_name)
    if variable is None or not (api_key := os.environ.get(variable)):
        raise ValueError(f"model provider {provider_name!r} is not configured")
    match provider_name:
        case "openai":
            client = AsyncOpenAI(api_key=api_key, max_retries=0)
            return OpenAIChatModel(
                cast(OpenAIModelName, model_name),
                provider=OpenAIProvider(openai_client=client),
            )
        case "anthropic":
            client = AsyncAnthropic(api_key=api_key, max_retries=0)
            return AnthropicModel(
                cast(AnthropicModelName, model_name),
                provider=AnthropicProvider(anthropic_client=client),
            )
        case "google" | "google-gla" | "google-vertex":
            from google.genai.types import HttpRetryOptions
            from pydantic_ai.models.google import GoogleModel, GoogleModelName
            from pydantic_ai.providers.google import GoogleProvider

            return GoogleModel(
                cast(GoogleModelName, model_name),
                provider=GoogleProvider(
                    api_key=api_key,
                    retry_options=HttpRetryOptions(attempts=1),
                ),
            )
        case _:
            raise ValueError(f"unsupported model provider {provider_name!r}")


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
        self._model = model or configured_model()
        self._output_type = output_type
        self._output_retries = output_retries
        self._transport_retries = transport_retries
        self._transport_deadline_seconds = transport_deadline_seconds
        self._instructions = instructions
        self._agent: Agent[None, StructureT] | None = None

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
        if self._agent is None:
            self._agent = Agent(
                _model_without_implicit_retries(self._model),
                output_type=self._output_type,
                instructions=self._instructions,
                retries=self._output_retries,
            )
        return self._agent

    def _run_sync(self, text: str) -> AgentRunResult[StructureT]:
        """One agent run. Kept as the causal external-boundary seam for tests."""

        return self._built().run_sync(text)

    def extract(self, text: str) -> Extraction[StructureT]:
        """Return the validated structure, or raise :class:`LlmError` with its class."""

        if not text.strip():
            raise LlmError("empty_source_text", Retryability.NOT_RETRYABLE, "no text to analyse")
        started = time.monotonic()
        transport_attempts = 0
        while True:
            transport_attempts += 1
            try:
                result = self._run_sync(text)
                break
            except UnexpectedModelBehavior as error:
                # Pydantic AI has spent the independent output-validation budget. Each
                # proposal required one successful transport request.
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
                    self._wait_before_retry(error.retry_after, transport_attempts, started)
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
                    self._wait_before_retry(None, transport_attempts, started)
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
        output_attempts = _request_count(result)
        return Extraction(
            structure=result.output,
            model=self._model,
            output_attempts=output_attempts,
            transport_attempts=transport_attempts - 1 + output_attempts,
        )

    def _wait_before_retry(self, retry_after: float | None, attempt: int, started: float) -> None:
        ceiling = min(_INITIAL_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)), _MAX_RETRY_DELAY_SECONDS)
        delay = retry_after if retry_after is not None else random.uniform(0.0, ceiling)
        if time.monotonic() - started + delay > self._transport_deadline_seconds:
            raise LlmError(
                "llm_transport_deadline_exceeded",
                Retryability.RETRYABLE,
                f"transport deadline {self._transport_deadline_seconds:g}s exhausted",
                transport_attempts=attempt,
            )
        time.sleep(delay)


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
    "StructuredAnalyst",
    "configured_model",
    "load_dotenv",
    "unavailable_reason",
]
