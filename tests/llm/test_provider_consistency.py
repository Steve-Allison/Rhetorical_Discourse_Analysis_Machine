"""All four LLM techniques share one configuration, input, and error algebra."""

from collections.abc import Callable

import pytest

from rdam import (
    ProviderError,
    ProviderRequest,
    Retryability,
    SourceIdentity,
    Technique,
    UnavailableCapability,
    UnavailableReason,
)
from rdam._llm import LlmError, StructuredAnalyst
from rdam._provider_provenance import llm_provider_failure
from rdam.pdtb import PdtbProvider
from rdam.sdrt import SdrtProvider
from rdam.toulmin import ToulminProvider
from rdam.walton import WaltonProvider

type ProviderFactory = Callable[..., PdtbProvider | SdrtProvider | ToulminProvider | WaltonProvider]

PROVIDERS: tuple[tuple[ProviderFactory, Technique], ...] = (
    (PdtbProvider, Technique.PDTB),
    (SdrtProvider, Technique.SDRT),
    (ToulminProvider, Technique.TOULMIN),
    (WaltonProvider, Technique.WALTON),
)


@pytest.fixture(autouse=True)
def configured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")


@pytest.mark.parametrize(("factory", "technique"), PROVIDERS)
@pytest.mark.parametrize(("text", "code"), ((None, "text_required"), (" \n ", "empty_source_text")))
def test_text_validation_is_identical_before_agent_construction(
    factory: ProviderFactory,
    technique: Technique,
    text: str | None,
    code: str,
) -> None:
    provider = factory(model="openai:test")
    source = SourceIdentity.from_bytes(b"source") if text is None else SourceIdentity.from_text(text)
    with pytest.raises(ProviderError) as caught:
        provider.analyse(ProviderRequest(source=source, text=text, structured_input=None))
    assert caught.value.failure.technique is technique
    assert caught.value.failure.code == code
    assert caught.value.failure.message_parameters == ()
    assert provider._analyst is None


@pytest.mark.parametrize(("factory", "_technique"), PROVIDERS)
def test_bare_model_identity_is_normalized_in_identity_and_provenance(
    factory: ProviderFactory,
    _technique: Technique,
) -> None:
    provider = factory(model="gpt-5.6-sol")
    assert provider.provider_id.endswith("/openai:gpt-5.6-sol")
    assert provider.declaration.provenance.model_identity == "openai:gpt-5.6-sol"


@pytest.mark.parametrize(("factory", "_technique"), PROVIDERS)
def test_malformed_identity_reports_unavailable_without_constructing_a_client(
    factory: ProviderFactory,
    _technique: Technique,
) -> None:
    provider = factory(model="openai:")
    assert provider.declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)
    assert provider._analyst is None


def test_attempt_evidence_has_one_parameter_order_for_every_llm_provider() -> None:
    error = LlmError(
        "llm_transport_failed",
        retryability=Retryability.RETRYABLE,
        detail="connection reset",
        output_attempts=2,
        transport_attempts=3,
    )
    failures = tuple(
        llm_provider_failure(error, technique=technique, provider_id=f"fixture/{technique.value}")
        for _, technique in PROVIDERS
    )
    expected = (("detail", "connection reset"), ("output_attempts", "2"), ("transport_attempts", "3"))
    assert all(failure.message_parameters == expected for failure in failures)


def test_invalid_identity_raises_precisely_when_client_construction_is_attempted() -> None:
    analyst = StructuredAnalyst(output_type=UnavailableCapability, instructions="test", model="openai:")
    with pytest.raises(ValueError, match="model identity"):
        _ = analyst.agent
