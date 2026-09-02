# Feature 009 — gate results (2026-09-02)

| Gate | Command | Result |
|---|---|---|
| Provider and machine tests, fast | `pixi run pytest tests/rst tests/machine -q -m "not slow"` | **55 passed** |
| Real-release provider tests | `pixi run pytest tests/rst -q -m slow` (CPU, `modernbert-v1-a52b70fbc1a3`) | **3 passed** in 10.18s |
| Fast suite | `pixi run test` | **898 passed**, 80 deselected |
| Ruff | `pixi run lint` (now includes `rst/`) | All checks passed |
| Pyright, strict | `pixi run typecheck` (now includes `rst/`) | see commit — 0 errors after narrowing the opaque payload in the test |
| Boundary inspection | `pixi run -e default production-boundary` | `valid: true`, 101 production modules, 331 files, 0 violations |
