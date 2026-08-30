# Retained-content contract fixtures

These fixtures exercise all six `SourceArtifact` forms. `mixed.docling.json`
declares DoclingDocument 1.10.0 and `mixed.dclg` plus
`archive-document.dclg` conform to DocLang 0.7.3. Tests construct the `.dclx`
archive deterministically from `archive-document.dclg` and
`archive-members.json`, avoiding an opaque binary fixture.
