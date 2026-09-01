"""Integrity-checked atomic cache for semantically eligible v2 outcomes."""

import os
from pathlib import Path
import tempfile

from pydantic import ValidationError

from isanlp_rst.ingest.contracts.analysis import (
    AnalysedOutcome,
    EmptyPrimaryAnalysisOutcome,
    ProductionAnalysisOutcome,
)
from isanlp_rst.ingest.contracts.base import Sha256Identity
from isanlp_rst.ingest.contracts.failure import (
    AssemblyCompletedEvidence,
    CacheIdentityContext,
    FailureCategory,
    LifecycleStage,
    ProductionFailure,
    ProductionIngestError,
    Retryability,
)
from isanlp_rst.ingest.identity import semantic_sha256
from isanlp_rst.ingest.serialization import (
    load_contract,
    serialize_contract,
    verify_semantic_digest,
)
from isanlp_rst.ingest.validation import (
    build_analysis_validation_receipt,
    validate_parser_analysis_result,
)


class ProductionIngestCache:
    """Local cache keyed by the complete semantic analysis-request identity."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def path_for(self, request_identity: Sha256Identity | str) -> Path:
        digest = (
            request_identity.hex_digest
            if isinstance(request_identity, Sha256Identity)
            else request_identity
        )
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("cache identity must be a lowercase SHA-256 digest")
        return self.root / digest[:2] / f"{digest}.json"

    def load(
        self,
        request_identity: Sha256Identity,
    ) -> ProductionAnalysisOutcome | None:
        path = self.path_for(request_identity)
        if not path.exists():
            return None
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise _cache_error(
                request_identity,
                code="cache_read_failed",
                category=FailureCategory.INTERNAL_PROCESSING_FAILURE,
                message="cached_record_could_not_be_read_from_storage",
                retryability=Retryability.UNKNOWN,
                cause=exc,
            ) from exc
        try:
            record = load_contract(payload)
        except (UnicodeError, ValueError, ValidationError) as exc:
            raise _cache_error(
                request_identity,
                code="corrupt_cache_entry",
                category=FailureCategory.CORRUPT_CACHE_ENTRY,
                message="cached_record_failed_canonical_contract_validation",
                cause=exc,
            ) from exc
        if not isinstance(record, AnalysedOutcome | EmptyPrimaryAnalysisOutcome):
            raise _cache_error(
                request_identity,
                code="wrong_cache_record_kind",
                category=FailureCategory.CORRUPT_CACHE_ENTRY,
                message="cache_entry_is_not_a_production_analysis_outcome",
            )
        if record.semantic.cache_request_identity != request_identity:
            raise _cache_error(
                request_identity,
                code="contradictory_cache_identity",
                category=FailureCategory.IDENTITY_CONTRADICTION,
                message="cached_request_identity_differs_from_cache_key",
            )
        expected_entry = cache_entry_identity(request_identity, _required_result_identity(record))
        if record.execution.cache_entry_identity != expected_entry:
            raise _cache_error(
                request_identity,
                code="contradictory_cache_entry_identity",
                category=FailureCategory.IDENTITY_CONTRADICTION,
                message="cached_entry_identity_differs_from_result_binding",
            )
        return record

    def store(
        self,
        request_identity: Sha256Identity,
        result: ProductionAnalysisOutcome,
    ) -> None:
        if result.semantic.cache_request_identity != request_identity:
            raise ValueError("analysis outcome request identity contradicts cache destination")
        _validate_cache_result(request_identity, result)
        path = self.path_for(request_identity)
        temporary: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = serialize_contract(result) + b"\n"
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{request_identity.hex_digest}.",
                suffix=".tmp",
                dir=path.parent,
            )
            temporary = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            failure = ProductionFailure(
                failed_stage=LifecycleStage.PERSISTENCE,
                category=FailureCategory.PERSISTENCE_FAILURE,
                code="cache_persistence_failed",
                retryability=Retryability.UNKNOWN,
                message_template="validated_outcome_could_not_be_persisted",
                diagnostic_context=(
                    CacheIdentityContext(
                        cache_identity=cache_entry_identity(
                            request_identity,
                            _required_result_identity(result),
                        ),
                        request_identity=request_identity,
                    ),
                ),
                completed=AssemblyCompletedEvidence(outcome=result),
            )
            raise ProductionIngestError(failure) from exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def cache_entry_identity(
    request_identity: Sha256Identity,
    result_identity: Sha256Identity,
) -> Sha256Identity:
    """Bind one cache entry to exactly one request and one validated result."""

    return Sha256Identity(
        hex_digest=semantic_sha256(
            {
                "request_identity": request_identity,
                "result_identity": result_identity,
            }
        )
    )


def _validate_cache_result(
    request_identity: Sha256Identity,
    result: ProductionAnalysisOutcome,
) -> None:
    verify_semantic_digest(result)
    if result.semantic.request.semantic_digest != request_identity:
        raise ValueError("analysis request identity contradicts cache destination")
    expected_entry = cache_entry_identity(request_identity, _required_result_identity(result))
    if result.execution.cache_entry_identity != expected_entry:
        raise ValueError("analysis cache-entry identity does not bind request and result")
    if isinstance(result, AnalysedOutcome):
        parser_result = result.semantic.parser_result
        analysed = result.semantic.analysed_document
        analysis = result.semantic.analysis
        validation = result.semantic.validation
        primary = result.semantic.primary_inference
        if (
            parser_result is None
            or analysed is None
            or analysis is None
            or validation is None
            or primary is None
        ):
            raise ValueError("analysed cache result lacks validated evidence")
        validate_parser_analysis_result(parser_result)
        rebuilt = build_analysis_validation_receipt(
            analysis,
            analysed,
            primary,
            result.semantic.erst_completion,
            result.semantic.anchors,
            policy=result.semantic.policy,
            composite=result.semantic.composite_identity,
            recombination=result.semantic.recombination,
        )
        if rebuilt != validation:
            raise ValueError("analysis cache result validation receipt does not reproduce")


def _required_result_identity(result: ProductionAnalysisOutcome) -> Sha256Identity:
    if result.semantic_digest is None:
        raise ValueError("analysis outcome has no semantic identity")
    return result.semantic_digest


def _cache_error(
    identity: Sha256Identity,
    *,
    code: str,
    category: FailureCategory,
    message: str,
    retryability: Retryability = Retryability.NOT_RETRYABLE,
    cause: Exception | None = None,
) -> ProductionIngestError:
    failure = ProductionFailure(
        failed_stage=LifecycleStage.CACHE_RETRIEVAL,
        category=category,
        code=code,
        retryability=retryability,
        message_template=message,
        diagnostic_context=(CacheIdentityContext(cache_identity=identity),),
    )
    error = ProductionIngestError(failure)
    if cause is not None:
        error.__cause__ = cause
    return error


__all__ = ["ProductionIngestCache", "cache_entry_identity"]
