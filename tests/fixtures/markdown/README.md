# Markdown fixtures

Source files for `tests/test_markdown_*.py`. Three fixtures cover the parse-shape variants the markdown-native entry point claims to handle.

## `minimal.md`

Three paragraphs under one `#` heading. No GFM, no front-matter. The smallest "real" document — one section, no edge cases. Used by tests that need a heading-bounded prose-only corpus.

## `multi-level.md`

Pre-heading paragraph, then `#`, `##`, `###`, `##`, `#` headings each followed by one paragraph. Verifies:

- the pre-heading `document` boundary is emitted
- `section-N` boundaries carry the heading's `level` (1, 2, 3, 2, 1)
- nesting is flat (no hierarchical containment) — sections are siblings, distinguished by `level` metadata

## `gfm-rich.md`

YAML front-matter + every harvest-eligible construct exercised at least once: GFM table, fenced code block, blockquote, list, inline image, raw HTML block. Used by the slow integration test for end-to-end coverage (including the per-table mini-parse in `table_analyses`) and by harvester unit tests for knob gating.

## `golden_two_para.rst.json`

Golden-output regression fixture for `test_golden_output_shape`: the `to_dict()` serialisation of a fixed two-paragraph source parsed with the deterministic stub parser (`tool_version` normalised to `"<normalised>"`). Regenerate only when the wire format deliberately changes — the test exists to catch accidental shape drift.
