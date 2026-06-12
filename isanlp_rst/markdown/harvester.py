"""Harvest text from a markdown token stream for RST parsing.

Two harvesters:

- ``harvest_markdown_text`` — the main document harvest. Walks the
  ``markdown-it-py`` token stream (front-matter already removed by
  ``loader``) and emits one ``HarvestSpan`` per harvest-eligible block.
  Table token ranges are always skipped here — tables are analysed
  separately (two-level analysis, 2026-06-12 directive Option 2).
- ``harvest_markdown_tables`` — one ``TableHarvest`` per table, cells
  in row-major order with ``#/tables/T/cells/K`` refs (K counts every
  grid position including empty cells, so refs stay stable).

Main-harvest block kinds:

- ``heading`` — ATX or Setext, ``level`` ∈ {1..6}.
- ``paragraph`` — top-level prose paragraph.
- ``list_item`` — one span per item; nested items collapse into the
  outer item's text.
- ``blockquote_paragraph`` / ``blockquote_heading`` — content inside
  ``<blockquote>``, gated as a whole by ``include_blockquotes``
  (default on). A quoted heading is quoted content, not document
  structure — ``boundaries`` opens sections only for ``kind ==
  "heading"``.
- ``code_block`` — fenced or indented, gated by ``include_code_blocks``
  (default on).
- ``html_block`` — raw HTML block with tags stripped to text, gated by
  ``include_html`` (default on).

Inline content is flattened plain-text only: emphasis / strikethrough /
link / code-span wrappers are dropped; text-bearing children (``text``,
``code_inline``, ``image`` alt, ``softbreak``/``hardbreak`` → space)
are concatenated.

Each main block gets a sequential ``#/blocks/N`` address. ``#/tables/T``
is a synthetic boundary-only marker — no ``HarvestSpan`` carries it.

Spans are concatenated with ``harvest_separator`` (default ``"\\n\\n"``).
"""

from __future__ import annotations

import re

from markdown_it.token import Token

from .schema import HarvestResult, HarvestSpan, TableHarvest

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _inline_text(inline: Token) -> str:
    """Flatten an ``inline`` token's children to plain text.

    Concatenates text-bearing children (``text``, ``code_inline``,
    ``image`` alt) and converts ``softbreak`` / ``hardbreak`` to a single
    space. Drops emphasis / strong / strikethrough / link / inline-HTML
    wrappers entirely (their text content lives in sibling ``text``
    tokens). When ``children`` is ``None`` (rare — shouldn't happen for
    block-level inlines), falls back to ``inline.content``.
    """
    if inline.children is None:
        return inline.content
    parts: list[str] = []
    for child in inline.children:
        match child.type:
            case "text" | "code_inline" | "image":
                parts.append(child.content)
            case "softbreak" | "hardbreak":
                parts.append(" ")
            case _:
                pass
    return "".join(parts)


def _strip_html(raw: str) -> str:
    """Strip tags from a raw HTML block and normalise whitespace runs.

    The RST parser wants prose, not markup — ``<div class="x">`` tokens
    would otherwise enter the harvest as junk.
    """
    return " ".join(_HTML_TAG_RE.sub(" ", raw).split())


def _line_range(tok: Token) -> tuple[int, int]:
    """Return ``(line_begin, line_end)`` from ``tok.map``, or ``(0, 0)``."""
    if tok.map is None:
        return 0, 0
    return tok.map[0], tok.map[1]


def harvest_markdown_text(
    tokens: tuple[Token, ...],
    *,
    include_blockquotes: bool = True,
    include_code_blocks: bool = True,
    include_html: bool = True,
    harvest_separator: str = "\n\n",
) -> HarvestResult:
    """Produce the main document harvest with per-span ``block_ref`` mapping.

    Args:
        tokens: the body token stream from ``loader.load_markdown``
            (front-matter already removed).
        include_blockquotes: include content inside ``<blockquote>`` —
            paragraphs, headings, lists, code fences, and HTML blocks
            alike. When False, the whole quoted region is skipped.
        include_code_blocks: include fenced and indented code blocks.
        include_html: include raw HTML blocks (tags stripped to text).
        harvest_separator: inserted between consecutive harvested spans.

    Returns:
        ``HarvestResult`` whose ``full_text`` is the document-level input
        for the RST parser, and whose ``spans`` map each text range back
        to its ``block_ref`` in document order. Tables are never
        included — see ``harvest_markdown_tables``.
    """
    pieces: list[str] = []
    spans: list[HarvestSpan] = []
    cursor = 0
    sep_len = len(harvest_separator)
    block_counter = 0

    def emit(
        kind: str,
        text: str,
        line_begin: int,
        line_end: int,
        *,
        level: int | None = None,
    ) -> None:
        nonlocal cursor, block_counter
        if not text:
            return
        if pieces:
            cursor += sep_len
        block_ref = f"#/blocks/{block_counter}"
        block_counter += 1
        start = cursor
        end = start + len(text)
        spans.append(
            HarvestSpan(
                block_ref=block_ref,
                kind=kind,
                text=text,
                start=start,
                end=end,
                line_begin=line_begin,
                line_end=line_end,
                level=level,
            )
        )
        pieces.append(text)
        cursor = end

    blockquote_depth = 0
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]
        ttype = tok.type
        in_bq = blockquote_depth > 0
        bq_gated = in_bq and not include_blockquotes

        if ttype == "blockquote_open":
            blockquote_depth += 1
            i += 1
            continue

        if ttype == "blockquote_close":
            blockquote_depth -= 1
            i += 1
            continue

        if ttype == "heading_open":
            if bq_gated:
                i += 3
                continue
            level = int(tok.tag[1])  # "h1" .. "h6" → 1..6
            line_begin, line_end = _line_range(tok)
            inline = tokens[i + 1] if i + 1 < n else None
            text = _inline_text(inline).strip() if inline is not None else ""
            kind = "blockquote_heading" if in_bq else "heading"
            emit(kind, text, line_begin, line_end, level=level)
            i += 3  # heading_open, inline, heading_close
            continue

        if ttype == "paragraph_open":
            if bq_gated:
                i += 3
                continue
            line_begin, line_end = _line_range(tok)
            inline = tokens[i + 1] if i + 1 < n else None
            text = _inline_text(inline).strip() if inline is not None else ""
            kind = "blockquote_paragraph" if in_bq else "paragraph"
            emit(kind, text, line_begin, line_end)
            i += 3
            continue

        if ttype == "list_item_open":
            line_begin, line_end = _line_range(tok)
            parts: list[str] = []
            depth = 1
            i += 1
            while i < n and depth > 0:
                inner = tokens[i]
                if inner.type == "list_item_open":
                    depth += 1
                elif inner.type == "list_item_close":
                    depth -= 1
                    if depth == 0:
                        break
                elif inner.type == "inline":
                    parts.append(_inline_text(inner))
                i += 1
            if not bq_gated:
                text = " ".join(p.strip() for p in parts if p.strip()).strip()
                emit("list_item", text, line_begin, line_end)
            i += 1  # consume list_item_close
            continue

        if ttype in {
            "bullet_list_open", "bullet_list_close",
            "ordered_list_open", "ordered_list_close",
        }:
            i += 1
            continue

        if ttype in ("fence", "code_block"):
            if include_code_blocks and not bq_gated:
                line_begin, line_end = _line_range(tok)
                text = tok.content.rstrip("\n")
                emit("code_block", text, line_begin, line_end)
            i += 1
            continue

        if ttype == "html_block":
            if include_html and not bq_gated:
                line_begin, line_end = _line_range(tok)
                emit("html_block", _strip_html(tok.content), line_begin, line_end)
            i += 1
            continue

        if ttype == "hr":
            i += 1
            continue

        if ttype == "table_open":
            # Tables are analysed per-table (harvest_markdown_tables);
            # skip the whole token range in the main harvest.
            while i < n and tokens[i].type != "table_close":
                i += 1
            i += 1  # consume table_close
            continue

        # Unknown / unhandled token — advance.
        i += 1

    return HarvestResult(
        full_text=harvest_separator.join(pieces),
        spans=tuple(spans),
    )


def harvest_markdown_tables(
    tokens: tuple[Token, ...],
    *,
    include_blockquotes: bool = True,
    harvest_separator: str = "\n\n",
) -> tuple[TableHarvest, ...]:
    """Produce one ``TableHarvest`` per table, in document order.

    Tables inside blockquotes are skipped entirely when
    ``include_blockquotes=False`` (no harvest → no boundary →
    consistent ``table-T`` numbering). Cell refs are
    ``#/tables/T/cells/K`` with K counting every grid position in
    row-major order; empty cells keep their K but yield no span.
    """
    harvests: list[TableHarvest] = []
    sep_len = len(harvest_separator)
    blockquote_depth = 0
    table_idx = 0
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]
        if tok.type == "blockquote_open":
            blockquote_depth += 1
            i += 1
            continue
        if tok.type == "blockquote_close":
            blockquote_depth -= 1
            i += 1
            continue
        if tok.type != "table_open":
            i += 1
            continue

        in_gated_bq = blockquote_depth > 0 and not include_blockquotes
        pieces: list[str] = []
        spans: list[HarvestSpan] = []
        cursor = 0
        cell_pos = 0
        row_idx = -1
        col_idx = 0

        i += 1
        while i < n and tokens[i].type != "table_close":
            inner = tokens[i]
            if inner.type == "tr_open":
                row_idx += 1
                col_idx = 0
            elif inner.type in ("th_open", "td_open"):
                is_th = inner.type == "th_open"
                line_begin, line_end = _line_range(inner)
                cell_text = ""
                j = i + 1
                while j < n and tokens[j].type not in ("th_close", "td_close"):
                    if tokens[j].type == "inline":
                        cell_text = _inline_text(tokens[j]).strip()
                    j += 1
                if cell_text and not in_gated_bq:
                    if pieces:
                        cursor += sep_len
                    start = cursor
                    end = start + len(cell_text)
                    spans.append(
                        HarvestSpan(
                            block_ref=f"#/tables/{table_idx}/cells/{cell_pos}",
                            kind="table_header_cell" if is_th else "table_cell",
                            text=cell_text,
                            start=start,
                            end=end,
                            line_begin=line_begin,
                            line_end=line_end,
                            table_idx=table_idx,
                            row_idx=row_idx,
                            col_idx=col_idx,
                        )
                    )
                    pieces.append(cell_text)
                    cursor = end
                cell_pos += 1
                col_idx += 1
                i = j  # jump to the closing th/td
            i += 1
        i += 1  # consume table_close

        if not in_gated_bq:
            harvests.append(
                TableHarvest(
                    table_idx=table_idx,
                    marker_ref=f"#/tables/{table_idx}",
                    full_text=harvest_separator.join(pieces),
                    spans=tuple(spans),
                )
            )
            table_idx += 1

    return tuple(harvests)


__all__ = ["harvest_markdown_tables", "harvest_markdown_text"]
