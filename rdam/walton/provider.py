"""The Walton provider: text in, scheme instances with their open critical questions out.

Matching an argument to a presumptive scheme, and seeing which of the scheme's critical
questions the text leaves unanswered, has no classical algorithm — it is judgement about
what is being argued, which is what 006 FR-032 makes an LLM-backed provider for.

The model proposes; :mod:`rdam.walton.schemes` disposes. A proposed instance must fill
exactly the premise roles its declared scheme names and may only report critical questions
that scheme actually has. A malformed proposal is refused, never repaired into a plausible
one. The provider reports which questions are open; it never answers them.
"""

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
from rdam.walton.schemes import SCHEMES, SCHEME_SET_ID, SchemeError, WaltonAnalysis

PROVIDER_ID_PREFIX: Final = f"rdam.walton/{SCHEME_SET_ID}"
FORMALISM_ID: Final = "walton_schemes"
CONTRACT_VERSION: Final = SemanticVersion(root="1.0.0")
LICENCE: Final = "MIT (LICENSE); analyses produced by a third-party model under that model's own terms"
_SOURCE_FILES: Final = ("schemes.py", "provider.py")


def _scheme_catalogue() -> str:
    lines: list[str] = []
    for scheme in SCHEMES.values():
        roles = ", ".join(scheme.premise_roles)
        lines.append(f"- {scheme.scheme_id.value} ({scheme.name}) — premise roles: {roles}")
        for index, question in enumerate(scheme.critical_questions):
            lines.append(f"    CQ{index}: {question}")
    return "\n".join(lines)


INSTRUCTIONS: Final = f"""\
You analyse a passage using Walton's argumentation schemes (Walton, Reed & Macagno 2008).

For each argument in the passage:
1. Identify which scheme it instances, from this set only. If an argument matches none of
   them, leave it out — never force a scheme onto an argument that does not fit.
2. Fill EXACTLY the premise roles that scheme names, from the passage. Every role must be
   filled and no other key may appear.
3. State the conclusion the argument presses.
4. Go through that scheme's critical questions. Mark each one 'addressed' if the passage
   itself takes it up (and say how, quoting the passage), or 'open' if it does not.
   Do NOT answer the open questions yourself — recording that they are open IS the
   analysis.

A passage that asserts without arguing yields an empty list of instances.

The scheme set, with each scheme's premise roles and its critical questions by index:

{_scheme_catalogue()}
"""


def source_identity() -> Sha256Identity:
    """Digest of the provider's source files, in a fixed order; recorded as provenance."""

    package = resources.files("rdam.walton")
    digest = semantic_sha256({name: sha256_bytes(package.joinpath(name).read_bytes()) for name in _SOURCE_FILES})
    return Sha256Identity(hex_digest=digest)


def _package_version() -> str:
    try:
        return version("rdam")
    except PackageNotFoundError:
        return "unknown"


class WaltonProvider:
    """Walton scheme analysis over raw text, backed by a language model."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model or configured_model()
        self._analyst: StructuredAnalyst[WaltonAnalysis] | None = None

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
            technique=Technique.WALTON,
            technique_curie=technique_curie(Technique.WALTON),
            formalisms=(
                FormalismDeclaration(
                    formalism_id=FORMALISM_ID,
                    technique=Technique.WALTON,
                    technique_curie=technique_curie(Technique.WALTON),
                    capability=capability,
                ),
            ),
            contract_version=CONTRACT_VERSION,
            provenance=ProviderProvenance(
                package="rdam.walton",
                version=_package_version(),
                source_revision=source_identity().hex_digest,
                model_identity=self._model,
                licence=LICENCE,
            ),
            capability=capability,
            requires_structured_input=False,
        )

    def _built(self) -> StructuredAnalyst[WaltonAnalysis]:
        if self._analyst is None:
            self._analyst = StructuredAnalyst(
                output_type=WaltonAnalysis,
                instructions=INSTRUCTIONS,
                model=self._model,
            )
        return self._analyst

    def analyse(self, request: ProviderRequest) -> NativeTechniqueResult:
        declaration = self.declaration
        if not isinstance(declaration.capability, AvailableCapability):
            raise ProviderError(
                self._failure("provider_not_available", Retryability.NOT_RETRYABLE, "ValueError", declaration.capability.reason.value)
            )
        if request.formalism_id not in (None, FORMALISM_ID):
            raise ProviderError(
                self._failure("formalism_not_declared", Retryability.NOT_RETRYABLE, "ValueError", str(request.formalism_id))
            )
        if request.text is None:
            raise ProviderError(self._failure("text_required", Retryability.NOT_RETRYABLE, "ValueError"))
        try:
            extraction = self._built().extract(request.text)
        except SchemeError as error:
            raise ProviderError(
                self._failure("invalid_scheme_instance", Retryability.NOT_RETRYABLE, "SchemeError", str(error))
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
            technique=Technique.WALTON,
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
                (("output_attempts", str(output_attempts)), ("transport_attempts", str(transport_attempts)))
            )
        return ProviderFailure(
            technique=Technique.WALTON,
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
    "WaltonProvider",
    "source_identity",
]
