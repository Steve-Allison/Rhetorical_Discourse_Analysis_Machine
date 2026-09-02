# Machine build — running state and handoff

**Started**: 2026-09-02 | **Authority**: `specs/006-rhetorical-discourse-machine/` (spec, contracts, data model) | **Owner ruling**: "Go — archive the runs, version 6.0.0, build it all."

This file is the handoff for the multi-feature build of the Rhetorical Discourse Analysis
Machine. It is updated at every feature boundary. If a session restarts, resume from
"Next step".

## Decisions (owner, 2026-09-02)

- Build the architecture feature 006 specified; 006 itself built nothing.
- Runs: archived (`workbench/experiments/archive/runs/`), none live — FR-026 satisfied,
  record in `specs/010-repository-migration/evidence/`.
- Release version: **6.0.0** (`v5.0.0` at `cc64f81` is published and stays).
- Import names (spec: boundary dirs never importable): `machine/rdam` → `rdam`;
  `dung/rdam_dung`; `ibis/rdam_ibis`; `rst/isanlp_rst` unchanged.
- SDRT / Toulmin / Walton / PDTB: `unavailable(no_promoted_implementation)` — no stubs.

## Feature order and status

| # | Feature | Status |
|---|---|---|
| 007 | Aggregate contract + ontology vendoring + D5 boundary checks | **done** — `specs/007-aggregate-contract/` |
| 008 | Workbench promotion system | **done** — `specs/008-promotion-system/`. All three ModernBERT releases fail the gate (a52b70 withhold: F1 0.198 vs baseline 0.487; 462d68 withhold: unevaluated; e5ea56 retire: fabricated evidence). **Owner ruling needed**: see 008 spec §Consequence |
| 009 | RST provider adapter | **done** — `specs/009-rst-provider-adapter/`; `rst/rdam_rst`. Reports RST `unavailable(withheld)` under the 008 verdicts |
| 010 | Repository migration + rename (`rst/`, `Rhetorical_Discourse_Analysis_Machine`, memory paths) | relocation **done** (baseline equivalent); rename is the final step after the release |
| 011 | Dung provider (formal) | pending |
| 012 | IBIS provider (formal) | pending |
| — | Release 6.0.0: tag, build, validate, clean-install, evidence | pending |

## Next step

010 — repository migration, under the rst-preservation contract:

1. Baseline capture: `test-all`, `production-api-contract`, `smoke` already green today;
   persist serialized outcomes for representative inputs across the six source forms
   into `specs/010-repository-migration/evidence/baseline/`.
2. `git mv isanlp_rst rst/isanlp_rst`; root `pyproject.toml` `packages = ["rst/isanlp_rst"]`
   and sdist include; pixi editable installs unchanged (root pyproject stays); pyright,
   ruff, ownership authority, import walker (`rst/isanlp_rst/x.py` → module `isanlp_rst.x`).
3. Post-migration comparison: identical commands, byte-equal serialized contracts.
4. Packaging gate (D2 `ASSUMED`): `build-production`, `validate-production-artifacts`,
   `production-clean-install`.
5. Identity adoption (D3): rename directory to `Rhetorical_Discourse_Analysis_Machine`,
   git remote and `[project.urls]`, sibling-repo path sweep, `~/.claude/projects/` memory
   migration, verify memory loads.

## Gates that must stay green

`pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`,
`pixi run -e default production-boundary`, `pixi run test-all` before each feature commit.
