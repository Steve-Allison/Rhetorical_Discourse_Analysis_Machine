"""The machine: capability reporting and aggregate analysis over independent providers.

Rules implemented here, from the 006 contracts:

- Capability reporting is side-effect-free: it reads provider *declarations*, never
  loads a model, never runs anything (capability contract §Aggregate behaviour 2).
- An aggregate request over N techniques returns N explicit outcomes. A technique with no
  registered provider is ``unavailable(not_implemented)``; a provider whose
  standing state is unavailable reports its reason; a structured-input technique with no
  structured input is ``unavailable(missing_structured_input)``; a provider's typed
  failure is a ``failed`` outcome. One provider's failure never suppresses another's
  success (FR-014, SC-005).
- The machine never retries (§Retryability). A provider may raise only ``ProviderError``;
  anything else is a bug and propagates natively rather than being relabelled as a
  provider failure (standardised pattern P9).
- Lineage is recorded, never invented (FR-015). When a request carries an earlier native
  result and a structured input declares it was derived from that result, the machine
  re-emits the upstream result untouched, hands the consumer the declared derivation, and
  records a ``ProviderDependencyReference`` naming the exact upstream artifact and both
  provider identities. The machine never derives one technique's input from another's
  output itself.
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
    ProviderDependencyReference,
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
    """An independently callable implementation for one technique (006 data model §Provider)."""

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
                        capability=UnavailableCapability(reason=UnavailableReason.NOT_IMPLEMENTED),
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
        """One explicit outcome per requested technique; successes are preserved untouched.

        Upstream results the request carries are re-emitted verbatim, and every declared
        derivation whose consumer produced a result becomes one lineage reference.
        """

        outcomes: list[ResultOutcome | UnavailableOutcome | FailedOutcome] = [
            ResultOutcome(result=upstream) for upstream in request.upstream_results
        ]
        lineage: list[ProviderDependencyReference] = []
        for technique in request.techniques:
            outcome = self._analyse_one(technique, request)
            outcomes.append(outcome)
            derivation = request.derivation_for(technique)
            if derivation is None or not isinstance(outcome, ResultOutcome):
                continue
            upstream = request.upstream_result(derivation)
            if upstream is None or upstream.semantic_digest is None:
                raise ValueError("a validated request carries every upstream result its derivations name")
            lineage.append(
                ProviderDependencyReference(
                    consumer_technique=technique,
                    consumer_provider_id=outcome.result.provider_id,
                    consumer_contract_version=outcome.result.provider_contract_version,
                    upstream_technique=upstream.technique,
                    upstream_provider_id=upstream.provider_id,
                    upstream_contract_version=upstream.provider_contract_version,
                    upstream_result_identity=upstream.semantic_digest,
                    upstream_model_identity=upstream.provenance.model_identity,
                )
            )
        return AggregateAnalysis(source=request.source, outcomes=tuple(outcomes), lineage=tuple(lineage))

    def _analyse_one(
        self,
        technique: Technique,
        request: AggregateRequest,
    ) -> ResultOutcome | UnavailableOutcome | FailedOutcome:
        provider = self._providers.get(technique)
        if provider is None:
            return UnavailableOutcome(technique=technique, reason=UnavailableReason.NOT_IMPLEMENTED)
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
                return UnavailableOutcome(technique=technique, reason=UnavailableReason.NOT_IMPLEMENTED)
            if isinstance(formalism.capability, UnavailableCapability):
                return UnavailableOutcome(technique=technique, reason=formalism.capability.reason)
        provider_request = ProviderRequest(
            source=request.source,
            text=request.text,
            structured_input=structured_input,
            formalism_id=chosen,
            derived_from=request.derivation_for(technique),
        )
        try:
            result = provider.analyse(provider_request)
        except ProviderError as error:
            violation = _failure_contract_violation(declaration, error.failure)
            if violation is None:
                return FailedOutcome(failure=error.failure)
            return FailedOutcome(
                failure=_contract_failure(
                    technique,
                    declaration,
                    code="provider_failure_contract_violation",
                    violation=violation,
                )
            )
        violation = _result_contract_violation(declaration, request, result)
        if violation is not None:
            return FailedOutcome(
                failure=_contract_failure(
                    technique,
                    declaration,
                    code="provider_result_contract_violation",
                    violation=violation,
                )
            )
        return ResultOutcome(result=result)


def production_machine(*, model: str | None = None) -> Machine:
    """Construct the supported seven-technique production composition.

    Provider imports stay local so importing :mod:`rdam` remains cheap. Construction
    reads declarations only; RST models and LLM clients remain lazy until invocation.
    ``model`` selects one explicit identity for every LLM-backed technique.
    """

    from rdam.dung import DungProvider
    from rdam.ibis import IbisProvider
    from rdam.pdtb import PdtbProvider
    from rdam.rst.provider import RstProvider
    from rdam.sdrt import SdrtProvider
    from rdam.toulmin import ToulminProvider
    from rdam.walton import WaltonProvider

    return Machine(
        (
            RstProvider(),
            PdtbProvider(model=model),
            SdrtProvider(model=model),
            ToulminProvider(model=model),
            WaltonProvider(model=model),
            DungProvider(),
            IbisProvider(),
        )
    )


def _result_contract_violation(
    declaration: ProviderDeclaration,
    request: AggregateRequest,
    result: NativeTechniqueResult,
) -> str | None:
    """A provider that returns a result outside its own declaration has failed, deterministically."""

    if result.provider_id != declaration.provider_id:
        return "result_names_a_different_provider"
    if result.provider_contract_version != declaration.contract_version:
        return "result_contract_version_differs_from_declaration"
    if result.provenance != declaration.provenance:
        return "result_provenance_differs_from_declaration"
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


def _failure_contract_violation(
    declaration: ProviderDeclaration,
    failure: ProviderFailure,
) -> str | None:
    if failure.technique is not declaration.technique:
        return "failure_technique_differs_from_declaration"
    if failure.provider_id != declaration.provider_id:
        return "failure_names_a_different_provider"
    if failure.failed_operation != "analyse":
        return "failure_operation_is_not_analyse"
    return None


def _contract_failure(
    technique: Technique,
    declaration: ProviderDeclaration,
    *,
    code: str,
    violation: str,
) -> ProviderFailure:
    return ProviderFailure(
        technique=technique,
        provider_id=declaration.provider_id,
        failed_operation="analyse",
        retryability=Retryability.NOT_RETRYABLE,
        code=code,
        exception_type="ContractViolation",
        message_template=violation,
    )


__all__ = ["Machine", "Provider", "production_machine"]
