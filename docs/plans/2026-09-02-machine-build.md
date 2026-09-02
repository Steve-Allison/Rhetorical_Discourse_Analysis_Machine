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
| 007 | Aggregate contract + ontology vendoring + D5 boundary checks | **done** — `specs/007-aggregate-contract/`; now `rdam/` at the root. FR-015 lineage (declared derivations → `ProviderDependencyReference`) completed after the release, `c878619` |
| 008 | Workbench promotion system | **done** — `specs/008-promotion-system/`. All three ModernBERT releases fail the gate (a52b70 withhold: F1 0.198 vs baseline 0.487; 462d68 withhold: unevaluated; e5ea56 retire: fabricated evidence). **Owner ruling needed**: see 008 spec §Consequence |
| 009 | RST provider adapter | **done** — `specs/009-rst-provider-adapter/`; now `rdam/rst/provider.py`. Reports RST `unavailable(withheld)` under the 008 verdicts |
| 010 | Repository migration + single-package restructure + rename to `rdam` 6.0.0 | relocation **done** (baseline `equivalent: true`); restructure to one package **done** at `6a647b6` (analytically equivalent, zero analytical differences; both stored releases re-declared compatible with 6.0.0); directory rename is the final step after the release |
| 011 | Dung provider (formal) | **done** — `specs/011-dung-provider/`; re-promoted at `rdam.dung` by decision `rdam.dung-exhaustive-subset-v1-replace-2026-09-02` (outcome replace) |
| 012 | IBIS provider (formal) | **done** — `specs/012-ibis-provider/`; promoted at `rdam.ibis` by decision `rdam.ibis-gibis-grammar-v1-promote-2026-09-02` |
| — | Release 6.0.0: tag, build, validate, clean-install, evidence | **done** — tag `v6.0.0` on `d4d59c0`; gates in `specs/010-repository-migration/evidence/gates.md` |
| — | Repository directory rename (`Rhetorical_Discourse_Analysis_Machine`), remote/URL, sibling-repo sweep, memory-path migration | **done** 2026-09-02 — GitHub renamed by Steve; directory moved; both pixi environments reinstalled at the new path (`pixi reinstall`, because entry-point scripts carry absolute paths); memory copied to the new project key |
| — | Consumers | `Presentation_Performance_Analyser` migrated to `rdam` / `rdam.rst` (its commit `b52c393`, not pushed); its worker still instantiates the archived `gumrrg` family — a design decision for that project. `Content_Structuring_Machine` vendors the 5.0.0 wheel; unaffected |

## Spec completeness (audited 2026-09-02 after the release)

Every 006 requirement with a buildable artifact is built and proven: FR-001..FR-017,
FR-020..FR-030, SC-001..SC-011. FR-018/FR-019 are governance (nothing to build; no
PDTB/SDRT/Toulmin/Walton code exists in production). The remaining follow-on features —
SDRT, Toulmin, Walton, PDTB providers and cross-provider orchestration — are correctly
unbuilt: FR-025 forbids authoring a provider feature before workbench evidence identifies
a credible candidate, and orchestration is ordered after every provider.

## Next step

None mechanical. Open owner rulings: the RST model gate (008 §Consequence); whether the
persisted contract identifiers move to the `rdam` name (recommendation: no); the shared
analysis store (006 standardised-patterns register; recommendation: keep per-consumer
`cache_directory`); the analyser's move from the archived `gumrrg` family to an
immutable ModernBERT release.

## Gates that must stay green

`pixi run lint`, `pixi run typecheck`, `pixi run test`, `pixi run mdlint`,
`pixi run -e default production-boundary`, `pixi run -e production production-import-check`,
`pixi run ontology-validate`, `pixi run smoke`, `pixi run rst-baseline compare --baseline specs/010-repository-migration/evidence/baseline`,
`pixi run test-all` before each feature commit.
