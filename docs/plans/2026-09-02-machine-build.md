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
| 008 | Workbench promotion system | in progress |
| 009 | RST provider adapter | pending |
| 010 | Repository migration + rename (`rst/`, `Rhetorical_Discourse_Analysis_Machine`, memory paths) | pending — runs reconciled |
| 011 | Dung provider (formal) | pending |
| 012 | IBIS provider (formal) | pending |
| — | Release 6.0.0: tag, build, validate, clean-install, evidence | pending |

## Next step

008: `workbench/promotion/decision.py` — `PromotionDecision` with the six evidence
classes of the 006 promotion-evidence contract, outcomes `promote | withhold | replace |
retire`, candidate comparison on identical partitions; wire ModernBERT promotion to
require a `promote` decision; author retroactive decisions for the two existing releases
from their real evidence.

## Gates that must stay green

`pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`,
`pixi run -e default production-boundary`, `pixi run test-all` before each feature commit.
