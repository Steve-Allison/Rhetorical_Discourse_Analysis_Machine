"""``parse_doclang`` entry point — load → harvest → boundaries → parse → flatten.

Two-level analysis (2026-06-12 directive, Option 2): the main document
harvest excludes table cells; each ``<table>`` gets its own RST
mini-parse whose relations land in ``DoclangRstResult.table_analyses``.

XML validation is delegated to the ``doclang`` PyPI package (validator-
only — see [[verified-doclang-spec]]). When ``validate_xml=True``
(default), the file is run through ``doclang.validate(path)`` before
parsing. If the package is not importable, validation fails closed with
``InvalidDoclangError`` (pass ``validate_xml=False`` to skip).

The underlying ``Parser`` is injectable so batch consumers construct it
once and reuse it across many ``parse_doclang`` calls. An optional
on-disk cache (``cache_dir=``) short-circuits repeat parses.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .._rst_common import (
    load_cached,
    model_identity_knobs,
    resolve_inventory,
    resolve_result_model_meta,
    resolve_tool_version,
    result_cache_key,
    store_cached,
)
from .boundaries import detect_boundaries
from .errors import (
    EmptyDoclangError,
    EmptyHarvestError,
    InputTooLargeError,
    InvalidDoclangError,
)
from .harvester import harvest_doclang_tables, harvest_doclang_text
from .loader import local_name, parse_doclang_xml
from .mapper import flatten_tree
from .schema import DoclangRstResult, TableAnalysis

if TYPE_CHECKING:
    from isanlp_rst.parser import Parser

SCHEMA_NAME = "isanlp_rst_doclang"
SCHEMA_VERSION = "1.0"
TOOL_NAME = "isanlp_rst"
DEFAULT_MAX_HARVEST_CHARS = 200_000

# DocLang XML namespace per spec.md:219-241 (default xmlns when declared).
DOCLANG_NS = "https://www.doclang.ai/ns/v0"

# Backwards-compatible aliases — tests and external callers import these
# from the entry module; the implementations live in _rst_common.
_resolve_inventory = resolve_inventory
_resolve_tool_version = resolve_tool_version


def _validate_xml(path: Path) -> None:
    """Validate ``path`` against the DocLang schema via the ``doclang`` package.

    When the package is not importable in the active env, raises
    ``InvalidDoclangError`` (fail-closed). When the package IS importable
    and validation fails, raises ``InvalidDoclangError`` wrapping the
    original error. Callers that cannot install ``doclang`` should pass
    ``validate_xml=False``.

    Current DocLang requires the ``DOCLANG_NS`` namespace, so a
    non-namespaced document fails here even though the loader / harvester
    can still read it — pass ``validate_xml=False`` to ``parse_doclang``
    to parse non-conforming input best-effort.
    """
    try:
        doclang_pkg = importlib.import_module("doclang")
    except ImportError as exc:
        raise InvalidDoclangError(
            f"{path}: validate_xml=True requires the doclang package. "
            "Install doclang or pass validate_xml=False."
        ) from exc
    try:
        doclang_pkg.validate(path)
    except Exception as exc:
        raise InvalidDoclangError(
            f"{path}: failed DocLang validation via the doclang package: {exc}. "
            f"Current DocLang requires the {DOCLANG_NS} namespace; pass "
            f"validate_xml=False to parse non-conforming input best-effort."
        ) from exc


def _source_origin(tree: Any) -> dict[str, Any]:
    """Capture lightweight provenance from the parsed tree.

    Reports: declared namespace (or ``""``), version attribute (or ``""``
    when the document declares none), and any first-level ``<head>`` child names.
    """
    root = tree.getroot()
    ns = ""
    if isinstance(root.tag, str) and root.tag.startswith("{"):
        ns = root.tag.split("}", 1)[0][1:]
    version_attr = root.get("version", "")
    head_children: list[str] = []
    for child in root:
        if isinstance(child.tag, str) and local_name(child) == "head":
            head_children = [
                local_name(c) for c in child if isinstance(c.tag, str)
            ]
            break
    return {
        "format": "doclang",
        "namespace": ns,
        "version": version_attr,
        "head_children": head_children,
    }


def parse_doclang(
    path: str | Path,
    *,
    parser: "Parser | None" = None,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",
    dtype: str | None = None,
    include_picture_captions: bool = True,
    include_background: bool = False,
    include_furniture: bool = False,
    include_field_regions: bool = False,
    include_code_blocks: bool = False,
    include_formulas: bool = False,
    include_table_cells: bool = True,
    harvest_separator: str = "\n\n",
    note_threshold: float = 0.90,
    validate_xml: bool = True,
    max_harvest_chars: int = DEFAULT_MAX_HARVEST_CHARS,
    cache_dir: str | Path | None = None,
) -> DoclangRstResult:
    """Parse a DocLang XML file and return its RST analysis.

    Args:
        path: filesystem path to a ``.dclg.xml`` file.
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
        include_picture_captions: harvest ``<picture><caption>`` text.
        include_background: include layer ``"background"`` items.
        include_furniture: include layer ``"furniture"`` items plus
            ``<page_header>`` / ``<page_footer>``.
        include_field_regions: harvest text inside ``<field_region>``
            (default off — boundary-only).
        include_code_blocks: harvest ``<code>`` text (default off).
        include_formulas: harvest ``<formula>`` text (default off).
        include_table_cells: run the per-table mini-parses (two-level
            analysis). When False, ``table_analyses`` is empty and table
            content is not analysed; the ``table-N`` boundaries are
            emitted either way. ``<index>`` and ``<tabular>`` are
            boundary-only in both modes.
        harvest_separator: inserted between harvested spans (thread
            continuations join with a single space instead).
        note_threshold: relations whose overlap is >= this ratio
            dominated by a single span get a ``note`` field.
        validate_xml: when True (default), validate against the DocLang
            schema via the ``doclang`` PyPI package before parsing. Raises
            ``InvalidDoclangError`` when the package is not importable
            (pass ``validate_xml=False`` to skip). Current DocLang requires
            the ``https://www.doclang.ai/ns/v0`` namespace, so a
            non-namespaced document is rejected here; pass
            ``validate_xml=False`` to parse non-conforming input best-effort.
        max_harvest_chars: raise ``InputTooLargeError`` above this size
            (checked for the main harvest and each table harvest).
        cache_dir: when set, results are cached on disk keyed by the
            source bytes + model identity + knobs; repeat calls return
            the cached result without loading the model.

    Raises:
        InvalidDoclangError: ``validate_xml=True`` and validation failed.
        EmptyDoclangError: the document has no harvestable content.
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
        "include_picture_captions": include_picture_captions,
        "include_background": include_background,
        "include_furniture": include_furniture,
        "include_field_regions": include_field_regions,
        "include_code_blocks": include_code_blocks,
        "include_formulas": include_formulas,
        "include_table_cells": include_table_cells,
        "harvest_separator": harvest_separator,
        "note_threshold": note_threshold,
        "validate_xml": validate_xml,
        "max_harvest_chars": max_harvest_chars,
        **model_identity_knobs(
            hf_model_name=hf_model_name,
            hf_model_version=hf_model_version,
            relinventory=relinventory,
            parser=parser,
        ),
    }
    cache_path = Path(cache_dir) if cache_dir is not None else None
    cache_key = result_cache_key(source_bytes, knobs)
    if cache_path is not None:
        cached = load_cached(cache_path, cache_key)
        if isinstance(cached, DoclangRstResult):
            return cached

    if validate_xml:
        _validate_xml(src_path)

    tree = parse_doclang_xml(src_path)
    root = tree.getroot()

    body_children = [
        c for c in root
        if isinstance(c.tag, str) and local_name(c) != "head"
    ]
    if not body_children:
        raise EmptyDoclangError(
            f"DocLang document at {src_path} has no body content — nothing to harvest."
        )

    harvest = harvest_doclang_text(
        tree,
        include_picture_captions=include_picture_captions,
        include_background=include_background,
        include_furniture=include_furniture,
        include_field_regions=include_field_regions,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        harvest_separator=harvest_separator,
    )
    table_harvests = (
        harvest_doclang_tables(
            tree,
            include_background=include_background,
            include_furniture=include_furniture,
            harvest_separator=harvest_separator,
        )
        if include_table_cells
        else ()
    )

    if not harvest.full_text and not any(th.full_text for th in table_harvests):
        raise EmptyHarvestError(
            f"No text harvested from {src_path}. Document may have all "
            f"eligible content excluded by knobs."
        )

    for label, text in (("main", harvest.full_text), *(
        (th.marker_xpath, th.full_text) for th in table_harvests
    )):
        if len(text) > max_harvest_chars:
            raise InputTooLargeError(
                f"Harvested text for {label} is {len(text)} chars, exceeds "
                f"max_harvest_chars={max_harvest_chars}. Chunk upstream or raise the limit."
            )

    boundaries = detect_boundaries(
        tree,
        include_code_blocks=include_code_blocks,
        include_formulas=include_formulas,
        include_field_regions=include_field_regions,
    )
    table_boundaries = {b.id: b for b in boundaries if b.kind == "table"}

    if parser is None:
        from isanlp_rst.parser import Parser
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
        rst_tree = parser(harvest.full_text)["rst"][0]
        relations, edus = flatten_tree(
            rst_tree, harvest.spans, boundaries, note_threshold=note_threshold
        )
    else:
        relations, edus = (), ()

    table_analyses: list[TableAnalysis] = []
    for th in table_harvests:
        if not th.full_text:
            continue
        boundary_id = f"table-{th.table_idx}"
        table_tree = parser(th.full_text)["rst"][0]
        t_relations, t_edus = flatten_tree(
            table_tree,
            th.spans,
            (table_boundaries[boundary_id],),
            note_threshold=note_threshold,
        )
        table_analyses.append(
            TableAnalysis(id=boundary_id, relations=t_relations, edus=t_edus)
        )

    result = DoclangRstResult(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        tool=TOOL_NAME,
        tool_version=resolve_tool_version(),
        model_version=model_version,
        inventory=inventory,
        source=src_path.name,
        source_origin=_source_origin(tree),
        boundaries=boundaries,
        relations=relations,
        edus=edus,
        table_analyses=tuple(table_analyses),
    )
    if cache_path is not None:
        store_cached(cache_path, cache_key, result)
    return result
