"""The RST provider adapter: capability from the published decision, never from a model load."""

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

import pytest

from rdam import (
    AggregateRequest,
    AvailableCapability,
    BaselineComparison,
    CalibrationEvidence,
    CandidateIdentity,
    CompatibilityEvidence,
    EmpiricalQualityEvidence,
    FormalismChoice,
    LatencyEvidence,
    LicensingEvidence,
    Machine,
    Measurement,
    PromotionDecision,
    PromotionOutcome,
    ProviderError,
    ProviderProvenance,
    ProviderRequest,
    ProvenanceEvidence,
    Recommendation,
    ResultOutcome,
    Sha256Identity,
    SourceIdentity,
    Technique,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
    UnmeasuredQuality,
    serialize_decision,
    technique_curie,
)
from rdam_rst import ProviderConfigurationError, RstProvider
from rdam_rst.provider import ERST_GRAPH, RST_TREE

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "models" / "model-releases"
REAL_RELEASE = "modernbert-v1-a52b70fbc1a3"


def _decision(release_id: str, outcome: PromotionOutcome, artifact_sha256: str) -> PromotionDecision:
    artifact = Sha256Identity(hex_digest=artifact_sha256)
    if outcome in {PromotionOutcome.PROMOTE, PromotionOutcome.REPLACE}:
        quality = EmpiricalQualityEvidence(
            gold_data="fixture",
            partitions=("test",),
            measurements=(Measurement(name="full_f1", value=0.9, partition="test", unit="f1"),),
            baselines=(
                BaselineComparison(
                    baseline_identity="fixture-baseline",
                    baseline_measurements=(Measurement(name="full_f1", value=0.5, partition="test", unit="f1"),),
                    comparison_basis="fixture",
                    candidate_exceeds_baseline=True,
                ),
            ),
            uncertainty="fixture CI",
        )
    else:
        quality = UnmeasuredQuality(reason="fixture")
    return PromotionDecision(
        decision_id=f"{release_id}-{outcome.value}",
        decided_at=datetime(2026, 9, 2, tzinfo=UTC),
        decided_by="test",
        candidate=CandidateIdentity(technique=Technique.RST, candidate_id=release_id, artifact_identity=artifact, description="fixture"),
        output_quality=quality,
        calibration=CalibrationEvidence(state="declared_absent", description="fixture"),
        latency=LatencyEvidence(state="measured", platform="fixture", measurements=(Measurement(name="p50_ms", value=1.0, partition="test", unit="ms"),)),
        compatibility=CompatibilityEvidence(state="verified", environment="fixture", import_time_side_effects=False, packaging_declares_dependencies=True),
        provenance=ProvenanceEvidence(code_revision="fixture", configuration_identity="fixture", model_asset_identity=artifact, corpus_partitions=("test",)),
        licensing=LicensingEvidence(licence="Apache-2.0", intended_use="local analysis", permits_intended_use=True, decision_note="fixture permits"),
        outcome=outcome,
        replaces="previous" if outcome is PromotionOutcome.REPLACE else None,
        recommendation=Recommendation(summary="fixture", strengths=("s",), limitations=("l",)),
    )


def _publish(store: Path, decision: PromotionDecision) -> None:
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{decision.candidate.candidate_id}.promotion.json").write_bytes(serialize_decision(decision))


class TestDeclaration:
    def test_no_decision_means_no_promoted_implementation(self, tmp_path: Path) -> None:
        provider = RstProvider(store=tmp_path, release_id="modernbert-v1-none")
        declaration = provider.declaration
        assert declaration.technique is Technique.RST
        assert declaration.technique_curie == technique_curie(Technique.RST)
        assert declaration.capability == UnavailableCapability(reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION)
        assert provider._parser is None, "declaring capability must not load a model"

    @pytest.mark.parametrize(
        ("outcome", "reason"),
        [(PromotionOutcome.WITHHOLD, UnavailableReason.WITHHELD), (PromotionOutcome.RETIRE, UnavailableReason.RETIRED)],
    )
    def test_negative_decisions_map_to_stable_reasons(self, tmp_path: Path, outcome: PromotionOutcome, reason: UnavailableReason) -> None:
        _publish(tmp_path, _decision("modernbert-v1-x", outcome, "a" * 64))
        provider = RstProvider(store=tmp_path, release_id="modernbert-v1-x")
        assert provider.declaration.capability == UnavailableCapability(reason=reason)
        for formalism in provider.declaration.formalisms:
            assert isinstance(formalism.capability, UnavailableCapability)

    def test_promote_decision_makes_rst_tree_available_and_erst_depends_on_a_bundle(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ISANLP_RST_ERST_CHECKPOINT", raising=False)
        monkeypatch.setattr("rdam_rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        _publish(tmp_path, _decision("modernbert-v1-x", PromotionOutcome.PROMOTE, "a" * 64))
        declaration = RstProvider(store=tmp_path, release_id="modernbert-v1-x").declaration
        assert isinstance(declaration.capability, AvailableCapability)
        assert declaration.capability.provider_id == "isanlp_rst/modernbert-v1-x"
        rst_tree = declaration.formalism(RST_TREE)
        erst = declaration.formalism(ERST_GRAPH)
        assert rst_tree is not None and isinstance(rst_tree.capability, AvailableCapability)
        assert erst is not None and erst.technique is Technique.ERST
        assert erst.capability == UnavailableCapability(reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION)
        assert declaration.provenance == ProviderProvenance(
            package="isanlp_rst", version=declaration.provenance.version, model_identity="modernbert-v1-x", licence_decision="fixture permits"
        )

    def test_a_decision_about_another_release_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ProviderConfigurationError, match="not release"):
            RstProvider(store=tmp_path, release_id="modernbert-v1-y", decision=_decision("modernbert-v1-x", PromotionOutcome.PROMOTE, "a" * 64))


class TestAnalyseGuards:
    def test_unavailable_provider_refuses_to_analyse_with_a_typed_failure(self, tmp_path: Path) -> None:
        provider = RstProvider(store=tmp_path, release_id="modernbert-v1-none")
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_text("t"), text="t", structured_input=None))
        assert caught.value.failure.code == "provider_not_available"
        assert caught.value.failure.message_parameters == (("detail", "no_promoted_implementation"),)

    def test_text_is_required_before_any_model_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam_rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        _publish(tmp_path, _decision("modernbert-v1-x", PromotionOutcome.PROMOTE, "a" * 64))
        provider = RstProvider(store=tmp_path, release_id="modernbert-v1-x")
        with pytest.raises(ProviderError) as caught:
            provider.analyse(ProviderRequest(source=SourceIdentity.from_bytes(b"x"), text=None, structured_input=None))
        assert caught.value.failure.code == "text_required"
        assert provider._parser is None

    def test_machine_reports_the_withheld_rst_provider_honestly(self, tmp_path: Path) -> None:
        _publish(tmp_path, _decision("modernbert-v1-x", PromotionOutcome.WITHHOLD, "a" * 64))
        machine = Machine([RstProvider(store=tmp_path, release_id="modernbert-v1-x")])
        assert machine.capabilities().capability_for(Technique.RST).capability == UnavailableCapability(reason=UnavailableReason.WITHHELD)
        outcome = machine.analyse(AggregateRequest.for_text("The cat sat.", (Technique.RST,))).outcome_for(Technique.RST)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.WITHHELD


@pytest.fixture(scope="module")
def real_artifact_sha256() -> str:
    manifest = STORE / REAL_RELEASE / "release-manifest.json"
    if not manifest.is_file():
        pytest.skip(f"{REAL_RELEASE} is not in the local store")
    files = json.loads(manifest.read_bytes())["files"]
    return next(item["sha256"] for item in files if item["role"] == "parser_state")


@pytest.mark.slow
class TestRealRelease:
    """Through the real release in the repository store, with a fixture promote decision naming its exact artifact."""

    def test_decision_for_a_different_artifact_cannot_borrow_the_release(self, real_artifact_sha256: str) -> None:
        wrong = _decision(REAL_RELEASE, PromotionOutcome.PROMOTE, hashlib.sha256(b"other").hexdigest())
        provider = RstProvider(store=STORE, release_id=REAL_RELEASE, device="cpu", decision=wrong)
        with pytest.raises(ProviderConfigurationError, match="names artifact"):
            provider.analyse(ProviderRequest(source=SourceIdentity.from_text("t"), text="t", structured_input=None))

    def test_machine_gets_isanlp_rst_outcome_envelope_as_the_native_payload(self, real_artifact_sha256: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam_rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        decision = _decision(REAL_RELEASE, PromotionOutcome.PROMOTE, real_artifact_sha256)
        provider = RstProvider(store=STORE, release_id=REAL_RELEASE, device="cpu", decision=decision)
        machine = Machine([provider])
        text = "The cat sat on the mat. It was a black cat. The mat was red."
        aggregate = machine.analyse(AggregateRequest.for_text(text, (Technique.RST, Technique.DUNG)))
        rst = aggregate.outcome_for(Technique.RST)
        assert isinstance(rst, ResultOutcome)
        assert rst.result.technique is Technique.RST
        assert rst.result.formalism_id == RST_TREE
        assert rst.result.provider_id == f"isanlp_rst/{REAL_RELEASE}"
        payload = rst.result.payload
        assert payload["contract"] == "isanlp_rst.production"
        assert payload["kind"] == "analysed_outcome"
        semantic = payload["semantic"]
        assert isinstance(semantic, Mapping)
        assert semantic["status"] == "analysed"
        analysis = semantic["analysis"]
        assert isinstance(analysis, Mapping)
        nodes = analysis["nodes"]
        assert isinstance(nodes, list) and nodes, "the native payload is isanlp_rst's own analysed outcome, verbatim"
        dung = aggregate.outcome_for(Technique.DUNG)
        assert isinstance(dung, UnavailableOutcome)

    def test_asking_for_erst_without_a_bundle_is_unavailable_not_failed(self, real_artifact_sha256: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("rdam_rst.provider.resolve_default_erst_checkpoint", lambda _path: None)
        decision = _decision(REAL_RELEASE, PromotionOutcome.PROMOTE, real_artifact_sha256)
        machine = Machine([RstProvider(store=STORE, release_id=REAL_RELEASE, device="cpu", decision=decision)])
        request = AggregateRequest.for_text("The cat sat.", (Technique.RST,), formalisms=(FormalismChoice(technique=Technique.RST, formalism_id=ERST_GRAPH),))
        outcome = machine.analyse(request).outcome_for(Technique.RST)
        assert isinstance(outcome, UnavailableOutcome)
        assert outcome.reason is UnavailableReason.NO_PROMOTED_IMPLEMENTATION
