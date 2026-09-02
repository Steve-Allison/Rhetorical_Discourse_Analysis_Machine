"""Deterministic stdlib JSON serialization and deserialization for contracts."""

from dataclasses import asdict, is_dataclass
from enum import Enum
import json
from typing import Any

from pydantic import BaseModel

from rdam.rst._version import resolve_installed_package_version
from rdam.rst.contracts.analysis import (
    DiscourseSignal,
    FormatRstAnalysis,
    PrimaryRelationEdge,
    RstAnalysis,
    RstNode,
    SecondaryRelationEdge,
    TimingRecord,
)
from rdam.rst.contracts.document import (
    DocumentToken,
    Edu,
    ProvenanceRecord,
    RstDocument,
    SourceReference,
    TextSpan,
)
from rdam.rst.contracts.enums import (
    FailureCodeEnum,
    InputFidelityEnum,
    NodeKindEnum,
    NuclearityPatternEnum,
    OutputFormalismEnum,
)

def _custom_asdict(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if is_dataclass(obj) and not isinstance(obj, type):
        result = {}
        for key, val in asdict(obj).items():
            result[key] = _custom_asdict(val)
        return result
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_custom_asdict(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _custom_asdict(v) for k, v in obj.items()}
    return obj


def _int_pair(value: Any, field_name: str) -> tuple[int, int]:
    """Validate and normalize a serialized two-integer coordinate pair."""

    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{field_name} must contain exactly two integers")
    first, second = value
    if isinstance(first, bool) or isinstance(second, bool) or not isinstance(first, int) or not isinstance(second, int):
        raise ValueError(f"{field_name} must contain exactly two integers")
    return first, second


def to_dict(obj: Any) -> dict[str, Any]:
    """Convert any contract dataclass into a JSON-serializable dictionary."""
    data = _custom_asdict(obj)
    if not isinstance(data, dict):
        raise TypeError(f"Expected dict from contract serialization, got {type(data)}")
    return data


def to_json(obj: Any, indent: int | None = 2) -> str:
    """Serialize a contract dataclass into a deterministic JSON string."""
    data = to_dict(obj)
    return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)


def document_from_dict(payload: dict[str, Any]) -> RstDocument:
    """Deserialize an RstDocument from a dictionary."""
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object / dict, got {type(payload).__name__}")

    tokens = tuple(
        DocumentToken(
            token_id=t["token_id"],
            text=t["text"],
            start=t["start"],
            end=t["end"],
            sentence_id=t.get("sentence_id"),
            paragraph_id=t.get("paragraph_id"),
        )
        for t in payload.get("tokens", [])
    )

    edus_payload = payload.get("edus")
    edus: tuple[Edu, ...] | None = None
    if edus_payload is not None:
        edus = tuple(
            Edu(
                edu_id=e["edu_id"],
                text=e["text"],
                start=e["start"],
                end=e["end"],
                token_ids=tuple(e.get("token_ids", ())),
                source_anchors=tuple(e.get("source_anchors", ())),
            )
            for e in edus_payload
        )

    sentence_boundaries = tuple(
        TextSpan(start=s["start"], end=s["end"], text=s["text"]) for s in payload.get("sentence_boundaries", [])
    )
    paragraph_boundaries = tuple(
        TextSpan(start=p["start"], end=p["end"], text=p["text"]) for p in payload.get("paragraph_boundaries", [])
    )

    source: SourceReference | None = None
    if payload.get("source"):
        src = payload["source"]
        source = SourceReference(
            uri=src.get("uri"),
            locator=src.get("locator"),
            mime_type=src.get("mime_type"),
        )

    prov_data = payload.get("provenance", {})
    provenance = ProvenanceRecord(
        producer=prov_data.get("producer", "isanlp_rst"),
        software_version=prov_data.get("software_version", resolve_installed_package_version()),
        source_revision=prov_data.get("source_revision"),
        timestamp=prov_data.get("timestamp", ""),
        model_id=prov_data.get("model_id"),
        model_digest=prov_data.get("model_digest"),
        ontology_version=prov_data.get("ontology_version"),
        ontology_digest=prov_data.get("ontology_digest"),
    )

    fidelity_str = payload.get("fidelity", InputFidelityEnum.LOSSLESS.value)
    fidelity = InputFidelityEnum(fidelity_str)

    return RstDocument(
        document_id=payload["document_id"],
        text=payload["text"],
        tokens=tokens,
        edus=edus,
        sentence_boundaries=sentence_boundaries,
        paragraph_boundaries=paragraph_boundaries,
        source=source,
        provenance=provenance,
        fidelity=fidelity,
    )


def document_from_json(json_str: str) -> RstDocument:
    """Deserialize an RstDocument from a JSON string."""
    return document_from_dict(json.loads(json_str))


def analysis_from_dict(payload: dict[str, Any]) -> RstAnalysis:
    """Deserialize an RstAnalysis from a dictionary."""
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object / dict, got {type(payload).__name__}")

    nodes = tuple(
        RstNode(
            node_id=n["node_id"],
            kind=NodeKindEnum(n["kind"]),
            edu_span=_int_pair(n["edu_span"], "edu_span"),
            char_span=_int_pair(n["char_span"], "char_span"),
            text=n["text"],
            confidence=n.get("confidence"),
        )
        for n in payload.get("nodes", [])
    )

    primary_edges = tuple(
        PrimaryRelationEdge(
            edge_id=e["edge_id"],
            parent_id=e["parent_id"],
            child_id=e["child_id"],
            relation_raw=e["relation_raw"],
            relation_concept=e["relation_concept"],
            nuclearity=NuclearityPatternEnum(e["nuclearity"]),
            confidence=e.get("confidence"),
            calibrated=e.get("calibrated", False),
        )
        for e in payload.get("primary_edges", [])
    )

    secondary_edges = tuple(
        SecondaryRelationEdge(
            edge_id=e["edge_id"],
            source_id=e["source_id"],
            target_id=e["target_id"],
            relation_raw=e["relation_raw"],
            relation_concept=e["relation_concept"],
            confidence=e.get("confidence"),
            calibrated=e.get("calibrated", False),
        )
        for e in payload.get("secondary_edges", [])
    )

    signals = tuple(DiscourseSignal.model_validate(signal) for signal in payload.get("signals", []))

    prov_data = payload.get("provenance", {})
    provenance = ProvenanceRecord(
        producer=prov_data.get("producer", "isanlp_rst"),
        software_version=prov_data.get("software_version", resolve_installed_package_version()),
        source_revision=prov_data.get("source_revision"),
        timestamp=prov_data.get("timestamp", ""),
        model_id=prov_data.get("model_id"),
        model_digest=prov_data.get("model_digest"),
        ontology_version=prov_data.get("ontology_version"),
        ontology_digest=prov_data.get("ontology_digest"),
    )

    timing_data = payload.get("timing", {})
    timing = TimingRecord(
        segmentation_ms=timing_data.get("segmentation_ms", 0.0),
        parsing_ms=timing_data.get("parsing_ms", 0.0),
        completion_ms=timing_data.get("completion_ms", 0.0),
        total_ms=timing_data.get("total_ms", 0.0),
    )

    failure_code: FailureCodeEnum | None = None
    if payload.get("failure_code"):
        failure_code = FailureCodeEnum(payload["failure_code"])

    return RstAnalysis(
        document_id=payload["document_id"],
        formalism=OutputFormalismEnum(payload["formalism"]),
        nodes=nodes,
        primary_edges=primary_edges,
        secondary_edges=secondary_edges,
        signals=signals,
        provenance=provenance,
        timing=timing,
        warnings=tuple(payload.get("warnings", ())),
        failure_code=failure_code,
    )


def analysis_from_json(json_str: str) -> RstAnalysis:
    """Deserialize an RstAnalysis from a JSON string."""
    return analysis_from_dict(json.loads(json_str))


def format_analysis_from_dict(payload: dict[str, Any]) -> FormatRstAnalysis:
    """Deserialize a FormatRstAnalysis from a dictionary."""
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object / dict, got {type(payload).__name__}")

    doc_analysis = analysis_from_dict(payload["document_analysis"])
    table_analyses = {key: analysis_from_dict(val) for key, val in payload.get("table_analyses", {}).items()}
    node_map = dict(payload.get("node_map", {}))
    return FormatRstAnalysis(
        document_analysis=doc_analysis,
        table_analyses=table_analyses,
        node_map=node_map,
    )


def format_analysis_from_json(json_str: str) -> FormatRstAnalysis:
    """Deserialize a FormatRstAnalysis from a JSON string."""
    return format_analysis_from_dict(json.loads(json_str))
