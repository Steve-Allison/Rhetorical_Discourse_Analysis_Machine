# Source Specification Currency Evidence

**Feature**: `004-production-api-contract`

**Checked**: 2026-08-29

**Disposition**: PASS — no Docling or DocLang remediation is required before
Feature 004 implementation.

## Docling

| Evidence | Observed value |
|---|---|
| Current PyPI release | `docling-core 2.92.0`, released 2026-08-19 |
| Project constraint | `docling-core>=2.92,<2.93` |
| Locked and installed release | `2.92.0` |
| Current `DoclingDocument` schema version | `1.10.0` |
| Local fixture schema versions | Four fixtures, all `1.10.0` |
| Fixture load result | All four accepted by `DoclingDocument.load_from_json()` |

Primary release evidence is the
[`docling-core` 2.92.0 PyPI record](https://pypi.org/project/docling-core/2.92.0/),
which identifies upstream source commit
[`bfbeb795e81b7de9be9d1908389dd9b93d770d31`](https://github.com/docling-project/docling-core/commit/bfbeb795e81b7de9be9d1908389dd9b93d770d31).
Runtime inspection in the locked `default` environment established:

```text
docling-core=2.92.0
DoclingDocument.CURRENT_VERSION=1.10.0
iterate_items=(self, root=None, with_groups=False, traverse_pictures=False,
               page_no=None, included_content_layers=None, _level=0)
ContentLayer=['body', 'furniture', 'background', 'invisible', 'notes']
```

The production inventory must continue to pass an explicit
`included_content_layers` set when complete layer coverage is required;
`iterate_items()` does not make that intent implicit. The package version and
embedded `DoclingDocument.version` are separate authorities and must not be
conflated.

## DocLang

| Evidence | Observed value |
|---|---|
| Current PyPI release | `doclang 0.7.3`, released 2026-07-15 |
| Project constraint | `doclang[schematron-saxon]>=0.7.3,<0.8` |
| Locked and installed release | `0.7.3` |
| Upstream valid fixture inventory | 42 files, all `.dclg` |
| Local fixture parity | 42 files byte-identical to upstream HEAD |
| Validation result | 42/42 accepted with namespace-aware invocation |

Primary release and optional-extra evidence is the
[`doclang` 0.7.3 PyPI record](https://pypi.org/project/doclang/0.7.3/).
The current specification is
[`spec.md`](https://github.com/doclang-project/doclang/blob/main/spec.md), and
the mirrored valid fixtures match upstream commit
[`6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`](https://github.com/doclang-project/doclang/commit/6d3b3d3c195d1f63333c5c5fcba8da17937a33bd).

Runtime inspection confirmed the current validation signature:

```text
validate(xml_file, *, allow_empty_namespace=False, xsd_only=False,
         schematron_only=False, schematron=None) -> None
```

The full validator requires the `schematron-saxon` extra. Namespace-free valid
fixtures require `allow_empty_namespace=True`; namespaced fixtures use the
default. Current element-head ordering, document layers, notes, captions,
tables, lists, cross-references, and the `.dclg` extension are represented in
the byte-identical upstream fixture set.

## Verification

Commands were run from the repository root through the locked Pixi
environment. The focused conformance command completed with:

```text
47 passed in 3.50s
```

The 47 tests comprise the 42 DocLang fixture validations plus current upstream
Docling/DocLang ingest conformance checks. No package, lock, fixture, harvest,
or source-contract change is required by this currency gate.
