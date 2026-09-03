"""LLM-assisted SDRT provider with deterministic native graph validation."""

from importlib import resources
from importlib.metadata import PackageNotFoundError, version
from typing import Final

from rdam import (
    AvailableCapability,
    FormalismDeclaration,
    NativeTechniqueResult,
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
    semantic_sha256,
    technique_curie,
)
from rdam._llm import LlmError, StructuredAnalyst, configured_model, unavailable_reason
from rdam._strict import JsonValue, sha256_bytes
from rdam.sdrt.graph import GraphError, SdrtAnalysis

PROVIDER_ID_PREFIX: Final = "rdam.sdrt/sdrs-graph-v1"
FORMALISM_ID: Final = "sdrs_graph"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("graph.py", "provider.py")

INSTRUCTIONS: Final = """\
Analyse the passage as a Segmented Discourse Representation Structure (SDRS).

Return elementary discourse units (EDUs) in source order with exact zero-based, half-open
character offsets and exact source text. Return complex discourse units (CDUs) explicitly
when a discourse relation scopes over a group rather than a single EDU. A CDU has at least
two members and may contain EDUs or already-defined CDUs.

Return directed discourse relations from the established/source argument to the newly
attached/target argument. Preserve the relation's meaningful label and classify it as:
- coordinating: arguments continue at equal discourse level (for example Narration,
  Contrast, Parallel, Continuation);
- subordinating: the target is subordinate to the source (for example Elaboration,
  Explanation, Background, Commentary).

Every EDU after the first must attach from the current SDRT right frontier. Non-adjacent
attachments and CDUs are expected when the discourse requires them. Do not force a tree,
invent disconnected units, or claim a formal dynamic-semantic interpretation. The native
validator, not this instruction, is authoritative for graph and source correctness.
"""


def source_identity() -> Sha256Identity:
    """Digest the complete provider source surface in a fixed order."""

    package = resources.files("rdam.sdrt")
    digest = semantic_sha256(
        {name: sha256_bytes(package.joinpath(name).read_bytes()) for name in _SOURCE_FILES}
    )
    return Sha256Identity(hex_digest=digest)


def _package_version() -> str:
    try:
        return version("rdam")
    except PackageNotFoundError:
        return "unknown"


class SdrtProvider:
    """Produce a validated native SDRS graph from raw text."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model or configured_model()
        self._analyst: StructuredAnalyst[SdrtAnalysis] | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_id(self) -> str:
        return f"{PROVIDER_ID_PREFIX}/{self._model}"

    @property
    def declaration(self) -> ProviderDeclaration:
        """Describe capability without constructing a model client."""

        reason = unavailable_reason(self._model)
        capability = (
            AvailableCapability(provider_id=self.provider_id, contract_version=CONTRACT_VERSION)
            if reason is None
            else UnavailableCapability(reason=reason)
        )
        return ProviderDeclaration(
            provider_id=self.provider_id,
            technique=Technique.SDRT,
            technique_curie=technique_curie(Technique.SDRT),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.SDRT,
                    technique_curie=technique_curie(Technique.SDRT),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=ProviderProvenance(
                package="rdam.sdrt",
                version=_package_version(),
                source_revision=source_identity().hex_digest,
                model_identity=self._model,
                licence=LICENCE,
            ),
            capability=capability,
            requires_structured_input=False,
        )

    def _built(self) -> StructuredAnalyst[SdrtAnalysis]:
        if self._analyst is None:
            self._analyst = StructuredAnalyst(
                output_type=SdrtAnalysis,
                instructions=INSTRUCTIONS,
                model=self._model,
            )
        return self._analyst

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if not isinstance(declaration.capability, AvailableCapability):
            raise ProviderError(
                self._failure(
                    "provider_not_available",
                    Retryability.NOT_RETRYABLE,
                    "ValueError",
                    declaration.capability.reason.value,
                )
            )
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(
                self._failure(
                    "formalism_not_declared",
                    Retryability.NOT_RETRYABLE,
                    "ValueError",
                    str(request.formalism_id),
                )
            )
        if request.text is None or not request.text.strip():
            raise ProviderError(
                self._failure("text_required", Retryability.NOT_RETRYABLE, "ValueError")
            )
        try:
            extraction = self._built().extract(request.text)
            extraction.structure.validate_source(request.text)
        except GraphError as error:
            raise ProviderError(
                self._failure(
                    "invalid_sdrs_source",
                    Retryability.NOT_RETRYABLE,
                    "GraphError",
                    str(error),
                )
            ) from error
        except LlmError as error:
            raise ProviderError(
                self._failure(
                    error.code,
                    error.retryability,
                    "LlmError",
                    error.detail,
                    output_attempts=error.output_attempts,
                    transport_attempts=error.transport_attempts,
                )
            ) from error
        payload: dict[str, JsonValue] = {
            **extraction.structure.to_payload(),
            "extraction": {
                "model": extraction.model,
                "output_attempts": extraction.output_attempts,
                "transport_attempts": extraction.transport_attempts,
                "instructions_digest": semantic_sha256(INSTRUCTIONS),
            },
        }
        return NativeTechniqueResult(
            technique=Technique.SDRT,
            formalism_id=FORMALISM_ID,
            provider_id=self.provider_id,
            provider_contract_version=CONTRACT_VERSION,
            source=request.source,
            payload=payload,
            provenance=declaration.provenance,
        )

    def _failure(
        self,
        code: str,
        retryability: Retryability,
        exception_type: str,
        detail: str | None = None,
        *,
        output_attempts: int = 0,
        transport_attempts: int = 0,
    ) -> ProviderFailure:
        parameters = [] if detail is None else [("detail", detail)]
        if output_attempts or transport_attempts:
            parameters.extend(
                (
                    ("output_attempts", str(output_attempts)),
                    ("transport_attempts", str(transport_attempts)),
                )
            )
        return ProviderFailure(
            technique=Technique.SDRT,
            provider_id=self.provider_id,
            failed_operation="analyse",
            retryability=retryability,
            code=code,
            exception_type=exception_type,
            message_template=code,
            message_parameters=tuple(parameters),
        )


__all__ = [
    "CONTRACT_VERSION",
    "FORMALISM_ID",
    "INSTRUCTIONS",
    "LICENCE",
    "PROVIDER_ID_PREFIX",
    "SdrtProvider",
    "source_identity",
]
