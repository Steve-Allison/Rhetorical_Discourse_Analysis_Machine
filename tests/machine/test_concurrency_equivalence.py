"""Concurrent execution preserves semantics and distinguishes failures from bugs."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from threading import Barrier
import os
from time import perf_counter, sleep

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from rdam import (
    AggregateRequest,
    ExecutionPolicy,
    FailedOutcome,
    Machine,
    NativeTechniqueResult,
    ProviderRequest,
    ResultOutcome,
    Technique,
)
from tests.machine.test_shared_runtime import RuntimeProvider, declaration
from tests.machine.conftest import FakeProvider, echo_result, rst_declaration, typed_failure
from rdam.toulmin import ToulminProvider
from rdam.walton import WaltonProvider
from rdam.pdtb import PdtbProvider
from rdam.sdrt import SdrtProvider


def test_parallel_and_serial_aggregate_digests_match_and_work_overlaps() -> None:
    barrier = Barrier(4)
    parallel = True
    techniques = (Technique.TOULMIN, Technique.WALTON, Technique.PDTB, Technique.SDRT)
    providers = []
    process = os.getpid()
    for technique in techniques:
        declared = declaration(technique)

        def run(request: ProviderRequest, item=declared) -> NativeTechniqueResult:
            assert os.getpid() == process
            if parallel:
                barrier.wait(timeout=5)
            sleep(0.06)
            return NativeTechniqueResult(
                technique=item.technique,
                formalism_id=f"{item.technique.value}_native",
                provider_id=item.provider_id,
                provider_contract_version=item.contract_version,
                source=request.source,
                payload={"native": item.technique.value},
                provenance=item.provenance,
            )

        providers.append(RuntimeProvider(declared, run))
    request = AggregateRequest.for_text("Evidence.", techniques)
    Machine().analyse(request)  # Warm the shared format imports equally before timing either policy.
    started = perf_counter()
    concurrent = Machine(providers).analyse(request)
    concurrent_time = perf_counter() - started
    parallel = False
    started = perf_counter()
    sequential = Machine(providers, execution_policy=ExecutionPolicy(max_workers=1)).analyse(request)
    sequential_time = perf_counter() - started
    assert concurrent.semantic_digest == sequential.semantic_digest
    assert concurrent_time < sequential_time * 0.8


def test_four_model_backed_techniques_overlap_at_the_external_model_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    providers = (ToulminProvider(), WaltonProvider(), PdtbProvider(), SdrtProvider())
    techniques = tuple(provider.declaration.technique for provider in providers)
    text = "Evidence supports the decision."
    proposals = (
        {"layouts": []},
        {"instances": []},
        {"relations": []},
        {"edus": [{"unit_id": "e1", "text": text, "start": 0, "end": len(text)}], "relations": []},
    )
    request = AggregateRequest.for_text(text, techniques)
    Machine().analyse(request)
    barrier = Barrier(4)
    parallel = True
    process = os.getpid()
    with ExitStack() as stack:
        for provider, proposal in zip(providers, proposals, strict=True):

            def respond(_messages: list[ModelMessage], info: AgentInfo, payload=proposal) -> ModelResponse:
                assert os.getpid() == process
                if parallel:
                    barrier.wait(timeout=10)
                sleep(0.15)
                return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, payload)])

            stack.enter_context(provider._built().agent.override(model=FunctionModel(respond)))
        started = perf_counter()
        concurrent = Machine(providers).analyse(request)
        concurrent_time = perf_counter() - started
        parallel = False
        started = perf_counter()
        sequential = Machine(providers, execution_policy=ExecutionPolicy(max_workers=1)).analyse(request)
        sequential_time = perf_counter() - started
    assert all(isinstance(outcome, ResultOutcome) for outcome in concurrent.outcomes)
    assert concurrent.semantic_digest == sequential.semantic_digest
    assert concurrent_time < sequential_time * 0.8, (concurrent_time, sequential_time)


def test_safe_provider_can_overlap_across_machine_instances() -> None:
    barrier = Barrier(2)
    declared = declaration(Technique.RST)

    def run(request: ProviderRequest) -> NativeTechniqueResult:
        barrier.wait(timeout=5)
        return NativeTechniqueResult(
            technique=Technique.RST,
            formalism_id="rst_native",
            provider_id=declared.provider_id,
            provider_contract_version=declared.contract_version,
            source=request.source,
            payload={},
            provenance=declared.provenance,
        )

    instance = RuntimeProvider(declared, run)
    request = AggregateRequest.for_text("Source.", (Technique.RST,))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.map(lambda machine: machine.analyse(request), (Machine([instance]), Machine([instance])))
        )
    assert results[0].semantic_digest == results[1].semantic_digest


def test_typed_failure_preserves_success_but_bug_propagates() -> None:
    good = RuntimeProvider(
        declaration(Technique.TOULMIN),
        lambda request: NativeTechniqueResult(
            technique=Technique.TOULMIN,
            formalism_id="toulmin_native",
            provider_id="fixture/toulmin",
            provider_contract_version=declaration(Technique.TOULMIN).contract_version,
            source=request.source,
            payload={},
            provenance=declaration(Technique.TOULMIN).provenance,
        ),
    )
    failing = FakeProvider(rst_declaration(), typed_failure())
    request = AggregateRequest.for_text("Source.", (Technique.RST, Technique.TOULMIN))
    result = Machine([failing, good]).analyse(request)
    assert isinstance(result.outcome_for(Technique.RST), FailedOutcome)
    assert isinstance(result.outcome_for(Technique.TOULMIN), ResultOutcome)

    def bug(_request: ProviderRequest) -> NativeTechniqueResult:
        raise KeyError("implementation defect")

    with pytest.raises(KeyError, match="implementation defect"):
        Machine(
            [
                FakeProvider(rst_declaration(), echo_result("rst_tree")),
                RuntimeProvider(declaration(Technique.TOULMIN), bug),
            ]
        ).analyse(request)
