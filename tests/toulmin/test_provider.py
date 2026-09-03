"""The Toulmin provider through the machine: capability is whether the model can be reached."""

import pytest

from rdam import (
    AggregateRequest,
    AvailableCapability,
    Machine,
    ProviderError,
    ProviderRequest,
    ResultOutcome,
    SourceIdentity,
    Technique,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    technique_curie,
)
from rdam.toulmin import PROVIDER_ID_PREFIX, ToulminProvider, source_identity

MODEL = "openai:gpt-5.6-sol"


@pytest.fixture
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """A machine with no key for the configured model, and no ``.env`` to fall back on."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("rdam._llm.load_dotenv", lambda *_args, **_kwargs: None)


@pytest.fixture
def with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used-for-any-request")


class TestDeclaration:
    def test_the_model_is_part_of_the_provider_identity(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        assert provider.provider_id == f"{PROVIDER_ID_PREFIX}/{MODEL}"

    def test_available_when_the_model_can_be_reached(self, with_credentials: None) -> None:
        declaration = ToulminProvider(model=MODEL).declaration
        assert declaration.technique is Technique.TOULMIN
        assert declaration.technique_curie == technique_curie(Technique.TOULMIN)
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.requires_structured_input is False

    def test_unavailable_with_a_stable_reason_when_no_key_resolves(self, no_credentials: None) -> None:
        declaration = ToulminProvider(model=MODEL).declaration
        assert declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)

    def test_declaring_capability_never_builds_an_agent(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        assert provider.declaration is not None
        assert provider._analyst is None, "declaring capability must not construct the model client"

    def test_provenance_names_the_model_the_source_and_the_licence(self, with_credentials: None) -> None:
        provenance = ToulminProvider(model=MODEL).declaration.provenance
        assert provenance.package == "rdam.toulmin"
        assert provenance.model_identity == MODEL
        assert provenance.source_revision == source_identity().hex_digest
        assert "MIT" in provenance.licence


class TestAnalyseGuards:
    def test_an_unreachable_model_refuses_to_analyse_with_a_typed_failure(self, no_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_text("t"), text="t", structured_input=None))
        assert caught.value.failure.code == "provider_not_available"
        assert caught.value.failure.message_parameters == (("detail", "model_unavailable"),)

    def test_text_is_required_before_any_model_call(self, with_credentials: None) -> None:
        provider = ToulminProvider(model=MODEL)
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None))
        assert caught.value.failure.code == "text_required"
        assert provider._analyst is None

    def test_an_undeclared_formalism_is_refused(self, with_credentials: None) -> None:
        with pytest.raises(ProviderError) as caught:
            ToulminProvider(model=MODEL).analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("t"), text="t", structured_input=None, formalism_id="not_a_formalism"
                )
            )
        assert caught.value.failure.code == "formalism_not_declared"


class TestThroughTheMachine:
    def test_an_unreachable_model_is_unavailable_not_failed(self, no_credentials: None) -> None:
        machine = Machine([ToulminProvider(model=MODEL)])
        outcome = machine.analyse(AggregateRequest.for_text("Some text.", (Technique.TOULMIN,))).outcome_for(Technique.TOULMIN)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE


@pytest.mark.slow
class TestAgainstTheRealModel:
    """One real call: the layout the machine returns is the model's proposal, validated."""

    def test_the_machine_returns_a_validated_toulmin_layout(self) -> None:
        machine = Machine([ToulminProvider()])
        text = (
            "The council should reject the proposal. It would cost £4m that is not in the budget, "
            "and two independent surveys both found the site is unstable."
        )
        outcome = machine.analyse(AggregateRequest.for_text(text, (Technique.TOULMIN,))).outcome_for(Technique.TOULMIN)
        assert isinstance(outcome, ResultOutcome)
        payload = outcome.result.payload
        layouts = payload["layouts"]
        assert isinstance(layouts, list) and layouts, "the passage argues; a layout is expected"
        first = layouts[0]
        assert isinstance(first, dict)
        assert first["claim"], "a layout always carries a claim"
        assert first["grounds"], "a layout always carries grounds"
        assert first["warrant"], "FR-019: a layout always carries a recovered warrant"
        extraction = payload["extraction"]
        assert isinstance(extraction, dict)
        assert extraction["model"] == outcome.result.provenance.model_identity
