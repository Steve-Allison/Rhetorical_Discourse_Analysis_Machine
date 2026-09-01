# Feature 006 — Evidence

This directory holds the verification record for feature 006. Feature 006 ships
governance artifacts rather than code, so its tasks are audits: each file below turns
a contract claim from `../contracts/` into a checked statement about the repository as
it stands, with the inspected file, command, or commit cited.

| File | Proves | Serves |
|---|---|---|
| [`rst-surface-audit.md`](rst-surface-audit.md) | Every row of [`contracts/rst-preservation.md`](../contracts/rst-preservation.md) names a real, currently supported public surface, and the equivalence commands the migration baseline will use exist and are green (or are defined-and-deferred). | SC-002 (T002, T003) |
| [`boundary-audit.md`](boundary-audit.md) | Every top-level repository path maps to exactly one row of [`contracts/architecture-boundaries.md`](../contracts/architecture-boundaries.md), no technique boundary directory exists yet, and the `production-boundary` gate's current state is recorded with its feature-007 extension gap named. | SC-001, SC-003, SC-007 (T004, T005) |
| [`identity-binding-audit.md`](identity-binding-audit.md) | All eight `coe:` identifiers in [`contracts/capability-declaration.md`](../contracts/capability-declaration.md) resolve to concepts in the pushed Central_Configs analytical-frameworks taxonomy. | FR-002 (T006) |
| [`promotion-gap-audit.md`](promotion-gap-audit.md) | For each evidence class in [`contracts/promotion-evidence.md`](../contracts/promotion-evidence.md), whether the existing promotion flow produces it, partially produces it, or lacks it — each verdict citing the file and lines read. | FR-027, SC-006 (T007) |

## Gate results (T010 and closure)

| Gate | Result |
|---|---|
| `pixi run mdlint` | **green** — `Linting: 129 files`, `Summary: 0 issues`, across every evidence and governance document in this feature |
| `pixi run lint` | **green** — `All checks passed!` |
| `pixi run typecheck` | **green** — `0 errors, 0 warnings` |
| `pixi run test` | **green** — includes the three new promotion tests |
| `pixi run test-all` | **green** — `868 passed` |
| `pixi run production-api-contract` | **green** — `244 passed` |
| `pixi run smoke-full-mps` | **PASS** — both releases on MPS (after the smoke-script fix recorded in `rst-surface-audit.md`) |
