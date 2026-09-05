"""The IBIS provider: typed issue-position-argument structure, validated under the grammar (FR-017).

Any automated extraction into IBIS structure would be a separate implementation; this
provider performs none. It accepts a supplied structure, validates it against the gIBIS
link grammar, and returns the organised deliberation map. The grammar is exact, so the
provider is available whenever it is imported.
"""

from typing import Final
from rdam.contracts import ProviderConfiguration
from rdam.ibis.interpretation import describe

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
from rdam.ibis.grammar import IbisStructure, StructureError, deliberation_map

PROVIDER_ID: Final = "rdam.ibis/gibis-grammar-v1"
FORMALISM_ID: Final = "ibis_structure"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE)"
_SOURCE_FILES: Final = ("grammar.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.ibis", _SOURCE_FILES)


class IbisProvider:
    """gIBIS structural validation, declared to the machine."""

    @property
    def declaration(self) -> ProviderDeclaration:
        capability = AvailableCapability(provider_id=PROVIDER_ID, contract_version=CONTRACT_VERSION)
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
            provenance=provider_provenance(
                package="rdam.ibis",
                licence=LICENCE,
            ),
            capability=capability,
            requires_structured_input=True,
            configuration=ProviderConfiguration(settings={}, cache_eligible=True,
                cache_reason="deterministic_supplied_structure"),
            interpretations=(describe(FORMALISM_ID, str(CONTRACT_VERSION)),),
        )

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(self._failure("formalism_not_declared", "ValueError", str(request.formalism_id)))
        if request.structured_input is None:
            raise ProviderError(self._failure("structured_input_required", "ValueError"))
        try:
            structure = IbisStructure.from_payload(thaw_json(request.structured_input))
        except StructureError as error:
            raise ProviderError(self._failure("invalid_ibis_structure", "StructureError", str(error))) from error
        payload: dict[str, JsonValue] = {
            "structure": structure.to_payload(),
            "input_origin": "explicitly_derived" if request.derived_from is not None else "supplied",
            "extraction": None,
            "grammar": "gibis-v1",
            "map": deliberation_map(structure),
        }
        if request.derived_from is not None:
            # FR-017: a structure the caller explicitly derived from another technique's
            # result names that exact result; ``extraction`` stays None -- nothing here
            # extracted anything, the derivation was the caller's.
            payload["derived_from"] = {
                "technique": request.derived_from.technique.value,
                "result_identity": request.derived_from.result_identity.hex_digest,
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
        return provider_failure(
            technique=Technique.IBIS,
            provider_id=PROVIDER_ID,
            code=code,
            retryability=Retryability.NOT_RETRYABLE,
            exception_type=exception_type,
            detail=detail,
        )


__all__ = ["CONTRACT_VERSION", "FORMALISM_ID", "LICENCE", "PROVIDER_ID", "IbisProvider", "source_identity"]
