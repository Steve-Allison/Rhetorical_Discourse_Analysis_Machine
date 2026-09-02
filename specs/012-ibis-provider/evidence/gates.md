# Feature 012 — gate results (2026-09-02)

| Gate | Command | Result |
|---|---|---|
| Grammar and provider tests | `pixi run pytest tests/ibis -q` (within `tests/dung tests/ibis tests/machine tests/rst -m 'not slow'`) | **88 passed** across the four suites; every 3 × 3 × 8 kind–kind–relation combination matches the gIBIS table |
| Ruff | `pixi run lint` (`rdam` includes `rdam/ibis`) | All checks passed |
| Pyright, strict | `pixi run typecheck` | 0 errors |
| Boundary inspection | `pixi run -e default production-boundary` and `-e production` | `valid: true`, 106 production modules, 0 violations |
| Promotion decision | scratch script over the committed tests, run at `6a647b6` | recorded `workbench/promotions/ibis/rdam.ibis-gibis-grammar-v1-promote-2026-09-02.json`; packaged `rdam/ibis/resources/promotion-decision.json`; outcome **promote**, all six classes admissible |
| Latency (measured, Apple Silicon, CPython 3.14) | `IbisStructure.from_payload` + `deliberation_map`, median of 5 after warm-up | 4 nodes: **0.010 ms**; 124 nodes: **0.283 ms** |
| Live capability | `IbisProvider().declaration` | `available`, provider `rdam.ibis/gibis-grammar-v1`, formalism `ibis_structure`, structured input required |
