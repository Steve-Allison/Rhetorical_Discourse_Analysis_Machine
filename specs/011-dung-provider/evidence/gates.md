# Feature 011 — gate results (2026-09-02)

| Gate | Command | Result |
|---|---|---|
| Semantics and provider tests | `pixi run pytest tests/dung -q` | **20 passed** (512 exhaustive three-argument frameworks + 200 seeded random frameworks satisfy every invariant) |
| Ruff | `pixi run lint` (now includes `dung/`) | All checks passed |
| Pyright, strict | `pixi run typecheck` (now includes `dung/`) | 0 errors |
| Boundary inspection | `pixi run -e default production-boundary` | `valid: true`, 104 production modules, 0 violations |
| ~~Promotion decision~~ | — | **Gate removed 2026-09-02** by owner ruling, the same day it ran. The correctness arguments and property tests it cited are the rows above and still pass; the decision record itself is deleted. See [006 spec](../../006-rhetorical-discourse-machine/spec.md). |
| Latency (measured, Apple Silicon, CPython 3.14) | `evaluate()` median of 5 after warm-up | 6 arguments: **0.122 ms**; 14 arguments (capacity): **24.055 ms** |
| Live capability | `Machine([DungProvider()]).capabilities()` | `available`, provider `rdam.dung/exhaustive-subset-v1`, formalism `dung_extensions`, structured input required |

## Current convergence verification (2026-09-03)

| Gate | Observed result |
|---|---|
| Causal red phase | 9 new invariant/capacity cases failed and 19 existing cases passed before implementation. |
| Dung semantics and provider | 28 passed in 0.10 seconds after framework-constructor and capacity validation. |
| Focused Ruff and strict Pyright | All checks passed; 0 errors, 0 warnings, 0 information messages. |
| Repository Ruff | All checks passed. |
| Repository strict Pyright | 0 errors, 0 warnings, 0 information messages. |
| Markdown | 200 files linted, 43 governed exclusions, 0 issues after removing six excess terminal blank lines exposed by the first run. |
| Ontology | Exit 0; schema and bindings validated and the framework projection matched its vendored authority. The configured ignored `_meta` naming warning remained visible. |
| Source boundary | Default and production environments each reported `valid: true`, 137 production modules/files, and zero violations. |
| Fast suite | 1,326 passed and 134 deselected in 33.42 seconds. |
| Complete suite | 1,404 passed and 56 skipped in 238.23 seconds. |
