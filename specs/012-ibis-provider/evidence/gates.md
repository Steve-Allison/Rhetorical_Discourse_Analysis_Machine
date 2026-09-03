# Feature 012 — gate results (2026-09-02)

| Gate | Command | Result |
|---|---|---|
| Grammar and provider tests | `pixi run pytest tests/ibis -q` (within `tests/dung tests/ibis tests/machine tests/rst -m 'not slow'`) | **88 passed** across the four suites; every 3 × 3 × 8 kind–kind–relation combination matches the gIBIS table |
| Ruff | `pixi run lint` (`rdam` includes `rdam/ibis`) | All checks passed |
| Pyright, strict | `pixi run typecheck` | 0 errors |
| Boundary inspection | `pixi run -e default production-boundary` and `-e production` | `valid: true`, 106 production modules, 0 violations |
| ~~Promotion decision~~ | — | **Gate removed 2026-09-02** by owner ruling, the same day it ran. The correctness arguments and property tests it cited are the rows above and still pass; the decision record itself is deleted. See [006 spec](../../006-rhetorical-discourse-machine/spec.md). |
| Latency (measured, Apple Silicon, CPython 3.14) | `IbisStructure.from_payload` + `deliberation_map`, median of 5 after warm-up | 4 nodes: **0.010 ms**; 124 nodes: **0.283 ms** |
| Live capability | `IbisProvider().declaration` | `available`, provider `rdam.ibis/gibis-grammar-v1`, formalism `ibis_structure`, structured input required |

## Current convergence verification (2026-09-03)

| Gate | Observed result |
|---|---|
| Causal red phase | 6 native-constructor cases failed and 14 existing/new provider cases passed before implementation. |
| IBIS grammar and provider | 20 passed in 0.06 seconds after native node/link/structure validation. |
| Focused Ruff and strict Pyright | All checks passed; 0 errors, 0 warnings, 0 information messages. |
| Repository Ruff | All checks passed. |
| Repository strict Pyright | 0 errors, 0 warnings, 0 information messages. |
| Markdown | 206 files linted, 43 governed exclusions, 0 issues. |
| Ontology | Exit 0; schema and bindings validated and the framework projection matched its vendored authority. The configured ignored `_meta` naming warning remained visible. |
| Source boundary | Default and production environments each reported `valid: true`, 137 production modules/files, and zero violations. |
| Fast suite | 1,333 passed and 134 deselected in 31.91 seconds. |
| Complete suite | 1,411 passed and 56 skipped in 234.43 seconds. |
