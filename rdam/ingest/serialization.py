"""Canonical UTF-8/I-JSON persistence for production contract records."""

import json
from typing import Any, Final, cast
from uuid import uuid4

from pydantic import BaseModel

from rdam._canonical import canonical_json_bytes as _canonical_json_bytes
from rdam._canonical import validate_ijson_value

from rdam.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    READABLE_CONTRACT_VERSIONS,
    Sha256Identity,
)
from rdam.ingest.contracts.analysis import (
    AnalysedOutcome,
    EmptyPrimaryAnalysisOutcome,
    ParserAnalysisResult,
)
from rdam.ingest.contracts.capabilities import ProductionCapabilities
from rdam.ingest.contracts.failure import (
    DiagnosticPolicy,
    DiagnosticProductionFailureRecord,
    ProductionFailure,
    ProductionIngestError,
    SafeProductionFailureRecord,
)
from rdam.ingest.contracts.preparation import PreparationOutcome
from rdam.ingest.identity import (
    analysis_outcome_semantic_projection,
    parser_result_semantic_projection,
    semantic_sha256,
)


class UnsupportedContractVersionError(ValueError):
    """The envelope names a well-formed contract version this runtime cannot read."""


class UnsupportedContractKindError(ValueError):
    """The envelope kind is not registered for the selected contract version."""


type PersistedContract = (
    ProductionCapabilities
    | PreparationOutcome
    | ParserAnalysisResult
    | AnalysedOutcome
    | EmptyPrimaryAnalysisOutcome
    | SafeProductionFailureRecord
    | DiagnosticProductionFailureRecord
)

_RECORD_TYPES: Final[dict[str, type[BaseModel]]] = {
    "capabilities": ProductionCapabilities,
    "preparation_outcome": PreparationOutcome,
    "parser_analysis_result": ParserAnalysisResult,
    "analysed_outcome": AnalysedOutcome,
    "empty_primary_analysis_outcome": EmptyPrimaryAnalysisOutcome,
    "safe_production_failure": SafeProductionFailureRecord,
    "diagnostic_production_failure": DiagnosticProductionFailureRecord,
}


def canonical_json_bytes(value: BaseModel | dict[str, Any]) -> bytes:
    """Return RFC 8785 canonical bytes for a JSON-compatible contract value."""

    payload = value.model_dump(mode="json", exclude_none=False) if isinstance(value, BaseModel) else value
    validate_ijson_value(payload)
    return _canonical_json_bytes(payload)


def serialize_contract(
    value: PersistedContract | ProductionFailure,
    *,
    diagnostic_policy: DiagnosticPolicy | None = None,
) -> bytes:
    """Serialize one supported record, safely projecting in-memory failures."""

    record: PersistedContract
    if isinstance(value, ProductionFailure):
        error = ProductionIngestError(value)
        execution_id = str(uuid4())
        record = (
            error.safe_record(execution_id=execution_id)
            if diagnostic_policy is None
            else error.diagnostic_record(
                policy=diagnostic_policy,
                execution_id=execution_id,
            )
        )
    else:
        record = value
    verify_semantic_digest(record)
    return canonical_json_bytes(record)


def load_contract(payload: bytes | str) -> PersistedContract:
    """Strictly decode, version-dispatch, validate, and verify one persisted record."""

    data = payload.encode("utf-8", errors="strict") if isinstance(payload, str) else bytes(payload)
    text = data.decode("utf-8", errors="strict")
    parsed = json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_non_finite,
    )
    validate_ijson_value(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("production contract payload must be a JSON object")
    envelope = cast(dict[object, object], parsed)
    contract = envelope.get("contract")
    contract_version = envelope.get("contract_version")
    kind = envelope.get("kind")
    if contract != PRODUCTION_CONTRACT:
        raise ValueError(f"unsupported contract family: {contract!r}")
    if contract_version not in READABLE_CONTRACT_VERSIONS:
        raise UnsupportedContractVersionError(
            f"unsupported {PRODUCTION_CONTRACT} contract version: {contract_version!r}"
        )
    record_type = _RECORD_TYPES.get(kind) if isinstance(kind, str) else None
    if record_type is None:
        raise UnsupportedContractKindError(f"unsupported {PRODUCTION_CONTRACT}/{contract_version} kind: {kind!r}")
    record = record_type.model_validate_json(data)
    verify_semantic_digest(record)
    return cast(PersistedContract, record)


def semantic_projection(value: BaseModel) -> dict[str, Any]:
    """Return the documented digest projection for one envelope record."""

    if isinstance(value, AnalysedOutcome | EmptyPrimaryAnalysisOutcome):
        return analysis_outcome_semantic_projection(value)
    if isinstance(value, ParserAnalysisResult):
        return parser_result_semantic_projection(value)
    payload = value.model_dump(mode="json", exclude_none=False)
    required = {"contract", "contract_version", "kind", "semantic"}
    if not required <= payload.keys():
        raise TypeError("semantic projection requires a production contract envelope")
    return {key: payload[key] for key in ("contract", "contract_version", "kind", "semantic")}


def verify_semantic_digest(value: BaseModel) -> None:
    """Reject a record whose digest disagrees with its semantic projection."""

    digest = getattr(value, "semantic_digest", None)
    if not isinstance(digest, Sha256Identity):
        raise ValueError("production contract record is missing a SHA-256 semantic digest")
    expected = semantic_sha256(semantic_projection(value))
    if digest.hex_digest != expected:
        raise ValueError("production contract semantic digest mismatch")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> Any:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


__all__ = [
    "PersistedContract",
    "UnsupportedContractKindError",
    "UnsupportedContractVersionError",
    "canonical_json_bytes",
    "load_contract",
    "semantic_projection",
    "serialize_contract",
    "verify_semantic_digest",
]
