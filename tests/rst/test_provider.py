"""The RST provider adapter: capability means the configured parser can run."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from rdam import (
    AggregateRequest,
    AvailableCapability,
    FormalismChoice,
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
from rdam.rst.provider import ERST_GRAPH, RST_TREE, ProviderConfigurationError, RstProvider

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "models" / "model-releases"


class TestConfiguration:
    def test_the_default_configuration_is_the_default_parser_version(self) -> None:
        provider = RstProvider()
        assert provider.model_identity == "gumrrg"
        assert provider.provider_id == "rdam.rst/gumrrg"

    def test_a_published_version_is_available_without_loading_a_model(self) -> None:
        provider = RstProvider(hf_model_version="gumrrg")
        declaration = provider.declaration
        assert declaration.technique is Technique.RST
        assert declaration.technique_curie == technique_curie(Technique.RST)
        assert isinstance(declaration.capability, AvailableCapability)
        assert provider._parser is None, "declaring capability must not load a model"

    def test_an_unknown_version_is_unavailable_with_a_stable_reason(self) -> None:
        declaration = RstProvider(hf_model_version="not-a-version").declaration
        assert declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)

    def test_an_absent_local_release_is_unavailable(self, tmp_path: Path) -> None:
        declaration = RstProvider(store=tmp_path, release_id="missing").declaration
        assert declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)

    def test_incoherent_configuration_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderConfigurationError, match="both store and release_id"):
            RstProvider(store=tmp_path)
        with pytest.raises(ProviderConfigurationError, match="not both"):
            RstProvider(hf_model_version="gumrrg", store=tmp_path, release_id="x")

    def test_the_weights_licence_is_reported(self) -> None:
        assert "CC BY-NC" in RstProvider().declaration.provenance.licence


class TestFormalisms:
    def test_erst_is_declared_with_its_own_identity_and_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam.rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        declaration = RstProvider(hf_model_version="gumrrg").declaration
        rst_tree = declaration.formalism(RST_TREE)
        erst = declaration.formalism(ERST_GRAPH)
        assert rst_tree is not None and isinstance(rst_tree.capability, AvailableCapability)
        assert erst is not None and erst.technique is Technique.ERST
        assert erst.technique_curie == technique_curie(Technique.ERST)
        assert isinstance(erst.capability, UnavailableCapability)

    def test_asking_for_erst_without_a_bundle_is_unavailable_not_failed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam.rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        machine = Machine([RstProvider(hf_model_version="gumrrg")])
        request = AggregateRequest.for_text(
            "The cat sat.",
            (Technique.RST,),
            formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=ERST_GRAPH),),
        )
        outcome = machine.analyse(request).outcome_for(Technique.RST)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.MODEL_UNAVAILABLE


class TestAnalyseGuards:
    def test_unavailable_provider_refuses_to_analyse_with_a_typed_failure(self) -> None:
        provider = RstProvider(hf_model_version="not-a-version")
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_text("t"), text="t", structured_input=None))
        assert caught.value.failure.code == "provider_not_available"
        assert caught.value.failure.message_parameters == (("detail", "model_unavailable"),)

    def test_text_is_required_before_any_model_load(self) -> None:
        provider = RstProvider(hf_model_version="gumrrg")
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None))
        assert caught.value.failure.code == "text_required"
        assert provider._parser is None


@pytest.mark.slow
class TestRealParser:
    """Through the real published parser: the machine receives rdam.rst's own envelope."""

    def test_machine_gets_the_rst_outcome_envelope_as_the_native_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam.rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        machine = Machine([RstProvider(hf_model_version="gumrrg", device="cpu")])
        text = "The cat sat on the mat. It was a black cat. The mat was red."
        aggregate = machine.analyse(AggregateRequest.for_text(text, (Technique.RST, Technique.DUNG)))
        rst = aggregate.outcome_for(Technique.RST)
        assert isinstance(rst, ResultOutcome)
        assert rst.result.technique is Technique.RST
        assert rst.result.formalism_id == RST_TREE
        assert rst.result.provider_id == "rdam.rst/gumrrg"
        payload = rst.result.payload
        assert payload["contract"] == "isanlp_rst.production"
        assert payload["kind"] == "analysed_outcome"
        semantic = payload["semantic"]
        assert isinstance(semantic, Mapping)
        assert semantic["status"] == "analysed"
        analysis = semantic["analysis"]
        assert isinstance(analysis, Mapping)
        nodes = analysis["nodes"]
        assert isinstance(nodes, list) and nodes, "the native payload is rdam.rst's own analysed outcome, verbatim"
        dung = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(dung, UnavailableOutcome)
