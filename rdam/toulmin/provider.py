"""The Toulmin provider: text in, a validated Toulmin layout out (FR-019, FR-031, FR-032).

Toulmin analysis has no classical algorithm — recovering an unstated warrant is the hard
part and is exactly what a language model is for. So this is an LLM-backed provider, which
006 FR-032 makes a first-class production provider rather than a deferred one.

The model proposes; :mod:`rdam.toulmin.argument` disposes. A proposal that is not a valid
:class:`~rdam.toulmin.argument.ToulminAnalysis` never reaches the caller, and a layout
without a genuine warrant is refused rather than downgraded to a claim-and-premise pair
(FR-019). Capability is whether the configured model can be reached — no gate, no
ceremony.
"""

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
from rdam.toulmin.argument import LayoutError, ToulminAnalysis

PROVIDER_ID_PREFIX: Final = "rdam.toulmin/layout-v1"
FORMALISM_ID: Final = "toulmin_layout"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("argument.py", "provider.py")


def source_identity() -> Sha256Identity:
    return _source_identity("rdam.toulmin", _SOURCE_FILES)


INSTRUCTIONS: Final = """\
You analyse a passage into Stephen Toulmin's layout of argument (1958).

For each distinct argument in the passage, identify:
- claim: the assertion the arguer wants accepted.
- grounds: the facts or evidence offered for it, as they appear in the passage.
- warrant: the general inference licence that authorises moving from those grounds to
  that claim. It is usually UNSTATED. Recovering it is the core of the analysis. State it
  as a general principle the arguer must be relying on. Never restate the claim or a
  ground as the warrant — if no licence connects them, there is no argument here.
- backing: what makes the warrant credible, if the passage offers any. Backing supports
  the WARRANT, never the claim directly.
- qualifier: the force attached to the claim ("presumably", "in most cases"), if present.
- rebuttals: conditions under which the warrant would not license the claim, if given.

Quote spans from the passage for grounds where you can. Do not invent arguments: if the
passage asserts without arguing, return an empty list of layouts.
"""


class ToulminProvider:
    """Toulmin layout analysis over raw text, backed by a language model."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = resolved_model_identity(model)
        self._build_lock = Lock()
        self._analyst: StructuredAnalyst[ToulminAnalysis] | None = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_id(self) -> str:
        return f"{PROVIDER_ID_PREFIX}/{self._model}"

    @property
    def declaration(self) -> ProviderDeclaration:
        """Side-effect-free: resolves a key, never opens a connection."""

        reason = unavailable_reason(self._model)
        capability = (
            AvailableCapability(provider_id=self.provider_id, contract_version=CONTRACT_VERSION)
            if reason is None
            else UnavailableCapability(reason=reason)
        )
        return ProviderDeclaration(
            provider_id=self.provider_id,
            technique=Technique.TOULMIN,
            technique_curie=technique_curie(Technique.TOULMIN),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.TOULMIN,
                    technique_curie=technique_curie(Technique.TOULMIN),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=provider_provenance(
                package="rdam.toulmin",
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
            "toulmin/argument-evidence-v1",
            (ContentClass.TITLE, ContentClass.HEADING, ContentClass.PARAGRAPH, ContentClass.LIST_ITEM, ContentClass.TURN, ContentClass.CAPTION, ContentClass.TABLE, ContentClass.TABLE_CELL),
            requires_speaker_identity=False,
        )

    def _built(self) -> StructuredAnalyst[ToulminAnalysis]:
        with self._build_lock:
            if self._analyst is None:
                self._analyst = StructuredAnalyst(
                    output_type=ToulminAnalysis,
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
                    "formalism_not_declared", Retryability.NOT_RETRYABLE, "ValueError", str(request.formalism_id)
                )
            )
        text = require_llm_text(
            request.projection.prepared_document.text if request.projection is not None else request.text,
            technique=Technique.TOULMIN, provider_id=self.provider_id,
        )
        try:
            extraction = self._built().extract(text)
        except LayoutError as error:
            raise ProviderError(
                self._failure("invalid_toulmin_layout", Retryability.NOT_RETRYABLE, "LayoutError", str(error))
            ) from error
        except LlmError as error:
            raise ProviderError(
                llm_provider_failure(error, technique=Technique.TOULMIN, provider_id=self.provider_id)
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
            technique=Technique.TOULMIN,
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
            technique=Technique.TOULMIN,
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
    "ToulminProvider",
    "source_identity",
]
