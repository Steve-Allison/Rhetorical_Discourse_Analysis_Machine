---
name: verified-doclang-fixtures
description: Phase 1 verification facts about DocLang 0.5 — structural shapes confirmed by inspecting all 40 valid fixtures from doclang-project/doclang main, 2026-06-10.
metadata:
  type: reference
---

Phase 1 of the DocLang-native RST plan ([`docs/plans/2026-05-15-doclang-native-rst.md`](../../docs/plans/2026-05-15-doclang-native-rst.md)).
All 40 valid fixtures from
[`doclang-project/doclang/tests/data/valid`](https://github.com/doclang-project/doclang/tree/main/tests/data/valid)
mirrored into [`tests/fixtures/doclang/`](../../tests/fixtures/doclang/) on 2026-06-10
and inspected end-to-end. Each finding below has an associated reproducer command
or a fixture-line citation.

## 1. Canonical XPath addressing — local-name path

`lxml.etree.ElementTree.getpath()` is **not usable** as the canonical address.
On a namespaced document (the spec-recommended shape), `getpath()` emits
wildcards: `/*/*[3]` instead of `/doclang[1]/heading[3]`. Round-trip and
human-readability both fail.

Resolution: build paths ourselves. Each step is `local_name[i]` where `i` is
the 1-based position among siblings sharing the same local name. Namespaces
are stripped via `el.tag.split("}", 1)[1]` when present.

Verified by harvesting all 464 elements in
[`ok_comprehensive.dclg.xml`](../../tests/fixtures/doclang/ok_comprehensive.dclg.xml):

- 464 / 464 paths round-trip via a `find_by_local_path()` resolver
- 464 / 464 paths are unique within the document
- Identical path shape for the namespace-absent
  [`ok_no_namespace.dclg.xml`](../../tests/fixtures/doclang/ok_no_namespace.dclg.xml)
  fixture (`/doclang[1]`, `/doclang[1]/heading[1]`, …)

Sample shape:

```text
/doclang[1]
/doclang[1]/head[1]/title[1]
/doclang[1]/head[1]/custom-field[1]/status[1]
/doclang[1]/heading[3]
/doclang[1]/text[7]
```

Reproducer: `pixi run python` + the script in the Phase 1 plan section.

## 2. Namespace handling — transparent

`<doclang>` may declare `xmlns="https://www.doclang.ai/ns/v0"` (per
[`spec.md:219-241`](https://github.com/doclang-project/doclang/blob/main/spec.md#L219-L241))
or omit the namespace (fixture
[`ok_no_namespace.dclg.xml:2`](../../tests/fixtures/doclang/ok_no_namespace.dclg.xml#L2)).
Both are valid.

Since the canonical XPath strips namespaces (item 1), the addressing scheme
produces identical output regardless. The decision is recorded as a knob-free
default: paths are namespace-agnostic.

## 3. Virtual-text addressing — marker `.tail` + intervening sibling tails

`<ldiv/>` and `<fcel/>` / `<ched/>` / `<rhed/>` / `<corn/>` / `<srow/>` /
`<lcel/>` / `<ucel/>` / `<xcel/>` are **self-closing markers**. The item / cell
content lives in lxml's tail-text position, not as an element child.

Evidence from
[`ok_content_in_virtual_text.dclg.xml`](../../tests/fixtures/doclang/ok_content_in_virtual_text.dclg.xml):

```xml
<list class="unordered">
  <ldiv/>
  First                       <!-- this string IS <ldiv/>.tail -->
  <ldiv/>
  <content>Second</content>   <!-- this <content> is sibling of <ldiv/> -->
</list>
```

After lxml parse: `ldiv[1].tail = 'First'`, `ldiv[2].tail = ''`, but the
`<content>Second</content>` is a following sibling of `ldiv[2]`.

The harvest walk for a `<list>` body is:

1. Walk children of `<list>` left-to-right.
2. Each `<ldiv/>` marker opens a new item. The item's text accumulates from:
   - `ldiv.tail`
   - all following siblings' `itertext()` (i.e. element body + nested children)
   - and those siblings' `.tail` strings
   - up to but not including the next `<ldiv/>` marker.
3. The canonical XPath of the item IS the `<ldiv/>` marker's XPath. No
   synthetic text-node addressing needed.

Same rule for `<table>` cells with cell-start markers + `<nl/>` terminating
rows. Confirmed on
[`ok_list_with_unwrapped_text.dclg.xml`](../../tests/fixtures/doclang/ok_list_with_unwrapped_text.dclg.xml)
(18 markers, 3 nested-list cases) and
[`ok_table_raw_before.dclg.xml`](../../tests/fixtures/doclang/ok_table_raw_before.dclg.xml).

## 4. `<thread>` semantics — exactly one per host

Across all 40 fixtures, the per-host `<thread>` count is **exactly 1** for the
5 hosts that carry one. Confirmed by counting `[c for c in el if local(c) ==
"thread"]` for every element.

Hosts seen:

- [`ok_thread.dclg.xml`](../../tests/fixtures/doclang/ok_thread.dclg.xml) —
  two `<text>` elements both bearing `<thread thread_id="1"/>`, demonstrating
  the cross-fragment continuation pattern from
  [`spec.md:2478-2494`](https://github.com/doclang-project/doclang/blob/main/spec.md#L2478-L2494).
- [`ok_thread_unused.dclg.xml`](../../tests/fixtures/doclang/ok_thread_unused.dclg.xml) —
  thread defined, never referenced by `<xref>`. Valid.
- [`ok_xref.dclg.xml`](../../tests/fixtures/doclang/ok_xref.dclg.xml) —
  `<picture>` declares `<thread thread_id="1"/>`; a sibling `<text>` carries
  `<xref thread_id="1"/>Figure 3` referencing it.
- [`ok_layer_element_head_order.dclg.xml`](../../tests/fixtures/doclang/ok_layer_element_head_order.dclg.xml) —
  `<thread>` inside element-head between `<label>` and `<layer>`.

Schema implication: `thread_id: int | None` on `DoclangHarvestSpan` and the
RST relation / EDU schemas. NOT `tuple[int, ...]` — the spec
([`spec.md:147-157`](https://github.com/doclang-project/doclang/blob/main/spec.md#L147-L157))
defines element-head ordering with `<thread>` as a single optional slot, and
the corpus confirms.

## 5. `<list>` granularity — per-item, with structural nesting

30 lists across the corpus. Item counts 1–5. Nesting confirmed: 2 nested-list
cases (in
[`ok_comprehensive.dclg.xml`](../../tests/fixtures/doclang/ok_comprehensive.dclg.xml)
and
[`ok_list_with_unwrapped_text.dclg.xml`](../../tests/fixtures/doclang/ok_list_with_unwrapped_text.dclg.xml)),
both at depth 1.

Per-item harvest emits one `DoclangHarvestSpan` per `<ldiv/>` marker, with
`xpath` pointing at the marker. Nested lists harvest independently — the
inner `<list>` is one of the outer item's text sources but is also walked as
its own list at its own XPath.

## 6. `<code>` and `<formula>` — defaults remain OFF for prose harvest

12 `<code>` blocks (R, Python, SQL, Java, plus inline / nested-formatting
variants), 3 `<formula>` blocks (LaTeX:
`E = mc^2`, `x = \frac{-b \pm \sqrt{b^{2} - 4ac}}{2a}`).

`<formula>` content is unambiguously LaTeX source ([`spec.md:2232`](https://github.com/doclang-project/doclang/blob/main/spec.md#L2232)
explicitly says no `$...$` wrappers — bare LaTeX). Excluding from RST harvest
is correct.

`<code>` content is mostly source code, but
[`ok_comprehensive.dclg.xml`](../../tests/fixtures/doclang/ok_comprehensive.dclg.xml)
shows mixed cases including `<code>` with inline `<bold>` markup and inline
prose. Default-off remains defensible; consumers can flip
`include_code_blocks=True` for cases where they want to feed code into the
RST parser as opaque token sequences.

## 7. Structural shape census — informs boundary design

Reproducer script counted across all 40 fixtures:

- `<page_break/>`: 1 instance, parent always `<doclang>` (per
  [`spec.md:2016-2040`](https://github.com/doclang-project/doclang/blob/main/spec.md#L2016-L2040)).
- `<heading level="N">`: 9 instances, levels seen = `{1: 4, 2: 3, 3: 2}`.
- `<field_region>`: 5 instances.
- `<group>` nesting depths: 13 at depth 0, 1 at depth 1.
- `<table>` nesting depths: 19 at depth 0, no nested tables.

Boundary plan in
[`docs/plans/2026-05-15-doclang-native-rst.md`](../../docs/plans/2026-05-15-doclang-native-rst.md)
covers all observed shapes:

- `heading-N` per top-level `<heading>`
- `page-N` per `<page_break/>` split
- `group-N` per top-level `<group>`; `group-N-M` for the depth-1 case
- `table-N` per `<table>`
- `field_region-N` per `<field_region>`
- `document` fallback

## Cross-reference

- Spec citations live in [[verified-doclang-spec]] (Phase 0 memory).
- Plan: [`docs/plans/2026-05-15-doclang-native-rst.md`](../../docs/plans/2026-05-15-doclang-native-rst.md).
- Fixture README: [`tests/fixtures/doclang/README.md`](../../tests/fixtures/doclang/README.md).
