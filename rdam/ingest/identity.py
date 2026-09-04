"""Canonical analytical identities for production source ingest."""

from typing import Any, cast

from pydantic import BaseModel

from rdam._canonical import canonical_json_bytes, semantic_sha256, sha256_bytes, sha256_file


def preparation_semantic_projection(outcome: BaseModel) -> dict[str, Any]:
    """Project a preparation outcome to exactly its semantic identity surface."""

    contract = getattr(outcome, "contract", None)
    contract_version = getattr(outcome, "contract_version", None)
    kind = getattr(outcome, "kind", None)
    semantic = getattr(outcome, "semantic", None)
    if not isinstance(contract, str) or not isinstance(contract_version, str):
        raise TypeError("preparation outcome has no public contract identity")
    if kind != "preparation_outcome" or not isinstance(semantic, BaseModel):
        raise TypeError("value is not a preparation outcome")
    semantic_payload = semantic.model_dump(mode="python")
    semantic_payload.pop("execution", None)
    return {
        "contract": contract,
        "contract_version": contract_version,
        "kind": kind,
        "semantic": semantic_payload,
    }


def preparation_semantic_identity(outcome: BaseModel) -> str:
    """Recompute a preparation semantic identity from public exposed values."""

    return semantic_sha256(preparation_semantic_projection(outcome))


def _normalize_analysis_semantic(payload: dict[str, Any]) -> None:
    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        if "timing" in analysis:
            analysis["timing"] = None
        if "provenance" in analysis and isinstance(analysis["provenance"], dict):
            provenance = dict(cast(dict[str, Any], analysis["provenance"]))
            provenance["timestamp"] = None
            analysis["provenance"] = provenance


def parser_result_semantic_projection(result: BaseModel) -> dict[str, Any]:
    """Project a parser result while excluding recombination execution timings."""

    contract = getattr(result, "contract", None)
    contract_version = getattr(result, "contract_version", None)
    kind = getattr(result, "kind", None)
    semantic = getattr(result, "semantic", None)
    if not isinstance(contract, str) or not isinstance(contract_version, str):
        raise TypeError("parser result has no public contract identity")
    if kind != "parser_analysis_result" or not isinstance(semantic, BaseModel):
        raise TypeError("value is not a parser analysis result")
    semantic_payload = semantic.model_dump(mode="python")
    semantic_payload.pop("execution", None)
    _normalize_analysis_semantic(semantic_payload)
    recombination = getattr(semantic, "recombination", None)
    if recombination is not None:
        if not isinstance(recombination, BaseModel):
            raise TypeError("parser recombination receipt is not a contract model")
        semantic_payload["recombination"] = recombination.model_dump(
            mode="python",
            exclude={"unit_durations_ms"},
        )
    return {
        "contract": contract,
        "contract_version": contract_version,
        "kind": kind,
        "semantic": semantic_payload,
    }


def parser_result_semantic_identity(result: BaseModel) -> str:
    """Recompute a parser-result identity without execution-only timings."""

    return semantic_sha256(parser_result_semantic_projection(result))


def analysis_outcome_semantic_projection(outcome: BaseModel) -> dict[str, Any]:
    """Project an analysis outcome while excluding all nested execution evidence."""

    contract = getattr(outcome, "contract", None)
    contract_version = getattr(outcome, "contract_version", None)
    kind = getattr(outcome, "kind", None)
    semantic = getattr(outcome, "semantic", None)
    if not isinstance(contract, str) or not isinstance(contract_version, str):
        raise TypeError("analysis outcome has no public contract identity")
    if kind not in {"analysed_outcome", "empty_primary_analysis_outcome"}:
        raise TypeError("value is not a production analysis outcome")
    if not isinstance(semantic, BaseModel):
        raise TypeError("analysis outcome has no semantic evidence")
    semantic_payload = semantic.model_dump(mode="python")
    semantic_payload.pop("execution", None)
    _normalize_analysis_semantic(semantic_payload)
    preparation = getattr(semantic, "preparation", None)
    if not isinstance(preparation, BaseModel):
        raise TypeError("analysis outcome has no preparation outcome")
    semantic_payload["preparation"] = preparation_semantic_projection(preparation)
    parser_result = getattr(semantic, "parser_result", None)
    if parser_result is not None:
        if not isinstance(parser_result, BaseModel):
            raise TypeError("analysis parser result is not a contract model")
        semantic_payload["parser_result"] = parser_result_semantic_projection(parser_result)
    recombination = getattr(semantic, "recombination", None)
    if recombination is not None:
        if not isinstance(recombination, BaseModel):
            raise TypeError("analysis recombination receipt is not a contract model")
        semantic_payload["recombination"] = recombination.model_dump(
            mode="python",
            exclude={"unit_durations_ms"},
        )
    return {
        "contract": contract,
        "contract_version": contract_version,
        "kind": kind,
        "semantic": semantic_payload,
    }


def analysis_outcome_semantic_identity(outcome: BaseModel) -> str:
    """Recompute analysis identity without timing, device, IDs, or cache status."""

    return semantic_sha256(analysis_outcome_semantic_projection(outcome))


__all__ = [
    "analysis_outcome_semantic_identity",
    "analysis_outcome_semantic_projection",
    "canonical_json_bytes",
    "parser_result_semantic_identity",
    "parser_result_semantic_projection",
    "preparation_semantic_identity",
    "preparation_semantic_projection",
    "semantic_sha256",
    "sha256_bytes",
    "sha256_file",
]
