"""Model-free and parser-aware production capability discovery."""

from typing import Protocol
from uuid import uuid4

from rdam.rst.ingest.contracts.capabilities import (
    Availability,
    CacheEligibility,
    CacheEligibilityState,
    EvidenceCapability,
    FormalismCapability,
    ModelIdentityState,
    ProductionCapabilities,
)
from rdam.rst.ingest.contracts.inference import EvidenceDetailPolicy, OutputFormalism


class ParserDescriptor(Protocol):
    @property
    def model_release_identity(self) -> object | None: ...


def describe_capabilities(
    parser: ParserDescriptor | None = None,
) -> ProductionCapabilities:
    """Return installed capabilities without importing a model or optional adapter."""

    capabilities = ProductionCapabilities.discover(execution_id=str(uuid4()))
    if parser is None:
        return capabilities
    release_identity = getattr(parser, "model_release_identity", None)
    immutable = release_identity is not None
    family = getattr(parser, "family", None)
    canonical = callable(getattr(parser, "analyse_document", None)) and family not in {
        "dmrst",
        "unirst",
    }
    identified = hasattr(parser, "model_release_identity")
    rst_available = canonical
    erst_available = canonical and getattr(parser, "erst_checkpoint", None) is not None and callable(
        getattr(parser, "complete_erst_document", None)
    )
    formalisms = tuple(
        capability.formalism
        for capability in (
            FormalismCapability(
                formalism=OutputFormalism.RST_TREE,
                availability=(Availability.AVAILABLE if rst_available else Availability.UNAVAILABLE),
                reason=("canonical_parser_result_supported" if rst_available else "canonical_parser_result_unavailable"),
            ),
            FormalismCapability(
                formalism=OutputFormalism.ERST_GRAPH,
                availability=(Availability.AVAILABLE if erst_available else Availability.UNAVAILABLE),
                reason=("validated_erst_checkpoint_loaded" if erst_available else "validated_erst_checkpoint_not_loaded"),
            ),
        )
        if capability.availability is Availability.AVAILABLE
    )
    formalism_capabilities = (
        FormalismCapability(
            formalism=OutputFormalism.RST_TREE,
            availability=(Availability.AVAILABLE if rst_available else Availability.UNAVAILABLE),
            reason=("canonical_parser_result_supported" if rst_available else "canonical_parser_result_unavailable"),
        ),
        FormalismCapability(
            formalism=OutputFormalism.ERST_GRAPH,
            availability=(Availability.AVAILABLE if erst_available else Availability.UNAVAILABLE),
            reason=("validated_erst_checkpoint_loaded" if erst_available else "validated_erst_checkpoint_not_loaded"),
        ),
    )
    evidence_capabilities = tuple(
        EvidenceCapability(
            detail=detail,
            availability=(Availability.AVAILABLE if canonical else Availability.UNAVAILABLE),
            reason=("backend_evidence_handoff_complete" if canonical else "canonical_parser_result_unavailable"),
        )
        for detail in EvidenceDetailPolicy
    )
    semantic = capabilities.semantic.model_copy(
        update={
            "parser_identity_state": (
                ModelIdentityState.IMMUTABLE_RELEASE
                if immutable
                else ModelIdentityState.MUTABLE_INSTANCE
                if identified
                else ModelIdentityState.UNIDENTIFIED
            ),
            "active_parser_family": family if isinstance(family, str) else type(parser).__qualname__,
            "canonical_parser_result_supported": canonical,
            "exact_runtime_identity_supported": canonical and identified,
            "formalism_capabilities": formalism_capabilities,
            "evidence_capabilities": evidence_capabilities,
            "output_formalisms": formalisms,
            "evidence_detail_levels": (
                tuple(EvidenceDetailPolicy) if canonical else ()
            ),
            "cache_eligibility": CacheEligibility(
                state=(
                    CacheEligibilityState.ELIGIBLE
                    if immutable and canonical
                    else CacheEligibilityState.INELIGIBLE
                ),
                reason=(
                    "all_participating_components_immutable"
                    if immutable and canonical
                    else "parser_has_no_canonical_result_support"
                    if not canonical
                    else "parser_has_no_immutable_release_identity"
                ),
            ),
        }
    )
    return ProductionCapabilities(semantic=semantic, execution=capabilities.execution)


__all__ = ["describe_capabilities"]
