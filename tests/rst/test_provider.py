"""The RST provider adapter: capability means the configured parser can run."""

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import pytest
from rdam.configuration import MachineConfig, LlmSettings

from rdam import (
    BOUNDARY_TECHNIQUES,
    AggregateRequest,
    AvailableCapability,
    FailedOutcome,
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
    canonical_json_bytes,
    production_machine,
    technique_curie,
)
from rdam.ingest import (
    FailureCategory,
    LifecycleStage,
    ProductionFailure,
    ProductionIngestError,
    ProductionIngestor,
    Retryability as IngestRetryability,
    SourceArtifact,
)
from rdam.ingest.serialization import PersistedContract, serialize_contract
from rdam.ingest.contracts.preparation import PreparationOutcome
from rdam.ingest.contracts.source import ContentClass
from rdam.rst.provider import ERST_GRAPH, RST_TREE, ProviderConfigurationError, RstProvider
from rdam.rst.model_loading.release import MODEL_RELEASE_MANIFEST
from tests.ingest.production_ingest.conftest import build_deterministic_parser

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "models" / "model-releases"


def _local_release(
    store: Path,
    *,
    release_id: str = "local-rst",
    compatibility_range: str = ">=6,<7",
    runtime_contract: str = "isanlp_rst.parser/dmrst-v1",
) -> Path:
    release = store / release_id
    release.mkdir(parents=True)
    weights = release / "model.bin"
    weights.write_bytes(b"tiny immutable parser")
    manifest = {
        "schema_version": "isanlp_rst_model_release/v1",
        "release_id": release_id,
        "model_task": "rst-parsing",
        "architecture": "tiny-test-parser",
        "runtime_contract": runtime_contract,
        "compatibility_range": compatibility_range,
        "source_model_identity": "fixture/tiny-rst",
        "source_revision": "a" * 40,
        "licence": "Fixture-RST-Licence",
        "use_restrictions": [],
        "evaluation_evidence": "tests/rst/test_provider.py",
        "evaluation_unavailable_reason": None,
        "created_at": datetime(2026, 9, 3, tzinfo=UTC).isoformat(),
        "producer_version": "6.0.0",
        "files": [
            {
                "path": weights.name,
                "role": "weights",
                "size_bytes": weights.stat().st_size,
                "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
            }
        ],
    }
    (release / MODEL_RELEASE_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    return release


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

    def test_a_valid_local_release_is_fully_validated_without_loading_a_parser(self, tmp_path: Path) -> None:
        store = tmp_path / "store"
        _local_release(store)
        provider = RstProvider(store=store, release_id="local-rst")
        declaration = provider.declaration
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.provenance.licence == "Fixture-RST-Licence"
        assert provider._parser is None

    @pytest.mark.parametrize(
        "defect",
        (
            "malformed",
            "incompatible",
            "missing_member",
            "size_mismatch",
            "hash_mismatch",
            "wrong_contract",
        ),
    )
    def test_invalid_local_release_is_unavailable_not_manifest_present(
        self,
        tmp_path: Path,
        defect: str,
    ) -> None:
        store = tmp_path / "store"
        release = _local_release(
            store,
            compatibility_range=">=99" if defect == "incompatible" else ">=6,<7",
            runtime_contract="not-an-rst-contract" if defect == "wrong_contract" else "isanlp_rst.parser/dmrst-v1",
        )
        if defect == "malformed":
            (release / MODEL_RELEASE_MANIFEST).write_text("{}", encoding="utf-8")
        elif defect == "missing_member":
            (release / "model.bin").unlink()
        elif defect == "size_mismatch":
            (release / "model.bin").write_bytes(b"changed bytes")
        elif defect == "hash_mismatch":
            original = (release / "model.bin").read_bytes()
            (release / "model.bin").write_bytes(b"x" * len(original))
        provider = RstProvider(store=store, release_id="local-rst")
        assert provider.declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)
        assert "CC BY-NC" not in provider.declaration.provenance.licence
        assert provider._parser is None

    def test_release_id_cannot_escape_the_configured_store(self, tmp_path: Path) -> None:
        store = tmp_path / "store"
        store.mkdir()
        _local_release(tmp_path, release_id="escaped")
        provider = RstProvider(store=store, release_id="../escaped")
        assert provider.declaration.capability == UnavailableCapability(reason=UnavailableReason.MODEL_UNAVAILABLE)
        assert provider._parser is None

    def test_local_release_validation_is_cached_per_provider(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        store = tmp_path / "store"
        _local_release(store)
        from rdam.rst.model_loading import load_model_release as real_load

        calls = 0

        def counted_load(store_path: Path, release_id: str):
            nonlocal calls
            calls += 1
            return real_load(store_path, release_id)

        monkeypatch.setattr("rdam.rst.provider.load_model_release", counted_load)
        provider = RstProvider(store=store, release_id="local-rst")
        assert isinstance(provider.declaration.capability, AvailableCapability)
        assert isinstance(provider.declaration.capability, AvailableCapability)
        assert calls == 1

    def test_incoherent_configuration_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderConfigurationError, match="both store and release_id"):
            RstProvider(store=tmp_path)
        with pytest.raises(ProviderConfigurationError, match="not both"):
            RstProvider(hf_model_version="gumrrg", store=tmp_path, release_id="x")

    def test_the_weights_licence_is_reported(self) -> None:
        assert "CC BY-NC" in RstProvider().declaration.provenance.licence

    def test_withholding_rst_changes_no_other_production_capability_bytes(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
        complete = production_machine(config=MachineConfig(llm=LlmSettings(model="openai:gpt-5.6-sol")))
        without_rst = Machine(
            provider
            for technique, provider in complete.providers.items()
            if technique is not Technique.RST
        )
        complete_capabilities = complete.capabilities()
        reduced_capabilities = without_rst.capabilities()
        for technique in BOUNDARY_TECHNIQUES:
            if technique is Technique.RST:
                continue
            assert canonical_json_bytes(
                complete_capabilities.capability_for(technique)
            ) == canonical_json_bytes(reduced_capabilities.capability_for(technique))
        assert reduced_capabilities.capability_for(Technique.RST).capability == (
            UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED)
        )


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

    def test_release_changed_after_declaration_is_a_typed_failure(self, tmp_path: Path) -> None:
        store = tmp_path / "store"
        release = _local_release(store)
        provider = RstProvider(store=store, release_id="local-rst")
        assert isinstance(provider.declaration.capability, AvailableCapability)
        (release / "model.bin").write_bytes(b"changed after declaration")

        with pytest.raises(ProviderError) as caught:
            provider.analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("text"),
                    text="text",
                    structured_input=None,
                )
            )
        assert caught.value.failure.code == "model_release_invalid"
        assert caught.value.failure.retryability.value == "not_retryable"
        assert provider._parser is None

    def test_canonical_ingest_bytes_are_the_exact_native_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        provider = RstProvider(hf_model_version="gumrrg")
        parser = build_deterministic_parser()
        monkeypatch.setattr(provider, "_load_parser", lambda: parser)
        serialized: list[bytes] = []

        def capture(value: PersistedContract | ProductionFailure) -> bytes:
            payload = serialize_contract(value)
            serialized.append(payload)
            return payload

        monkeypatch.setattr("rdam.rst.provider.serialize_contract", capture)
        request = AggregateRequest.for_text(
            "First sentence. Second sentence.",
            (Technique.RST,),
            formalisms=(
                FormalismChoice(technique=Technique.RST, formalism_id=RST_TREE),
            ),
        )
        aggregate = Machine([provider]).analyse(request)
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, ResultOutcome)
        assert serialized and outcome.result.payload == json.loads(serialized[0])
        assert outcome.result.formalism_id == RST_TREE
        assert outcome.result.provider_id == provider.declaration.provider_id
        assert outcome.result.provider_contract_version == provider.declaration.contract_version
        assert outcome.result.provenance == provider.declaration.provenance
        assert outcome.result.source == request.source

    def test_production_ingest_failure_fields_are_preserved(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        provider = RstProvider(hf_model_version="gumrrg")
        monkeypatch.setattr(provider, "_load_parser", build_deterministic_parser)
        ingest_failure = ProductionFailure(
            failed_stage=LifecycleStage.INFERENCE,
            category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
            code="fixture_inference_failed",
            retryability=IngestRetryability.UNKNOWN,
            message_template="fixture_parser_failed",
        )

        def fail_ingest(
            _ingestor: ProductionIngestor,
            _preparation: PreparationOutcome,
            **_options: object,
        ) -> None:
            raise ProductionIngestError(ingest_failure)

        monkeypatch.setattr(ProductionIngestor, "analyse_prepared", fail_ingest)
        aggregate = Machine([provider]).analyse(
            AggregateRequest.for_text("text", (Technique.RST,))
        )
        outcome = aggregate.outcome_for(Technique.RST)
        assert isinstance(outcome, FailedOutcome)
        assert outcome.failure.code == ingest_failure.code
        assert outcome.failure.retryability.value == ingest_failure.retryability.value
        assert outcome.failure.message_template == ingest_failure.message_template
        assert outcome.failure.message_parameters == (
            ("failed_stage", ingest_failure.failed_stage.value),
            ("category", ingest_failure.category.value),
        )

    def test_declared_projection_excludes_tables_without_losing_inventory(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        provider = RstProvider(device="cpu")
        monkeypatch.setattr(provider, "_load_parser", build_deterministic_parser)
        result = Machine([provider]).analyse(AggregateRequest.for_source(
            ROOT / "tests/fixtures/pipeline/tabular-evidence.md", (Technique.RST,),
        ))
        assert isinstance(result.outcome_for(Technique.RST), ResultOutcome)
        assert result.preparation is not None
        inventory = {item.item_id: item for item in result.preparation.preparation.inventory}
        assert any(item.classification is ContentClass.TABLE_CELL for item in inventory.values())
        projection = result.preparation.projections[0]
        contributors = {item_id for segment in projection.prepared_document.segments
                        for item_id in segment.contributing_item_ids}
        assert contributors
        assert all(inventory[item_id].classification in provider.content_requirement.admitted_classes
                   for item_id in contributors)
        assert not {ContentClass.TABLE, ContentClass.TABLE_CELL}.intersection(
            inventory[item_id].classification for item_id in contributors
        )

    def test_unexpected_ingest_exception_propagates_as_an_adapter_bug(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        provider = RstProvider(hf_model_version="gumrrg")
        monkeypatch.setattr(provider, "_load_parser", build_deterministic_parser)

        def break_ingest(
            _ingestor: ProductionIngestor,
            _source: SourceArtifact,
            **_options: object,
        ) -> None:
            raise KeyError("unexpected adapter defect")

        monkeypatch.setattr(ProductionIngestor, "analyse", break_ingest)
        with pytest.raises(KeyError, match="unexpected adapter defect"):
            provider.analyse(
                ProviderRequest(
                    source=SourceIdentity.from_text("text"),
                    text="text",
                    structured_input=None,
                )
            )


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
