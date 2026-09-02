"""Canonical UTF-8/I-JSON persistence for production contract records."""

import json
from typing import Any, Final, cast
from uuid import uuid4

from pydantic import BaseModel
import rfc8785

from isanlp_rst.ingest.contracts.base import (
    PRODUCTION_CONTRACT,
    READABLE_CONTRACT_VERSIONS,
    Sha256Identity,
)
from isanlp_rst.ingest.contracts.analysis import (
    AnalysedOutcome,
    EmptyPrimaryAnalysisOutcome,
    ParserAnalysisResult,
)
from isanlp_rst.ingest.contracts.capabilities import ProductionCapabilities
from isanlp_rst.ingest.contracts.failure import (
    DiagnosticPolicy,
    DiagnosticProductionFailureRecord,
    ProductionFailure,
    ProductionIngestError,
    SafeProductionFailureRecord,
)
from isanlp_rst.ingest.contracts.preparation import PreparationOutcome
from isanlp_rst.ingest.identity import (
    analysis_outcome_semantic_projection,
    parser_result_semantic_projection,
    semantic_sha256,
)

_IJSON_INTEGER_LIMIT: Final = 9_007_199_254_740_991


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
    _validate_ijson_value(payload)
    return rfc8785.dumps(payload)


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
    _validate_ijson_value(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("production contract payload must be a JSON object")
    contract = parsed.get("contract")
    contract_version = parsed.get("contract_version")
    kind = parsed.get("kind")
    if contract != PRODUCTION_CONTRACT:
        raise ValueError(f"unsupported contract family: {contract!r}")
    if contract_version not in READABLE_CONTRACT_VERSIONS:
        raise UnsupportedContractVersionError(
            f"unsupported {PRODUCTION_CONTRACT} contract version: {contract_version!r}"
        )
    record_type = _RECORD_TYPES.get(kind) if isinstance(kind, str) else None
    if record_type is None:
        raise UnsupportedContractKindError(
            f"unsupported {PRODUCTION_CONTRACT}/{contract_version} kind: {kind!r}"
        )
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


def _validate_ijson_value(value: Any) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("unpaired Unicode surrogate is forbidden by I-JSON")
        return
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if abs(value) > _IJSON_INTEGER_LIMIT:
            raise ValueError("integer exceeds the interoperable I-JSON range")
        return
    if isinstance(value, float):
        if not (-float("inf") < value < float("inf")):
            raise ValueError("non-finite JSON number is forbidden")
        return
    if isinstance(value, list | tuple):
        for item in value:
            _validate_ijson_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            _validate_ijson_value(key)
            _validate_ijson_value(item)
        return
    raise TypeError(f"value is outside the JSON data model: {type(value).__name__}")


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
