"""The machine's one LLM boundary: key resolution, capability, and the failure algebra.

The model is the one legitimate mock target under the project's test-honesty rule — it is
a genuinely external system. Every model here is a Pydantic AI ``FunctionModel``, so the
structure the boundary receives is chosen by the test, not by a live model.
"""

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai.exceptions import (
    AgentRunError,
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
import pytest

from rdam import Retryability, UnavailableReason
from rdam._llm import (
    DEFAULT_MODEL,
    MODEL_ENV,
    LlmError,
    StructuredAnalyst,
    configured_model,
    load_dotenv,
    unavailable_reason,
)


class Finding(BaseModel):
    claim: str = Field(description="the claim")


def _returning(**arguments: object):
    """A model that always proposes the given structure."""

    def behaviour(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        assert info.output_tools, "the boundary always asks for a typed structure"
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=dict(arguments))])

    return FunctionModel(behaviour)


def _raising(error: Exception):
    def behaviour(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise error

    return FunctionModel(behaviour)


def _analyst() -> StructuredAnalyst[Finding]:
    return StructuredAnalyst(output_type=Finding, instructions="find the claim", model="openai:test")


class TestModelConfiguration:
    def test_the_default_model_is_used_when_nothing_overrides_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(MODEL_ENV, raising=False)
        assert configured_model() == DEFAULT_MODEL

    def test_the_environment_overrides_the_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(MODEL_ENV, "anthropic:claude-opus-5")
        assert configured_model() == "anthropic:claude-opus-5"

    def test_the_model_string_carries_its_provider(self) -> None:
        assert DEFAULT_MODEL.startswith("openai:"), "provider is part of the model identity"


class TestCapability:
    """Capability resolves a key. It never opens a connection."""

    def test_available_when_the_provider_key_is_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        assert unavailable_reason("openai:gpt-5.6-sol") is None

    def test_each_provider_reads_its_own_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_a, **_k: None)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
        assert unavailable_reason("anthropic:claude-opus-5") is None
        assert unavailable_reason("openai:gpt-5.6-sol") is UnavailableReason.MODEL_UNAVAILABLE

    def test_model_unavailable_when_no_key_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_a, **_k: None)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert unavailable_reason("openai:gpt-5.6-sol") is UnavailableReason.MODEL_UNAVAILABLE

    def test_an_unknown_provider_is_model_unavailable_not_a_crash(self) -> None:
        assert unavailable_reason("nosuchvendor:whatever") is UnavailableReason.MODEL_UNAVAILABLE

    def test_a_bare_model_name_is_treated_as_openai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "k")
        assert unavailable_reason("gpt-5.6-sol") is None


class TestDotEnv:
    def test_keys_are_read_from_a_dotenv_beside_the_working_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".env").write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        load_dotenv(tmp_path)
        import os

        assert os.environ["OPENAI_API_KEY"] == "from-file"

    def test_an_explicit_environment_variable_always_wins(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / ".env").write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
        monkeypatch.setenv("OPENAI_API_KEY", "explicit")
        load_dotenv(tmp_path)
        import os

        assert os.environ["OPENAI_API_KEY"] == "explicit", "a deliberate export is never silently replaced"

    def test_comments_blanks_exports_and_quotes_are_handled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / ".env").write_text(
            '\n# a comment\nexport ANTHROPIC_API_KEY="quoted-value"\n\nNOT_A_KEY=ignored\n', encoding="utf-8"
        )
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        load_dotenv(tmp_path)
        import os

        assert os.environ["ANTHROPIC_API_KEY"] == "quoted-value"

    def test_a_dotenv_further_up_the_tree_is_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / ".env").write_text("GOOGLE_API_KEY=up-there\n", encoding="utf-8")
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        load_dotenv(nested)
        import os

        assert os.environ["GOOGLE_API_KEY"] == "up-there"

    def test_no_dotenv_anywhere_is_not_an_error(self, tmp_path: Path) -> None:
        load_dotenv(tmp_path / "empty")


class TestExtraction:
    def test_a_valid_proposal_is_returned_with_its_model_and_attempt_count(self) -> None:
        analyst = _analyst()
        with analyst.agent.override(model=_returning(claim="the site is unstable")):
            extraction = analyst.extract("some passage")
        assert extraction.structure.claim == "the site is unstable"
        assert extraction.model == "openai:test"
        assert extraction.output_attempts >= 1

    def test_empty_text_never_reaches_the_model(self) -> None:
        with pytest.raises(LlmError) as caught:
            _analyst().extract("   \n  ")
        assert caught.value.code == "empty_source_text"
        assert caught.value.retryability is Retryability.NOT_RETRYABLE


class TestFailureAlgebra:
    """Every failure is typed and classified. The boundary never retries on its own."""

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (429, Retryability.RETRYABLE),
            (500, Retryability.RETRYABLE),
            (503, Retryability.RETRYABLE),
            (408, Retryability.RETRYABLE),
            (400, Retryability.NOT_RETRYABLE),
            (401, Retryability.NOT_RETRYABLE),
            (403, Retryability.NOT_RETRYABLE),
            (404, Retryability.NOT_RETRYABLE),
        ],
    )
    def test_http_status_decides_retryability(self, status: int, expected: Retryability) -> None:
        analyst = _analyst()
        error = ModelHTTPError(status_code=status, model_name="test", body=None)
        with analyst.agent.override(model=_raising(error)), pytest.raises(LlmError) as caught:
            analyst.extract("passage")
        assert caught.value.code == "llm_request_rejected"
        assert caught.value.retryability is expected

    def test_exhausted_output_validation_is_not_retryable(self) -> None:
        analyst = _analyst()
        error = UnexpectedModelBehavior("exceeded max retries")
        with analyst.agent.override(model=_raising(error)), pytest.raises(LlmError) as caught:
            analyst.extract("passage")
        assert caught.value.code == "llm_output_failed_validation"
        assert caught.value.retryability is Retryability.NOT_RETRYABLE
        assert "Finding" in caught.value.detail, "the failure names the contract that was not satisfied"

    def test_transport_failure_is_retryable(self) -> None:
        analyst = _analyst()
        transport = ModelAPIError(model_name="test", message="connection reset")
        with analyst.agent.override(model=_raising(transport)), pytest.raises(LlmError) as caught:
            analyst.extract("passage")
        assert caught.value.code == "llm_transport_failed"
        assert caught.value.retryability is Retryability.RETRYABLE

    def test_usage_limit_is_not_retryable(self) -> None:
        analyst = _analyst()
        with analyst.agent.override(model=_raising(UsageLimitExceeded("budget"))), pytest.raises(LlmError) as caught:
            analyst.extract("passage")
        assert caught.value.code == "llm_usage_limit_exceeded"
        assert caught.value.retryability is Retryability.NOT_RETRYABLE

    def test_an_unclassified_run_failure_is_unknown_not_guessed(self) -> None:
        analyst = _analyst()
        with analyst.agent.override(model=_raising(AgentRunError("something else"))), pytest.raises(LlmError) as caught:
            analyst.extract("passage")
        assert caught.value.code == "llm_run_failed"
        assert caught.value.retryability is Retryability.UNKNOWN

    def test_every_failure_carries_a_classification(self) -> None:
        """No failure may leave retryability unset — the capability contract requires it."""

        for error in (
            ModelHTTPError(status_code=500, model_name="t", body=None),
            UnexpectedModelBehavior("x"),
            ModelAPIError(model_name="t", message="x"),
            UsageLimitExceeded("x"),
            AgentRunError("x"),
        ):
            analyst = _analyst()
            with analyst.agent.override(model=_raising(error)), pytest.raises(LlmError) as caught:
                analyst.extract("passage")
            assert isinstance(caught.value.retryability, Retryability)
            assert caught.value.code and caught.value.detail


class TestNoHiddenNetwork:
    def test_constructing_an_analyst_opens_no_connection(self) -> None:
        analyst = StructuredAnalyst(output_type=Finding, instructions="i", model="openai:gpt-5.6-sol")
        assert analyst.model == "openai:gpt-5.6-sol"

    def test_the_agent_is_built_once_and_reused(self) -> None:
        analyst = _analyst()
        assert analyst.agent is analyst.agent
