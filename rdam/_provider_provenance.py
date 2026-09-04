"""Small composition helpers shared by production providers."""

from functools import cache
from importlib import resources
from typing import Protocol

from rdam._strict import sha256_bytes
from rdam._provenance import installed_package_version, resolve_source_revision
from rdam.contracts import (
    ProviderError,
    ProviderFailure,
    ProviderProvenance,
    Retryability,
    Sha256Identity,
    Technique,
    semantic_sha256,
)


@cache
def package_version() -> str:
    """Return the installed RDAM version without repeating metadata I/O."""

    return installed_package_version()


@cache
def source_identity(package_name: str, source_files: tuple[str, ...]) -> Sha256Identity:
    """Digest an immutable provider source surface once per process."""

    package = resources.files(package_name)
    digest = semantic_sha256({name: sha256_bytes(package.joinpath(name).read_bytes()) for name in source_files})
    return Sha256Identity(hex_digest=digest)


def provider_provenance(
    *,
    package: str,
    licence: str,
    model_identity: str | None = None,
    instructions: str | None = None,
) -> ProviderProvenance:
    """Build complete runtime provenance without provider-specific boilerplate."""

    revision = resolve_source_revision()
    if instructions is not None:
        dirty = revision.endswith("-dirty")
        revision = f"{revision.removesuffix('-dirty')}:instructions:{semantic_sha256(instructions)}"
        if dirty:
            revision += "-dirty"
    return ProviderProvenance(
        package=package,
        version=package_version(),
        source_revision=revision,
        model_identity=model_identity,
        licence=licence,
    )


def provider_failure(
    *,
    technique: Technique,
    provider_id: str,
    code: str,
    retryability: Retryability,
    exception_type: str,
    detail: str | None = None,
    message_parameters: tuple[tuple[str, str], ...] = (),
) -> ProviderFailure:
    """Build one typed analyse failure with deterministic parameter order."""

    parameters = (("detail", detail),) if detail is not None else ()
    return ProviderFailure(
        technique=technique,
        provider_id=provider_id,
        failed_operation="analyse",
        retryability=retryability,
        code=code,
        exception_type=exception_type,
        message_template=code,
        message_parameters=parameters + message_parameters,
    )


def require_llm_text(text: str | None, *, technique: Technique, provider_id: str) -> str:
    """Apply the uniform LLM-provider text contract and return accepted text."""

    if text is None:
        raise ProviderError(
            provider_failure(
                technique=technique,
                provider_id=provider_id,
                code="text_required",
                retryability=Retryability.NOT_RETRYABLE,
                exception_type="ValueError",
            )
        )
    if not text.strip():
        raise ProviderError(
            provider_failure(
                technique=technique,
                provider_id=provider_id,
                code="empty_source_text",
                retryability=Retryability.NOT_RETRYABLE,
                exception_type="ValueError",
            )
        )
    return text


class LlmFailure(Protocol):
    code: str
    retryability: Retryability
    detail: str
    output_attempts: int
    transport_attempts: int


def llm_provider_failure(
    error: LlmFailure,
    *,
    technique: Technique,
    provider_id: str,
) -> ProviderFailure:
    """Convert one LLM-boundary error to the common provider failure shape."""

    return provider_failure(
        technique=technique,
        provider_id=provider_id,
        code=error.code,
        retryability=error.retryability,
        exception_type="LlmError",
        detail=error.detail,
        message_parameters=(
            ("output_attempts", str(error.output_attempts)),
            ("transport_attempts", str(error.transport_attempts)),
        ),
    )


__all__ = [
    "llm_provider_failure",
    "package_version",
    "provider_failure",
    "provider_provenance",
    "require_llm_text",
    "source_identity",
]
