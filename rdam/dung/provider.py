"""The Dung provider: formal evaluation of a supplied argumentation framework (FR-016).

The semantics are exact and deterministic, so the provider is available whenever it is
imported. It never derives a framework from text: it evaluates the structure the caller
supplies, or the one the caller explicitly declares it derived from another technique's
result. Reporting capability computes a digest of two source files and nothing else.
"""

from typing import Final

from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
    ProviderDeclaration,
    ProviderError,
    ProviderFailure,
    ProviderRequest,
    Retryability,
    SemanticVersion,
    Sha256Identity,
    Technique,
    technique_curie,
)
from rdam._provider_provenance import provider_failure, provider_provenance, source_identity as _source_identity
from rdam._immutable_json import thaw_json
from rdam._strict import JsonValue
from rdam.dung.semantics import (
    DEFAULT_CAPACITY,
    ArgumentationFramework,
    FrameworkCapacityError,
    FrameworkError,
    evaluate,
    validate_capacity,
)

PROVIDER_ID: Final = "rdam.dung/exhaustive-subset-v1"
FORMALISM_ID: Final = "dung_extensions"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE)"
_SOURCE_FILES: Final = ("semantics.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.dung", _SOURCE_FILES)


def input_origin(request: ProviderRequest) -> str:
    """``supplied`` by the caller as-is, or ``explicitly_derived`` from a named upstream result (FR-016)."""

    return "explicitly_derived" if request.derived_from is not None else "supplied"


class DungProvider:
    """Dung abstract argumentation semantics, declared to the machine."""

    def __init__(self, *, capacity: int = DEFAULT_CAPACITY) -> None:
        self._capacity = validate_capacity(capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def declaration(self) -> ProviderDeclaration:
        capability = AvailableCapability(provider_id=PROVIDER_ID, contract_version=CONTRACT_VERSION)
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
            provenance=provider_provenance(
                package="rdam.dung",
                licence=LICENCE,
            ),
            capability=capability,
            requires_structured_input=True,
        )

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(self._failure("formalism_not_declared", "ValueError", str(request.formalism_id)))
        if request.structured_input is None:
            raise ProviderError(self._failure("structured_input_required", "ValueError"))
        try:
            framework = ArgumentationFramework.from_payload(thaw_json(request.structured_input))
        except FrameworkError as error:
            raise ProviderError(
                self._failure("invalid_argumentation_framework", "FrameworkError", str(error))
            ) from error
        try:
            semantics = evaluate(framework, capacity=self._capacity)
        except FrameworkCapacityError as error:
            raise ProviderError(
                self._failure("framework_exceeds_declared_capacity", "FrameworkCapacityError", str(error))
            ) from error
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
        return provider_failure(
            technique=Technique.DUNG,
            provider_id=PROVIDER_ID,
            code=code,
            retryability=Retryability.NOT_RETRYABLE,
            exception_type=exception_type,
            detail=detail,
        )


__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "LICENCE",
    "PROVIDER_ID",
    "DungProvider",
    "input_origin",
    "source_identity",
]
