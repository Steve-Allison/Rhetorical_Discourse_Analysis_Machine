"""The IBIS provider: typed issue–position–argument structure, validated under the grammar (FR-017).

Any automated extraction into IBIS structure would be a separately identified and
evaluated candidate; this provider performs none. It accepts a supplied structure,
validates it against the gIBIS link grammar, and returns the organised deliberation map.
Capability comes from the promotion decision packaged with the provider, bound to the
digest of this provider's source files exactly as the Dung provider does.
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
from rdam.ibis.grammar import IbisStructure, StructureError, deliberation_map

PROVIDER_ID: Final = "rdam.ibis/gibis-grammar-v1"
FORMALISM_ID: Final = "ibis_structure"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
_SOURCE_FILES: Final = ("grammar.py", "provider.py")


def source_identity() -> Sha256Identity:
    package = resources.files("rdam.ibis")
    digest = semantic_sha256({name: sha256_bytes(package.joinpath(name).read_bytes()) for name in _SOURCE_FILES})
    return Sha256Identity(hex_digest=digest)


def packaged_decision() -> PromotionDecision | None:
    resource = resources.files("rdam.ibis").joinpath("resources/promotion-decision.json")
    if not resource.is_file():
        return None
    return load_decision(resource.read_bytes())


def _package_version() -> str:
    try:
        return version("rdam")
    except PackageNotFoundError:
        return "unknown"


class IbisProvider:
    """One promoted IBIS structural-validation implementation, declared to the machine."""

    def __init__(self, decision: PromotionDecision | None = None) -> None:
        self._decision = decision if decision is not None else packaged_decision()

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
            technique=Technique.IBIS,
            technique_curie=technique_curie(Technique.IBIS),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.IBIS,
                    technique_curie=technique_curie(Technique.IBIS),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=ProviderProvenance(
                package="rdam.ibis",
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
            structure = IbisStructure.from_payload(request.structured_input)
        except StructureError as error:
            raise ProviderError(self._failure("invalid_ibis_structure", "StructureError", str(error))) from error
        payload: dict[str, JsonValue] = {
            "structure": structure.to_payload(),
            "input_origin": "supplied",
            "extraction": None,
            "grammar": "gibis-v1",
            "map": deliberation_map(structure),
        }
        return NativeTechniqueResult(
            technique=Technique.IBIS,
            formalism_id=FORMALISM_ID,
            provider_id=PROVIDER_ID,
            provider_contract_version=CONTRACT_VERSION,
            source=request.source,
            payload=payload,
            provenance=declaration.provenance,
        )

    def _failure(self, code: str, exception_type: str, detail: str | None = None) -> ProviderFailure:
        return ProviderFailure(
            technique=Technique.IBIS,
            provider_id=PROVIDER_ID,
            failed_operation="analyse",
            retryability=Retryability.NOT_RETRYABLE,
            code=code,
            exception_type=exception_type,
            message_template=code,
            message_parameters=(("detail", detail),) if detail is not None else (),
        )


__all__ = ["CONTRACT_VERSION", "FORMALISM_ID", "PROVIDER_ID", "IbisProvider", "packaged_decision", "source_identity"]
