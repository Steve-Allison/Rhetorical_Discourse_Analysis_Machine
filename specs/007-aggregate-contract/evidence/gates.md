# Feature 007 — gate results (2026-09-02)

| Gate | Command | Result |
|---|---|---|
| Machine and boundary tests | `pixi run pytest tests/machine tests/integration/test_production_boundary.py tests/production_boundary -q` | **65 passed** |
| Fast suite | `pixi run test` | **877 passed**, 77 deselected |
| Ruff | `pixi run lint` (now includes `machine/`) | All checks passed |
| Pyright, strict | `pixi run typecheck` (now includes `machine/`) | 0 errors, 0 warnings |
| Boundary inspection | `pixi run -e default production-boundary` | `valid: true`, 98 production modules, 327 files, 0 violations |
| Ontology | `pixi run ontology-validate` | schema valid; `ProviderBindings` instances valid; projection matches the vendored taxonomy (`linkml lint` warns only about Central's own `_meta` slot and a prefix name; warnings are ignored by design) |
| Production env import check | `pixi run -e production production-import-check` | `valid: true`, `editable_source: true` |
| Markdown | `pixi run mdlint` | 0 issues |

Central distribution vendored from `Central_Configs` at `46056cd` after its own
`ontology-check` (LinkML + SHACL: `Conforms: True`) and `stage-distribution` (53 files).
