"""The machine: capability reporting and aggregate analysis over independent providers.

Rules implemented here, from the 006 contracts:

- Capability reporting is side-effect-free: it reads provider *declarations*, never
  loads a model, never runs anything (capability contract §Aggregate behaviour 2).
- An aggregate request over N techniques returns N explicit outcomes. A technique with no
  promoted provider is ``unavailable(no_promoted_implementation)``; a provider whose
  standing state is unavailable reports its reason; a structured-input technique with no
  structured input is ``unavailable(missing_structured_input)``; a provider's typed
  failure is a ``failed`` outcome. One provider's failure never suppresses another's
  success (FR-014, SC-005).
- The machine never retries (§Retryability). A provider may raise only ``ProviderError``;
  anything else is a bug and propagates natively rather than being relabelled as a
  provider failure (standardised pattern P9).
"""

from collections.abc import Iterable, Mapping
from typing import Protocol

from rdam.contracts import (
    AggregateAnalysis,
    AggregateRequest,
    AvailableCapability,
    FailedOutcome,
    MachineCapabilities,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderRequest,
    ResultOutcome,
    Retryability,
    TechniqueCapability,
    UnavailableCapability,
    UnavailableOutcome,
    UnavailableReason,
)
from rdam.frameworks import BOUNDARY_TECHNIQUES, STRUCTURED_INPUT_TECHNIQUES, Technique, technique_curie


class Provider(Protocol):
    """An independently callable, promoted implementation for one technique (006 data model §Provider)."""

    @property
    def declaration(self) -> ProviderDeclaration: ...

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        """Return this technique's native result, or raise ``ProviderError`` with a typed failure."""
        ...


class Machine:
    """Runs several techniques side by side without collapsing them into one formalism."""

    def __init__(self, providers: Iterable[Provider] = ()) -> None:
        registry: dict[Technique, Provider] = {}
        for provider in providers:
            technique = provider.declaration.technique
            if technique in registry:
                raise ValueError(f"two providers declare {technique.value}; a boundary has exactly one provider")
            registry[technique] = provider
        self._providers: Mapping[Technique, Provider] = registry

    @property
    def providers(self) -> Mapping[Technique, Provider]:
        return self._providers

    def capabilities(self) -> MachineCapabilities:
        """Every boundary technique in exactly one state, from declarations alone."""

        techniques: list[TechniqueCapability] = []
        for technique in BOUNDARY_TECHNIQUES:
            provider = self._providers.get(technique)
            if provider is None:
                techniques.append(
                    TechniqueCapability(
                        technique=technique,
                        technique_curie=technique_curie(technique),
                        capability=UnavailableCapability(reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION),
                        requires_structured_input=technique in STRUCTURED_INPUT_TECHNIQUES,
                    )
                )
                continue
            declaration = provider.declaration
            techniques.append(
                TechniqueCapability(
                    technique=technique,
                    technique_curie=declaration.technique_curie,
                    capability=declaration.capability,
                    formalisms=declaration.formalisms,
                    requires_structured_input=declaration.requires_structured_input,
                )
            )
        return MachineCapabilities(techniques=tuple(techniques))

    def analyse(self, request: AggregateRequest) -> AggregateAnalysis:
        """One explicit outcome per requested technique; successes are preserved untouched."""

        outcomes: list[ResultOutcome | UnavailableOutcome | FailedOutcome] = []
        for technique in request.techniques:
            outcomes.append(self._analyse_one(technique, request))
        return AggregateAnalysis(source=request.source, outcomes=tuple(outcomes))

    def _analyse_one(
        self,
        technique: Technique,
        request: AggregateRequest,
    ) -> ResultOutcome | UnavailableOutcome | FailedOutcome:
        provider = self._providers.get(technique)
        if provider is None:
            return UnavailableOutcome(technique=technique, reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION)
        declaration = provider.declaration
        if isinstance(declaration.capability, UnavailableCapability):
            return UnavailableOutcome(technique=technique, reason=declaration.capability.reason)
        structured_input = request.structured_input_for(technique)
        if declaration.requires_structured_input and structured_input is None:
            return UnavailableOutcome(technique=technique, reason=UnavailableReason.MISSING_STRUCTURED_INPUT)
        chosen = request.formalism_for(technique)
        if chosen is not None:
            formalism = declaration.formalism(chosen)
            if formalism is None:
                return UnavailableOutcome(technique=technique, reason=UnavailableReason.NO_PROMOTED_IMPLEMENTATION)
            if isinstance(formalism.capability, UnavailableCapability):
                return UnavailableOutcome(technique=technique, reason=formalism.capability.reason)
        provider_request = ProviderRequest(
            source=request.source, text=request.text, structured_input=structured_input, formalism_id=chosen
        )
        try:
            result = provider.analyse(provider_request)
        except ProviderError as error:
            return FailedOutcome(failure=error.failure)
        violation = _result_contract_violation(declaration, request, result)
        if violation is not None:
            return FailedOutcome(
                failure=ProviderFailure(
                    technique=technique,
                    provider_id=declaration.provider_id,
                    failed_operation="analyse",
                    retryability=Retryability.NOT_RETRYABLE,
                    code="provider_result_contract_violation",
                    exception_type="ContractViolation",
                    message_template=violation,
                )
            )
        return ResultOutcome(result=result)


def _result_contract_violation(
    declaration: ProviderDeclaration,
    request: AggregateRequest,
    result: NativeTechniqueResult,
) -> str | None:
    """A provider that returns a result outside its own declaration has failed, deterministically."""

    if result.provider_id != declaration.provider_id:
        return "result_names_a_different_provider"
    if result.source != request.source:
        return "result_is_about_a_different_source"
    formalism = declaration.formalism(result.formalism_id)
    if formalism is None:
        return "result_formalism_is_not_declared"
    if result.technique is not formalism.technique:
        return "result_technique_differs_from_its_formalism"
    if not isinstance(formalism.capability, AvailableCapability):
        return "result_formalism_is_declared_unavailable"
    return None


__all__ = ["Machine", "Provider"]
