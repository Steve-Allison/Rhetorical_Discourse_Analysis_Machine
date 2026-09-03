"""LLM-assisted PDTB-3 provider with deterministic native relation validation."""

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
from rdam.pdtb.relations import PdtbAnalysis, RelationError

PROVIDER_ID_PREFIX: Final = "rdam.pdtb/pdtb3-relations-v1"
FORMALISM_ID: Final = "pdtb3_relations"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("relations.py", "provider.py")

INSTRUCTIONS: Final = """\
Analyse the passage using the Penn Discourse Treebank 3.0 annotation framework.

Return binary relations with exact Arg1 and Arg2 source spans. Preserve PDTB-3 argument
labels: for inter-sentential and coordinating relations Arg1 is the left argument and
Arg2 the right; for intra-sentential subordinating structures Arg2 is the subordinate
structure even when it occurs first.

Use exactly these relation types and evidence rules:
- Explicit: exact source connective spans and one or more PDTB-3 senses.
- Implicit: inferred connective text (not a source quote) and one or more senses.
- AltLex: exact alternative lexicalization spans and one or more senses.
- AltLexC: exact lexico-syntactic construction spans and one or more senses.
- EntRel: entity coherence only; no connective and no sense.
- Hypophora: an information-seeking question and its answer; no connective and no sense.
- NoRel: adjacent material with no discourse relation; no connective and no sense.

Use only the PDTB-3 sense labels admitted by the output schema. Preserve multiple senses
when they hold. Spans are zero-based, half-open Python character offsets and their text
must exactly equal the source slice. Do not invent an RST/SDRT hierarchy or repair a weak
relation into a plausible one.
"""


def source_identity() -> Sha256Identity:
    """Digest the complete provider source surface in a fixed order."""

    package = resources.files("rdam.pdtb")
    digest = semantic_sha256(
        {name: sha256_bytes(package.joinpath(name).read_bytes()) for name in _SOURCE_FILES}
    )
    return Sha256Identity(hex_digest=digest)


def _package_version() -> str:
    try:
        return version("rdam")
    except PackageNotFoundError:
        return "unknown"


class PdtbProvider:
    """Produce validated native PDTB-3 relations from raw text."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model or configured_model()
        self._analyst: StructuredAnalyst[PdtbAnalysis] | None = None

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
            technique=Technique.PDTB,
            technique_curie=technique_curie(Technique.PDTB),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.PDTB,
                    technique_curie=technique_curie(Technique.PDTB),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=ProviderProvenance(
                package="rdam.pdtb",
                version=_package_version(),
                source_revision=source_identity().hex_digest,
                model_identity=self._model,
                licence=LICENCE,
            ),
            capability=capability,
            requires_structured_input=False,
        )

    def _built(self) -> StructuredAnalyst[PdtbAnalysis]:
        if self._analyst is None:
            self._analyst = StructuredAnalyst(
                output_type=PdtbAnalysis,
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
        except RelationError as error:
            raise ProviderError(
                self._failure(
                    "invalid_pdtb_source",
                    Retryability.NOT_RETRYABLE,
                    "RelationError",
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
            technique=Technique.PDTB,
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
            technique=Technique.PDTB,
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
    "PdtbProvider",
    "source_identity",
]
