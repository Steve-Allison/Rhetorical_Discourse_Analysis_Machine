"""Source, inventory, representation, relationship, and anchor contracts."""

from collections.abc import Sequence
import base64
import binascii
from enum import StrEnum
import json
from pathlib import Path
from typing import Annotated, Literal, Self, cast

from pydantic import Field, ValidationInfo, field_serializer, field_validator, model_validator

from rdam.ingest.contracts.base import SemanticVersion, Sha256Identity, StrictContractModel
from rdam.ingest.identity import semantic_sha256, sha256_bytes


class SourceForm(StrEnum):
    TEXT = "text"
    EDUS = "edus"
    MARKDOWN = "markdown"
    DOCLING_JSON = "docling_json"
    DOCLANG_XML = "doclang_xml"
    DOCLANG_ARCHIVE = "doclang_archive"


class OriginClassification(StrEnum):
    IN_MEMORY = "in_memory"
    LOCAL_FILE = "local_file"
    URI = "uri"
    DECLARED = "declared"


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


class DispositionDecision(StrEnum):
    PRIMARY = "primary"
    RETAINED = "retained"
    DUPLICATE = "duplicate"
    TRANSFORMED = "transformed"
    REJECTED_INVALID = "rejected_invalid"


class DispositionReason(StrEnum):
    AUTHORED_PRIMARY = "authored_primary"
    MACHINE_GENERATED_PRIMARY = "machine_generated_primary"
    VALID_NON_PRIMARY = "valid_non_primary"
    UNSUPPORTED_FOR_ANALYSIS = "unsupported_for_analysis"
    EXACT_CONVERSION_DUPLICATE = "exact_conversion_duplicate"
    NORMALIZED_FOR_ANALYSIS = "normalized_for_analysis"
    INVALID_SOURCE_ITEM = "invalid_source_item"


class AnchorKind(StrEnum):
    TEXT_SPAN = "text_span"
    PAGE_BOX = "page_box"
    SOURCE_PATH = "source_path"
    ITEM = "item"
    TABLE_COORDINATE = "table_coordinate"
    ARCHIVE_MEMBER = "archive_member"


class ConversionActivity(StrictContractModel):
    activity_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    tool_version: str | None = None
    source_identity: str | None = None
    output_identity: str | None = None


class RawContractDeclaration(StrictContractModel):
    schema_name: str | None = None
    version: str | None = None
    namespace: str | None = None


class SourceArtifact(StrictContractModel):
    """Exact in-memory submission boundary for all six supported source forms."""

    source_id: str = ""
    source_name: str = Field(min_length=1)
    source_form: SourceForm
    media_type: str = Field(min_length=1)
    encoding: Literal["utf-8"] | None = None
    raw_sha256: Sha256Identity | None = None
    raw_size_bytes: int = Field(default=-1, ge=-1)
    raw_bytes: bytes | None = Field(default=None, json_schema_extra={"contentEncoding": "base64"})
    edus: tuple[str, ...] | None = None
    declared_artifact_id: str | None = None
    declared_origin: str | None = None
    origin_classification: OriginClassification = OriginClassification.IN_MEMORY
    conversion_provenance: tuple[ConversionActivity, ...] = ()
    raw_contract: RawContractDeclaration | None = None

    @field_validator("raw_bytes", mode="before")
    @classmethod
    def decode_standard_base64(cls, value: object, info: ValidationInfo) -> object:
        if info.mode != "json" or value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("raw_bytes must be standard padded base64")
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("invalid standard base64") from error
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("base64 must use canonical padding and alphabet")
        return decoded

    @field_serializer("raw_bytes", when_used="json")
    def encode_standard_base64(self, value: bytes | None) -> str | None:
        return None if value is None else base64.b64encode(value).decode("ascii")

    @model_validator(mode="after")
    def complete_identity(self) -> Self:
        if self.raw_bytes is None and self.edus is None:
            raise ValueError("provide exactly one source payload: raw_bytes or edus")
        if self.raw_bytes is not None and self.source_form is not SourceForm.DOCLANG_ARCHIVE:
            self.raw_bytes.decode("utf-8", errors="strict")
        if self.raw_bytes is not None and self.edus is not None:
            if self.source_form is not SourceForm.EDUS or json.loads(self.raw_bytes) != list(self.edus):
                raise ValueError("raw EDU bytes must match the supplied EDUs")
        if self.source_form is SourceForm.EDUS:
            if not self.edus:
                raise ValueError("EDU source form requires at least one EDU")
            for index, edu in enumerate(self.edus):
                if not edu.strip():
                    raise ValueError(f"EDU at index {index} must be a non-empty string")
        elif self.raw_bytes is None:
            raise ValueError("non-EDU source form requires raw_bytes")
        payload = self.raw_bytes if self.raw_bytes is not None else _canonical_edus(self.edus or ())
        digest = Sha256Identity(hex_digest=sha256_bytes(payload))
        source_id = semantic_sha256(
            {
                "source_name": self.source_name,
                "source_form": self.source_form,
                "media_type": self.media_type,
                "encoding": self.encoding,
                "raw_sha256": digest,
                "raw_size_bytes": len(payload),
                "declared_artifact_id": self.declared_artifact_id,
                "declared_origin": self.declared_origin,
                "origin_classification": self.origin_classification,
                "conversion_provenance": self.conversion_provenance,
                "raw_contract": self.raw_contract,
            }
        )
        if self.raw_sha256 is not None and self.raw_sha256 != digest:
            raise ValueError("raw payload SHA-256 does not match raw_sha256")
        if self.raw_size_bytes >= 0 and self.raw_size_bytes != len(payload):
            raise ValueError("raw payload size does not match raw_size_bytes")
        if self.source_id and self.source_id != source_id:
            raise ValueError("source identity does not match immutable source fields")
        object.__setattr__(self, "raw_sha256", digest)
        object.__setattr__(self, "raw_size_bytes", len(payload))
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
            encoding="utf-8",
            raw_bytes=text.encode("utf-8"),
            declared_origin=original_source,
            origin_classification=(OriginClassification.URI if original_source else OriginClassification.IN_MEMORY),
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
        if not materialized:
            raise ValueError("EDU source must contain at least one EDU")
        for index, edu in enumerate(materialized):
            if not edu.strip():
                raise ValueError(f"EDU at index {index} must be a non-empty string")
        return cls(
            source_name=source_name,
            source_form=SourceForm.EDUS,
            media_type="application/vnd.isanlp-rst.edus+json",
            encoding="utf-8",
            edus=materialized,
            declared_origin=original_source,
            origin_classification=(OriginClassification.URI if original_source else OriginClassification.IN_MEMORY),
            conversion_provenance=tuple(conversion_provenance),
        )

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        *,
        source_form: SourceForm,
        source_name: str,
        media_type: str | None = None,
        original_source: str | None = None,
        conversion_provenance: Sequence[ConversionActivity] = (),
    ) -> Self:
        if source_form is SourceForm.EDUS:
            payload: object = json.loads(data)
            if not isinstance(payload, list) or not payload or not all(
                isinstance(edu, str) and edu.strip() for edu in cast(list[object], payload)
            ):
                raise ValueError("EDU bytes must contain a non-empty JSON array of non-empty strings")
            return cls(
                source_name=source_name, source_form=source_form,
                media_type=media_type or _media_type(source_form), encoding="utf-8",
                raw_bytes=bytes(data), edus=tuple(cast(list[str], payload)),
                declared_origin=original_source,
                origin_classification=OriginClassification.URI if original_source else OriginClassification.IN_MEMORY,
                conversion_provenance=tuple(conversion_provenance),
            )
        textual = source_form is not SourceForm.DOCLANG_ARCHIVE
        if textual:
            data.decode("utf-8", errors="strict")
        return cls(
            source_name=source_name,
            source_form=source_form,
            media_type=media_type or _media_type(source_form),
            encoding="utf-8" if textual else None,
            raw_bytes=bytes(data),
            declared_origin=original_source,
            origin_classification=(OriginClassification.URI if original_source else OriginClassification.IN_MEMORY),
            conversion_provenance=tuple(conversion_provenance),
            raw_contract=_raw_contract(data, source_form),
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
        selected = source_form or _identify_path(source_path, data)
        artifact = cls.from_bytes(
            data,
            source_form=selected,
            source_name=source_path.name,
            media_type=_media_type(selected),
            original_source=original_source or source_path.resolve().as_uri(),
            conversion_provenance=conversion_provenance,
        )
        return cls.model_validate({
            **artifact.model_dump(exclude={"source_id"}),
            "origin_classification": OriginClassification.LOCAL_FILE,
        })

    def summary(self) -> SourceSummary:
        if self.raw_sha256 is None:
            raise ValueError("validated source artifact has no byte identity")
        return SourceSummary(
            source_id=self.source_id,
            source_name=self.source_name,
            source_form=self.source_form,
            origin_classification=self.origin_classification,
            declared_artifact_id=self.declared_artifact_id,
            media_type=self.media_type,
            encoding=self.encoding,
            byte_length=self.raw_size_bytes,
            byte_identity=self.raw_sha256,
            raw_contract=self.raw_contract,
        )

    @property
    def original_source(self) -> str | None:
        return self.declared_origin


class SourceSummary(StrictContractModel):
    source_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_name: str = Field(min_length=1)
    source_form: SourceForm
    origin_classification: OriginClassification
    declared_artifact_id: str | None = None
    media_type: str = Field(min_length=1)
    encoding: Literal["utf-8"] | None = None
    byte_length: int = Field(ge=0)
    byte_identity: Sha256Identity
    raw_contract: RawContractDeclaration | None = None

    @property
    def raw_sha256(self) -> str:
        return self.byte_identity.hex_digest

    @property
    def raw_size_bytes(self) -> int:
        return self.byte_length


class SourceContractIdentity(StrictContractModel):
    adapter: str = Field(min_length=1)
    adapter_contract_version: SemanticVersion
    upstream_format: str | None = None
    upstream_version: str | None = None
    schema_identity: Sha256Identity | None = None
    assumptions: tuple[str, ...] = ()

    @property
    def semantic_digest(self) -> str:
        return semantic_sha256(self)


class SourceOrigin(StrictContractModel):
    authorship: AuthorshipRole
    source_layer: str | None = None
    producer: str | None = None


class TextRepresentation(StrictContractModel):
    kind: Literal["text"] = "text"
    text: str
    language: str | None = None
    semantic_role: str
    attributes: tuple[tuple[str, str], ...] = ()


class TableCell(StrictContractModel):
    cell_id: str
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    row_span: int = Field(default=1, gt=0)
    column_span: int = Field(default=1, gt=0)
    text: str | None = None
    header: bool = False
    linked_item_ids: tuple[str, ...] = ()


class TableRepresentation(StrictContractModel):
    kind: Literal["table"] = "table"
    cells: tuple[TableCell, ...]


class ListItemRepresentation(StrictContractModel):
    item_id: str
    text: str | None
    child_item_ids: tuple[str, ...] = ()


class ListRepresentation(StrictContractModel):
    kind: Literal["list"] = "list"
    ordered: bool
    marker: str | None = None
    items: tuple[ListItemRepresentation, ...]


class MetadataEntry(StrictContractModel):
    key: str
    value: str
    value_type: str


class MetadataRepresentation(StrictContractModel):
    kind: Literal["metadata"] = "metadata"
    entries: tuple[MetadataEntry, ...]


class AnnotationRepresentation(StrictContractModel):
    kind: Literal["annotation"] = "annotation"
    label: str
    text: str | None = None


class MediaReferenceRepresentation(StrictContractModel):
    kind: Literal["media_reference"] = "media_reference"
    media_identity: str
    source_reference: str | None = None
    caption: str | None = None
    description: str | None = None


class StructureRepresentation(StrictContractModel):
    kind: Literal["structure"] = "structure"
    structure_type: str
    label: str | None = None
    child_ids: tuple[str, ...] = ()


class CrossReferenceRepresentation(StrictContractModel):
    kind: Literal["cross_reference"] = "cross_reference"
    target_identity: str
    relation: str


class RedactedContentRepresentation(StrictContractModel):
    kind: Literal["redacted"] = "redacted"
    original_kind: str
    byte_length: int = Field(ge=0)
    character_length: int | None = Field(default=None, ge=0)
    identity: Sha256Identity


type ContentRepresentation = Annotated[
    TextRepresentation
    | TableRepresentation
    | ListRepresentation
    | MetadataRepresentation
    | AnnotationRepresentation
    | MediaReferenceRepresentation
    | StructureRepresentation
    | CrossReferenceRepresentation
    | RedactedContentRepresentation,
    Field(discriminator="kind"),
]


class TextSpanAnchor(StrictContractModel):
    kind: Literal["text_span"] = "text_span"
    artifact_identity: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str | None = None

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("text anchor end must be greater than start")
        return self


class PageBoxAnchor(StrictContractModel):
    kind: Literal["page_box"] = "page_box"
    artifact_identity: str
    page: int = Field(ge=1)
    left: float
    top: float
    right: float
    bottom: float
    coordinate_origin: str


class PageAnchor(StrictContractModel):
    kind: Literal["page"] = "page"
    artifact_identity: str
    page: int = Field(ge=1)
    provenance_index: int | None = Field(default=None, ge=0)


class CoordinateBoxAnchor(StrictContractModel):
    kind: Literal["coordinate_box"] = "coordinate_box"
    artifact_identity: str
    x0: float
    y0: float
    x1: float
    y1: float
    x0_resolution: str
    y0_resolution: str
    x1_resolution: str
    y1_resolution: str
    coordinate_system: str


class SourcePathAnchor(StrictContractModel):
    kind: Literal["source_path"] = "source_path"
    artifact_identity: str
    path_kind: Literal["json_pointer", "xml_path", "line"]
    path: str


class ItemAnchor(StrictContractModel):
    kind: Literal["item"] = "item"
    artifact_identity: str
    item_identity: str


class TableCoordinateAnchor(StrictContractModel):
    kind: Literal["table_coordinate"] = "table_coordinate"
    artifact_identity: str
    row: int = Field(ge=0)
    column: int = Field(ge=0)


class ArchiveMemberAnchor(StrictContractModel):
    kind: Literal["archive_member"] = "archive_member"
    artifact_identity: str
    member_path: str
    member_identity: Sha256Identity


type SourceAnchor = Annotated[
    TextSpanAnchor
    | PageAnchor
    | PageBoxAnchor
    | CoordinateBoxAnchor
    | SourcePathAnchor
    | ItemAnchor
    | TableCoordinateAnchor
    | ArchiveMemberAnchor,
    Field(discriminator="kind"),
]


class ItemRelationship(StrictContractModel):
    relation: str
    target_identity: str
    target_kind: Literal["inventory_item", "external"]


class Disposition(StrictContractModel):
    decision: DispositionDecision
    reason: DispositionReason
    primary_segment_ids: tuple[str, ...] = ()
    duplicate_of: str | None = None
    transformation_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def coherent_decision(self) -> Self:
        if (self.decision is DispositionDecision.DUPLICATE) != (self.duplicate_of is not None):
            raise ValueError("duplicate disposition must name exactly one canonical item")
        if self.decision is not DispositionDecision.PRIMARY and self.primary_segment_ids:
            raise ValueError("only primary items can name primary segments")
        return self

    @property
    def retained(self) -> bool:
        return self.decision in {
            DispositionDecision.RETAINED,
            DispositionDecision.DUPLICATE,
            DispositionDecision.TRANSFORMED,
        }


class SpeakerIdentity(StrictContractModel):
    resolution: Literal["resolved", "unresolved"]
    participant_id: str | None = Field(default=None, min_length=1)
    display_name: str | None = Field(default=None, min_length=1)
    evidence: str = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_resolution(self) -> Self:
        if (self.resolution == "resolved") != (self.participant_id is not None):
            raise ValueError("resolved speakers require a participant id; unresolved speakers forbid one")
        return self


def _absent_speaker(value: SpeakerIdentity | None) -> bool:
    return value is None


class ContentInventoryItem(StrictContractModel):
    item_id: str = Field(min_length=1)
    classification: ContentClass
    origin: SourceOrigin
    representation: ContentRepresentation
    anchors: tuple[SourceAnchor, ...] = Field(min_length=1)
    parent_id: str | None = None
    child_ids: tuple[str, ...] = ()
    relationships: tuple[ItemRelationship, ...] = ()
    provider_attributes: tuple[tuple[str, str], ...] = ()
    disposition: Disposition
    speaker: SpeakerIdentity | None = Field(default=None, exclude_if=_absent_speaker)

    @model_validator(mode="after")
    def unique_links(self) -> Self:
        if self.classification is not ContentClass.TURN and self.speaker is not None:
            raise ValueError("only turns carry speaker identity")
        if len(self.child_ids) != len(set(self.child_ids)):
            raise ValueError("inventory child IDs must be unique")
        if len(self.provider_attributes) != len({key for key, _value in self.provider_attributes}):
            raise ValueError("provider attribute keys must be unique")
        return self

    @property
    def text(self) -> str | None:
        if isinstance(self.representation, TextRepresentation | AnnotationRepresentation):
            return self.representation.text
        return None


def _canonical_edus(edus: tuple[str, ...]) -> bytes:
    return json.dumps(edus, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


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
        prefix = data.decode("utf-8", errors="strict")[:4096]
        namespace = prefix.split('xmlns="', 1)[1].split('"', 1)[0] if 'xmlns="' in prefix else None
        return RawContractDeclaration(namespace=namespace)
    return None


def _identify_path(path: Path, data: bytes) -> SourceForm:
    name = path.name.casefold()
    if name.endswith((".txt", ".text")):
        return SourceForm.TEXT
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
    "AnchorKind",
    "AnnotationRepresentation",
    "ArchiveMemberAnchor",
    "AuthorshipRole",
    "ContentClass",
    "ContentInventoryItem",
    "ContentRepresentation",
    "ConversionActivity",
    "CoordinateBoxAnchor",
    "CrossReferenceRepresentation",
    "Disposition",
    "DispositionDecision",
    "DispositionReason",
    "ItemAnchor",
    "ItemRelationship",
    "ListItemRepresentation",
    "ListRepresentation",
    "MediaReferenceRepresentation",
    "MetadataEntry",
    "MetadataRepresentation",
    "OriginClassification",
    "PageAnchor",
    "PageBoxAnchor",
    "RawContractDeclaration",
    "RedactedContentRepresentation",
    "SourceAnchor",
    "SourceArtifact",
    "SourceContractIdentity",
    "SourceForm",
    "SourceOrigin",
    "SourcePathAnchor",
    "SourceSummary",
    "SpeakerIdentity",
    "StructureRepresentation",
    "TableCell",
    "TableCoordinateAnchor",
    "TableRepresentation",
    "TextRepresentation",
    "TextSpanAnchor",
]
