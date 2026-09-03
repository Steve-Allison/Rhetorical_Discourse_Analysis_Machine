"""Version 1 contract models retained only during the version 2 migration."""

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
from typing import Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from rdam.rst.contracts.analysis import RstAnalysis
from rdam.rst.contracts.document import RstDocument
from rdam.rst.ingest.identity import semantic_sha256, sha256_bytes

INGEST_SCHEMA_NAME = "isanlp_rst_ingest"
INGEST_SCHEMA_VERSION = "1.0.0"
INGEST_PIPELINE_VERSION = "1.0.0"


class SourceForm(StrEnum):
    TEXT = "text"
    EDUS = "edus"
    MARKDOWN = "markdown"
    DOCLING_JSON = "docling_json"
    DOCLANG_XML = "doclang_xml"
    DOCLANG_ARCHIVE = "doclang_archive"


class AuthorshipRole(StrEnum):
    AUTHORED = "authored"
    MACHINE_GENERATED = "machine_generated"
    TRANSCRIBED = "transcribed"
    UNKNOWN = "unknown"


class ContentClass(StrEnum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TURN = "turn"
    CAPTION = "caption"
    TABLE = "table"
    TABLE_CELL = "table_cell"
    CODE = "code"
    FORMULA = "formula"
    RAW_MARKUP = "raw_markup"
    PICTURE = "picture"
    PICTURE_DESCRIPTION = "picture_description"
    NOTE = "note"
    NAVIGATION = "navigation"
    METADATA = "metadata"
    FURNITURE = "furniture"
    BACKGROUND = "background"
    INVISIBLE = "invisible"
    GROUP = "group"
    FIELD = "field"
    ASSET = "asset"
    OTHER = "other"


class DispositionKind(StrEnum):
    PRIMARY = "primary"
    SIDE_CHANNEL = "side_channel"
    EXCLUDED = "excluded"
    TRANSFORMED = "transformed"
    DEDUPLICATED = "deduplicated"
    REJECTED = "rejected"


class AnalysisStatus(StrEnum):
    ANALYSED = "analysed"
    NOT_ANALYSED = "not_analysed"
    EMPTY_PRIMARY_DISCOURSE = "empty_primary_discourse"


class SegmentKind(StrEnum):
    SOURCE = "source"
    SEPARATOR = "separator"
    MACRO_REPRESENTATION = "macro_representation"


class AnchorKind(StrEnum):
    CHARACTER = "character"
    BYTE = "byte"
    LINE = "line"
    ITEM = "item"
    XML_PATH = "xml_path"
    JSON_POINTER = "json_pointer"
    PAGE = "page"
    TIME = "time"
    BOUNDING_BOX = "bounding_box"
    TABLE_COORDINATE = "table_coordinate"
    QUOTE = "quote"


class StructureKind(StrEnum):
    DOCUMENT = "document"
    SECTION = "section"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TURN = "turn"
    SLIDE = "slide"
    PAGE = "page"
    TABLE = "table"
    ROW = "row"
    CELL = "cell"
    GROUP = "group"
    FIELD = "field"
    RANGE = "range"


class CacheStatus(StrEnum):
    DISABLED = "disabled"
    MISS = "miss"
    HIT = "hit"
    WRITTEN = "written"


class FailureStage(StrEnum):
    READ = "read"
    IDENTIFY = "identify"
    VALIDATE = "validate"
    INVENTORY = "inventory"
    POLICY = "policy"
    PREPARE = "prepare"
    VERIFY = "verify"
    CACHE = "cache"
    ANALYSE = "analyse"
    ANCHOR = "anchor"
    SERIALIZE = "serialize"


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )


class PreparedRange(_StrictModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("range end must be greater than start")
        return self

    @property
    def length(self) -> int:
        return self.end - self.start


class ConversionActivity(_StrictModel):
    activity_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    tool_version: str | None = None
    source_identity: str | None = None
    output_identity: str | None = None


class RawContractDeclaration(_StrictModel):
    schema_name: str | None = None
    version: str | None = None
    namespace: str | None = None


class SourceSummary(_StrictModel):
    source_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_name: str = Field(min_length=1)
    source_form: SourceForm
    media_type: str = Field(min_length=1)
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_size_bytes: int = Field(ge=0)
    original_source: str | None = None
    conversion_provenance: tuple[ConversionActivity, ...] = ()
    raw_contract: RawContractDeclaration | None = None


class SourceArtifact(_StrictModel):
    schema_version: str = "1.0.0"
    source_id: str = ""
    source_name: str = Field(min_length=1)
    source_form: SourceForm
    media_type: str = Field(min_length=1)
    raw_sha256: str = ""
    raw_size_bytes: int = -1
    raw_bytes: bytes | None = None
    edus: tuple[str, ...] | None = None
    original_source: str | None = None
    conversion_provenance: tuple[ConversionActivity, ...] = ()
    raw_contract: RawContractDeclaration | None = None

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        if (self.raw_bytes is None) == (self.edus is None):
            raise ValueError("provide exactly one of raw_bytes or edus")
        if self.source_form is SourceForm.EDUS and self.edus is None:
            raise ValueError("EDU source form requires edus")
        if self.source_form is not SourceForm.EDUS and self.raw_bytes is None:
            raise ValueError("non-EDU source form requires raw_bytes")
        payload_bytes = self.raw_bytes if self.raw_bytes is not None else _canonical_edus(self.edus or ())
        raw_sha256 = sha256_bytes(payload_bytes)
        raw_size_bytes = len(payload_bytes)
        identity_payload = {
            "schema_version": self.schema_version,
            "source_name": self.source_name,
            "source_form": self.source_form.value,
            "media_type": self.media_type,
            "raw_sha256": raw_sha256,
            "raw_size_bytes": raw_size_bytes,
            "original_source": self.original_source,
            "conversion_provenance": self.conversion_provenance,
            "raw_contract": self.raw_contract,
        }
        source_id = semantic_sha256(identity_payload)
        if self.raw_sha256 and self.raw_sha256 != raw_sha256:
            raise ValueError("raw payload SHA-256 does not match raw_sha256")
        if self.raw_size_bytes >= 0 and self.raw_size_bytes != raw_size_bytes:
            raise ValueError("raw payload size does not match raw_size_bytes")
        if self.source_id and self.source_id != source_id:
            raise ValueError("source identity does not match immutable source fields")
        object.__setattr__(self, "raw_sha256", raw_sha256)
        object.__setattr__(self, "raw_size_bytes", raw_size_bytes)
        object.__setattr__(self, "source_id", source_id)
        return self

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        source_name: str,
        original_source: str | None = None,
        conversion_provenance: Sequence[ConversionActivity] = (),
    ) -> Self:
        return cls(
            source_name=source_name,
            source_form=SourceForm.TEXT,
            media_type="text/plain; charset=utf-8",
            raw_bytes=text.encode("utf-8"),
            original_source=original_source,
            conversion_provenance=tuple(conversion_provenance),
        )

    @classmethod
    def from_edus(
        cls,
        edus: Sequence[str],
        *,
        source_name: str,
        original_source: str | None = None,
        conversion_provenance: Sequence[ConversionActivity] = (),
    ) -> Self:
        materialized = tuple(edus)
        for index, edu in enumerate(materialized):
            if not edu.strip():
                raise ValueError(f"EDU at index {index} must be a non-empty string")
        if not materialized:
            raise ValueError("EDU source must contain at least one EDU")
        return cls(
            source_name=source_name,
            source_form=SourceForm.EDUS,
            media_type="application/vnd.isanlp-rst.edus+json",
            edus=materialized,
            original_source=original_source,
            conversion_provenance=tuple(conversion_provenance),
        )

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        *,
        source_form: SourceForm,
        source_name: str,
        media_type: str,
        original_source: str | None = None,
        conversion_provenance: Sequence[ConversionActivity] = (),
    ) -> Self:
        if source_form is SourceForm.EDUS:
            raise ValueError("use from_edus for presegmented EDU input")
        if source_form in {SourceForm.TEXT, SourceForm.MARKDOWN, SourceForm.DOCLANG_XML, SourceForm.DOCLING_JSON}:
            data.decode("utf-8", errors="strict")
        raw_contract = _raw_contract(data, source_form)
        return cls(
            source_name=source_name,
            source_form=source_form,
            media_type=media_type,
            raw_bytes=bytes(data),
            original_source=original_source,
            conversion_provenance=tuple(conversion_provenance),
            raw_contract=raw_contract,
        )

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        source_form: SourceForm | None = None,
        original_source: str | None = None,
        conversion_provenance: Sequence[ConversionActivity] = (),
    ) -> Self:
        source_path = Path(path)
        data = source_path.read_bytes()
        selected_form = source_form or _identify_path(source_path, data)
        media_type = _media_type(selected_form)
        return cls.from_bytes(
            data,
            source_form=selected_form,
            source_name=source_path.name,
            media_type=media_type,
            original_source=original_source or source_path.resolve().as_uri(),
            conversion_provenance=conversion_provenance,
        )

    def summary(self) -> SourceSummary:
        return SourceSummary(
            source_id=self.source_id,
            source_name=self.source_name,
            source_form=self.source_form,
            media_type=self.media_type,
            raw_sha256=self.raw_sha256,
            raw_size_bytes=self.raw_size_bytes,
            original_source=self.original_source,
            conversion_provenance=self.conversion_provenance,
            raw_contract=self.raw_contract,
        )


class SourceContractIdentity(_StrictModel):
    family: str = Field(min_length=1)
    raw_declared_schema: RawContractDeclaration | None = None
    accepted_schema: RawContractDeclaration | None = None
    validator_distribution: str = Field(min_length=1)
    validator_version: str = Field(min_length=1)
    validator_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_profile: tuple[tuple[str, str], ...] = ()

    @property
    def semantic_digest(self) -> str:
        return semantic_sha256(self)


class NativeAnchor(_StrictModel):
    artifact_id: str = Field(min_length=1)
    item_id: str | None = None
    kind: AnchorKind
    selector: str = Field(min_length=1)
    range: PreparedRange | None = None
    quote: str | None = None
    prefix: str | None = None
    suffix: str | None = None
    structure_path: tuple[str, ...] = ()


class ContentInventoryItem(_StrictModel):
    item_id: str = Field(min_length=1)
    parent_id: str | None
    child_ids: tuple[str, ...] = ()
    content_class: ContentClass
    authorship_role: AuthorshipRole = AuthorshipRole.UNKNOWN
    content_layer: str | None = None
    text: str | None = None
    text_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    native_anchors: tuple[NativeAnchor, ...] = ()
    attributes: tuple[tuple[str, str], ...] = ()
    inventory_adapter: str = "isanlp_rst.ingest/v1"

    @model_validator(mode="after")
    def text_identity(self) -> Self:
        if self.text is None and self.text_sha256 is not None:
            raise ValueError("text_sha256 requires text")
        if self.text is not None:
            expected = sha256_bytes(self.text.encode("utf-8"))
            if self.text_sha256 is None:
                object.__setattr__(self, "text_sha256", expected)
            elif self.text_sha256 != expected:
                raise ValueError("inventory text SHA-256 mismatch")
        if len(self.child_ids) != len(set(self.child_ids)):
            raise ValueError("inventory child IDs must be unique")
        return self


class Disposition(_StrictModel):
    item_id: str = Field(min_length=1)
    kind: DispositionKind
    reason_code: str = Field(min_length=1)
    policy_rule_id: str = Field(min_length=1)
    prepared_segment_ids: tuple[str, ...] = ()
    side_channel_id: str | None = None
    replaced_by_item_id: str | None = None


class DuplicateFinding(_StrictModel):
    normalized_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    item_ids: tuple[str, ...] = Field(min_length=2)
    exact: bool = True
    action: str = Field(min_length=1)


class PreparationPolicy(_StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    primary_classes: tuple[ContentClass, ...]
    side_channel_classes: tuple[ContentClass, ...]
    excluded_classes: tuple[ContentClass, ...]
    deduplicate_conversion_artifacts: bool = False
    normalization: str = "preserve"
    partial: bool = False

    @model_validator(mode="after")
    def disjoint_classes(self) -> Self:
        groups = (set(self.primary_classes), set(self.side_channel_classes), set(self.excluded_classes))
        if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
            raise ValueError("policy content-class groups must be disjoint")
        if self.partial:
            raise ValueError("partial production ingest is not supported by contract v1")
        return self

    @property
    def policy_digest(self) -> str:
        return semantic_sha256(self)


class PreparedSegment(_StrictModel):
    segment_id: str = Field(min_length=1)
    kind: SegmentKind
    prepared_range: PreparedRange
    text: str
    source_item_id: str | None = None
    source_range: PreparedRange | None = None
    original_text: str | None = None
    transformation_ids: tuple[str, ...] = ()
    native_anchors: tuple[NativeAnchor, ...] = ()
    structure_path: tuple[str, ...] = ()

    @model_validator(mode="after")
    def origin_is_coherent(self) -> Self:
        if len(self.text) != self.prepared_range.length:
            raise ValueError("segment text length must equal prepared range length")
        if self.kind is SegmentKind.SOURCE:
            if self.source_item_id is None or self.source_range is None or self.original_text is None:
                raise ValueError("source segment requires source identity, range, and original text")
        elif self.source_item_id is not None or self.source_range is not None:
            raise ValueError("synthetic segment cannot claim a source range")
        return self


class StructureNode(_StrictModel):
    node_id: str = Field(min_length=1)
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    kind: StructureKind
    prepared_range: PreparedRange | None = None
    source_item_ids: tuple[str, ...] = ()


class PreparedRstDocument(_StrictModel):
    text: str
    document: RstDocument
    segments: tuple[PreparedSegment, ...]
    structure: tuple[StructureNode, ...]
    primary_item_ids: tuple[str, ...]
    side_channel_item_ids: tuple[str, ...]
    semantic_digest: str = ""

    @model_validator(mode="after")
    def complete_prepared_text(self) -> Self:
        cursor = 0
        parts: list[str] = []
        for segment in self.segments:
            if segment.prepared_range.start != cursor:
                raise ValueError("prepared segments must be contiguous and ordered")
            cursor = segment.prepared_range.end
            parts.append(segment.text)
        if cursor != len(self.text) or "".join(parts) != self.text:
            raise ValueError("prepared segments must cover prepared text exactly")
        digest = semantic_sha256(
            {
                "text": self.text,
                "segments": self.segments,
                "structure": self.structure,
                "primary_item_ids": self.primary_item_ids,
                "side_channel_item_ids": self.side_channel_item_ids,
            }
        )
        if self.semantic_digest and self.semantic_digest != digest:
            raise ValueError("prepared document semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", digest)
        return self


class AnalysisUnit(_StrictModel):
    unit_id: str = Field(min_length=1)
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    structure_kind: StructureKind
    output_range: PreparedRange
    context_range: PreparedRange | None = None
    source_item_ids: tuple[str, ...] = ()
    capacity_unit: str = Field(min_length=1)
    capacity_maximum: int = Field(gt=0)


class SubdivisionPlan(_StrictModel):
    algorithm_version: str = Field(min_length=1)
    units: tuple[AnalysisUnit, ...]
    semantic_digest: str = ""

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        ids = [unit.unit_id for unit in self.units]
        if len(ids) != len(set(ids)):
            raise ValueError("analysis unit IDs must be unique")
        digest = semantic_sha256({"algorithm_version": self.algorithm_version, "units": self.units})
        if self.semantic_digest and self.semantic_digest != digest:
            raise ValueError("subdivision semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", digest)
        return self


class AnalysisAnchor(_StrictModel):
    analysis_id: str = Field(min_length=1)
    analysis_kind: str = Field(min_length=1)
    prepared_ranges: tuple[PreparedRange, ...]
    source_segment_ids: tuple[str, ...]
    native_anchors: tuple[NativeAnchor, ...]
    origin: str = Field(pattern=r"^(local|macro)$")


class PreparationReceipt(_StrictModel):
    source_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    preparation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    subdivision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    pipeline_version: str = INGEST_PIPELINE_VERSION
    result_contract_version: str = INGEST_SCHEMA_VERSION
    inventory_count: int = Field(ge=0)
    disposition_count: int = Field(ge=0)
    inventory_coverage: float = Field(ge=0.0, le=1.0)
    primary_source_coverage: float = Field(ge=0.0, le=1.0)
    prepared_text_coverage: float = Field(ge=0.0, le=1.0)
    analysis_anchor_coverage: float = Field(ge=0.0, le=1.0)
    dispositions: tuple[Disposition, ...] = ()
    duplicate_findings: tuple[DuplicateFinding, ...] = ()
    warnings: tuple[str, ...] = ()
    cache_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def reconciled(self) -> Self:
        if self.inventory_count != self.disposition_count:
            raise ValueError("inventory and disposition totals do not reconcile")
        if self.dispositions and len(self.dispositions) != self.disposition_count:
            raise ValueError("disposition ledger length does not reconcile")
        if len({item.item_id for item in self.dispositions}) != len(self.dispositions):
            raise ValueError("each inventory item must have exactly one disposition")
        return self


class ExecutionReceipt(_StrictModel):
    run_id: str = Field(min_length=1)
    started_at: datetime
    cache_status: CacheStatus
    duration_ms: tuple[tuple[str, float], ...] = ()
    peak_rss_bytes: int | None = Field(default=None, ge=0)
    warnings: tuple[str, ...] = ()

    def semantic_payload(self) -> dict[str, object]:
        return {}


class ProductionAnalysisResult(_StrictModel):
    schema_name: str = INGEST_SCHEMA_NAME
    schema_version: str = INGEST_SCHEMA_VERSION
    source: SourceSummary
    analysis_status: AnalysisStatus
    prepared_document: PreparedRstDocument | None = None
    analysis: RstAnalysis | None = None
    analysis_anchors: tuple[AnalysisAnchor, ...] = ()
    preparation_receipt: PreparationReceipt
    execution_receipt: ExecutionReceipt
    semantic_digest: str = ""

    @model_validator(mode="after")
    def valid_envelope(self) -> Self:
        if self.schema_name != INGEST_SCHEMA_NAME or self.schema_version != INGEST_SCHEMA_VERSION:
            raise ValueError("unsupported production ingest result schema")
        if self.source.source_id != self.preparation_receipt.source_id:
            raise ValueError("source and preparation receipt identities differ")
        if self.analysis_status is AnalysisStatus.EMPTY_PRIMARY_DISCOURSE and self.analysis is not None:
            raise ValueError("empty primary discourse cannot contain an analysis")
        semantic = {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "source": self.source,
            "analysis_status": self.analysis_status,
            "prepared_document_digest": (
                self.prepared_document.semantic_digest if self.prepared_document is not None else None
            ),
            "analysis": _analysis_semantic_payload(self.analysis),
            "analysis_anchors": self.analysis_anchors,
            "preparation_receipt": self.preparation_receipt,
        }
        digest = semantic_sha256(semantic)
        if self.semantic_digest and self.semantic_digest != digest:
            raise ValueError("production result semantic digest mismatch")
        object.__setattr__(self, "semantic_digest", digest)
        return self

    def to_json(self, *, indent: int | None = None) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, payload: str | bytes) -> Self:
        return cls.model_validate_json(payload)


class ProductionIngestError(RuntimeError):
    """Typed failure with safe, completed-stage diagnostic evidence."""

    def __init__(
        self,
        *,
        stage: FailureStage,
        code: str,
        artifact_id: str,
        expectation: str,
        detail: str,
        item_id: str | None = None,
        diagnostic_counts: dict[str, int] | None = None,
    ) -> None:
        self.stage = stage
        self.code = code
        self.artifact_id = artifact_id
        self.item_id = item_id
        self.expectation = expectation
        self.detail = detail
        self.diagnostic_counts = dict(diagnostic_counts or {})
        super().__init__(f"{stage.value}/{code} for {artifact_id}: {expectation}; {detail}")

    def as_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage.value,
            "code": self.code,
            "artifact_id": self.artifact_id,
            "item_id": self.item_id,
            "expectation": self.expectation,
            "detail": self.detail,
            "diagnostic_counts": dict(sorted(self.diagnostic_counts.items())),
        }


def _canonical_edus(edus: tuple[str, ...]) -> bytes:
    return json.dumps(edus, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _analysis_semantic_payload(analysis: RstAnalysis | None) -> dict[str, object] | None:
    if analysis is None:
        return None
    provenance = analysis.provenance
    return {
        "document_id": analysis.document_id,
        "formalism": analysis.formalism,
        "nodes": analysis.nodes,
        "primary_edges": analysis.primary_edges,
        "secondary_edges": analysis.secondary_edges,
        "signals": analysis.signals,
        "provenance": {
            "producer": provenance.producer,
            "software_version": provenance.software_version,
            "source_revision": provenance.source_revision,
            "model_id": provenance.model_id,
            "model_digest": provenance.model_digest,
            "ontology_version": provenance.ontology_version,
            "ontology_digest": provenance.ontology_digest,
        },
        "warnings": analysis.warnings,
        "failure_code": analysis.failure_code,
    }


def _raw_contract(data: bytes, source_form: SourceForm) -> RawContractDeclaration | None:
    if source_form is SourceForm.DOCLING_JSON:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            document = cast(dict[object, object], payload)
            schema_name = document.get("schema_name")
            version = document.get("version")
            return RawContractDeclaration(
                schema_name=schema_name if isinstance(schema_name, str) else None,
                version=version if isinstance(version, str) else None,
            )
    if source_form is SourceForm.DOCLANG_XML:
        prefix = data[:4096].decode("utf-8", errors="strict")
        namespace = None
        if 'xmlns="' in prefix:
            namespace = prefix.split('xmlns="', 1)[1].split('"', 1)[0]
        return RawContractDeclaration(namespace=namespace)
    return None


def _identify_path(path: Path, data: bytes) -> SourceForm:
    name = path.name.lower()
    if name.endswith((".md", ".markdown")):
        return SourceForm.MARKDOWN
    if name.endswith((".dclg", ".dclg.xml")):
        return SourceForm.DOCLANG_XML
    if name.endswith(".dclx"):
        return SourceForm.DOCLANG_ARCHIVE
    if name.endswith(".docling.json"):
        return SourceForm.DOCLING_JSON
    if name.endswith(".json"):
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError("JSON source is invalid and source_form cannot be inferred") from exc
        if isinstance(payload, dict) and cast(dict[object, object], payload).get("schema_name") == "DoclingDocument":
            return SourceForm.DOCLING_JSON
    raise ValueError(f"source_form is required for ambiguous path {path.name!r}")


def _media_type(source_form: SourceForm) -> str:
    return {
        SourceForm.TEXT: "text/plain; charset=utf-8",
        SourceForm.EDUS: "application/vnd.isanlp-rst.edus+json",
        SourceForm.MARKDOWN: "text/markdown; charset=utf-8",
        SourceForm.DOCLING_JSON: "application/vnd.docling.document+json",
        SourceForm.DOCLANG_XML: "application/vnd.doclang+xml",
        SourceForm.DOCLANG_ARCHIVE: "application/vnd.doclang.archive+zip",
    }[source_form]


__all__ = [
    "INGEST_PIPELINE_VERSION",
    "INGEST_SCHEMA_NAME",
    "INGEST_SCHEMA_VERSION",
    "AnalysisAnchor",
    "AnalysisStatus",
    "AnalysisUnit",
    "AnchorKind",
    "AuthorshipRole",
    "CacheStatus",
    "ContentClass",
    "ContentInventoryItem",
    "ConversionActivity",
    "Disposition",
    "DispositionKind",
    "DuplicateFinding",
    "ExecutionReceipt",
    "FailureStage",
    "NativeAnchor",
    "PreparationPolicy",
    "PreparationReceipt",
    "PreparedRange",
    "PreparedRstDocument",
    "PreparedSegment",
    "ProductionAnalysisResult",
    "ProductionIngestError",
    "RawContractDeclaration",
    "SegmentKind",
    "SourceArtifact",
    "SourceContractIdentity",
    "SourceForm",
    "SourceSummary",
    "StructureKind",
    "StructureNode",
    "SubdivisionPlan",
]
