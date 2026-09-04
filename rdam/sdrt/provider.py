"""LLM-assisted SDRT provider with deterministic native graph validation."""

from typing import Final
from threading import Lock

from rdam.ingest.contracts.preparation import ContentRequirement
from rdam.ingest.contracts.source import ContentClass
from rdam.ingest.requirements import llm_requirement
from rdam.ingest.alignment import align_payload

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
    UnavailableCapability,
    semantic_sha256,
    technique_curie,
)
from rdam._llm import LlmError, StructuredAnalyst, resolved_model_identity, unavailable_reason
from rdam._provider_provenance import (
    llm_provider_failure,
    provider_failure,
    provider_provenance,
    require_llm_text,
    source_identity as _source_identity,
)
from rdam._strict import JsonValue
from rdam.sdrt.graph import GraphError, SdrtAnalysis

PROVIDER_ID_PREFIX: Final = "rdam.sdrt/sdrs-graph-v1"
FORMALISM_ID: Final = "sdrs_graph"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("graph.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.sdrt", _SOURCE_FILES)


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


class SdrtProvider:
    """Produce a validated native SDRS graph from raw text."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = resolved_model_identity(model)
        self._build_lock = Lock()
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
            provenance=provider_provenance(
                package="rdam.sdrt",
                model_identity=self._model,
                licence=LICENCE,
                instructions=INSTRUCTIONS,
            ),
            capability=capability,
            requires_structured_input=False,
            content_requirement=self.content_requirement,
            parallel_safety="concurrent",
            instructions_identity=Sha256Identity(hex_digest=semantic_sha256(INSTRUCTIONS)),
        )

    @property
    def content_requirement(self) -> ContentRequirement:
        return llm_requirement(
            "sdrt/dialogue-v1",
            (ContentClass.TITLE, ContentClass.HEADING, ContentClass.PARAGRAPH, ContentClass.LIST_ITEM, ContentClass.TURN, ContentClass.CAPTION),
            requires_speaker_identity=True,
        )

    def _built(self) -> StructuredAnalyst[SdrtAnalysis]:
        with self._build_lock:
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
        text = require_llm_text(
            request.projection.prepared_document.text if request.projection is not None else request.text,
            technique=Technique.SDRT, provider_id=self.provider_id,
        )
        try:
            extraction = self._built().extract(text)
            extraction.structure.validate_source(text)
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
                llm_provider_failure(error, technique=Technique.SDRT, provider_id=self.provider_id)
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
            source_alignment=align_payload(extraction.structure.to_payload(), request.projection),
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
        return provider_failure(
            technique=Technique.SDRT,
            provider_id=self.provider_id,
            code=code,
            retryability=retryability,
            exception_type=exception_type,
            detail=detail,
            message_parameters=(
                ("output_attempts", str(output_attempts)),
                ("transport_attempts", str(transport_attempts)),
            )
            if output_attempts or transport_attempts
            else (),
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
