"""Private source-format harvesters retained behind the v2 inventory adapter."""

from importlib.metadata import version
from pathlib import Path
import re
import tempfile
from typing import Any

from isanlp_rst.ingest.contracts.legacy import (
    AnchorKind,
    AuthorshipRole,
    ContentClass,
    ContentInventoryItem,
    NativeAnchor,
    PreparedRange,
    RawContractDeclaration,
    SourceArtifact,
    SourceContractIdentity,
    SourceForm,
)
from isanlp_rst.ingest.identity import semantic_sha256, sha256_file


def inventory_source(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    """Validate current source contract and inventory every semantic item."""

    match artifact.source_form:
        case SourceForm.TEXT:
            return _inventory_text(artifact)
        case SourceForm.EDUS:
            return _inventory_edus(artifact)
        case SourceForm.MARKDOWN:
            return _inventory_markdown(artifact)
        case SourceForm.DOCLING_JSON:
            return _inventory_docling(artifact)
        case SourceForm.DOCLANG_XML:
            return _inventory_doclang(artifact)
        case SourceForm.DOCLANG_ARCHIVE:
            return _inventory_doclang_archive(artifact)


def _inventory_text(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    text = (artifact.raw_bytes or b"").decode("utf-8")
    items: tuple[ContentInventoryItem, ...]
    if text.strip():
        items = (
            ContentInventoryItem(
                item_id="text:document",
                parent_id=None,
                content_class=ContentClass.PARAGRAPH,
                authorship_role=AuthorshipRole.AUTHORED,
                text=text,
                native_anchors=(
                    NativeAnchor(
                        artifact_id=artifact.source_id,
                        item_id="text:document",
                        kind=AnchorKind.CHARACTER,
                        selector=f"char=0,{len(text)}",
                        range=PreparedRange(start=0, end=len(text)),
                        quote=text,
                    ),
                ),
                inventory_adapter="isanlp_rst.ingest.text/v1",
            ),
        )
    else:
        items = ()
    return items, _builtin_contract("plain_text", "isanlp_rst.ingest.text/v1")


def _inventory_edus(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    items = tuple(
        ContentInventoryItem(
            item_id=f"edu:{index}",
            parent_id=None,
            content_class=ContentClass.PARAGRAPH,
            authorship_role=AuthorshipRole.AUTHORED,
            text=text,
            native_anchors=(
                NativeAnchor(
                    artifact_id=artifact.source_id,
                    item_id=f"edu:{index}",
                    kind=AnchorKind.ITEM,
                    selector=f"edu={index}",
                    quote=text,
                ),
            ),
            inventory_adapter="isanlp_rst.ingest.edus/v1",
        )
        for index, text in enumerate(artifact.edus or ())
    )
    return items, _builtin_contract("presegmented_edus", "isanlp_rst.ingest.edus/v1")


def _inventory_markdown(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    from isanlp_rst.markdown.loader import load_markdown

    source = (artifact.raw_bytes or b"").decode("utf-8")
    loaded = load_markdown(source, gfm=True)
    line_starts = _line_starts(source)
    items: list[ContentInventoryItem] = []
    parent_stack: list[str | None] = []

    if loaded.front_matter is not None:
        items.append(
            _item(
                artifact,
                "markdown:front_matter",
                None,
                ContentClass.METADATA,
                loaded.front_matter,
                AnchorKind.LINE,
                "front_matter",
                adapter="isanlp_rst.markdown.inventory/v1",
            )
        )

    for index, token in enumerate(loaded.tokens):
        token_id = f"markdown:token:{index}"
        if token.nesting == -1:
            if parent_stack:
                parent_stack.pop()
            continue
        parent_id = next((item_id for item_id in reversed(parent_stack) if item_id is not None), None)
        content_class, text = _markdown_content(token, loaded.tokens, index)
        if content_class is not None:
            items.append(
                _item(
                    artifact,
                    token_id,
                    parent_id,
                    content_class,
                    text,
                    AnchorKind.LINE,
                    _markdown_selector(token, index),
                    attributes=_markdown_attributes(loaded.tokens, index),
                    additional_anchors=_markdown_character_anchors(
                        artifact,
                        token_id,
                        token,
                        source,
                        text,
                        line_starts,
                    ),
                    adapter="isanlp_rst.markdown.inventory/v1",
                )
            )
            if token.type == "html_block" and text:
                items.extend(_inventory_html_fragment(artifact, token_id, text, index))
        if token.nesting == 1:
            parent_stack.append(token_id if content_class is not None else None)

    return _reclassify_markdown(_with_children(tuple(items))), _distribution_contract(
        "markdown",
        "markdown-it-py",
        "isanlp_rst.markdown.inventory/v1",
    )


def _inventory_docling(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    from docling_core.types.doc import ContentLayer, DoclingDocument

    with tempfile.NamedTemporaryFile(suffix=".docling.json") as stream:
        stream.write(artifact.raw_bytes or b"")
        stream.flush()
        doc = DoclingDocument.load_from_json(stream.name)
    items: list[ContentInventoryItem] = []
    for node, _depth in doc.iterate_items(
        with_groups=True,
        traverse_pictures=True,
        included_content_layers=set(ContentLayer),
    ):
        item_id = str(node.self_ref)
        parent_ref = getattr(getattr(node, "parent", None), "cref", None)
        label = getattr(getattr(node, "label", None), "value", "other")
        layer = getattr(getattr(node, "content_layer", None), "value", "body")
        content_class = _docling_class(label, layer)
        text = getattr(node, "text", None)
        if _is_transcript(doc) and isinstance(text, str) and _is_speaker_turn(text):
            content_class = ContentClass.TURN
        items.append(
            _item(
                artifact,
                item_id,
                str(parent_ref) if parent_ref else None,
                content_class,
                text if isinstance(text, str) else None,
                AnchorKind.JSON_POINTER,
                item_id,
                layer=layer,
                authorship=AuthorshipRole.TRANSCRIBED if label == "text" and _is_transcript(doc) else AuthorshipRole.AUTHORED,
                additional_anchors=_docling_anchors(artifact, node),
                attributes=_docling_attributes(node, label=label, layer=layer),
                adapter="isanlp_rst.docling.inventory/v1",
            )
        )
        if label == "table":
            cells = getattr(getattr(node, "data", None), "table_cells", ())
            for cell_index, cell in enumerate(cells):
                cell_text = getattr(cell, "text", None)
                cell_id = f"{item_id}/data/table_cells/{cell_index}"
                items.append(
                    _item(
                        artifact,
                        cell_id,
                        item_id,
                        ContentClass.TABLE_CELL,
                        cell_text if isinstance(cell_text, str) else None,
                        AnchorKind.JSON_POINTER,
                        cell_id,
                        layer=layer,
                        attributes=(
                            ("row_span", str(getattr(cell, "row_span", 1))),
                            ("col_span", str(getattr(cell, "col_span", 1))),
                            ("column_header", str(bool(getattr(cell, "column_header", False))).lower()),
                            ("row_header", str(bool(getattr(cell, "row_header", False))).lower()),
                        ),
                        additional_anchors=_docling_cell_anchors(artifact, cell_id, cell),
                        adapter="isanlp_rst.docling.inventory/v1",
                    )
                )
        description = getattr(getattr(getattr(node, "meta", None), "description", None), "text", None)
        if isinstance(description, str) and description:
            description_id = f"{item_id}/meta/description/text"
            items.append(
                _item(
                    artifact,
                    description_id,
                    item_id,
                    ContentClass.PICTURE_DESCRIPTION,
                    description,
                    AnchorKind.JSON_POINTER,
                    description_id,
                    layer=layer,
                    authorship=AuthorshipRole.MACHINE_GENERATED,
                    adapter="isanlp_rst.docling.inventory/v1",
                )
            )
    raw = artifact.raw_contract
    accepted = RawContractDeclaration(schema_name="DoclingDocument", version=str(doc.version))
    contract = SourceContractIdentity(
        family="docling",
        raw_declared_schema=raw,
        accepted_schema=accepted,
        validator_distribution="docling-core",
        validator_version=version("docling-core"),
        validator_digest=_adapter_digest(Path(__file__)),
        validation_profile=(("all_content_layers", "true"), ("groups", "true"), ("pictures", "true")),
    )
    return _reclassify_back_matter(_with_children(tuple(items))), contract


def _inventory_doclang(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    return _inventory_doclang_data(artifact, artifact.raw_bytes or b"", archive_members=())


def _inventory_doclang_archive(
    artifact: SourceArtifact,
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    from isanlp_rst.doclang.loader import load_doclang_archive

    archive = load_doclang_archive(artifact.raw_bytes or b"")
    return _inventory_doclang_data(artifact, archive.document_bytes, archive_members=archive.members)


def _inventory_doclang_data(
    artifact: SourceArtifact,
    data: bytes,
    *,
    archive_members: tuple[Any, ...],
) -> tuple[tuple[ContentInventoryItem, ...], SourceContractIdentity]:
    from doclang import ValidationError as DoclangValidationError
    from doclang import validate
    from lxml import etree
    from isanlp_rst.doclang.errors import InvalidDoclangError
    from isanlp_rst.doclang.loader import local_path

    try:
        with tempfile.NamedTemporaryFile(suffix=".dclg") as stream:
            stream.write(data)
            stream.flush()
            validate(stream.name, allow_empty_namespace=True)
        parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, recover=False, huge_tree=False)
        root = etree.fromstring(data, parser=parser)
    except (DoclangValidationError, etree.XMLSyntaxError) as exc:
        raise InvalidDoclangError(
            f"DocLang XML failed current validation ({type(exc).__name__})"
        ) from exc
    items: list[ContentInventoryItem] = []
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        item_id = local_path(element)
        parent = element.getparent()
        parent_id = local_path(parent) if parent is not None else None
        tag = etree.QName(element).localname
        content_class = _doclang_class(tag)
        ancestor_names = _doclang_ancestor_names(element)
        if "table" in ancestor_names and tag != "table":
            content_class = ContentClass.TABLE_CELL
        elif "picture" in ancestor_names and content_class is ContentClass.PARAGRAPH:
            content_class = ContentClass.PICTURE_DESCRIPTION
        elif "field_region" in ancestor_names or "field_item" in ancestor_names:
            content_class = ContentClass.FIELD
        text = _doclang_text(element, tag)
        if content_class is ContentClass.PARAGRAPH and isinstance(text, str) and _is_speaker_turn(text):
            content_class = ContentClass.TURN
        layer = _doclang_layer(element)
        items.append(
            _item(
                artifact,
                item_id,
                parent_id,
                content_class,
                text,
                AnchorKind.XML_PATH,
                item_id,
                layer=layer,
                attributes=tuple(sorted((str(key), str(value)) for key, value in element.attrib.items())),
                additional_anchors=_doclang_anchors(artifact, element, item_id, tag),
                adapter="isanlp_rst.doclang.inventory/v1",
            )
        )
    for member in archive_members:
        if member.name in {"[Content_Types].xml", "_rels/.rels", "document.xml"} or member.name.endswith("/"):
            continue
        items.append(
            _item(
                artifact,
                f"archive:{member.name}",
                None,
                ContentClass.ASSET,
                None,
                AnchorKind.ITEM,
                member.name,
                attributes=(
                    ("sha256", member.sha256),
                    ("size_bytes", str(member.size_bytes)),
                    ("compressed_size_bytes", str(member.compressed_size_bytes)),
                ),
                adapter="isanlp_rst.doclang.archive.inventory/v1",
            )
        )
    contract = SourceContractIdentity(
        family="doclang",
        raw_declared_schema=artifact.raw_contract,
        accepted_schema=RawContractDeclaration(namespace=etree.QName(root).namespace),
        validator_distribution="doclang",
        validator_version=version("doclang"),
        validator_digest=_adapter_digest(Path(__file__), Path(__file__).parents[1] / "doclang/loader.py"),
        validation_profile=(("allow_empty_namespace", "true"), ("xsd", "true"), ("schematron", "true")),
    )
    return _reclassify_back_matter(_with_children(tuple(items))), contract


def _item(
    artifact: SourceArtifact,
    item_id: str,
    parent_id: str | None,
    content_class: ContentClass,
    text: str | None,
    anchor_kind: AnchorKind,
    selector: str,
    *,
    layer: str | None = None,
    authorship: AuthorshipRole = AuthorshipRole.AUTHORED,
    attributes: tuple[tuple[str, str], ...] = (),
    additional_anchors: tuple[NativeAnchor, ...] = (),
    adapter: str,
) -> ContentInventoryItem:
    anchor = NativeAnchor(
        artifact_id=artifact.source_id,
        item_id=item_id,
        kind=anchor_kind,
        selector=selector,
        quote=text if text else None,
    )
    return ContentInventoryItem(
        item_id=item_id,
        parent_id=parent_id,
        content_class=content_class,
        authorship_role=authorship,
        content_layer=layer,
        text=text,
        native_anchors=(anchor, *additional_anchors),
        attributes=attributes,
        inventory_adapter=adapter,
    )


def _docling_anchors(artifact: SourceArtifact, node: Any) -> tuple[NativeAnchor, ...]:
    anchors: list[NativeAnchor] = []
    for index, provenance in enumerate(getattr(node, "prov", ())):
        page_no = getattr(provenance, "page_no", None)
        if isinstance(page_no, int):
            anchors.append(
                NativeAnchor(
                    artifact_id=artifact.source_id,
                    item_id=str(node.self_ref),
                    kind=AnchorKind.PAGE,
                    selector=f"page={page_no};provenance={index}",
                )
            )
        bbox = getattr(provenance, "bbox", None)
        if bbox is not None:
            origin = getattr(getattr(bbox, "coord_origin", None), "value", "unknown")
            anchors.append(
                NativeAnchor(
                    artifact_id=artifact.source_id,
                    item_id=str(node.self_ref),
                    kind=AnchorKind.BOUNDING_BOX,
                    selector=(
                        f"page={page_no};l={bbox.l:.12g};t={bbox.t:.12g};"
                        f"r={bbox.r:.12g};b={bbox.b:.12g};origin={origin}"
                    ),
                )
            )
        charspan = getattr(provenance, "charspan", None)
        if (
            isinstance(charspan, tuple)
            and len(charspan) == 2
            and isinstance(charspan[0], int)
            and isinstance(charspan[1], int)
            and charspan[1] > charspan[0]
        ):
            anchors.append(
                NativeAnchor(
                    artifact_id=artifact.source_id,
                    item_id=str(node.self_ref),
                    kind=AnchorKind.CHARACTER,
                    selector=f"item_char={charspan[0]},{charspan[1]}",
                    range=PreparedRange(start=charspan[0], end=charspan[1]),
                )
            )
    return tuple(anchors)


def _docling_attributes(node: Any, *, label: str, layer: str) -> tuple[tuple[str, str], ...]:
    attributes: list[tuple[str, str]] = [("content_layer", layer), ("label", label)]
    hyperlink = getattr(node, "hyperlink", None)
    if hyperlink is not None:
        attributes.append(("href", str(hyperlink)))
    formatting = getattr(node, "formatting", None)
    if formatting is not None:
        model_dump_json = getattr(formatting, "model_dump_json", None)
        attributes.append(
            (
                "text_formatting",
                str(model_dump_json()) if callable(model_dump_json) else str(formatting),
            )
        )
    for relationship_name in ("captions", "references", "footnotes"):
        for index, reference in enumerate(getattr(node, relationship_name, ())):
            target = getattr(reference, "cref", None)
            if target is not None:
                attributes.append(
                    (f"relationship:{relationship_name}:{index}", str(target))
                )
    for index, comment in enumerate(getattr(node, "comments", ())):
        model_dump_json = getattr(comment, "model_dump_json", None)
        attributes.append(
            (
                f"comment:{index}",
                str(model_dump_json()) if callable(model_dump_json) else str(comment),
            )
        )
    classification = getattr(getattr(node, "meta", None), "classification", None)
    predictions = getattr(classification, "predictions", ())
    if predictions:
        prediction = predictions[0]
        class_name = getattr(prediction, "class_name", None)
        confidence = getattr(prediction, "confidence", None)
        created_by = getattr(prediction, "created_by", None)
        if isinstance(class_name, str) and class_name:
            attributes.append(("picture_class", class_name))
        if isinstance(confidence, int | float):
            attributes.append(("picture_class_confidence", f"{float(confidence):.12g}"))
        if isinstance(created_by, str) and created_by:
            attributes.append(("picture_class_created_by", created_by))
    return tuple(sorted(attributes))


def _docling_cell_anchors(artifact: SourceArtifact, cell_id: str, cell: Any) -> tuple[NativeAnchor, ...]:
    row_start = getattr(cell, "start_row_offset_idx", None)
    row_end = getattr(cell, "end_row_offset_idx", None)
    column_start = getattr(cell, "start_col_offset_idx", None)
    column_end = getattr(cell, "end_col_offset_idx", None)
    anchors = [
        NativeAnchor(
            artifact_id=artifact.source_id,
            item_id=cell_id,
            kind=AnchorKind.TABLE_COORDINATE,
            selector=f"row={row_start},{row_end};column={column_start},{column_end}",
        )
    ]
    bbox = getattr(cell, "bbox", None)
    if bbox is not None:
        origin = getattr(getattr(bbox, "coord_origin", None), "value", "unknown")
        anchors.append(
            NativeAnchor(
                artifact_id=artifact.source_id,
                item_id=cell_id,
                kind=AnchorKind.BOUNDING_BOX,
                selector=(
                    f"l={bbox.l:.12g};t={bbox.t:.12g};r={bbox.r:.12g};"
                    f"b={bbox.b:.12g};origin={origin}"
                ),
            )
        )
    return tuple(anchors)


def _with_children(items: tuple[ContentInventoryItem, ...]) -> tuple[ContentInventoryItem, ...]:
    ids = {item.item_id for item in items}
    children: dict[str, list[str]] = {item_id: [] for item_id in ids}
    for item in items:
        if item.parent_id in ids:
            children[item.parent_id].append(item.item_id)
    return tuple(item.model_copy(update={"child_ids": tuple(children[item.item_id])}) for item in items)


def _reclassify_markdown(items: tuple[ContentInventoryItem, ...]) -> tuple[ContentInventoryItem, ...]:
    revised = list(items)
    presentation_analysis_next = False
    for index, item in enumerate(revised):
        text = (item.text or "").strip()
        normalized = " ".join(text.upper().split())
        if item.content_class is ContentClass.HEADING and (
            normalized.endswith("VISUAL DESCRIPTION")
            or normalized.endswith("CONCEPTUAL ANALYSIS & METAPHOR")
        ):
            revised[index] = item.model_copy(update={"content_class": ContentClass.NAVIGATION})
            presentation_analysis_next = True
            continue
        if presentation_analysis_next and item.content_class is ContentClass.PARAGRAPH:
            revised[index] = item.model_copy(update={"content_class": ContentClass.NAVIGATION})
            presentation_analysis_next = False
            continue
        if item.content_class is ContentClass.PARAGRAPH and _is_image_only_markdown(text):
            revised[index] = item.model_copy(update={"content_class": ContentClass.PICTURE})
    return _reclassify_back_matter(tuple(revised))


def _reclassify_back_matter(items: tuple[ContentInventoryItem, ...]) -> tuple[ContentInventoryItem, ...]:
    revised = list(items)
    abstract_index = next(
        (
            index
            for index, item in enumerate(revised)
            if item.content_class is ContentClass.HEADING and (item.text or "").strip().casefold() == "abstract"
        ),
        None,
    )
    if abstract_index is not None:
        first_heading = next(
            (index for index, item in enumerate(revised[:abstract_index]) if item.content_class in {ContentClass.TITLE, ContentClass.HEADING}),
            None,
        )
        if first_heading is not None:
            for index in range(first_heading + 1, abstract_index):
                if revised[index].content_class in {ContentClass.PARAGRAPH, ContentClass.LIST_ITEM}:
                    revised[index] = revised[index].model_copy(update={"content_class": ContentClass.METADATA})
    back_matter = False
    for index, item in enumerate(revised):
        if item.content_class in {ContentClass.TITLE, ContentClass.HEADING}:
            heading = " ".join((item.text or "").casefold().split()).rstrip(":")
            if heading in {"references", "bibliography", "works cited"}:
                back_matter = True
        if back_matter and item.content_class in {
            ContentClass.TITLE,
            ContentClass.HEADING,
            ContentClass.PARAGRAPH,
            ContentClass.LIST_ITEM,
        }:
            revised[index] = item.model_copy(update={"content_class": ContentClass.NAVIGATION})
    return tuple(revised)


def _is_image_only_markdown(text: str) -> bool:
    return re.fullmatch(r"!\[[^\]]*\]\([^\n)]+\)", text) is not None


def _verify_inventory(items: tuple[ContentInventoryItem, ...]) -> None:
    ids = [item.item_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("complete inventory contains duplicate item IDs")
    known = set(ids)
    for item in items:
        if item.parent_id is not None and item.parent_id not in known:
            raise ValueError(f"inventory item {item.item_id} has unknown parent: {item.parent_id}")
        unknown_children = set(item.child_ids) - known
        if unknown_children:
            raise ValueError(f"inventory item {item.item_id} has unknown children: {sorted(unknown_children)}")


def _builtin_contract(family: str, adapter: str) -> SourceContractIdentity:
    return SourceContractIdentity(
        family=family,
        validator_distribution="isanlp-rst",
        validator_version=version("isanlp-rst"),
        validator_digest=semantic_sha256({"adapter": adapter, "file": _adapter_digest(Path(__file__))}),
    )


def _distribution_contract(family: str, distribution: str, adapter: str) -> SourceContractIdentity:
    return SourceContractIdentity(
        family=family,
        validator_distribution=distribution,
        validator_version=version(distribution),
        validator_digest=semantic_sha256(
            {
                "adapter": adapter,
                "files": (
                    sha256_file(Path(__file__)),
                    sha256_file(Path(__file__).parents[1] / "markdown/loader.py"),
                ),
            }
        ),
    )


def _adapter_digest(*paths: Path) -> str:
    return semantic_sha256(tuple((path.name, sha256_file(path)) for path in paths))


def _markdown_content(token: Any, tokens: tuple[Any, ...], index: int) -> tuple[ContentClass | None, str | None]:
    kind = token.type
    if kind == "heading_open":
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        return ContentClass.HEADING, getattr(inline, "content", None)
    if kind == "paragraph_open":
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        return ContentClass.PARAGRAPH, getattr(inline, "content", None)
    if kind == "list_item_open":
        return ContentClass.LIST_ITEM, None
    if kind in {"bullet_list_open", "ordered_list_open", "blockquote_open"}:
        return ContentClass.GROUP, None
    if kind == "table_open":
        return ContentClass.TABLE, None
    if kind in {"th_open", "td_open"}:
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        return ContentClass.TABLE_CELL, getattr(inline, "content", None)
    if kind in {"fence", "code_block"}:
        return ContentClass.CODE, token.content.rstrip("\n")
    if kind == "html_block":
        return ContentClass.RAW_MARKUP, token.content
    if kind == "hr":
        return ContentClass.METADATA, None
    return None, None


def _markdown_selector(token: Any, index: int) -> str:
    if token.map is None:
        return f"token={index}"
    return f"line={token.map[0]},{token.map[1]}"


def _markdown_attributes(tokens: tuple[Any, ...], index: int) -> tuple[tuple[str, str], ...]:
    inline = tokens[index + 1] if index + 1 < len(tokens) else None
    children = getattr(inline, "children", ()) or ()
    attributes: list[tuple[str, str]] = []
    for child_index, child in enumerate(children):
        if child.type not in {"link_open", "image"}:
            continue
        target = child.attrGet("href") if child.type == "link_open" else child.attrGet("src")
        if target:
            relation = "link" if child.type == "link_open" else "image"
            attributes.append((f"relationship:{relation}:{child_index}", target))
    return tuple(attributes)


def _line_starts(source: str) -> tuple[int, ...]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer("\n", source))
    return tuple(starts)


def _markdown_character_anchors(
    artifact: SourceArtifact,
    item_id: str,
    token: Any,
    source: str,
    text: str | None,
    line_starts: tuple[int, ...],
) -> tuple[NativeAnchor, ...]:
    if token.map is None or text is None:
        return ()
    start_line, end_line = token.map
    block_start = line_starts[start_line]
    block_end = line_starts[end_line] if end_line < len(line_starts) else len(source)
    relative = source[block_start:block_end].find(text)
    if relative < 0:
        return ()
    start = block_start + relative
    end = start + len(text)
    return (
        NativeAnchor(
            artifact_id=artifact.source_id,
            item_id=item_id,
            kind=AnchorKind.CHARACTER,
            selector=f"char={start},{end}",
            range=PreparedRange(start=start, end=end),
            quote=text,
        ),
    )


def _inventory_html_fragment(
    artifact: SourceArtifact,
    token_id: str,
    source: str,
    token_index: int,
) -> tuple[ContentInventoryItem, ...]:
    from lxml import etree, html

    parser = html.HTMLParser(no_network=True, recover=True)
    wrapper = html.fragment_fromstring(source, create_parent="div", parser=parser)
    tree = wrapper.getroottree()
    items: list[ContentInventoryItem] = []
    element_ids: dict[Any, str] = {wrapper: token_id}
    blocked = {"script", "style", "nav", "template", "noscript", "head", "meta", "link"}
    authored = {
        "p": ContentClass.PARAGRAPH,
        "h1": ContentClass.HEADING,
        "h2": ContentClass.HEADING,
        "h3": ContentClass.HEADING,
        "h4": ContentClass.HEADING,
        "h5": ContentClass.HEADING,
        "h6": ContentClass.HEADING,
        "li": ContentClass.LIST_ITEM,
        "blockquote": ContentClass.PARAGRAPH,
        "figcaption": ContentClass.CAPTION,
    }
    for element in wrapper.iterdescendants():
        if not isinstance(element.tag, str):
            continue
        path = tree.getpath(element)
        element_id = f"{token_id}:html:{path}"
        parent = element.getparent()
        parent_id = element_ids.get(parent, token_id)
        element_ids[element] = element_id
        tag = etree.QName(element).localname.lower()
        element_text = "".join(_safe_html_text(element, blocked)).strip()
        content_class = authored.get(tag, ContentClass.NAVIGATION if tag in blocked else ContentClass.RAW_MARKUP)
        items.append(
            _item(
                artifact,
                element_id,
                parent_id,
                content_class,
                element_text or None,
                AnchorKind.XML_PATH,
                f"token={token_index};dom={path}",
                authorship=AuthorshipRole.AUTHORED if tag in authored else AuthorshipRole.UNKNOWN,
                adapter="isanlp_rst.markdown.html.inventory/v1",
            )
        )
    return tuple(items)


def _safe_html_text(element: Any, blocked: set[str]) -> tuple[str, ...]:
    from lxml import etree

    pieces: list[str] = []
    if element.text:
        pieces.append(element.text)
    for child in element:
        if isinstance(child.tag, str) and etree.QName(child).localname.lower() not in blocked:
            pieces.extend(_safe_html_text(child, blocked))
        if child.tail:
            pieces.append(child.tail)
    return tuple(pieces)


def _docling_class(label: str, layer: str) -> ContentClass:
    if layer == "notes":
        return ContentClass.NOTE
    if layer == "furniture":
        return ContentClass.FURNITURE
    if layer == "background":
        return ContentClass.BACKGROUND
    if layer == "invisible":
        return ContentClass.INVISIBLE
    return {
        "title": ContentClass.TITLE,
        "chapter": ContentClass.HEADING,
        "section_header": ContentClass.HEADING,
        "paragraph": ContentClass.PARAGRAPH,
        "text": ContentClass.PARAGRAPH,
        "list": ContentClass.GROUP,
        "list_item": ContentClass.LIST_ITEM,
        "table": ContentClass.TABLE,
        "picture": ContentClass.PICTURE,
        "caption": ContentClass.CAPTION,
        "formula": ContentClass.FORMULA,
        "code": ContentClass.CODE,
        "page_header": ContentClass.FURNITURE,
        "page_footer": ContentClass.FURNITURE,
    }.get(label, ContentClass.GROUP if label in {"unspecified", "section", "inline"} else ContentClass.OTHER)


def _is_transcript(doc: Any) -> bool:
    origin = getattr(doc, "origin", None)
    return getattr(origin, "mimetype", None) in {"text/vtt", "audio/mpeg", "video/mp4"}


def _is_speaker_turn(text: str) -> bool:
    return re.match(r"^\s*(?:SPEAKER[_ -]?\d+|[A-Z][A-Z0-9 _-]{1,40}):\s+", text) is not None


def _doclang_class(tag: str) -> ContentClass:
    return {
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
    }.get(tag, ContentClass.METADATA if tag in {"label", "thread", "layer", "location"} else ContentClass.OTHER)


def _doclang_text(element: Any, tag: str) -> str | None:
    from isanlp_rst.doclang.loader import local_name
    from isanlp_rst.doclang.text_walker import body_text

    if tag in {"text", "heading", "footnote", "code", "formula", "caption", "description", "key", "value"}:
        text = body_text(element)
        return text or None
    if tag == "ldiv":
        tail = element.tail or ""
        return tail.strip() or None
    if tag in {"ched", "rhed", "corn", "fcel"}:
        pieces = [element.tail or ""]
        for sibling in element.itersiblings():
            if isinstance(sibling.tag, str) and local_name(sibling) in {"ched", "rhed", "corn", "fcel", "ecel", "lcel", "ucel", "xcel", "nl"}:
                break
            pieces.append("".join(sibling.itertext()))
            if sibling.tail:
                pieces.append(sibling.tail)
        text = "".join(pieces).strip()
        return text or None
    return None


def _doclang_layer(element: Any) -> str:
    from isanlp_rst.doclang.loader import local_name

    for child in element:
        if isinstance(child.tag, str) and local_name(child) == "layer":
            value = child.get("value")
            if value:
                return value
    return "body"


_DOCLANG_CELL_TOKENS = frozenset({"ched", "rhed", "corn", "fcel", "ecel", "lcel", "ucel", "xcel"})


def _doclang_anchors(
    artifact: SourceArtifact,
    element: Any,
    item_id: str,
    tag: str,
) -> tuple[NativeAnchor, ...]:
    from isanlp_rst.doclang.loader import local_name

    anchors: list[NativeAnchor] = []
    locations = [
        child
        for child in element
        if isinstance(child.tag, str) and local_name(child) == "location"
    ]
    if len(locations) == 4:
        coordinates = ";".join(
            f"{axis}={location.get('value')};{axis}_resolution={location.get('resolution') or 'default'}"
            for axis, location in zip(("x0", "y0", "x1", "y1"), locations, strict=True)
        )
        anchors.append(
            NativeAnchor(
                artifact_id=artifact.source_id,
                item_id=item_id,
                kind=AnchorKind.BOUNDING_BOX,
                selector=coordinates,
            )
        )
    if tag in _DOCLANG_CELL_TOKENS:
        parent = element.getparent()
        if parent is not None and local_name(parent) in {"table", "index", "tabular"}:
            row = 0
            column = 0
            for sibling in parent:
                if sibling is element:
                    break
                if not isinstance(sibling.tag, str):
                    continue
                sibling_name = local_name(sibling)
                if sibling_name == "nl":
                    row += 1
                    column = 0
                elif sibling_name in _DOCLANG_CELL_TOKENS:
                    column += 1
            anchors.append(
                NativeAnchor(
                    artifact_id=artifact.source_id,
                    item_id=item_id,
                    kind=AnchorKind.TABLE_COORDINATE,
                    selector=f"row={row};column={column};token={tag}",
                )
            )
    return tuple(anchors)


def _doclang_ancestor_names(element: Any) -> frozenset[str]:
    from isanlp_rst.doclang.loader import local_name

    names: set[str] = set()
    parent = element.getparent()
    while parent is not None:
        if isinstance(parent.tag, str):
            names.add(local_name(parent))
        parent = parent.getparent()
    return frozenset(names)


def _structure_path(item: ContentInventoryItem, inventory: tuple[ContentInventoryItem, ...]) -> tuple[str, ...]:
    by_id = {candidate.item_id: candidate for candidate in inventory}
    path = [item.item_id]
    current = item
    while current.parent_id is not None and current.parent_id in by_id:
        current = by_id[current.parent_id]
        path.append(current.item_id)
    return tuple(reversed(path))


__all__ = ["inventory_source"]
