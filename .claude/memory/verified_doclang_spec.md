---
name: verified-doclang-spec
description: Verified facts about the DocLang 0.5 spec and the doclang PyPI package, from reading the full spec.md and the package source on 2026-05-15. Line citations against doclang-project/doclang main branch.
metadata:
  type: reference
---

Investigated 2026-05-15 by reading the **full** `spec.md` (3734 lines) at <https://github.com/doclang-project/doclang>, the `doclang` Python package source (`__init__.py`, `validation.py`, `cli.py`), and two real `.dclg.xml` fixtures from `tests/data/valid/`. Line numbers below cite `spec.md` on the `main` branch.

## What DocLang is

XML-based AI-native document markup format authored by an industrial consortium (IBM, ABBYY, RedHat, HumanSignal, NVIDIA, Forgis — `spec.md:11-32`). File extension `.dclg.xml`. Designed to be LLM-tokeniser-friendly (target ≤ 1000 syntax tokens, `spec.md:69`).

## Root element

`<doclang>` exists exactly once at root (`spec.md:1969-1994`). Attributes:

- `xmlns` — optional; default `"https://www.doclang.ai/ns/v0"`. Real fixtures vary: `tests/data/valid/doclang_example.dclg.xml` omits namespace; `tests/data/valid/ok_comprehensive.dclg.xml:2` declares it explicitly.
- `version` — optional; default `"0.5"`; `MAJOR.MINOR` format (`spec.md:219-241`). `0.x` minor bumps are breaking; `1.x+` follows SemVer compat.

## Element head ordering (fixed) — `spec.md:147-157`

A semantic element's content begins with an optional **element head**, components in this strict order:

1. `<label value="..."/>` (optional)
2. `<thread thread_id="N"/>` (optional)
3. `<xref thread_id="N"/>` OR `<href uri="..."/>` (mutually exclusive, optional)
4. `<layer value="..."/>` (optional)
5. Sequence of exactly 4 `<location value="..."/>` (alternating x/y; optional)
6. `<caption>...</caption>` (optional)
7. `<custom>...</custom>` (optional)

The element **body** follows.

## Document head: `<head>`

Optional, first child of `<doclang>` (`spec.md:1996-2014`). v0.5 normatively defines only `<default_resolution width="..." height="..."/>` (`spec.md:3025-3042`; default `width=512`, `height=512`). Rich metadata (`<title>`, `<author>`, governance fields like `<licenses>`, `<pii_status>`, etc.) is **Appendix C: Future Extensions** (`spec.md:3203-onwards`), NOT enforced in v0.5. Real fixtures put arbitrary children inside `<head>` — verified at `tests/data/valid/ok_comprehensive.dclg.xml:5-14` (`<title>`, `<author>`, `<date>`, `<keywords>`, `<custom-field>`).

## Primary semantic elements (top-level under `<doclang>`)

Verified at `spec.md:2046-2454`:

| Element | Attributes | Notes |
|---|---|---|
| `<text>` | none | The workhorse content element. |
| `<heading level="N">` | `level` (positive int, default `"1"`) | Used for sections. |
| `<footnote>` | none | |
| `<page_header>` | none | Material repeated at top of page. |
| `<page_footer>` | none | Material repeated at bottom. |
| `<field_region>` | none | Container for forms / key-value structures. |
| `<list class="...">` | `class` ∈ `{"unordered", "ordered"}`, default `"unordered"` | Items via `<ldiv/>`. Body must begin with `<ldiv>`. |
| `<table>` | none | OTSL inline cell tokens. Body must begin with a cell token. |
| `<index>` | none | OTSL-based; same cell model as `<table>`. |
| `<formula>` | none | Raw LaTeX (no `$...$` wrappers — `spec.md:2232`). |
| `<code>` | none | Standalone or inline. Language via `<label>` head. |
| `<picture class="...">` | `class` ∈ `{"undefined", "chart"}`, default `"undefined"` | `<src uri="..."/>` for source. `<tabular>` only allowed for `class="chart"`. |
| `<marker>` | none | Visible glyph/number (e.g. for list items). |
| `<group>` | none | Generic container for multiple semantic elements. Body of `<doclang>` can be arbitrary grouping. |
| `<caption>` | none | Element-head only — `spec.md:2442`. |

## Secondary semantic elements (scoped)

- `<field_heading level="N">`: descendant of `<field_region>` (`spec.md:2336-2353`)
- `<field_item>`: descendant of `<field_region>` (`spec.md:2354-2372`)
- `<key>`: descendant of `<field_item>`, 0–1 per field_item (`spec.md:2374-2393`)
- `<value class="...">`: descendant of `<field_item>`, 0–N; `class` ∈ `{"read_only", "fillable"}`, default `"read_only"` (`spec.md:2394-2414`)
- `<hint>`: descendant of `<field_region>` (`spec.md:2416-2434`)

## Property elements (head components)

- `<label value="..."/>` — `value` default `"undefined"`; per-host recommended values (NOT validated) (`spec.md:2460-2476`).
- `<thread thread_id="N"/>` — `thread_id` REQUIRED positive int. All `<thread>` instances sharing a thread_id MUST be under same host element type (`spec.md:2478-2494`).
- `<xref thread_id="N"/>` — REQUIRED positive int; must reference an existing thread (`spec.md:2496-2512`).
- `<href uri="..."/>` — REQUIRED URI (`spec.md:2514-2534`).
- `<custom>` — arbitrary content; namespacing recommended (`spec.md:2536-2554`).
- `<location value="N" resolution="N"/>` — `value` REQUIRED int in `[0, resolution)`; `resolution` optional, defaults to `default_resolution@width`/`@height` or `"512"` (`spec.md:2556-2573`).
- `<layer value="..."/>` — `value` ∈ `{"body", "background", "furniture"}`, default `"body"` (`spec.md:2575-2591`). **NO `notes` value.** Three values total, not five (cf. Docling's `ContentLayer` enum).

## Payload elements

- `<src uri="..."/>` — REQUIRED URI; supports `data:` URIs (RFC 2397 base64) and relative URIs. Only inside `<picture>` body (`spec.md:2597-2613`).
- `<tabular>` — only inside `<picture class="chart">` body (`spec.md:2615-2633`).
- `<checkbox class="..."/>` — `class` ∈ `{"unselected", "selected"}`, default `"unselected"` (`spec.md:2635-2651`).
- `<content>` — whitespace-preserving (equivalent to `xml:space="preserve"`); for code blocks, multi-line text, etc. (`spec.md:2653-2671`).

## Formatting elements (inline only, no attributes)

`<bold>`, `<italic>`, `<underline>`, `<strikethrough>`, `<superscript>`, `<subscript>`, `<handwriting>`, `<rtl>` (`spec.md:2673-2835`). Each contains raw text + nested formatting.

## Structural elements (table / list)

Only as children of `<table>`, `<index>`, `<tabular>` (cell tokens) or `<list>` (`<ldiv/>`):

| Element | Meaning | spec.md ref |
|---|---|---|
| `<fcel/>` | Full cell start | 2841-2855 |
| `<ecel/>` | Empty cell start | 2857-2871 |
| `<ched/>` | Column header cell | 2873-2887 |
| `<rhed/>` | Row header cell | 2889-2903 |
| `<corn/>` | Corner cell | 2905-2919 |
| `<srow/>` | Section row header | 2921-2935 |
| `<lcel/>` | Left-merge (colspan continuation) | 2937-2951 |
| `<ucel/>` | Upward-merge (rowspan continuation) | 2953-2967 |
| `<xcel/>` | Cross-merge | 2969-2983 |
| `<nl/>` | Row terminator | 2985-2999 |
| `<ldiv/>` | List-item start (only child of `<list>`) | 3001-3019 |

## Threading model — `spec.md:2478-2494`

`<thread thread_id="N"/>` is the **fragment continuation** primitive, NOT a stable element identifier. Used for:

- Cross-page content (close all elements before `<page_break/>`, then re-open with same thread_id after).
- Cross-column content (e.g. two-column layouts).
- Cross-fragment table content via `<thread>` (and the proposed `<h_thread>` in Appendix C).
- Anchor target for `<xref thread_id="N"/>`.

**Crucial constraint:** all `<thread>` instances with the same `thread_id` MUST be under the same host element type (e.g. all under `<text>`, not mixed `<text>` and `<picture>`).

**There is no DocLang concept of stable per-element identifier.** XPath into the parsed XML tree is the only way to address arbitrary elements uniquely.

## Pages, sections, slides

- **Pages:** delimited by `<page_break/>` empty elements; only allowed as child of `<doclang>` (`spec.md:2016-2040`). Content between `<page_break/>` markers forms a valid DocLang body.
- **Sections:** `<heading level="N">` (`spec.md:2066-2086`). `level` is a positive integer with no upper bound.
- **Slides:** spec.md does NOT define slides. `<group>` is the only generic container.

## What the `doclang` Python package provides

Read verbatim from `doclang/__init__.py`, `doclang/validation.py`, `doclang/cli.py` on `main` (2026-05-15):

```python
# doclang/__init__.py — entire content:
"""DocLang reference validator."""
from doclang.validation import ValidationError, validate
__all__ = ["ValidationError", "validate"]
```

Public API: **`validate(xml_file, *, allow_empty_namespace=False, xsd_only=False, schematron_only=False) -> None`**. Raises `ValidationError` on failure.

`ValidationError` fields: `file`, `xsd_valid`, `xsd_errors`, `schematron_valid`, `schematron_errors`.

**The `doclang` package is validator-only.** It does NOT expose a parser, DOM, or object model for `.dclg.xml` files. For programmatic use we must parse the XML ourselves (`lxml`, `xml.etree.ElementTree`, etc.).

CLI entry point via `typer`: `doclang validate <xml_file>`. Subcommands and flags in `doclang/cli.py`.

## Real fixture observations

Read `tests/data/valid/doclang_example.dclg.xml` and `ok_comprehensive.dclg.xml` directly:

- `doclang_example.dclg.xml` has `<?xml version="1.0" encoding="UTF-8"?>` XML prolog; `<doclang>` element does NOT declare `xmlns`. Uses `<picture><label value="flow_chart"/>`, `<table>` with OTSL tokens, `<heading level="2">`, `<text>`, `<list>` with virtual text, `<code><label value="R"/><content><![CDATA[...]]></content></code>`.
- `ok_comprehensive.dclg.xml:2`: `<doclang xmlns="https://www.doclang.ai/ns/v0">`. `<head>` (lines 5-14) contains arbitrary children (`<title>`, `<author>`, `<date>`, `<keywords>`, `<custom-field>`) — the XSD permits any structure inside `<head>` in v0.5.
- Empty `<picture/>` is valid (`ok_comprehensive.dclg.xml:217`).
- Empty `<group></group>` is valid (`ok_comprehensive.dclg.xml:565`).
- Nested `<group>` is valid (`ok_comprehensive.dclg.xml:667-674`).
- Mixed semantic content inside `<text>` is valid: `<text>` can nest `<text>`, `<code>`, `<picture>`, `<formula>`, `<list>` inline.

## What this means for the isanlp_rst.doclang work

This memory is reference-only — design decisions belong in the plan doc. Key constraints that affect any RST integration:

1. **No stable element identifiers in DocLang v0.5.** Any per-element addressing scheme we use (XPath, thread_id where present, positional counter) is OUR choice, not DocLang's.
2. **No `notes` content layer.** PPTX-via-DocLang loses slide notes.
3. **No slide concept.** PPTX-via-DocLang loses slide groups.
4. **Tables are OTSL inline tokens, not separate blocks.** Different from Docling's `TableItem`.
5. **`<head>` is schema-free in v0.5.** Document metadata is whatever the producer puts there.
6. **Must parse XML ourselves.** The `doclang` Python package is validator-only.

Related: [[decision-one-tree-per-document]], [[verified-docling-core-api]], [[verified-docling-schema]].
