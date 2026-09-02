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
- **Layout (supersedes 006's boundary roster and the earlier import-name plan)**: one
  production package at the repository root, `rdam/`, every technique a sub-package
  (`rdam.rst`, `rdam.dung`, `rdam.ibis`), one wheel. `isanlp_rst` is not a protected
  name ("just call it RST"); no `production/` wrapper; `rdam` is the root name (the full
  `Rhetorical_Discourse_Analysis_Machine` is the repository directory name at the end).
- Persisted contract identifiers (`isanlp_rst.production`, `isanlp_rst.parser/modernbert-v1`,
  `isanlp_rst.build_provenance`, `isanlp_rst.public_surface`, schema `$id`s,
  `ISANLP_RST_ERST_CHECKPOINT`) are kept — **owner ruling needed** on whether they move.
- SDRT / Toulmin / Walton / PDTB: `unavailable(no_promoted_implementation)` — no stubs.

## Feature order and status

| # | Feature | Status |
|---|---|---|
| 007 | Aggregate contract + ontology vendoring + D5 boundary checks | **done** — `specs/007-aggregate-contract/`; now `rdam/` at the root |
| 008 | Workbench promotion system | **done** — `specs/008-promotion-system/`. All three ModernBERT releases fail the gate (a52b70 withhold: F1 0.198 vs baseline 0.487; 462d68 withhold: unevaluated; e5ea56 retire: fabricated evidence). **Owner ruling needed**: see 008 spec §Consequence |
| 009 | RST provider adapter | **done** — `specs/009-rst-provider-adapter/`; now `rdam/rst/provider.py`. Reports RST `unavailable(withheld)` under the 008 verdicts |
| 010 | Repository migration + single-package restructure + rename to `rdam` 6.0.0 | relocation **done** (baseline `equivalent: true`); restructure to one package **done** at `6a647b6` (analytically equivalent, zero analytical differences; both stored releases re-declared compatible with 6.0.0); directory rename is the final step after the release |
| 011 | Dung provider (formal) | **done** — `specs/011-dung-provider/`; re-promoted at `rdam.dung` by decision `rdam.dung-exhaustive-subset-v1-replace-2026-09-02` (outcome replace) |
| 012 | IBIS provider (formal) | **done** — `specs/012-ibis-provider/`; promoted at `rdam.ibis` by decision `rdam.ibis-gibis-grammar-v1-promote-2026-09-02` |
| — | Release 6.0.0: tag, build, validate, clean-install, evidence | pending |
| — | Repository directory rename (`Rhetorical_Discourse_Analysis_Machine`), remote/URL, sibling-repo sweep, memory-path migration | pending, last |

## Next step

Release 6.0.0, then identity adoption:

1. `git tag v6.0.0` on the commit carrying the decisions and docs; `pixi run build-production`
   (writes `dist/6.0.0/` and the evidence JSON under
   `specs/010-repository-migration/evidence/release/`); `pixi run validate-production-artifacts`;
   `pixi run -e production production-artifacts`; `pixi run -e production production-clean-install`
   (full acceptance on `modernbert-v1-a52b70fbc1a3`); commit the evidence.
2. Identity adoption (010 §Identity adoption): rename the directory, update
   `[project.urls]` and the git remote once the GitHub repository is renamed, sweep the
   sibling repositories for path references, migrate
   `~/.claude/projects/-Users-steveallison-AI-Projects-Code-isanlp-rst/` to the new key,
   verify memory loads. Requires a fresh session afterwards (tooling paths).

## Gates that must stay green

`pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`,
`pixi run -e default production-boundary`, `pixi run -e production production-import-check`,
`pixi run ontology-validate`, `pixi run smoke`, `pixi run rst-baseline compare --baseline specs/010-repository-migration/evidence/baseline`,
`pixi run test-all` before each feature commit.
