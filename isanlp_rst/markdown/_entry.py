"""``parse_markdown`` entry point — load → harvest → boundaries → parse → flatten.

Two-level analysis (2026-06-12 directive, Option 2): the main document
harvest excludes table cells; each table gets its own RST mini-parse
whose relations land in ``MarkdownRstResult.table_analyses``.

The underlying ``Parser`` is injectable so batch consumers construct it
once and reuse it across many ``parse_markdown`` calls. An optional
on-disk cache (``cache_dir=``) short-circuits repeat parses.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .._rst_common import (
    load_cached,
    resolve_inventory,
    resolve_tool_version,
    result_cache_key,
    store_cached,
)
from .boundaries import detect_boundaries
from .errors import EmptyHarvestError, EmptyMarkdownError, InputTooLargeError
from .harvester import harvest_markdown_tables, harvest_markdown_text
from .loader import load_markdown
from .mapper import flatten_tree
from .schema import MarkdownRstResult, TableAnalysis

if TYPE_CHECKING:
    from isanlp_rst.parser import Parser

SCHEMA_NAME = "isanlp_rst_markdown"
SCHEMA_VERSION = "1.0"
TOOL_NAME = "isanlp_rst"
DEFAULT_MAX_HARVEST_CHARS = 200_000

# Backwards-compatible aliases — tests and external callers import these
# from the entry module; the implementations live in _rst_common.
_resolve_inventory = resolve_inventory
_resolve_tool_version = resolve_tool_version


def _source_origin(
    front_matter: str | None,
    front_matter_format: str | None,
    *,
    gfm: bool,
) -> dict[str, Any]:
    """Build the ``source_origin`` block for the result."""
    return {
        "format": "markdown",
        "gfm": gfm,
        "front_matter": front_matter,
        "front_matter_format": front_matter_format,
    }


def parse_markdown(
    path: str | Path,
    *,
    parser: "Parser | None" = None,
    hf_model_name: str = "tchewik/isanlp_rst_v3",
    hf_model_version: str = "gumrrg",
    relinventory: str | None = None,
    device: str = "auto",
    dtype: str | None = None,
    gfm: bool = True,
    include_blockquotes: bool = True,
    include_table_cells: bool = True,
    include_code_blocks: bool = True,
    include_html: bool = True,
    harvest_separator: str = "\n\n",
    note_threshold: float = 0.90,
    max_harvest_chars: int = DEFAULT_MAX_HARVEST_CHARS,
    cache_dir: str | Path | None = None,
) -> MarkdownRstResult:
    """Parse a markdown file and return its RST analysis.

    Args:
        path: filesystem path to a ``.md`` / ``.markdown`` file.
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
        gfm: enable GFM tables + strikethrough (default on).
        include_blockquotes: harvest content inside ``<blockquote>`` —
            paragraphs, headings, lists, code fences, HTML blocks, and
            tables alike.
        include_table_cells: run the per-table mini-parses (two-level
            analysis). When False, ``table_analyses`` is empty, table
            content is not analysed, and no ``table-T`` boundaries are
            emitted (markdown boundaries derive from the harvests).
        include_code_blocks: harvest fenced and indented code blocks.
        include_html: harvest raw HTML blocks (tags stripped to text).
        harvest_separator: inserted between consecutive harvested spans.
        note_threshold: relations whose overlap is >= this ratio
            dominated by a single span get a ``note`` field.
        max_harvest_chars: raise ``InputTooLargeError`` above this size
            (checked for the main harvest and each table harvest).
        cache_dir: when set, results are cached on disk keyed by the
            source bytes + model identity + knobs; repeat calls return
            the cached result without loading the model.

    Raises:
        EmptyMarkdownError: the file has no body tokens (whitespace or
            front-matter only).
        EmptyHarvestError: neither the main harvest nor any table
            harvest produced text.
        InputTooLargeError: a harvest exceeds ``max_harvest_chars``.
    """
    src_path = Path(path)
    source_bytes = src_path.read_bytes()

    knobs: dict[str, object] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "hf_model_version": hf_model_version,
        "relinventory": relinventory,
        "dtype": dtype,
        "gfm": gfm,
        "include_blockquotes": include_blockquotes,
        "include_table_cells": include_table_cells,
        "include_code_blocks": include_code_blocks,
        "include_html": include_html,
        "harvest_separator": harvest_separator,
        "note_threshold": note_threshold,
        "max_harvest_chars": max_harvest_chars,
    }
    cache_path = Path(cache_dir) if cache_dir is not None else None
    cache_key = result_cache_key(source_bytes, knobs)
    if cache_path is not None:
        cached = load_cached(cache_path, cache_key)
        if isinstance(cached, MarkdownRstResult):
            return cached

    loaded = load_markdown(source_bytes.decode("utf-8"), gfm=gfm)
    if not loaded.tokens:
        raise EmptyMarkdownError(
            f"Markdown file at {src_path} has no body content "
            f"(only whitespace or front-matter)."
        )

    harvest = harvest_markdown_text(
        loaded.tokens,
        include_blockquotes=include_blockquotes,
        include_code_blocks=include_code_blocks,
        include_html=include_html,
        harvest_separator=harvest_separator,
    )
    table_harvests = (
        harvest_markdown_tables(
            loaded.tokens,
            include_blockquotes=include_blockquotes,
            harvest_separator=harvest_separator,
        )
        if include_table_cells
        else ()
    )

    if not harvest.full_text and not any(th.full_text for th in table_harvests):
        raise EmptyHarvestError(
            f"No text harvested from {src_path}. The file may contain only "
            f"thematic breaks, or all eligible content was excluded by knobs."
        )

    for label, text in (("main", harvest.full_text), *(
        (th.marker_ref, th.full_text) for th in table_harvests
    )):
        if len(text) > max_harvest_chars:
            raise InputTooLargeError(
                f"Harvested text for {label} is {len(text)} chars, exceeds "
                f"max_harvest_chars={max_harvest_chars}. Chunk upstream or raise the limit."
            )

    boundaries = detect_boundaries(harvest.spans, table_harvests)
    table_boundaries = {b.id: b for b in boundaries if b.kind == "table"}

    if parser is None:
        from isanlp_rst.parser import Parser  # lazy — avoids loading on every import
        parser = Parser(
            hf_model_name=hf_model_name,
            hf_model_version=hf_model_version,
            relinventory=relinventory,
            device=device,
            dtype=dtype,
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

    result = MarkdownRstResult(
        schema_name=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        tool=TOOL_NAME,
        tool_version=resolve_tool_version(),
        model_version=hf_model_version,
        inventory=resolve_inventory(hf_model_version, relinventory),
        source=src_path.name,
        source_origin=_source_origin(
            loaded.front_matter, loaded.front_matter_format, gfm=gfm
        ),
        boundaries=boundaries,
        relations=relations,
        edus=edus,
        table_analyses=tuple(table_analyses),
    )
    if cache_path is not None:
        store_cached(cache_path, cache_key, result)
    return result
