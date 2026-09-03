"""Causal regression tests for Feature 018 shared execution and caching."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from stat import S_IMODE
from threading import Barrier, Event, Lock
import time

import pytest

from rdam import (
    BOUNDARY_TECHNIQUES,
    STRUCTURED_INPUT_TECHNIQUES,
    AggregateRequest,
    AvailableCapability,
    ExecutionPolicy,
    FormalismDeclaration,
    Machine,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    ProviderRequest,
    ResultOutcome,
    Retryability,
    SemanticVersion,
    SourceIdentity,
    StructuredInput,
    Technique,
    UpstreamResultReference,
    production_machine,
    load,
    serialize,
    technique_curie,
)
from rdam.machine import _cache_key

V1 = SemanticVersion(root="1.0.0")


def declaration(
    technique: Technique,
    *,
    revision: str | None = "clean-revision",
    model: str | None = None,
    contract: SemanticVersion = V1,
) -> ProviderDeclaration:
    provider_id = f"fixture/{technique.value}"
    capability = AvailableCapability(provider_id=provider_id, contract_version=contract)
    return ProviderDeclaration(
        provider_id=provider_id,
        technique=technique,
        technique_curie=technique_curie(technique),
        formalisms=(
            FormalismDeclaration(
                formalism_id=f"{technique.value}_native",
                technique=technique,
                technique_curie=technique_curie(technique),
                capability=capability,
            ),
        ),
        contract_version=contract,
        provenance=ProviderProvenance(
            package=f"fixture.{technique.value}",
            version="1.0.0",
            source_revision=revision,
            model_identity=model,
            licence="test fixture",
        ),
        capability=capability,
        requires_structured_input=technique in STRUCTURED_INPUT_TECHNIQUES,
    )


@dataclass
class RuntimeProvider:
    _declaration: ProviderDeclaration
    behaviour: Callable[[ProviderRequest], NativeTechniqueResult]
    calls: int = 0

    @property
    def declaration(self) -> ProviderDeclaration:
        return self._declaration

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        self.calls += 1
        return self.behaviour(request)


def provider(
    technique: Technique,
    *,
    revision: str | None = "clean-revision",
    behaviour: Callable[[ProviderRequest], NativeTechniqueResult] | None = None,
) -> RuntimeProvider:
    declared = declaration(technique, revision=revision)

    def result(request: ProviderRequest) -> NativeTechniqueResult:
        return NativeTechniqueResult(
            technique=technique,
            formalism_id=f"{technique.value}_native",
            provider_id=declared.provider_id,
            provider_contract_version=declared.contract_version,
            source=request.source,
            payload={"technique": technique.value},
            provenance=declared.provenance,
        )

    return RuntimeProvider(declared, behaviour or result)


def all_techniques_request(text: str = "shared source") -> AggregateRequest:
    structured = tuple(
        StructuredInput(technique=technique, payload={"nodes": [technique.value]})
        for technique in BOUNDARY_TECHNIQUES
        if technique in STRUCTURED_INPUT_TECHNIQUES
    )
    return AggregateRequest.for_text(text, BOUNDARY_TECHNIQUES, structured_inputs=structured)


class TestExecutionPolicy:
    @pytest.mark.parametrize("workers", (True, 0, 8))
    def test_worker_count_is_bounded_by_the_seven_technique_boundaries(self, workers: int) -> None:
        with pytest.raises(ValueError, match="between 1 and 7"):
            ExecutionPolicy(max_workers=workers)

    def test_registry_exposure_is_immutable(self) -> None:
        machine = Machine([provider(Technique.RST)])
        with pytest.raises(TypeError):
            machine.providers[Technique.PDTB] = provider(Technique.PDTB)

    def test_different_providers_overlap_but_default_never_exceeds_four_workers(self) -> None:
        guard = Lock()
        first_wave = Barrier(4)
        active = 0
        maximum = 0
        entered = 0

        # Bind one closure per declaration so results cannot cross provider identities.
        providers: list[RuntimeProvider] = []
        request = all_techniques_request()
        for technique in BOUNDARY_TECHNIQUES:
            declared = declaration(technique)

            def run(provider_request: ProviderRequest, *, item: ProviderDeclaration = declared) -> NativeTechniqueResult:
                nonlocal active, maximum, entered
                with guard:
                    active += 1
                    entered += 1
                    ordinal = entered
                    maximum = max(maximum, active)
                if ordinal <= 4:
                    first_wave.wait(timeout=2)
                time.sleep(0.01)
                with guard:
                    active -= 1
                return NativeTechniqueResult(
                    technique=item.technique,
                    formalism_id=f"{item.technique.value}_native",
                    provider_id=item.provider_id,
                    provider_contract_version=item.contract_version,
                    source=provider_request.source,
                    payload={"ok": True},
                    provenance=item.provenance,
                )

            providers.append(RuntimeProvider(declared, run))

        aggregate = Machine(providers).analyse(request)
        assert maximum == 4
        assert tuple(outcome.result.technique for outcome in aggregate.outcomes if isinstance(outcome, ResultOutcome)) == (
            BOUNDARY_TECHNIQUES
        )

    def test_concurrent_calls_to_one_provider_instance_are_serialized(self) -> None:
        guard = Lock()
        active = 0
        maximum = 0
        declared = declaration(Technique.RST)

        def slow(request: ProviderRequest) -> NativeTechniqueResult:
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.02)
            with guard:
                active -= 1
            return NativeTechniqueResult(
                technique=Technique.RST,
                formalism_id="rst_native",
                provider_id=declared.provider_id,
                provider_contract_version=declared.contract_version,
                source=request.source,
                payload={"ok": True},
                provenance=declared.provenance,
            )

        shared_provider = RuntimeProvider(declared, slow)
        machines = (Machine([shared_provider]), Machine([shared_provider]))
        request = AggregateRequest.for_text("same", (Technique.RST,))
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(lambda machine: machine.analyse(request), machines))
        assert all(isinstance(item.outcome_for(Technique.RST), ResultOutcome) for item in results)
        assert maximum == 1

    def test_outcomes_remain_in_request_order_when_completion_order_is_reversed(self) -> None:
        pdtb_finished = Event()
        rst_declaration = declaration(Technique.RST)
        pdtb_declaration = declaration(Technique.PDTB)

        def rst_result(request: ProviderRequest) -> NativeTechniqueResult:
            assert pdtb_finished.wait(timeout=2)
            return NativeTechniqueResult(
                technique=Technique.RST,
                formalism_id="rst_native",
                provider_id=rst_declaration.provider_id,
                provider_contract_version=V1,
                source=request.source,
                payload={},
                provenance=rst_declaration.provenance,
            )

        def pdtb_result(request: ProviderRequest) -> NativeTechniqueResult:
            pdtb_finished.set()
            return NativeTechniqueResult(
                technique=Technique.PDTB,
                formalism_id="pdtb_native",
                provider_id=pdtb_declaration.provider_id,
                provider_contract_version=V1,
                source=request.source,
                payload={},
                provenance=pdtb_declaration.provenance,
            )

        aggregate = Machine(
            [RuntimeProvider(rst_declaration, rst_result), RuntimeProvider(pdtb_declaration, pdtb_result)]
        ).analyse(AggregateRequest.for_text("order", (Technique.RST, Technique.PDTB)))
        assert tuple(outcome.result.technique for outcome in aggregate.outcomes if isinstance(outcome, ResultOutcome)) == (
            Technique.RST,
            Technique.PDTB,
        )


class TestResultCache:
    def test_success_is_reused_and_written_owner_only(self, tmp_path: Path) -> None:
        cached_provider = provider(Technique.RST)
        machine = Machine([cached_provider], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        request = AggregateRequest.for_text("cache me", (Technique.RST,))

        first = machine.analyse(request)
        second = machine.analyse(request)

        assert isinstance(first.outcome_for(Technique.RST), ResultOutcome)
        assert first == second
        assert cached_provider.calls == 1
        entries = tuple(tmp_path.glob("*.json"))
        assert len(entries) == 1
        assert S_IMODE(tmp_path.stat().st_mode) == 0o700
        assert S_IMODE(entries[0].stat().st_mode) == 0o600
        assert not tuple(tmp_path.glob(".*")), "atomic temporary files must not survive"

    def test_dirty_revision_bypasses_the_cache(self, tmp_path: Path) -> None:
        dirty = provider(Technique.RST, revision="abc-dirty")
        machine = Machine([dirty], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        request = AggregateRequest.for_text("do not cache", (Technique.RST,))
        machine.analyse(request)
        machine.analyse(request)
        assert dirty.calls == 2
        assert not tuple(tmp_path.glob("*.json"))

    def test_corrupt_entry_is_deleted_warned_and_recomputed(self, tmp_path: Path) -> None:
        cached_provider = provider(Technique.RST)
        machine = Machine([cached_provider], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        request = AggregateRequest.for_text("repair", (Technique.RST,))
        machine.analyse(request)
        entry = next(tmp_path.glob("*.json"))
        entry.write_bytes(b'{"tampered":true}')

        with pytest.warns(RuntimeWarning, match="discarded corrupt RDAM cache entry"):
            outcome = machine.analyse(request)

        assert isinstance(outcome.outcome_for(Technique.RST), ResultOutcome)
        assert cached_provider.calls == 2

    def test_valid_but_request_incompatible_entry_is_rejected_and_recomputed(self, tmp_path: Path) -> None:
        cached_provider = provider(Technique.RST)
        machine = Machine([cached_provider], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        request = AggregateRequest.for_text("expected source", (Technique.RST,))
        machine.analyse(request)
        entry = next(tmp_path.glob("*.json"))
        incompatible = cached_provider.behaviour(
            ProviderRequest(
                source=SourceIdentity.from_text("different source"),
                text="different source",
                structured_input=None,
            )
        )
        entry.write_bytes(serialize(incompatible))

        with pytest.warns(RuntimeWarning, match="result_is_about_a_different_source"):
            outcome = machine.analyse(request)

        assert isinstance(outcome.outcome_for(Technique.RST), ResultOutcome)
        assert cached_provider.calls == 2

    def test_single_flight_rechecks_after_waiting_and_avoids_duplicate_calls(self, tmp_path: Path) -> None:
        declared = declaration(Technique.RST)

        def slow(request: ProviderRequest) -> NativeTechniqueResult:
            time.sleep(0.03)
            return NativeTechniqueResult(
                technique=Technique.RST,
                formalism_id="rst_native",
                provider_id=declared.provider_id,
                provider_contract_version=declared.contract_version,
                source=request.source,
                payload={"ok": True},
                provenance=declared.provenance,
            )

        cached_provider = RuntimeProvider(declared, slow)
        machine = Machine([cached_provider], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        request = AggregateRequest.for_text("single flight", (Technique.RST,))
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = tuple(executor.map(machine.analyse, (request, request)))
        assert all(isinstance(item.outcome_for(Technique.RST), ResultOutcome) for item in results)
        assert cached_provider.calls == 1

    def test_typed_failures_are_never_cached(self, tmp_path: Path) -> None:
        declared = declaration(Technique.RST)

        def fail(_request: ProviderRequest) -> NativeTechniqueResult:
            raise ProviderError(
                ProviderFailure(
                    technique=Technique.RST,
                    provider_id=declared.provider_id,
                    failed_operation="analyse",
                    retryability=Retryability.RETRYABLE,
                    code="temporary_failure",
                    exception_type="FixtureError",
                    message_template="temporary_failure",
                )
            )

        failing = RuntimeProvider(declared, fail)
        machine = Machine([failing], execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        request = AggregateRequest.for_text("fail", (Technique.RST,))
        machine.analyse(request)
        machine.analyse(request)
        assert failing.calls == 2
        assert not tuple(tmp_path.glob("*.json"))

    def test_unavailable_outcomes_are_never_cached(self, tmp_path: Path) -> None:
        machine = Machine(execution_policy=ExecutionPolicy(cache_directory=tmp_path))
        machine.analyse(AggregateRequest.for_text("unavailable", (Technique.RST,)))
        assert not tuple(tmp_path.glob("*.json"))

    def test_every_declared_key_component_changes_the_content_address(self) -> None:
        declared = declaration(Technique.RST, model="openai:model-a")
        request = ProviderRequest(
            source=SourceIdentity.from_text("source"),
            text="source",
            structured_input={"nodes": [1]},
            formalism_id="rst_native",
            derived_from=UpstreamResultReference(
                technique=Technique.PDTB,
                result_identity=NativeTechniqueResult(
                    technique=Technique.PDTB,
                    formalism_id="pdtb_native",
                    provider_id="upstream",
                    provider_contract_version=V1,
                    source=SourceIdentity.from_text("source"),
                    payload={},
                    provenance=ProviderProvenance(
                        package="upstream", version="1", source_revision="clean", licence="test"
                    ),
                ).semantic_digest,
            ),
        )
        assert request.derived_from is not None
        baseline = _cache_key(Technique.RST, declared, request)
        mutations: tuple[tuple[Technique, ProviderDeclaration, ProviderRequest], ...] = (
            (Technique.RST, declared, request.model_copy(update={"source": SourceIdentity.from_text("other")})),
            (Technique.PDTB, declared, request),
            (Technique.RST, declared, request.model_copy(update={"formalism_id": "other_formalism"})),
            (Technique.RST, declared, request.model_copy(update={"structured_input": {"nodes": [2]}})),
            (
                Technique.RST,
                declared,
                request.model_copy(
                    update={
                        "derived_from": UpstreamResultReference(
                            technique=Technique.PDTB,
                            result_identity=request.derived_from.result_identity.model_copy(
                                update={"hex_digest": "f" * 64}
                            ),
                        )
                    }
                ),
            ),
            (Technique.RST, declaration(Technique.RST, contract=SemanticVersion(root="2.0.0")), request),
            (Technique.RST, declaration(Technique.RST, revision="other-revision", model="openai:model-a"), request),
            (Technique.RST, declaration(Technique.RST, model="openai:model-b"), request),
        )
        assert all(_cache_key(technique, item, changed) != baseline for technique, item, changed in mutations)


def test_available_provider_requires_source_revision_but_historical_provenance_remains_valid() -> None:
    historical = ProviderProvenance(package="old", version="1", licence="test")
    assert historical.source_revision is None
    with pytest.raises(ValueError, match="must carry a source revision"):
        Machine([provider(Technique.RST, revision=None)])


def test_historical_native_result_without_source_revision_round_trips_byte_identically() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "machine" / "native-result-v1-no-source-revision.json"
    payload = fixture.read_bytes().rstrip(b"\n")
    record = load(payload)
    assert isinstance(record, NativeTechniqueResult)
    assert record.provenance.source_revision is None
    assert serialize(record) == payload


def test_machine_and_rst_share_byte_identical_canonical_serialization() -> None:
    from rdam import canonical_json_bytes as machine_canonical
    from rdam.rst.ingest.identity import canonical_json_bytes as rst_identity_canonical
    from rdam.rst.ingest.serialization import canonical_json_bytes as rst_serialization_canonical

    value = {"z": [3, {"é": True}], "a": {"number": 1.5, "none": None}}
    expected = machine_canonical(value)
    assert rst_identity_canonical(value) == expected
    assert rst_serialization_canonical(value) == expected


def test_production_composition_covers_all_seven_source_revisions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    machine = production_machine(model="openai:gpt-5.6-sol")
    assert len(machine.providers) == 7
    assert all(item.declaration.provenance.source_revision for item in machine.providers.values())
