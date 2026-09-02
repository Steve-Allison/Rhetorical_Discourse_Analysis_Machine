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
| 009 | RST provider adapter | in progress |
| 010 | Repository migration + rename (`rst/`, `Rhetorical_Discourse_Analysis_Machine`, memory paths) | pending — runs reconciled |
| 011 | Dung provider (formal) | pending |
| 012 | IBIS provider (formal) | pending |
| — | Release 6.0.0: tag, build, validate, clean-install, evidence | pending |

## Next step

009: `rst/`? No — the RST adapter is machine-facing code that *consumes* `isanlp_rst`'s
public contract (FR-010). It lives with the machine: `machine/rdam/providers/rst.py`
(`rdam` depends on `isanlp_rst` optionally? No — the adapter is its own package
`rdam_rst` under `rst/` at migration; until migration it lives under `machine/rdam_rst/`
as a separate distribution depending on both `rdam` and `isanlp_rst`). Declaration bound
to `…/rst` with formalisms `rst_tree`/`erst_graph`; capability derived from
`describe_capabilities(parser)` plus the published decision beside the configured release
(`unavailable(withheld|retired)` when no `promote` decision exists); `analyse` runs
`ProductionIngestor(parser).analyse(SourceArtifact.from_text(...))` and returns the
serialized outcome as the opaque native payload.

## Gates that must stay green

`pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`,
`pixi run -e default production-boundary`, `pixi run test-all` before each feature commit.
