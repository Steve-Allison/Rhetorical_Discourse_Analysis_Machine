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
