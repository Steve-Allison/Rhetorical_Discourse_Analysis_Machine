# Markdown fixtures

These files exercise the private Markdown loader and the shared `rdam.ingest`
source boundary. Current tests live under `tests/ingest/`, including
`test_markdown_loader.py` and `production_ingest/test_markdown_*.py`.

- `minimal.md`: a heading and short prose paragraphs.
- `multi-level.md`: pre-heading prose and headings at several levels.
- `gfm-rich.md`: front matter, a table, code, blockquote, list, image and raw HTML.
  These constructs enter the complete inventory; each provider's requirements
  determine what is admitted to its analysis. RST does not perform a separate
  table-cell mini-parse.
- `golden_two_para.rst.json`: a retained historical format-specific output,
  not the current v3 canonical ingest schema. Do not regenerate it as a current
  report or use it to infer the public API.

Use the [production ingest guide](../../../docs/production-source-ingest.md) for
current APIs and canonical persistence. Fixture input contents remain unchanged.
