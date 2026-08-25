"""``parse_docling`` entry point — load → harvest → boundaries → parse → flatten.

Two-level analysis (2026-06-12 directive, Option 2): the main document
harvest excludes table cells; each table gets its own RST mini-parse
whose relations land in ``DoclingRstResult.table_analyses``. Table
discourse therefore never distorts the document-level tree.

The underlying ``Parser`` is injectable so batch consumers construct it
once and reuse it across many ``parse_docling`` calls (otherwise each
call reloads the ~2 GB model from disk). An optional on-disk cache
(``cache_dir=``) short-circuits repeat parses of unchanged sources.
"""

from pathlib import Path
from typing import Any

from docling_core.types.doc.document import DoclingDocument

from .._version import DOCLING_SCHEMA_NAME as SCHEMA_NAME
from .._version import DOCLING_SCHEMA_VERSION as SCHEMA_VERSION
from .._version import TOOL_NAME
from .._rst_common import (
    dataclass_from_dict,
    load_cached,
    model_identity_knobs,
    resolve_inventory,
    resolve_result_model_meta,
    resolve_source_revision,
    resolve_tool_version,
    result_cache_key,
    RstParser,
    store_cached,
)
from ..utils.parse_result import extract_root_tree
from .boundaries import detect_boundaries
from .errors import EmptyDoclingError, EmptyHarvestError, InputTooLargeError
from .harvester import harvest_docling_tables, harvest_docling_text
from .mapper import flatten_tree
from ._mimetypes import ensure_docling_mimetypes
from .schema import DoclingRstResult, TableAnalysis

DEFAULT_MAX_HARVEST_CHARS = 200_000

# Backwards-compatible aliases — tests and external callers import these
# from the entry module; the implementations live in _rst_common.
_resolve_inventory = resolve_inventory
_resolve_tool_version = resolve_tool_version


def _serialise_source_origin(origin: Any) -> dict[str, Any]:
    """Serialise ``doc.origin`` (a Pydantic model) to a JSON-safe dict.

    Returns ``{}`` when origin is None.
    """
    if origin is None:
        return {}
    if hasattr(origin, "model_dump"):
        return origin.model_dump(mode="json")
    return {}


def parse_docling(
    path: str | Path,
    *,
    parser: RstParser | None = None,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",
    dtype: str | None = None,
    include_picture_descriptions: bool = True,
    include_slide_notes: bool = True,
    include_furniture: bool = False,
    include_table_cells: bool = True,
    harvest_separator: str = "\n\n",
    coalesce_speaker_turns: bool = True,
    note_threshold: float = 0.90,
    max_harvest_chars: int = DEFAULT_MAX_HARVEST_CHARS,
    cache_dir: str | Path | None = None,
) -> DoclingRstResult:
    """Parse a Docling JSON file and return its RST analysis.

    Args:
        path: filesystem path to a Docling JSON file.
        parser: a pre-constructed ``Parser`` to reuse. Batch consumers
            should construct once and inject — otherwise each call
            reloads the model from disk.
        hf_model_name, hf_model_version, relinventory: passed to a new
            ``Parser`` only when ``parser is None``.
        device: ``"auto" | "cpu" | "mps" | "cuda" | "cuda:N"``. ``"auto"``
            picks GPU when torch reports one, else CPU. Used only when
            constructing a new ``Parser``.
        dtype: ``"float32" | "bf16" | "fp16" | None`` — mixed-precision
            override passed to a new ``Parser``.
        include_picture_descriptions: harvest
            ``picture.meta.description.text`` when present.
        include_slide_notes: include ``ContentLayer.NOTES`` items.
        include_furniture: include ``ContentLayer.FURNITURE`` items.
        include_table_cells: run the per-table mini-parses (two-level
            analysis). When False, ``table_analyses`` is empty and table
            content is not analysed; the ``table-N`` boundaries are
            emitted either way.
        harvest_separator: inserted between harvested spans.
        coalesce_speaker_turns: VTT only — coalesce consecutive
            same-voice runs into one ``turn-K`` boundary.
        note_threshold: relations whose overlap is >= this ratio
            dominated by a single span get a ``note`` field.
        max_harvest_chars: raise ``InputTooLargeError`` above this size
            (checked for the main harvest and each table harvest).
        cache_dir: when set, results are cached on disk keyed by the
            source bytes + model identity + knobs; repeat calls return
            the cached result without loading the model.

    Raises:
        EmptyDoclingError: the document has no body content.
        EmptyHarvestError: neither the main harvest nor any table
            harvest produced text.
        InputTooLargeError: a harvest exceeds ``max_harvest_chars``.
    """
    src_path = Path(path)
    source_bytes = src_path.read_bytes()

    knobs: dict[str, object] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "dtype": dtype,
        "device": str(device),
        "include_picture_descriptions": include_picture_descriptions,
        "include_slide_notes": include_slide_notes,
        "include_furniture": include_furniture,
        "include_table_cells": include_table_cells,
        "harvest_separator": harvest_separator,
        "coalesce_speaker_turns": coalesce_speaker_turns,
        "note_threshold": note_threshold,
        "max_harvest_chars": max_harvest_chars,
        **model_identity_knobs(
            hf_model_name=hf_model_name,
            hf_model_version=hf_model_version,
            relinventory=relinventory,
            parser=parser,
        ),
    }
    cache_path = Path(cache_dir) if cache_dir is not None else None
    cache_key = result_cache_key(source_bytes, knobs, source_basename=src_path.name)
    if cache_path is not None:
        cached = load_cached(
            cache_path,
            cache_key,
            rebuild=lambda data: dataclass_from_dict(DoclingRstResult, data),
        )
        if isinstance(cached, DoclingRstResult):
            return cached

    ensure_docling_mimetypes()
    doc = DoclingDocument.load_from_json(src_path)

    body_children = getattr(getattr(doc, "body", None), "children", None) or ()
    if not body_children:
        raise EmptyDoclingError(f"DoclingDocument at {src_path} has an empty body — nothing to harvest.")

    harvest = harvest_docling_text(
        doc,
        include_picture_descriptions=include_picture_descriptions,
        include_slide_notes=include_slide_notes,
        include_furniture=include_furniture,
        harvest_separator=harvest_separator,
    )
    table_harvests = harvest_docling_tables(doc, harvest_separator=harvest_separator) if include_table_cells else ()

    if not harvest.full_text and not any(th.full_text for th in table_harvests):
        raise EmptyHarvestError(
            f"No text harvested from {src_path}. Document may have all content layers filtered out."
        )

    for label, text in (("main", harvest.full_text), *((th.marker_ref, th.full_text) for th in table_harvests)):
        if len(text) > max_harvest_chars:
            raise InputTooLargeError(
                f"Harvested text for {label} is {len(text)} chars, exceeds "
                f"max_harvest_chars={max_harvest_chars}. Chunk upstream or raise the limit."
            )

    boundaries = detect_boundaries(
        doc,
        coalesce_speaker_turns=coalesce_speaker_turns,
        include_slide_notes=include_slide_notes,
        include_furniture=include_furniture,
    )
    table_boundaries = {b.id: b for b in boundaries if b.kind == "table"}

    if parser is None:
        from isanlp_rst.parser import Parser  # lazy import — avoids loading on every import

        parser = Parser(
            hf_model_name=hf_model_name,
            hf_model_version=hf_model_version,
            relinventory=relinventory,
            device=device,
            dtype=dtype,
        )

    model_version, inventory = resolve_result_model_meta(
        parser, hf_model_version, relinventory, resolve_inventory=resolve_inventory
    )

    if harvest.full_text:
        tree = extract_root_tree(parser(harvest.full_text))
        relations, edus = flatten_tree(
            tree,
            harvest.spans,
            boundaries,
            source_text=harvest.full_text,
            note_threshold=note_threshold,
        )
    else:
        relations, edus = (), ()

    table_analyses: list[TableAnalysis] = []
    for th in table_harvests:
        if not th.full_text:
            continue
        boundary_id = f"table-{th.table_idx}"
        table_tree = extract_root_tree(parser(th.full_text))
        t_relations, t_edus = flatten_tree(
            table_tree,
            th.spans,
            (table_boundaries[boundary_id],),
            source_text=th.full_text,
            note_threshold=note_threshold,
        )
        table_analyses.append(TableAnalysis(id=boundary_id, relations=t_relations, edus=t_edus))

    result = DoclingRstResult(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        tool=TOOL_NAME,
        tool_version=resolve_tool_version(),
        source_revision=resolve_source_revision(),
        model_version=model_version,
        inventory=inventory,
        source=src_path.name,
        source_origin=_serialise_source_origin(getattr(doc, "origin", None)),
        boundaries=boundaries,
        relations=relations,
        edus=edus,
        table_analyses=tuple(table_analyses),
    )
    if cache_path is not None:
        store_cached(cache_path, cache_key, result)
    return result
