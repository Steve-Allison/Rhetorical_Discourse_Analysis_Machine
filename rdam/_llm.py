"""The machine's one LLM boundary: text in, a validated native structure out.

Ten techniques share one semantic contract: *propose a structure with a model, then accept
it only if this technique's own deterministic validator accepts it*.

**The model proposes; the formalism disposes.** Nothing here repairs, coerces, or
back-fills a malformed proposal. The model is asked for a structure typed by the
technique's own Pydantic contract; Pydantic AI validates it against that contract and, on
failure, re-asks the model with the validation error a bounded number of times. If it
still does not validate, that is a typed failure and the technique fails the request — it
never returns a half-structure dressed as an analysis.

**Shared-prefix KV caching.** When ``use_shared_constitution=True``, every LLM technique
shares the byte-identical :func:`load_shared_system_prompt` system instruction and places
the canonical ``<source_document>`` + ``<linguistic_signals>`` prefix before a Pydantic AI
``CachePoint`` in the user prompt, followed by ``<technique_task>``. Anthropic emits an
ephemeral ``cache_control`` breakpoint at ``CachePoint``, OpenAI receives
``openai_prompt_cache_key``, and Gemini ``v1/interactions`` caches the identical prefix
automatically (`store=False`).
"""

import asyncio
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
import json
from math import isfinite
import os
from pathlib import Path
import random
import sys
from threading import Event, Lock
from typing import Any, Final, Literal, cast

from dotenv import dotenv_values
from dotenv import load_dotenv as load_dotenv_file
from pydantic import BaseModel, NonNegativeInt
import pydantic_ai
from pydantic_ai import Agent, AgentRunResult, ModelRequestContext, ModelRetry, RunContext
from pydantic_ai.capabilities import AbstractCapability, WrapModelRequestHandler
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import (
    CachePoint,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponsePart,
    RetryFeedbackPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RequestUsage

from rdam.contracts import Retryability, UnavailableReason
from rdam.ingest.contracts.evidence import SourceEvidenceSpan

# rdam owns its terminal output; Pydantic AI's first-run banner must not appear on it.
pydantic_ai.BANNER_ENABLED = False

DEFAULT_MODEL: Final = "openai:gpt-5.6-sol"
"""The model the LLM-backed providers call unless ``RDAM_LLM_MODEL`` overrides it."""

MODEL_ENV: Final = "RDAM_LLM_MODEL"
DEFAULT_OUTPUT_RETRIES: Final = 2
DEFAULT_TRANSPORT_RETRIES: Final = 2
# Verified equal to `openai.DEFAULT_TIMEOUT.read` (600.0s) without importing `openai` at cold start.
DEFAULT_TRANSPORT_DEADLINE_SECONDS: Final[float] = 600.0
_INITIAL_RETRY_DELAY_SECONDS: Final = 0.25
_MAX_RETRY_DELAY_SECONDS: Final = 8.0

_PROVIDER_CREDENTIAL_ENVS: Final[Mapping[str, tuple[str, ...]]] = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "google": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "google-gla": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "google-vertex": ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "CLOUD_ML_PROJECT_ID"),
}

type ThinkingLevelLiteral = Literal["minimal", "low", "medium", "high"]


def __getattr__(name: str) -> Any:
    """Lazily expose SDK client classes so cold-start stays fast while monkeypatching works."""
    if name == "AsyncOpenAI":
        from openai import AsyncOpenAI as _AsyncOpenAI

        return _AsyncOpenAI
    if name == "AsyncAnthropic":
        from anthropic import AsyncAnthropic as _AsyncAnthropic

        return _AsyncAnthropic
    if name == "AsyncClient":
        from httpx2 import AsyncClient as _AsyncClient

        return _AsyncClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _sdk_attr(name: str) -> Any:
    return getattr(sys.modules[__name__], name)


@cache
def load_shared_system_prompt() -> str:
    """Load the shared analytical constitution cached across all LLM-backed providers."""
    return files("rdam.resources").joinpath("shared-system-prompt.md").read_text(encoding="utf-8").strip()


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
    if provider not in _PROVIDER_CREDENTIAL_ENVS:
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
    """Populate missing API-key variables from the nearest ``.env``, without overwriting."""

    if env_file := _nearest_dotenv(start):
        load_dotenv_file(env_file, override=False)


def unavailable_reason(model: str | None = None) -> UnavailableReason | None:
    """``None`` when the configured model can be called; a stable reason when it cannot."""

    resolved = configured_model() if model is None else model
    try:
        identity = parse_model_identity(resolved)
    except ModelIdentityError:
        return UnavailableReason.MODEL_UNAVAILABLE
    candidates = _PROVIDER_CREDENTIAL_ENVS[identity.provider]
    if any(os.environ.get(variable) for variable in candidates):
        return None
    env_file = _nearest_dotenv()
    if env_file is not None:
        values = dotenv_values(env_file)
        if any(values.get(variable) for variable in candidates):
            return None
    return UnavailableReason.MODEL_UNAVAILABLE


def _uses_thinking_level(model_name: str) -> bool:
    lowered = model_name.lower()
    return lowered.startswith(("gemini-3", "gemini-4"))


def _render_user_part_text(content: str | Sequence[object]) -> str:
    if isinstance(content, str):
        return content
    chunks: list[str] = []
    for item in content:
        if isinstance(item, str):
            chunks.append(item)
        else:
            text_attr = getattr(item, "content", None)
            if isinstance(text_attr, str):
                chunks.append(text_attr)
    return "\n\n".join(chunk for chunk in chunks if chunk)


class _GoogleInteractionsModel(Model):
    """Pydantic AI ``Model`` backed by ``google-genai`` GA ``v1/interactions``."""

    def __init__(
        self,
        aclient: Any,
        *,
        model_name: str,
        system_name: str = "google",
        thinking_level: ThinkingLevelLiteral = "medium",
    ) -> None:
        super().__init__(
            profile=ModelProfile(
                supports_json_schema_output=True,
                supports_json_object_output=True,
                default_structured_output_mode="native",
            )
        )
        self._aclient = aclient
        self._model_name = model_name
        self._system_name = system_name
        self._thinking_level: ThinkingLevelLiteral = thinking_level

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def system(self) -> str:
        return self._system_name

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        from google.genai._interactions import APIError as InteractionsAPIError
        from google.genai._interactions import APIStatusError as InteractionsAPIStatusError
        from google.genai.errors import APIError as GenAIClientAPIError
        from pydantic_ai._instrumentation import get_instructions

        prepared_settings, params = self.prepare_request(model_settings, model_request_parameters)
        instructions = get_instructions(messages, params)
        steps: list[dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, ModelRequest):
                user_texts: list[str] = []
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        rendered = _render_user_part_text(part.content)
                        if rendered:
                            user_texts.append(rendered)
                    elif isinstance(part, RetryFeedbackPart):
                        user_texts.append(part.model_response())
                    elif isinstance(part, ToolReturnPart):
                        steps.append(
                            {
                                "type": "function_result",
                                "call_id": part.tool_call_id,
                                "name": part.tool_name,
                                "result": part.model_response_str(),
                            }
                        )
                    elif getattr(part, "part_kind", None) == "retry-prompt":
                        legacy_resp = getattr(part, "model_response", None)
                        if callable(legacy_resp):
                            user_texts.append(str(legacy_resp()))
                if user_texts:
                    steps.append(
                        {
                            "type": "user_input",
                            "content": [{"type": "text", "text": "\n\n".join(user_texts)}],
                        }
                    )
            else:
                model_texts = [p.content for p in msg.parts if isinstance(p, TextPart) and p.content]
                if model_texts:
                    steps.append(
                        {
                            "type": "model_output",
                            "content": [{"type": "text", "text": "".join(model_texts)}],
                        }
                    )
                steps.extend(
                    {
                        "type": "function_call",
                        "id": part.tool_call_id,
                        "name": part.tool_name,
                        "arguments": part.args_as_dict(),
                    }
                    for part in msg.parts
                    if isinstance(part, ToolCallPart)
                )

        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "store": False,
            "input": steps,
        }
        if instructions:
            kwargs["system_instruction"] = instructions
        if params.output_object is not None:
            kwargs["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": params.output_object.json_schema,
            }
        if params.function_tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.parameters_json_schema,
                }
                for tool in params.function_tools
            ]

        gen_cfg: dict[str, Any] = {}
        if _uses_thinking_level(self._model_name):
            gen_cfg["thinking_level"] = self._thinking_level
        elif prepared_settings and "temperature" in prepared_settings:
            gen_cfg["temperature"] = prepared_settings["temperature"]
        if prepared_settings and "max_tokens" in prepared_settings:
            gen_cfg["max_output_tokens"] = prepared_settings["max_tokens"]
        if gen_cfg:
            kwargs["generation_config"] = gen_cfg

        try:
            interaction = await self._aclient.interactions.create(**kwargs)
        except InteractionsAPIStatusError as error:
            raw_resp: Any = getattr(error, "response", None)
            headers: dict[str, str] | None = (
                {str(k): str(v) for k, v in raw_resp.headers.items()} if raw_resp is not None else None
            )
            status_code = error.status_code if error.status_code is not None else 500
            raise ModelHTTPError(
                status_code=status_code,
                model_name=self._model_name,
                body=error.body,
                headers=headers,
            ) from error
        except (InteractionsAPIError, GenAIClientAPIError) as error:
            code = getattr(error, "code", None)
            if isinstance(code, int) and 400 <= code < 600:
                raise ModelHTTPError(
                    status_code=code,
                    model_name=self._model_name,
                    body=getattr(error, "details", str(error)),
                ) from error
            raise ModelAPIError(model_name=self._model_name, message=str(error)) from error

        response_parts: list[ModelResponsePart] = []
        for step in interaction.steps or ():
            step_type = getattr(step, "type", None)
            if step_type == "thought":
                summary_items = getattr(step, "summary", None) or ()
                summary_text = "".join(
                    getattr(item, "text", "")
                    for item in summary_items
                    if getattr(item, "type", None) == "text"
                )
                signature = getattr(step, "signature", None)
                if summary_text or signature:
                    response_parts.append(
                        ThinkingPart(
                            content=summary_text,
                            signature=signature,
                            provider_name=self._system_name if signature else None,
                        )
                    )
            elif step_type == "function_call":
                raw_args: Any = getattr(step, "arguments", None)
                args_payload: dict[str, Any] | str
                if isinstance(raw_args, dict):
                    args_payload = cast(dict[str, Any], raw_args)
                elif isinstance(raw_args, str):
                    args_payload = raw_args
                else:
                    args_payload = json.dumps(raw_args or {})
                response_parts.append(
                    ToolCallPart(
                        tool_name=str(getattr(step, "name", "")),
                        args=args_payload,
                        tool_call_id=str(getattr(step, "id", "") or "call_0"),
                    )
                )

        output_text = getattr(interaction, "output_text", None)
        if isinstance(output_text, str) and output_text:
            response_parts.append(TextPart(content=output_text))

        usage_obj = getattr(interaction, "usage", None)
        if usage_obj is not None:
            input_tokens = int(getattr(usage_obj, "total_input_tokens", 0) or 0)
            cached_tokens = int(getattr(usage_obj, "total_cached_tokens", 0) or 0)
            output_tokens = int(getattr(usage_obj, "total_output_tokens", 0) or 0)
            thought_tokens = int(getattr(usage_obj, "total_thought_tokens", 0) or 0)
            req_usage = RequestUsage(
                input_tokens=max(input_tokens, cached_tokens),
                cache_read_tokens=cached_tokens,
                output_tokens=output_tokens + thought_tokens,
                output_reasoning_tokens=thought_tokens,
            )
        else:
            req_usage = RequestUsage()

        return ModelResponse(
            parts=response_parts,
            model_name=self._model_name,
            provider_name=self._system_name,
            provider_response_id=getattr(interaction, "id", None) or None,
            usage=req_usage,
        )


@asynccontextmanager
async def _model_without_implicit_retries(
    model: str,
    *,
    timeout_seconds: float,
    thinking_level: ThinkingLevelLiteral = "medium",
) -> AsyncGenerator[Model]:
    """Build a supported model whose SDK performs one HTTP attempt per agent request."""

    load_dotenv()
    identity = parse_model_identity(model)
    match identity.provider:
        case "openai":
            if not (api_key := os.environ.get("OPENAI_API_KEY")):
                raise ValueError("model provider 'openai' is not configured")
            from pydantic_ai.models.openai import OpenAIModelName, OpenAIResponsesModel
            from pydantic_ai.providers.openai import OpenAIProvider

            openai_cls = _sdk_attr("AsyncOpenAI")
            async with openai_cls(api_key=api_key, max_retries=0, timeout=timeout_seconds) as client:
                yield OpenAIResponsesModel(
                    cast(OpenAIModelName, identity.model),
                    provider=OpenAIProvider(openai_client=client),
                )
        case "anthropic":
            if not (api_key := os.environ.get("ANTHROPIC_API_KEY")):
                raise ValueError("model provider 'anthropic' is not configured")
            from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelName
            from pydantic_ai.providers.anthropic import AnthropicProvider

            anthropic_cls = _sdk_attr("AsyncAnthropic")
            async with anthropic_cls(api_key=api_key, max_retries=0, timeout=timeout_seconds) as client:
                yield AnthropicModel(
                    cast(AnthropicModelName, identity.model),
                    provider=AnthropicProvider(anthropic_client=client),
                )
        case "google" | "google-gla":
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(f"model provider {identity.provider!r} is not configured")
            import google.genai as genai
            from google.genai.types import HttpOptions, HttpRetryOptions

            http_cls = _sdk_attr("AsyncClient")
            async with http_cls(timeout=timeout_seconds) as http_client:
                gclient = genai.Client(
                    api_key=api_key,
                    http_options=HttpOptions(
                        httpx_async_client=http_client,
                        retry_options=HttpRetryOptions(attempts=1),
                    ),
                )
                with gclient:
                    async with gclient.aio as aclient:
                        yield _GoogleInteractionsModel(
                            aclient,
                            model_name=identity.model,
                            system_name="google",
                            thinking_level=thinking_level,
                        )
        case "google-vertex":
            project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("CLOUD_ML_PROJECT_ID")
            api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            if not project and not api_key:
                raise ValueError("model provider 'google-vertex' is not configured")
            import google.genai as genai
            from google.genai.types import HttpOptions, HttpRetryOptions

            http_cls = _sdk_attr("AsyncClient")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
            async with http_cls(timeout=timeout_seconds) as http_client:
                client_kwargs: dict[str, Any] = {
                    "vertexai": True,
                    "http_options": HttpOptions(
                        httpx_async_client=http_client,
                        retry_options=HttpRetryOptions(attempts=1),
                    ),
                }
                if project:
                    client_kwargs["project"] = project
                    client_kwargs["location"] = location
                elif api_key:
                    client_kwargs["api_key"] = api_key
                gclient = genai.Client(**client_kwargs)
                with gclient:
                    async with gclient.aio as aclient:
                        yield _GoogleInteractionsModel(
                            aclient,
                            model_name=identity.model,
                            system_name="google-vertex",
                            thinking_level=thinking_level,
                        )
        case _:
            raise AssertionError("model identity parser admitted an unsupported provider")


def source_locations(context: RunContext[str], quotations: list[str]) -> dict[str, tuple[SourceEvidenceSpan, ...]]:
    """Locate each nonempty quotation literally in the source, retaining all ambiguous occurrences."""
    locations: dict[str, tuple[SourceEvidenceSpan, ...]] = {}
    for quotation in quotations:
        matches: list[SourceEvidenceSpan] = []
        if quotation:
            start = context.deps.find(quotation)
            while start >= 0:
                matches.append(SourceEvidenceSpan(start=start, end=start + len(quotation), text=quotation))
                start = context.deps.find(quotation, start + 1)
        locations[quotation] = tuple(matches)
    return locations


@dataclass(frozen=True, slots=True)
class PromptPayload:
    """Shared-prefix KV-cached prompt envelope paired with verbatim ``PreparedDocument.text``."""

    source_text: str
    cached_prefix: str
    task_prompt: str = ""
    cache_key: str | None = None


class PrefixWarmthCoordinator:
    """Coordinate concurrent multi-technique LLM calls so the first request warms the shared KV prefix."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._states: dict[tuple[str, str], tuple[Event, bool]] = {}

    def enter(self, model: str, cache_key: str | None) -> tuple[bool, Event | None]:
        if not cache_key:
            return True, None
        key = (model, cache_key)
        with self._lock:
            existing = self._states.get(key)
            if existing is None:
                event = Event()
                if len(self._states) >= 256:
                    self._states.clear()
                self._states[key] = (event, False)
                return True, event
            event, warmed = existing
            return warmed, None if warmed else event

    def complete(self, model: str, cache_key: str | None) -> None:
        if not cache_key:
            return
        key = (model, cache_key)
        with self._lock:
            existing = self._states.get(key)
            if existing is not None:
                event, _ = existing
                self._states[key] = (event, True)
                event.set()


PREFIX_WARMTH_COORDINATOR: Final = PrefixWarmthCoordinator()


@dataclass(frozen=True, slots=True)
class Extraction[StructureT: BaseModel]:
    """One accepted proposal, with the identity, cache telemetry, and effort that produced it."""

    structure: StructureT
    model: str
    output_attempts: int
    transport_attempts: int
    cached_input_tokens: int = 0


@dataclass
class _AttemptEvidence(AbstractCapability[str]):
    """One extraction's observed requests, including its validation and transport retries."""

    output_attempts: int = 0
    transport_attempts: int = 0
    cached_input_tokens: int = 0

    async def wrap_model_request(
        self,
        ctx: RunContext[str],
        *,
        request_context: ModelRequestContext,
        handler: WrapModelRequestHandler,
    ) -> ModelResponse:
        self.transport_attempts += 1
        try:
            response = await handler(request_context)
        except UnexpectedModelBehavior:
            self.output_attempts += 1
            raise
        self.cached_input_tokens += int(getattr(response.usage, "cache_read_tokens", 0) or 0)
        function_names = {tool.name for tool in request_context.model_request_parameters.function_tools}
        calls = [part for part in response.parts if isinstance(part, ToolCallPart)]
        if not calls or any(call.tool_name not in function_names for call in calls):
            self.output_attempts += 1
        return response


def _has_model_override(agent: Agent[Any, Any]) -> bool:
    override_var: Any = getattr(agent, "_override_model", None)
    return override_var is not None and override_var.get() is not None


class StructuredAnalyst[StructureT: BaseModel]:
    """Asks one model for one technique's native structure, typed by that technique."""

    def __init__(
        self,
        *,
        output_type: type[StructureT],
        instructions: str,
        model: str | None = None,
        output_retries: int = DEFAULT_OUTPUT_RETRIES,
        transport_retries: int = DEFAULT_TRANSPORT_RETRIES,
        transport_deadline_seconds: float = DEFAULT_TRANSPORT_DEADLINE_SECONDS,
        source_validator: Callable[[StructureT, str], object] | None = None,
        use_shared_constitution: bool = False,
        thinking_level: ThinkingLevelLiteral = "medium",
    ) -> None:
        if type(output_retries) is not int or type(transport_retries) is not int or output_retries < 0 or transport_retries < 0:
            raise ValueError("retry counts must be non-negative")
        if isinstance(transport_deadline_seconds, bool) or not isfinite(transport_deadline_seconds) or transport_deadline_seconds <= 0:
            raise ValueError("transport deadline must be positive")
        self._model = resolved_model_identity(model)
        self._output_type = output_type
        self._output_retries = output_retries
        self._transport_retries = transport_retries
        self._transport_deadline_seconds = transport_deadline_seconds
        self._instructions = instructions
        self._source_validator = source_validator
        self._use_shared_constitution = use_shared_constitution
        self._thinking_level: ThinkingLevelLiteral = thinking_level
        self._agent: Agent[str, StructureT] | None = None
        self._agent_lock = Lock()

    @property
    def model(self) -> str:
        return self._model

    @property
    def effective_instructions(self) -> str:
        if self._use_shared_constitution:
            return f"{load_shared_system_prompt()}\n\n{self._instructions}"
        return self._instructions

    @property
    def agent(self) -> Agent[str, StructureT]:
        """The configured agent, built on first access."""
        return self._built()

    def _built(self) -> Agent[str, StructureT]:
        if self._agent is not None:
            return self._agent
        with self._agent_lock:
            if self._agent is None:
                system_text = load_shared_system_prompt() if self._use_shared_constitution else self._instructions
                self._agent = Agent(
                    output_type=self._output_type,
                    deps_type=str,
                    instructions=system_text,
                    retries=self._output_retries,
                )
                self._agent.output_validator(self._validate_output)
        return self._agent

    def _validate_output(self, context: RunContext[str], output: StructureT) -> StructureT:
        if self._source_validator is not None:
            try:
                self._source_validator(output, context.deps)
            except ValueError as error:
                raise ModelRetry(
                    "Source evidence must match the exact input text and declared character offsets. "
                    f"{error}"
                ) from error
        return output

    def _build_user_prompt(
        self,
        payload: str | PromptPayload,
    ) -> tuple[str | Sequence[Any], str, ModelSettings | None]:
        if isinstance(payload, str):
            if self._use_shared_constitution:
                prompt_str = (
                    f"<source_document>\n{payload}\n</source_document>\n\n"
                    f"<technique_task>\n{self._instructions}\n</technique_task>"
                )
                return prompt_str, payload, None
            return payload, payload, None

        task_parts = [self._instructions] if self._use_shared_constitution else []
        if payload.task_prompt:
            task_parts.append(payload.task_prompt)
        suffix = (
            f"<technique_task>\n{'\n\n'.join(task_parts)}\n</technique_task>"
            if task_parts
            else "Analyse the document."
        )
        user_content: list[Any] = [payload.cached_prefix, CachePoint(), suffix]
        settings: ModelSettings | None = None
        if payload.cache_key and self._model.startswith("openai:"):
            settings = cast(ModelSettings, {"openai_prompt_cache_key": payload.cache_key})
        return user_content, payload.source_text, settings

    async def _run(
        self,
        user_prompt: str | Sequence[Any],
        deps_text: str,
        model_settings: ModelSettings | None,
        evidence: _AttemptEvidence,
    ) -> AgentRunResult[StructureT]:
        """One agent run with extraction-local observation of every model request."""
        agent = self._built()
        if _has_model_override(agent):
            return await agent.run(
                user_prompt,
                deps=deps_text,
                model_settings=model_settings,
                capabilities=[evidence],
            )
        context_factory = (
            _model_without_implicit_retries(
                self._model,
                timeout_seconds=self._transport_deadline_seconds,
            )
            if self._thinking_level == "medium"
            else _model_without_implicit_retries(
                self._model,
                timeout_seconds=self._transport_deadline_seconds,
                thinking_level=self._thinking_level,
            )
        )
        async with context_factory as model:
            return await agent.run(
                user_prompt,
                deps=deps_text,
                model=model,
                model_settings=model_settings,
                capabilities=[evidence],
            )

    def extract(self, text: str) -> Extraction[StructureT]:
        """Return the validated structure, or raise :class:`LlmError` with its class."""
        return asyncio.run(self.extract_async(text))

    def extract_prompt(self, payload: PromptPayload) -> Extraction[StructureT]:
        """Extract using a shared KV-cached ``PromptPayload`` coordinated across techniques."""
        is_leader, wait_event = PREFIX_WARMTH_COORDINATOR.enter(self._model, payload.cache_key)
        if not is_leader and wait_event is not None:
            wait_event.wait(timeout=min(15.0, self._transport_deadline_seconds / 4))
        try:
            return asyncio.run(self.extract_prompt_async(payload))
        finally:
            if is_leader:
                PREFIX_WARMTH_COORDINATOR.complete(self._model, payload.cache_key)

    async def extract_prompt_async(self, payload: PromptPayload) -> Extraction[StructureT]:
        return await self._extract_impl(payload)

    async def extract_async(self, text: str) -> Extraction[StructureT]:
        """Async extraction under one deadline covering requests, validation, and retries."""
        return await self._extract_impl(text)

    async def _extract_impl(self, payload: str | PromptPayload) -> Extraction[StructureT]:
        source_text = payload if isinstance(payload, str) else payload.source_text
        if not source_text.strip():
            raise LlmError("empty_source_text", Retryability.NOT_RETRYABLE, "no text to analyse")
        user_prompt, deps_text, model_settings = self._build_user_prompt(payload)
        evidence = _AttemptEvidence()
        transport_runs = 0
        try:
            async with asyncio.timeout(self._transport_deadline_seconds):
                while True:
                    transport_runs += 1
                    try:
                        result = await self._run(user_prompt, deps_text, model_settings, evidence)
                        break
                    except UnexpectedModelBehavior as error:
                        raise LlmError(
                            "llm_output_failed_validation",
                            Retryability.NOT_RETRYABLE,
                            f"no valid {self._output_type.__name__} in {evidence.output_attempts} attempts: {error}",
                            output_attempts=evidence.output_attempts,
                            transport_attempts=evidence.transport_attempts,
                        ) from error
                    except ModelHTTPError as error:
                        retryable = error.status_code in {408, 409, 429} or error.status_code >= 500
                        if retryable and transport_runs <= self._transport_retries:
                            await self._wait_before_retry(error.retry_after, transport_runs)
                            continue
                        raise LlmError(
                            "llm_request_rejected",
                            Retryability.RETRYABLE if retryable else Retryability.NOT_RETRYABLE,
                            f"HTTP {error.status_code}",
                            output_attempts=evidence.output_attempts,
                            transport_attempts=evidence.transport_attempts,
                        ) from error
                    except UsageLimitExceeded as error:
                        raise LlmError(
                            "llm_usage_limit_exceeded",
                            Retryability.NOT_RETRYABLE,
                            str(error),
                            output_attempts=evidence.output_attempts,
                            transport_attempts=evidence.transport_attempts,
                        ) from error
                    except ModelAPIError as error:
                        if transport_runs <= self._transport_retries:
                            await self._wait_before_retry(None, transport_runs)
                            continue
                        raise LlmError(
                            "llm_transport_failed",
                            Retryability.RETRYABLE,
                            str(error),
                            output_attempts=evidence.output_attempts,
                            transport_attempts=evidence.transport_attempts,
                        ) from error
                    except AgentRunError as error:
                        raise LlmError(
                            "llm_run_failed",
                            Retryability.UNKNOWN,
                            str(error),
                            output_attempts=evidence.output_attempts,
                            transport_attempts=evidence.transport_attempts,
                        ) from error
        except TimeoutError as error:
            raise LlmError(
                "llm_transport_deadline_exceeded",
                Retryability.RETRYABLE,
                f"transport deadline {self._transport_deadline_seconds:g}s exhausted",
                output_attempts=evidence.output_attempts,
                transport_attempts=evidence.transport_attempts,
            ) from error
        return Extraction(
            structure=result.output,
            model=self._model,
            output_attempts=evidence.output_attempts,
            transport_attempts=evidence.transport_attempts,
            cached_input_tokens=evidence.cached_input_tokens,
        )

    async def _wait_before_retry(self, retry_after: float | None, attempt: int) -> None:
        ceiling = min(_INITIAL_RETRY_DELAY_SECONDS * (2 ** (attempt - 1)), _MAX_RETRY_DELAY_SECONDS)
        delay = retry_after if retry_after is not None else random.uniform(0.0, ceiling)
        await asyncio.sleep(delay)


__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_OUTPUT_RETRIES",
    "DEFAULT_TRANSPORT_DEADLINE_SECONDS",
    "DEFAULT_TRANSPORT_RETRIES",
    "MODEL_ENV",
    "PREFIX_WARMTH_COORDINATOR",
    "Extraction",
    "LlmError",
    "ModelIdentity",
    "ModelIdentityError",
    "PrefixWarmthCoordinator",
    "PromptPayload",
    "StructuredAnalyst",
    "_GoogleInteractionsModel",
    "configured_model",
    "load_dotenv",
    "load_shared_system_prompt",
    "normalize_model_identity",
    "parse_model_identity",
    "resolved_model_identity",
    "unavailable_reason",
]
