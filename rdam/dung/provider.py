"""The Dung provider: formal evaluation of a supplied argumentation framework (FR-016).

Capability comes from the promotion decision packaged with the provider
(``resources/promotion-decision.json``): the decision names the exact source identity of
this provider's code, so a change to the semantics without a new decision makes the
provider ``unavailable(no_promoted_implementation)`` — the decision cannot be inherited by
code it did not evaluate. Reporting capability computes a digest of two source files and
reads one JSON file; it never evaluates a framework.
"""

from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from typing import Final

from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
    PromotionDecision,
    PromotionOutcome,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    ProviderRequest,
    Retryability,
    SemanticVersion,
    Sha256Identity,
    Technique,
    UnavailableCapability,
    UnavailableReason,
    load_decision,
    semantic_sha256,
    technique_curie,
)
from rdam._strict import JsonValue, sha256_bytes
from rdam.dung.semantics import (
    DEFAULT_CAPACITY,
    ArgumentationFramework,
    FrameworkCapacityError,
    FrameworkError,
    evaluate,
)

PROVIDER_ID: Final = "rdam.dung/exhaustive-subset-v1"
FORMALISM_ID: Final = "dung_extensions"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
_SOURCE_FILES: Final = ("semantics.py", "provider.py")


def source_identity() -> Sha256Identity:
    """Digest of the provider's evaluated source files, in a fixed order."""

    package = resources.files("rdam.dung")
    digest = semantic_sha256(
        {name: sha256_bytes(package.joinpath(name).read_bytes()) for name in _SOURCE_FILES}
    )
    return Sha256Identity(hex_digest=digest)


def packaged_decision() -> PromotionDecision | None:
    resource = resources.files("rdam.dung").joinpath("resources/promotion-decision.json")
    if not resource.is_file():
        return None
    return load_decision(resource.read_bytes())


def _package_version() -> str:
    try:
        return version("rdam")
    except PackageNotFoundError:
        return "unknown"


def input_origin(request: ProviderRequest) -> str:
    """``supplied`` by the caller as-is, or ``explicitly_derived`` from a named upstream result (FR-016)."""

    return "explicitly_derived" if request.derived_from is not None else "supplied"


class DungProvider:
    """One promoted Dung semantics implementation, declared to the machine."""

    def __init__(self, decision: PromotionDecision | None = None, *, capacity: int = DEFAULT_CAPACITY) -> None:
        self._decision = decision if decision is not None else packaged_decision()
        self._capacity = capacity

    @property
    def decision(self) -> PromotionDecision | None:
        return self._decision

    def _unavailable_reason(self) -> UnavailableReason | None:
        decision = self._decision
        if decision is None:
            return UnavailableReason.NO_PROMOTED_IMPLEMENTATION
        if decision.candidate.candidate_id != PROVIDER_ID or decision.candidate.artifact_identity != source_identity():
            return UnavailableReason.NO_PROMOTED_IMPLEMENTATION
        return {
            PromotionOutcome.PROMOTE: None,
            PromotionOutcome.REPLACE: None,
            PromotionOutcome.WITHHOLD: UnavailableReason.WITHHELD,
            PromotionOutcome.RETIRE: UnavailableReason.RETIRED,
        }[decision.outcome]

    @property
    def declaration(self) -> ProviderDeclaration:
        reason = self._unavailable_reason()
        capability = (
            AvailableCapability(provider_id=PROVIDER_ID, contract_version=CONTRACT_VERSION)
            if reason is None
            else UnavailableCapability(reason=reason)
        )
        decision = self._decision
        return ProviderDeclaration(
            provider_id=PROVIDER_ID,
            technique=Technique.DUNG,
            technique_curie=technique_curie(Technique.DUNG),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.DUNG,
                    technique_curie=technique_curie(Technique.DUNG),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=ProviderProvenance(
                package="rdam.dung",
                version=_package_version(),
                source_revision=source_identity().hex_digest,
                licence_decision=decision.licensing.decision_note if decision is not None else "no promotion decision packaged",
            ),
            capability=capability,
            requires_structured_input=True,
        )

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if not isinstance(declaration.capability, AvailableCapability):
            raise ProviderError(self._failure("provider_not_available", "ValueError", declaration.capability.reason.value))
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(self._failure("formalism_not_declared", "ValueError", str(request.formalism_id)))
        if request.structured_input is None:
            raise ProviderError(self._failure("structured_input_required", "ValueError"))
        try:
            framework = ArgumentationFramework.from_payload(request.structured_input)
        except FrameworkError as error:
            raise ProviderError(self._failure("invalid_argumentation_framework", "FrameworkError", str(error))) from error
        try:
            semantics = evaluate(framework, capacity=self._capacity)
        except FrameworkCapacityError as error:
            raise ProviderError(self._failure("framework_exceeds_declared_capacity", "FrameworkCapacityError", str(error))) from error
        algorithm: dict[str, JsonValue] = {"name": "exhaustive-subset", "version": "1", "capacity": self._capacity}
        payload: dict[str, JsonValue] = {
            "framework": framework.to_payload(),
            "input_origin": input_origin(request),
            "extensions": semantics.to_payload(framework),
            "algorithm": algorithm,
        }
        if request.derived_from is not None:
            # FR-016: a framework explicitly derived from another technique's result names
            # that exact result; the machine records the same consumption as lineage.
            payload["derived_from"] = {
                "technique": request.derived_from.technique.value,
                "result_identity": request.derived_from.result_identity.hex_digest,
            }
        return NativeTechniqueResult(
            technique=Technique.DUNG,
            formalism_id=FORMALISM_ID,
            provider_id=PROVIDER_ID,
            provider_contract_version=CONTRACT_VERSION,
            source=request.source,
            payload=payload,
            provenance=declaration.provenance,
        )

    def _failure(self, code: str, exception_type: str, detail: str | None = None) -> ProviderFailure:
        return ProviderFailure(
            technique=Technique.DUNG,
            provider_id=PROVIDER_ID,
            failed_operation="analyse",
            retryability=Retryability.NOT_RETRYABLE,
            code=code,
            exception_type=exception_type,
            message_template=code,
            message_parameters=(("detail", detail),) if detail is not None else (),
        )


__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "PROVIDER_ID",
    "DungProvider",
    "input_origin",
    "packaged_decision",
    "source_identity",
]
