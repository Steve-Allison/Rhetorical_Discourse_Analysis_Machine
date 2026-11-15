"""Direct DocLang mapping into the current immutable ingestion contract via native dclq."""

from importlib.metadata import distribution
import json
from pathlib import Path
import warnings

from dclq.document import LoadedDocument

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
    PageAnchor,
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
from rdam.ingest.doclang import decoder, document, loader, text_walker
from rdam.ingest.doclang.decoder import DecodedDoclangItem, decode_document, item_index
from rdam.ingest.doclang.document import DoclangDocument
from rdam.ingest.doclang.loader import to_dclq_xpath
from rdam.ingest.identity import semantic_sha256, sha256_file
from rdam.ingest.speakers import explicitly_marked_turn, resolve_speaker, resolve_voice

_TABLE_CONTAINERS = frozenset({"table", "tabular", "index"})
_ELEMENT_HEAD_TAGS = frozenset(
    {"caption", "description", "summary", "location", "layer", "thread", "href", "label", "custom", "xref"}
)
_DECORATIVE_PICTURE_LABELS = frozenset(
    {"logo", "icon", "qr_code", "barcode", "stamp", "signature", "decorative"}
)


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


def _decorative_picture_paths(decoded: tuple[DecodedDoclangItem, ...]) -> frozenset[str]:
    by_path = item_index(decoded)
    decorative: set[str] = set()
    for item in decoded:
        if item.tag != "picture":
            continue
        for child_path in item.child_paths:
            child = by_path.get(child_path)
            if child is None or child.tag != "label":
                continue
            label_value = dict(child.attributes).get("value", "").strip().casefold()
            if label_value in _DECORATIVE_PICTURE_LABELS:
                decorative.add(item.path)
                break
    return frozenset(decorative)


def _inside_any(path: str, roots: frozenset[str]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def _classification_for(item: DecodedDoclangItem, decorative_pictures: frozenset[str]) -> ContentClass:
    if item.tag in {"head", "custom"} or {"head", "custom"} & item.ancestors:
        return ContentClass.METADATA
    if item.tag in {"page_header", "page_footer"} or {"page_header", "page_footer"} & item.ancestors:
        return ContentClass.FURNITURE
    if item.layer == "furniture":
        return ContentClass.FURNITURE
    if item.layer == "background":
        return ContentClass.BACKGROUND
    if item.layer == "invisible":
        return ContentClass.INVISIBLE
    if _inside_any(item.path, decorative_pictures) and item.tag != "picture":
        return ContentClass.FURNITURE

    classification = {
        "head": ContentClass.METADATA,
        "summary": ContentClass.METADATA,
        "title": ContentClass.TITLE,
        "heading": ContentClass.HEADING,
        "text": ContentClass.PARAGRAPH,
        "footnote": ContentClass.PARAGRAPH,
        "list": ContentClass.GROUP,
        "ldiv": ContentClass.LIST_ITEM,
        "table": ContentClass.TABLE,
        "tabular": ContentClass.TABLE,
        "index": ContentClass.TABLE,
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
        "field_region": ContentClass.FIELD,
        "field_heading": ContentClass.FIELD,
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
    if (_TABLE_CONTAINERS & item.ancestors) and item.tag not in (_TABLE_CONTAINERS | _ELEMENT_HEAD_TAGS):
        return ContentClass.TABLE_CELL
    if "picture" in item.ancestors and classification is ContentClass.PARAGRAPH:
        return ContentClass.PICTURE_DESCRIPTION
    if {"field_region", "field_item"} & item.ancestors and item.tag not in _ELEMENT_HEAD_TAGS:
        return ContentClass.FIELD
    if item.layer == "notes" and classification is ContentClass.PARAGRAPH:
        return ContentClass.NOTE
    if (
        classification is ContentClass.PARAGRAPH
        and item.text is not None
        and explicitly_marked_turn(item.text)
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
            ordered=attributes.get("class") == "ordered",
            items=tuple(
                ListItemRepresentation(item_id=child.path, text=child.text, child_item_ids=child.child_paths)
                for child in children
                if child.tag == "ldiv"
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


def _anchors(item: DecodedDoclangItem, artifact: SourceArtifact, *, page_no: int | None) -> tuple[SourceAnchor, ...]:
    anchors: list[SourceAnchor] = [
        SourcePathAnchor(artifact_identity=artifact.source_id, path_kind="xml_path", path=item.path)
    ]
    if page_no is not None and page_no >= 1 and item.parent_path is not None:
        anchors.append(PageAnchor(artifact_identity=artifact.source_id, page=page_no))
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


def _load_dclq_document(xml_bytes: bytes) -> LoadedDocument:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r".*<track> is not supported yet.*", category=UserWarning)
        warnings.filterwarnings("ignore", message=r".*No DocLang version declared.*", category=UserWarning)
        return LoadedDocument.load("-", stdin_bytes=xml_bytes, validate=False)


def _merge_unique_attributes(
    *groups: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    merged: dict[str, str] = {}
    for group in groups:
        for key, value in group:
            if key not in merged:
                merged[key] = value
    return tuple(merged.items())


def inventory_doclang(artifact: SourceArtifact) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    loaded = DoclangDocument.load(artifact.raw_bytes or b"", archive=artifact.source_form is SourceForm.DOCLANG_ARCHIVE)
    dclq_doc = _load_dclq_document(loaded.xml_bytes)
    unit_by_xpath = {unit.xpath: unit for unit in dclq_doc.units}
    xpath_by_ref = {unit.item_ref: unit.xpath for unit in dclq_doc.units if unit.item_ref is not None}

    decoded = decode_document(loaded)
    by_path = item_index(decoded)
    decorative_pictures = _decorative_picture_paths(decoded)
    classes = _classification.back_matter_classes(
        tuple((_classification_for(item, decorative_pictures), item.text) for item in decoded)
    )
    items: list[ContentInventoryItem] = []
    for item, classification in zip(decoded, classes, strict=True):
        dclq_xpath = to_dclq_xpath(item.path)
        page_no = dclq_doc.source_pages.get(dclq_xpath)
        unit = unit_by_xpath.get(dclq_xpath)
        dclq_extra: list[tuple[str, str]] = [("dclq_xpath", dclq_xpath)]
        if unit is not None:
            dclq_extra.append(("dclq_logical_type", unit.logical_type))
            heading_ref = dclq_doc.nearest_heading_ref(unit)
            if heading_ref is not None and heading_ref in xpath_by_ref:
                dclq_extra.append(("dclq_section_heading_xpath", xpath_by_ref[heading_ref]))
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
                anchors=_anchors(item, artifact, page_no=page_no),
                parent_id=item.parent_path,
                child_ids=item.child_paths,
                relationships=relationships,
                provider_attributes=_merge_unique_attributes(item.attributes, cue_attributes, tuple(dclq_extra)),
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
        assumptions=("allow_empty_namespace=true", "dclq=true", "xsd=true", "schematron=true"),
    )
