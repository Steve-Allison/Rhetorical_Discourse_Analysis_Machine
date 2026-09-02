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
| — | Release 6.0.0: tag, build, validate, clean-install, evidence | **done** — tag `v6.0.0` on `d4d59c0`; gates in `specs/010-repository-migration/evidence/gates.md` |
| — | Repository directory rename (`Rhetorical_Discourse_Analysis_Machine`), remote/URL, sibling-repo sweep, memory-path migration | **awaiting Steve's go** (see Next step) |

## Next step

Identity adoption (010 §Identity adoption) — one decision, then mechanical:

1. Steve renames the GitHub repository (`Steve-Allison/isanlp_rst` → the new name) and
   says go. Then: `mv ~/AI_Projects+Code/isanlp_rst ~/AI_Projects+Code/Rhetorical_Discourse_Analysis_Machine`,
   `git remote set-url origin …`, `[project.urls]` in `pyproject.toml`, `pixi install`
   in the new location (the environments carry absolute paths), copy
   `~/.claude/projects/-Users-steveallison-AI-Projects-Code-isanlp-rst/memory/` to the new
   project key, and resume in a fresh session from the new directory.
2. Consumers found by the sweep (read-only, 2026-09-02): `Presentation_Performance_Analyser`
   pins `isanlp_rst = { path = "../isanlp_rst", editable = true }` and imports
   `isanlp_rst` — already broken by the distribution rename; needs
   `rdam = { path = "../Rhetorical_Discourse_Analysis_Machine", editable = true }` and
   `rdam.rst` imports, or a pin to the `v5.0.0` wheel. `Content_Structuring_Machine`
   vendors the 5.0.0 wheel and is unaffected until it chooses to upgrade. Neither is
   edited without Steve's ruling.

## Gates that must stay green

`pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`,
`pixi run -e default production-boundary`, `pixi run -e production production-import-check`,
`pixi run ontology-validate`, `pixi run smoke`, `pixi run rst-baseline compare --baseline specs/010-repository-migration/evidence/baseline`,
`pixi run test-all` before each feature commit.
