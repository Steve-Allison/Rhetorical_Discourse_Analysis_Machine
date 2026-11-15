# Retained-content contract fixtures

These fixtures exercise the four active `SourceArtifact` forms (`text`, `edus`,
`doclang_xml`, `doclang_archive`; `rdam/ingest/contracts/source.py:17-21`).
`mixed.dclg` and `archive-document.dclg` conform to DocLang, and tests construct
the `.dclx` archive deterministically from `archive-document.dclg` and
`archive-members.json`, avoiding an opaque binary fixture. `mixed.docling.json`
and `mixed.md` remain preserved on disk as historical specimens after raw Docling
JSON and Markdown harvesting were retired in `rdam` `6.1.0`.
