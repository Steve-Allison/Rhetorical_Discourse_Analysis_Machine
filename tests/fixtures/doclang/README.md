# DocLang test fixtures

42 valid DocLang 0.7 fixtures mirrored from
[`doclang-project/doclang`](https://github.com/doclang-project/doclang/tree/main/tests/data/valid)
`main` branch as of 2026-08-16. Upstream filenames are ``*.dclg`` (0.7
recommended extension); we store them as ``*.dclg.xml`` so existing
test paths keep working. Pulled via the GitHub Contents API; raw
downloads from `raw.githubusercontent.com`.

These are upstream-authored examples covering each element / property /
boundary shape allowed by the spec. We use them to verify the
DocLang-native RST design decisions (see
[`docs/plans/2026-05-15-doclang-native-rst.md`](../../../docs/plans/2026-05-15-doclang-native-rst.md)
Phase 1).

## Licence and provenance

Upstream repository licence: Apache 2.0 (per
[`LICENSE`](https://github.com/doclang-project/doclang/blob/main/LICENSE)
on the upstream repo as at 2026-08-16). Mirrored verbatim — no
modifications. Each file remains attributable to its upstream commit.

To refresh from upstream:

```bash
cd tests/fixtures/doclang
curl -sS https://api.github.com/repos/doclang-project/doclang/contents/tests/data/valid \
  > /tmp/doclang_valid_listing.json
pixi run python -c "
import json, urllib.request
with open('/tmp/doclang_valid_listing.json') as f:
    files = json.load(f)
for e in files:
    urllib.request.urlretrieve(e['download_url'], e['name'])
"
```

## Fixture map (42 files)

| Fixture | Tests what |
|---|---|
| `doclang_example.dclg.xml` | Real-document fragment: table, picture, list, code, heading. No namespace. |
| `ok_comprehensive.dclg.xml` | 48 shapes exercised, namespace present, arbitrary `<head>` children. |
| `ok_no_namespace.dclg.xml` | Namespace absent — XPath dialect sanity check. |
| `ok_thread.dclg.xml` | `<thread>` continuation referenced by `<xref>`. |
| `ok_thread_unused.dclg.xml` | `<thread>` present but never referenced. |
| `ok_xref.dclg.xml` | `<xref thread_id>` lookup. |
| `ok_href.dclg.xml` | `<href uri>` element-head property. |
| `ok_page_break_top_level.dclg.xml` | `<page_break/>` boundary marker. |
| `ok_list_raw_before.dclg.xml` | `<list>` with raw text before first `<ldiv>`. |
| `ok_list_raw_none.dclg.xml` | `<list>` with raw text only inside `<ldiv>`. |
| `ok_list_wrapped_before.dclg.xml` | `<list>` with wrapped `<text>` before first `<ldiv>`. |
| `ok_list_wrapped_none.dclg.xml` | `<list>` with wrapped `<text>` only inside `<ldiv>`. |
| `ok_list_with_unwrapped_text.dclg.xml` | Long list with raw text per `<ldiv>`. |
| `ok_table_raw_before.dclg.xml` | `<table>` raw text before first cell. |
| `ok_table_raw_none.dclg.xml` | `<table>` raw text only inside cells. |
| `ok_table_wrapped_before.dclg.xml` | `<table>` wrapped text before first cell. |
| `ok_table_wrapped_none.dclg.xml` | `<table>` wrapped text only inside cells. |
| `ok_table_rectangular.dclg.xml` | Multi-row OTSL table. |
| `ok_table_class_data.dclg.xml` | `<table>` with `class` attribute. |
| `ok_index.dclg.xml` | `<index>` element. |
| `ok_content_in_virtual_text.dclg.xml` | Raw text inside `<ldiv>` / cells without `<text>` wrapper. |
| `ok_layer.dclg.xml` | `<layer value="background">` and `<layer value="furniture">`. |
| `ok_layer_default.dclg.xml` | `<layer>` omitted (default `body`). |
| `ok_layer_element_head_order.dclg.xml` | Element-head ordering with `<layer>`. |
| `ok_label_element_head.dclg.xml` | `<label value>` element-head property. |
| `ok_marker_location_head.dclg.xml` | `<marker>` + `<location>` head. |
| `ok_location_axis_limits.dclg.xml` | `<location>` x/y axis edges. |
| `ok_location_equal_bounds.dclg.xml` | `<location>` upper/lower at same coord. |
| `ok_location_normalized_allows_raw_desc.dclg.xml` | Normalised location with raw description. |
| `ok_caption_property_head.dclg.xml` | `<caption>` in element-head. |
| `ok_caption_semantic.dclg.xml` | `<caption>` as semantic element. |
| `ok_default_resolution_in_head.dclg.xml` | `<default_resolution width height>` in `<head>`. |
| `ok_default_resolution_width_only.dclg.xml` | Width-only `<default_resolution>`. |
| `ok_field_item_nested_descendant_key_scope.dclg.xml` | `<field_item>` scoping. |
| `ok_picture_with_text.dclg.xml` | `<picture>` with `<text>` child. |
| `ok_picture_with_body.dclg.xml` | `<picture>` with body content. |
| `ok_picture_with_subpictures.dclg.xml` | Nested `<picture>`. |
| `ok_picture_chart.dclg.xml` | `<picture class="chart">` with `<tabular>`. |
| `ok_picture_chemistry_structure.dclg.xml` | Chemistry-shape picture. |
| `ok_picture_src_data_uri.dclg.xml` | `<src uri="data:..."/>` base64 URI. |
| `ok_description_element_head.dclg.xml` | 0.7 `<description>` / `<summary>` element-head (new 2026-08-16 remirror). |
| `ok_namespaced_and_versioned.dclg.xml` | `xmlns` plus `version="0.7"` on `<doclang>`. |
