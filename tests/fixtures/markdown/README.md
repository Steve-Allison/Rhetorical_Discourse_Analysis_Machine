# Markdown fixtures (historical)

> **Status reconciled 2026-11-15:** Dedicated Markdown harvesting (`rdam.rst.markdown`
> and `SourceForm.MARKDOWN`) was retired in `rdam` `6.1.0` in favour of unified
> `dclq` and DocLang ingestion (`rdam/ingest/contracts/source.py:17-21`). These specimen
> files remain unchanged in the repository as historical fixture data; active document
> fixtures live in [`../doclang/`](../doclang/README.md).

Historical specimen contents:

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
