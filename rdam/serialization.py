"""Canonical persistence for machine-layer records, digest-verified on both directions."""

import json
from importlib import import_module
from pathlib import Path
from typing import Any, Final, Literal, cast
from collections.abc import Mapping

from pydantic import BaseModel

from rdam._strict import JsonValue, Sha256Identity, canonical_json_bytes
from rdam.frameworks import BOUNDARY_TECHNIQUES, Technique
from rdam.configuration import MachineConfig
from rdam.interpretation import AnalysisView, ViewRequest
from rdam._interpretation_types import NativeInterpretationDescriptor
from rdam.contracts import (
    AGGREGATE_CONTRACT,
    CAPABILITIES_CONTRACT,
    NATIVE_RESULT_CONTRACT,
    AggregateAnalysis,
    AggregateRequest,
    ContractSupport,
    MachinePreparation,
    HistoricalMachinePreparation,
    MachineCapabilities,
    NativeTechniqueResult,
    OperationFailure,
    PreparationRequest,
    VersionInfo,
)
from rdam.historical import (
    HistoricalAggregateAnalysis,
    HistoricalMachineCapabilities,
    HistoricalNativeTechniqueResult,
)

type PersistedRecord = (
    AggregateAnalysis | MachineCapabilities | NativeTechniqueResult
    | HistoricalAggregateAnalysis | HistoricalMachineCapabilities | HistoricalNativeTechniqueResult
    | MachinePreparation | HistoricalMachinePreparation | OperationFailure | VersionInfo | AnalysisView
)

_RECORD_TYPES: Final[dict[tuple[str, str], type[BaseModel]]] = {
    (AGGREGATE_CONTRACT, "2.0.0"): AggregateAnalysis,
    (CAPABILITIES_CONTRACT, "2.0.0"): MachineCapabilities,
    (NATIVE_RESULT_CONTRACT, "2.0.0"): NativeTechniqueResult,
    (AGGREGATE_CONTRACT, "1.0.0"): HistoricalAggregateAnalysis,
    (CAPABILITIES_CONTRACT, "1.0.0"): HistoricalMachineCapabilities,
    (NATIVE_RESULT_CONTRACT, "1.0.0"): HistoricalNativeTechniqueResult,
    ("rdam.preparation", "1.0.0"): HistoricalMachinePreparation,
    ("rdam.preparation", "2.0.0"): MachinePreparation,
    ("rdam.operation_error", "1.0.0"): OperationFailure,
    ("rdam.version", "1.0.0"): VersionInfo,
    ("rdam.analysis_view", "1.0.0"): AnalysisView,
}


class UnsupportedRecordError(ValueError):
    """The payload names a contract or version this runtime cannot read."""


def verify_semantic_digest(record: BaseModel) -> None:
    digest = getattr(record, "semantic_digest", None)
    if "semantic_digest" in type(record).model_fields and not isinstance(digest, Sha256Identity):
        raise ValueError("record has no semantic digest")
    # Rebuild from data, not the model instance: this checks nested records too
    # and applies each contract's own semantic-versus-execution identity rule.
    type(record).model_validate(record.model_dump())


def serialize(record: PersistedRecord) -> bytes:
    """RFC 8785 canonical bytes of a digest-verified record."""

    verify_semantic_digest(record)
    return canonical_json_bytes(record)


def load(payload: bytes | str) -> PersistedRecord:
    """Strictly decode, dispatch on contract, validate, and verify one persisted record."""

    text = payload if isinstance(payload, str) else payload.decode("utf-8", errors="strict")
    parsed: Any = json.loads(text, object_pairs_hook=_unique_object)
    canonical_json_bytes(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("record payload must be a JSON object")
    envelope = cast(dict[object, object], parsed)
    contract = envelope.get("contract")
    version = envelope.get("contract_version")
    record_type = _RECORD_TYPES.get((contract, version)) if isinstance(contract, str) and isinstance(version, str) else None
    if record_type is None:
        raise UnsupportedRecordError(f"unsupported record contract: {contract!r}")
    record = record_type.model_validate_json(text)
    _require_saved_digests(envelope, record)
    verify_semantic_digest(record)
    return cast(PersistedRecord, record)


def load_native_payload(payload: bytes | str) -> BaseModel:
    """Load a current native envelope and validate its technique-owned payload.

    Generic ``load`` establishes envelope integrity only. This explicit consumer
    boundary additionally validates native structure and computed summaries. It
    does not establish extraction accuracy or reinterpret historical payloads.
    """
    record = load(payload)
    if not isinstance(record, NativeTechniqueResult):
        raise UnsupportedRecordError("native validation requires a current native-result envelope")
    return validate_native_result(record)


def validate_native_result(record: NativeTechniqueResult) -> BaseModel:
    """Validate envelope integrity and the current technique-owned native content."""
    verify_semantic_digest(record)
    output_technique = record.technique
    if record.technique in {Technique.RST, Technique.ERST}:
        from rdam.ingest.contracts.inference import OutputFormalism
        from rdam.ingest.contracts.base import WRITE_CONTRACT_VERSION

        formalism = (
            OutputFormalism.ERST_GRAPH
            if record.technique is Technique.ERST or record.formalism_id == OutputFormalism.ERST_GRAPH.value
            else OutputFormalism.RST_TREE
        )
        output_technique = Technique.ERST if formalism is OutputFormalism.ERST_GRAPH else Technique.RST
        expected_formalism = formalism.value
        supported_version = WRITE_CONTRACT_VERSION
    else:
        provider_module = import_module(f"rdam.{record.technique.value}.provider")
        expected_formalism = provider_module.FORMALISM_ID
        supported_version = str(provider_module.CONTRACT_VERSION)
    if record.formalism_id != expected_formalism:
        raise UnsupportedRecordError(
            f"native {record.technique.value} requires formalism {expected_formalism!r}, "
            f"not {record.formalism_id!r}"
        )
    if str(record.provider_contract_version) != supported_version:
        raise UnsupportedRecordError(
            f"native {record.technique.value} version {record.provider_contract_version} "
            f"requires a historical or unsupported schema; current version is {supported_version}"
        )
    return native_output_model(output_technique).model_validate_json(canonical_json_bytes(record.payload))


def _require_saved_digests(value: object, record: object) -> None:
    """Inspect typed record fields, never interpret a native payload's user data."""
    if isinstance(record, BaseModel) and isinstance(value, dict):
        item = cast(dict[str, object], value)
        if isinstance(record, NativeInterpretationDescriptor) and not isinstance(item.get("identity"), dict):
            raise ValueError("persisted descriptor requires its identity")
        if isinstance(
            record,
            (
                AggregateAnalysis,
                HistoricalAggregateAnalysis,
                NativeTechniqueResult,
                HistoricalNativeTechniqueResult,
                MachineCapabilities,
                HistoricalMachineCapabilities,
                MachinePreparation,
                HistoricalMachinePreparation,
                AnalysisView,
            ),
        ) and not isinstance(item.get("semantic_digest"), dict):
            raise ValueError("persisted record requires a semantic digest")
        if isinstance(record, (NativeTechniqueResult, HistoricalNativeTechniqueResult)) and not isinstance(
            item.get("artifact_digest"), dict
        ):
            raise ValueError("persisted native result requires an artifact digest")
        for name in type(record).model_fields:
            if name in item:
                _require_saved_digests(item[name], getattr(record, name))
    elif isinstance(record, tuple) and isinstance(value, list):
        for child, typed in zip(cast(list[object], value), cast(tuple[object, ...], record), strict=True):
            _require_saved_digests(child, typed)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def decode_object(payload: bytes | str) -> dict[str, Any]:
    """Decode one interoperable JSON object without lossy parser extensions."""
    text = payload if isinstance(payload, str) else payload.decode("utf-8", errors="strict")
    parsed: Any = json.loads(text, object_pairs_hook=_unique_object)
    canonical_json_bytes(parsed)
    if not isinstance(parsed, dict):
        raise ValueError("JSON payload must be an object")
    return cast(dict[str, Any], parsed)


def _load_typed[T: BaseModel](payload: bytes | str, model: type[T]) -> T:
    parsed = decode_object(payload)
    for name in ("contract", "contract_version"):
        if parsed.get(name) != model.model_fields[name].default:
            raise UnsupportedRecordError("unsupported contract or version")
    return model.model_validate_json(canonical_json_bytes(parsed))


def _serialize_typed(record: BaseModel) -> bytes:
    validated = type(record).model_validate(record.model_dump())
    return canonical_json_bytes(validated)


def serialize_request(request: AggregateRequest) -> bytes:
    return _serialize_typed(request)


def load_request(payload: bytes | str) -> AggregateRequest:
    parsed = decode_object(payload)
    request = _load_typed(payload, AggregateRequest)
    _require_saved_digests(parsed, request)
    return request


def serialize_preparation_request(request: PreparationRequest) -> bytes:
    return _serialize_typed(request)


def load_preparation_request(payload: bytes | str) -> PreparationRequest:
    return _load_typed(payload, PreparationRequest)


def serialize_view_request(request: ViewRequest) -> bytes:
    return _serialize_typed(request)


def load_view_request(payload: bytes | str) -> ViewRequest:
    request = _load_typed(payload, ViewRequest)
    _require_saved_digests(decode_object(payload), request)
    return request


def serialize_config(config: MachineConfig) -> bytes:
    return _serialize_typed(config)


def load_config(path: Path | str) -> MachineConfig:
    source = Path(path).resolve()
    parsed = decode_object(source.read_bytes())
    for section, name in (("execution", "cache_directory"),):
        container = parsed.get(section)
        if isinstance(container, dict):
            values = cast(dict[str, object], container)
            relative = values.get(name)
            if isinstance(relative, str):
                values[name] = str((source.parent / relative).resolve())
    rst = parsed.get("rst")
    if isinstance(rst, dict):
        model = cast(dict[str, object], rst).get("model")
        if isinstance(model, dict):
            values = cast(dict[str, object], model)
            relative = values.get("store")
            if values.get("kind") == "local_release" and isinstance(relative, str):
                values["store"] = str((source.parent / relative).resolve())
    return _load_typed(canonical_json_bytes(parsed), MachineConfig)


def contract_support() -> tuple[ContractSupport, ...]:
    registered = schema_models()
    models = {name: model for name, model in registered.items()
              if "contract" in model.model_fields and not name.endswith("-v1")}
    return tuple(ContractSupport(
        contract=str(model.model_fields["contract"].default),
        write_version=str(model.model_fields["contract_version"].default),
        read_versions=tuple(version for contract, version in _RECORD_TYPES
                            if contract == model.model_fields["contract"].default)
                      or (str(model.model_fields["contract_version"].default),),
        schema_names=tuple(alias for alias, candidate in registered.items()
                           if "contract" in candidate.model_fields
                           and candidate.model_fields["contract"].default == model.model_fields["contract"].default),
    ) for model in models.values())


def version_info() -> VersionInfo:
    from importlib.metadata import version
    return VersionInfo(version=version("rdam"), contracts=contract_support())


def native_output_model(technique: Technique) -> type[BaseModel]:
    """Resolve one technique-owned output type without importing other providers."""
    match technique:
        case Technique.DUNG:
            from rdam.dung.output import DungOutput
            return DungOutput
        case Technique.IBIS:
            from rdam.ibis.output import IbisOutput
            return IbisOutput
        case Technique.PDTB:
            from rdam.pdtb.output import PdtbOutput
            return PdtbOutput
        case Technique.SDRT:
            from rdam.sdrt.output import SdrtOutput
            return SdrtOutput
        case Technique.TOULMIN:
            from rdam.toulmin.output import ToulminOutput
            return ToulminOutput
        case Technique.WALTON:
            from rdam.walton.output import WaltonOutput
            return WaltonOutput
        case Technique.RST:
            from rdam.rst.output import RstOutput
            return RstOutput
        case Technique.ERST:
            from rdam.rst.output import ErstOutput
            return ErstOutput
    raise UnsupportedRecordError(f"no native output schema for {technique!r}")


def schema_models() -> dict[str, type[BaseModel]]:
    from rdam.dung.semantics import DungInput
    from rdam.ibis.grammar import IbisInput
    from rdam.toulmin.output import HistoricalToulminOutput
    from rdam.walton.output import HistoricalWaltonOutput
    return {
        **{f"{technique.value}-result": native_output_model(technique) for technique in BOUNDARY_TECHNIQUES},
        "dung-input": DungInput, "ibis-input": IbisInput,
        "toulmin-result-v1": HistoricalToulminOutput, "walton-result-v1": HistoricalWaltonOutput,
        "request": AggregateRequest, "preparation-request": PreparationRequest,
        "configuration": MachineConfig, "preparation": MachinePreparation,
        "preparation-v1": HistoricalMachinePreparation,
        "aggregate": AggregateAnalysis, "capabilities": MachineCapabilities,
        "native-result": NativeTechniqueResult, "operation-error": OperationFailure,
        "version": VersionInfo, "analysis-view": AnalysisView, "view-request": ViewRequest,
        "aggregate-v1": HistoricalAggregateAnalysis, "capabilities-v1": HistoricalMachineCapabilities,
        "native-result-v1": HistoricalNativeTechniqueResult,
    }


def schema(record_name: str, *, mode: Literal["validation", "serialization"] = "validation") -> Mapping[str, JsonValue]:
    from rdam.ingest.contracts.base import WRITE_CONTRACT_VERSION

    if mode not in {"validation", "serialization"}:
        raise ValueError("unsupported schema mode")
    model = schema_models().get(record_name)
    if model is None:
        raise ValueError("unsupported schema name")
    document = model.model_json_schema(mode=mode)
    document["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    contract = model.model_fields.get("contract")
    version = model.model_fields.get("contract_version")
    identifier = contract.default if contract is not None else record_name
    if version is not None:
        revision = version.default
    elif record_name in {f"{technique.value}-result" for technique in Technique}:
        technique = Technique(record_name.removesuffix("-result"))
        if technique in {Technique.RST, Technique.ERST}:
            revision = WRITE_CONTRACT_VERSION
        else:
            revision = str(import_module(f"rdam.{technique.value}.provider").CONTRACT_VERSION)
    else:
        # Historical native models and input schemas retain their v1 identity.
        revision = "1.0.0"
    document["$id"] = f"https://schemas.rdam.local/{identifier}/{revision}/{mode}.schema.json"
    return cast(Mapping[str, JsonValue], document)


__all__ = ["PersistedRecord", "UnsupportedRecordError", "load", "load_native_payload", "serialize", "verify_semantic_digest"]
