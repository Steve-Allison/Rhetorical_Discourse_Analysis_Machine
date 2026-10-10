"""Direct DocLang mapping into the current immutable ingestion contract."""

from importlib.metadata import distribution
import json
from pathlib import Path
import re

from rdam.ingest.doclang import decoder, document, loader, text_walker
from rdam.ingest.doclang.decoder import DecodedDoclangItem, decode_document, item_index
from rdam.ingest.doclang.document import DoclangDocument
from rdam.ingest import _classification, speakers
from rdam.ingest.contracts.base import SemanticVersion, Sha256Identity
from rdam.ingest.contracts.source import (
    AnnotationRepresentation,
    ArchiveMemberAnchor,
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    ContentRepresentation,
    CoordinateBoxAnchor,
    CrossReferenceRepresentation,
    Disposition,
    DispositionDecision,
    DispositionReason,
    ItemAnchor,
    ItemRelationship,
    ListItemRepresentation,
    ListRepresentation,
    MediaReferenceRepresentation,
    MetadataEntry,
    MetadataRepresentation,
    SourceAnchor,
    SourceArtifact,
    SourceContractIdentity,
    SourceForm,
    SourceOrigin,
    SourcePathAnchor,
    StructureRepresentation,
    TableCell,
    TableCoordinateAnchor,
    TableRepresentation,
    TextRepresentation,
)
from rdam.ingest.identity import semantic_sha256, sha256_file
from rdam.ingest.speakers import resolve_speaker, resolve_voice


def implementation_digest() -> str:
    """Bind every owned decoding and mapping dependency in the existing identity."""
    paths = (
        Path(__file__),
        Path(_classification.__file__),
        Path(document.__file__),
        Path(decoder.__file__),
        Path(loader.__file__),
        Path(text_walker.__file__),
        Path(speakers.__file__),
    )
    return semantic_sha256(tuple((path.name, sha256_file(path)) for path in paths))


def upstream_version() -> str:
    """The installed DocLang version, qualified by the upstream commit when installed from git."""
    installed = distribution("doclang")
    direct_url = installed.read_text("direct_url.json")
    commit = json.loads(direct_url).get("vcs_info", {}).get("commit_id") if direct_url else None
    return f"{installed.version}+git.{commit}" if commit else installed.version


def _classification_for(item: DecodedDoclangItem) -> ContentClass:
    classification = {
        "head": ContentClass.METADATA,
        "title": ContentClass.TITLE,
        "heading": ContentClass.HEADING,
        "text": ContentClass.PARAGRAPH,
        "footnote": ContentClass.PARAGRAPH,
        "list": ContentClass.GROUP,
        "ldiv": ContentClass.LIST_ITEM,
        "table": ContentClass.TABLE,
        "ched": ContentClass.TABLE_CELL,
        "rhed": ContentClass.TABLE_CELL,
        "corn": ContentClass.TABLE_CELL,
        "srow": ContentClass.TABLE_CELL,
        "fcel": ContentClass.TABLE_CELL,
        "ecel": ContentClass.TABLE_CELL,
        "code": ContentClass.CODE,
        "formula": ContentClass.FORMULA,
        "picture": ContentClass.PICTURE,
        "caption": ContentClass.CAPTION,
        "description": ContentClass.PICTURE_DESCRIPTION,
        "page_header": ContentClass.FURNITURE,
        "page_footer": ContentClass.FURNITURE,
        "field_region": ContentClass.FIELD,
        "field_item": ContentClass.FIELD,
        "key": ContentClass.FIELD,
        "value": ContentClass.FIELD,
        "asset": ContentClass.ASSET,
        "group": ContentClass.GROUP,
        "track": ContentClass.GROUP,
        "chapter": ContentClass.HEADING,
        "cover": ContentClass.PICTURE,
        "frame": ContentClass.PICTURE,
        "audio": ContentClass.ASSET,
    }.get(
        item.tag,
        ContentClass.METADATA
        if item.tag in {"label", "thread", "layer", "location", "hours", "minutes", "seconds", "msecs"}
        else ContentClass.OTHER,
    )
    if item.turn is not None:
        classification = ContentClass.TURN
    if "table" in item.ancestors and item.tag != "table":
        return ContentClass.TABLE_CELL
    if "picture" in item.ancestors and classification is ContentClass.PARAGRAPH:
        return ContentClass.PICTURE_DESCRIPTION
    if {"field_region", "field_item"} & item.ancestors:
        return ContentClass.FIELD
    if (
        classification is ContentClass.PARAGRAPH
        and item.text is not None
        and re.match(r"^\s*(?:SPEAKER[_ -]?\d+|[A-Z][A-Z0-9 _-]{1,40}):\s+", item.text)
    ):
        return ContentClass.TURN
    return classification


def _representation(
    item: DecodedDoclangItem, classification: ContentClass, children: tuple[DecodedDoclangItem, ...]
) -> ContentRepresentation:
    if classification is ContentClass.TABLE:
        return TableRepresentation(
            cells=tuple(
                TableCell(
                    cell_id=cell.path,
                    row=cell.row,
                    column=cell.column,
                    row_span=cell.row_span,
                    column_span=cell.column_span,
                    text=cell.surface.text or None,
                    header=cell.header,
                    linked_item_ids=cell.linked_paths,
                )
                for cell in item.cells
                if cell.path == cell.owner_path
            )
        )
    attributes = dict(item.attributes)
    target = attributes.get("uri") or attributes.get("href") or attributes.get("target")
    if target is not None and item.text is None:
        return CrossReferenceRepresentation(target_identity=target, relation="source_reference")
    if classification is ContentClass.GROUP and any(child.tag == "ldiv" for child in children):
        return ListRepresentation(
            ordered=False,
            items=tuple(
                ListItemRepresentation(item_id=child.path, text=child.text, child_item_ids=child.child_paths)
                for child in children
            ),
        )
    if classification in {ContentClass.METADATA, ContentClass.FIELD}:
        entries = tuple(MetadataEntry(key=key, value=value, value_type="string") for key, value in item.attributes)
        if item.text is not None:
            entries += (MetadataEntry(key="text", value=item.text, value_type="string"),)
        return MetadataRepresentation(entries=entries)
    if classification in {ContentClass.CAPTION, ContentClass.NOTE, ContentClass.PICTURE_DESCRIPTION}:
        return AnnotationRepresentation(label=classification.value, text=item.text)
    if classification in {ContentClass.PICTURE, ContentClass.ASSET}:
        reference = next((dict(child.attributes)["uri"] for child in children if "uri" in dict(child.attributes)), None)
        return MediaReferenceRepresentation(media_identity=item.path, source_reference=reference, description=item.text)
    if item.text is not None:
        return TextRepresentation(
            text=item.text,
            semantic_role=classification.value,
            attributes=tuple(
                (key, value)
                for key, value in item.attributes
                if not key.startswith("relationship:") and key not in {"href", "uri", "target"}
            ),
        )
    return StructureRepresentation(structure_type=classification.value, child_ids=item.child_paths)


def _anchors(item: DecodedDoclangItem, artifact: SourceArtifact) -> tuple[SourceAnchor, ...]:
    anchors: list[SourceAnchor] = [
        SourcePathAnchor(artifact_identity=artifact.source_id, path_kind="xml_path", path=item.path)
    ]
    if len(item.locations) == 4:
        (x0, xr0), (y0, yr0), (x1, xr1), (y1, yr1) = item.locations
        anchors.append(
            CoordinateBoxAnchor(
                artifact_identity=artifact.source_id,
                x0=float(x0),
                y0=float(y0),
                x1=float(x1),
                y1=float(y1),
                x0_resolution=xr0,
                y0_resolution=yr0,
                x1_resolution=xr1,
                y1_resolution=yr1,
                coordinate_system="doclang_location_axes",
            )
        )
    if item.cell is not None:
        anchors.append(
            TableCoordinateAnchor(artifact_identity=artifact.source_id, row=item.cell.row, column=item.cell.column)
        )
    return tuple(anchors)


def inventory_doclang(artifact: SourceArtifact) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    loaded = DoclangDocument.load(artifact.raw_bytes or b"", archive=artifact.source_form is SourceForm.DOCLANG_ARCHIVE)
    decoded = decode_document(loaded)
    by_path = item_index(decoded)
    classes = _classification.back_matter_classes(tuple((_classification_for(item), item.text) for item in decoded))
    items: list[ContentInventoryItem] = []
    for item, classification in zip(decoded, classes, strict=True):
        relationships = tuple(
            ItemRelationship(
                relation=key, target_identity=target, target_kind="inventory_item" if target in by_path else "external"
            )
            for key, target in item.attributes
            if key in {"href", "uri", "target"}
        )
        cue_attributes = (
            (("cue_id", item.cue.path), ("cue_start_ms", str(item.cue.start_ms)), ("cue_end_ms", str(item.cue.end_ms)))
            if item.cue is not None
            else ()
        )
        items.append(
            ContentInventoryItem(
                item_id=item.path,
                classification=classification,
                origin=SourceOrigin(
                    authorship=AuthorshipRole.TRANSCRIBED if item.turn is not None else AuthorshipRole.AUTHORED,
                    source_layer=item.layer,
                    producer="isanlp_rst.doclang.inventory/v1",
                ),
                representation=_representation(item, classification, tuple(by_path[path] for path in item.child_paths)),
                anchors=_anchors(item, artifact),
                parent_id=item.parent_path,
                child_ids=item.child_paths,
                relationships=relationships,
                provider_attributes=item.attributes + cue_attributes,
                speaker=(
                    resolve_voice(item.turn.speaker)
                    if item.turn is not None
                    else resolve_speaker(item.text or "", item.attributes)
                )
                if classification is ContentClass.TURN
                else None,
                disposition=Disposition(
                    decision=DispositionDecision.RETAINED, reason=DispositionReason.VALID_NON_PRIMARY
                ),
            )
        )
    for member in loaded.members:
        if member.name in {"[Content_Types].xml", "_rels/.rels", "document.xml"} or member.name.endswith("/"):
            continue
        path = f"archive:{member.name}"
        items.append(
            ContentInventoryItem(
                item_id=path,
                classification=ContentClass.ASSET,
                origin=SourceOrigin(
                    authorship=AuthorshipRole.AUTHORED, producer="isanlp_rst.doclang.archive.inventory/v1"
                ),
                representation=MediaReferenceRepresentation(media_identity=path),
                anchors=(
                    ItemAnchor(artifact_identity=artifact.source_id, item_identity=member.name),
                    ArchiveMemberAnchor(
                        artifact_identity=artifact.source_id,
                        member_path=member.name,
                        member_identity=Sha256Identity(hex_digest=member.sha256),
                    ),
                ),
                provider_attributes=(
                    ("sha256", member.sha256),
                    ("size_bytes", str(member.size_bytes)),
                    ("compressed_size_bytes", str(member.compressed_size_bytes)),
                ),
                disposition=Disposition(
                    decision=DispositionDecision.RETAINED, reason=DispositionReason.VALID_NON_PRIMARY
                ),
            )
        )
    return tuple(items), SourceContractIdentity(
        adapter="isanlp_rst.ingest.doclang",
        adapter_contract_version=SemanticVersion(root="2.0.0"),
        upstream_format="doclang",
        upstream_version=upstream_version(),
        schema_identity=Sha256Identity(hex_digest=implementation_digest()),
        assumptions=("allow_empty_namespace=true", "xsd=true", "schematron=true"),
    )
