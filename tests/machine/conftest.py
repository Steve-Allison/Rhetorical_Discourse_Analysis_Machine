"""Fake providers exercising the machine contract without any model or network."""

from collections.abc import Callable

import pytest
from rdam._interpretation_types import NativeInterpretationDescriptor
from rdam.contracts import ProviderConfiguration
from rdam.frameworks import STRUCTURED_INPUT_TECHNIQUES
from tests.ingest.test_projection_contracts import prose_requirement

from rdam import (
    AvailableCapability,
    CapabilityState,
    FormalismDeclaration,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    ProviderRequest,
    Retryability,
    SemanticVersion,
    Technique,
    UnavailableCapability,
    UnavailableReason,
    technique_curie,
)

V1 = SemanticVersion(root="1.0.0")
PROVENANCE = ProviderProvenance(
    package="fake-provider",
    version="0.0.0",
    source_revision="fixture-revision",
    licence="test fixture",
)


def available(provider_id: str) -> AvailableCapability:
    return AvailableCapability(provider_id=provider_id, contract_version=V1)


def formalism(formalism_id: str, technique: Technique, capability: CapabilityState) -> FormalismDeclaration:
    return FormalismDeclaration(
        formalism_id=formalism_id,
        technique=technique,
        technique_curie=technique_curie(technique),
        capability=capability,
    )


def fixture_descriptor(formalism_id: str, technique: Technique, version: SemanticVersion = V1) -> NativeInterpretationDescriptor:
    return NativeInterpretationDescriptor(
        formalism_id=formalism_id, native_contract_version="2.0.0", provider_contract_version=str(version),
        purpose="Exercise orchestration with explicit deterministic fixture behaviour.",
        input_basis="caller_structure" if technique in STRUCTURED_INPUT_TECHNIQUES else "source_projection",
        method="deterministic_computation", sections=(), evidence_rules=(),
        validation_scope=("Machine envelope and supplied fixture assertions only.",),
        limitations=("This fixture does not implement a production analytical formalism.",),
        empty_result_meaning="The fixture returned no analytical content.",
    )


def rst_declaration(*, erst_loaded: bool = True, capability: CapabilityState | None = None) -> ProviderDeclaration:
    provider_id = "fake-rst"
    return ProviderDeclaration(
        provider_id=provider_id,
        technique=Technique.RST,
        technique_curie=technique_curie(Technique.RST),
        formalisms=(
            formalism("rst_tree", Technique.RST, available(provider_id)),
            formalism(
                "erst_graph",
                Technique.ERST,
                available(provider_id)
                if erst_loaded
                else UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED),
            ),
        ),
        contract_version=V1,
        provenance=PROVENANCE,
        capability=capability if capability is not None else available(provider_id),
        requires_structured_input=False,
        content_requirement=prose_requirement(),
        configuration=ProviderConfiguration(settings={}, cache_eligible=False, cache_reason="uncached_fixture"),
        interpretations=tuple(fixture_descriptor(name, Technique.RST) for name in ("rst_tree", "erst_graph")),
    )


def dung_declaration(*, capability: CapabilityState | None = None) -> ProviderDeclaration:
    provider_id = "fake-dung"
    return ProviderDeclaration(
        provider_id=provider_id,
        technique=Technique.DUNG,
        technique_curie=technique_curie(Technique.DUNG),
        formalisms=(formalism("dung_extensions", Technique.DUNG, available(provider_id)),),
        contract_version=V1,
        provenance=PROVENANCE,
        capability=capability if capability is not None else available(provider_id),
        requires_structured_input=True,
        configuration=ProviderConfiguration(settings={}, cache_eligible=False, cache_reason="uncached_fixture"),
        interpretations=(fixture_descriptor("dung_extensions", Technique.DUNG),),
    )


class FakeProvider:
    """A provider whose behaviour is a function of the request."""

    def __init__(
        self,
        declaration: ProviderDeclaration,
        behaviour: Callable[[ProviderDeclaration, ProviderRequest], NativeTechniqueResult],
    ) -> None:
        self._declaration = declaration
        self._behaviour = behaviour
        self.calls: list[ProviderRequest] = []

    @property
    def declaration(self) -> ProviderDeclaration:
        return self._declaration

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        self.calls.append(request)
        return self._behaviour(self._declaration, request)


def echo_result(formalism_id: str) -> Callable[[ProviderDeclaration, ProviderRequest], NativeTechniqueResult]:
    def behaviour(declaration: ProviderDeclaration, request: ProviderRequest) -> NativeTechniqueResult:
        target = declaration.formalism(formalism_id)
        assert target is not None
        return NativeTechniqueResult(
            technique=target.technique,
            formalism_id=formalism_id,
            provider_id=declaration.provider_id,
            provider_contract_version=declaration.contract_version,
            source=request.source,
            payload={"text": request.text, "structured": request.structured_input},
            provenance=declaration.provenance,
        )

    return behaviour


def typed_failure(retryability: Retryability = Retryability.NOT_RETRYABLE) -> Callable[[ProviderDeclaration, ProviderRequest], NativeTechniqueResult]:
    def behaviour(declaration: ProviderDeclaration, request: ProviderRequest) -> NativeTechniqueResult:
        raise ProviderError(
            ProviderFailure(
                technique=declaration.technique,
                provider_id=declaration.provider_id,
                failed_operation="analyse",
                retryability=retryability,
                code="fixture_failure",
                exception_type="FixtureError",
                message_template="the_fixture_was_told_to_fail",
            )
        )

    return behaviour


@pytest.fixture
def rst_provider() -> FakeProvider:
    return FakeProvider(rst_declaration(), echo_result("rst_tree"))


@pytest.fixture
def dung_provider() -> FakeProvider:
    return FakeProvider(dung_declaration(), echo_result("dung_extensions"))
