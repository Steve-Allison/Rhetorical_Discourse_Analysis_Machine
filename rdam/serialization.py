"""Canonical persistence for machine-layer records, digest-verified on both directions."""

import json
from typing import Any, Final, cast

from pydantic import BaseModel

from rdam._strict import Sha256Identity, canonical_json_bytes, semantic_sha256
from rdam.contracts import (
    AGGREGATE_CONTRACT,
    CAPABILITIES_CONTRACT,
    CONTRACT_VERSION,
    NATIVE_RESULT_CONTRACT,
    AggregateAnalysis,
    MachineCapabilities,
    NativeTechniqueResult,
)

type PersistedRecord = AggregateAnalysis | MachineCapabilities | NativeTechniqueResult

_RECORD_TYPES: Final[dict[str, type[BaseModel]]] = {
    AGGREGATE_CONTRACT: AggregateAnalysis,
    CAPABILITIES_CONTRACT: MachineCapabilities,
    NATIVE_RESULT_CONTRACT: NativeTechniqueResult,
}


class UnsupportedRecordError(ValueError):
    """The payload names a contract or version this runtime cannot read."""


def verify_semantic_digest(record: BaseModel) -> None:
    digest = getattr(record, "semantic_digest", None)
    if not isinstance(digest, Sha256Identity):
        raise ValueError("record has no semantic digest")
    expected = semantic_sha256(record.model_dump(exclude={"semantic_digest"}))
    if digest.hex_digest != expected:
        raise ValueError("record semantic digest mismatch")


def serialize(record: PersistedRecord) -> bytes:
    """RFC 8785 canonical bytes of a digest-verified record."""

    verify_semantic_digest(record)
    return canonical_json_bytes(record)


def load(payload: bytes | str) -> PersistedRecord:
    """Strictly decode, dispatch on contract, validate, and verify one persisted record."""

    text = payload if isinstance(payload, str) else payload.decode("utf-8", errors="strict")
    parsed: Any = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(parsed, dict):
        raise ValueError("record payload must be a JSON object")
    contract = parsed.get("contract")
    version = parsed.get("contract_version")
    record_type = _RECORD_TYPES.get(contract) if isinstance(contract, str) else None
    if record_type is None:
        raise UnsupportedRecordError(f"unsupported record contract: {contract!r}")
    if version != CONTRACT_VERSION:
        raise UnsupportedRecordError(f"unsupported {contract} contract version: {version!r}")
    record = record_type.model_validate_json(text)
    verify_semantic_digest(record)
    return cast(PersistedRecord, record)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


__all__ = ["PersistedRecord", "UnsupportedRecordError", "load", "serialize", "verify_semantic_digest"]
