# Contract: Architecture Boundaries and Ownership

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-002..FR-007, FR-028..FR-030, SC-001, SC-003

Every follow-on feature and every future change to this repository is bound by the rules
below. A violation is a defect, not a style choice.

> **Superseded in part by the owner rulings of 2026-09-02**, recorded in
> [010 §Single package and rename](../../010-repository-migration/spec.md): the
> production boundary is **one package at the repository root, `rdam/`**, and every
> technique is a sub-package of it (`rdam.rst`, `rdam.dung`, `rdam.ibis`),
> shipped as one wheel. The roster's per-technique top-level directories (`rst/`,
> `dung/`, …) and `machine/` no longer exist, and structural rule 2's namespaced
> per-boundary import names are replaced by sub-packages of `rdam`. Everything else
> below stands: no `production/` subdirectory, creation only on implementation (now: a
> sub-package), one framework identity per technique, exactly one `workbench/`, the
> import and distribution rules (enforced from the `rdam` root), the independence
> rules, and the scale rule. `ontology/` remains a repository directory as listed.

## Boundary roster (SC-001 — every owner named, none ambiguous)

| Boundary | Owner of | Exists |
|---|---|---|
| `rst/` | The RST/eRST boundary: the canonical `isanlp_rst` provider package (moves in at migration, feature 010) and the machine-facing adapter `rst/rdam_rst` (import name `rdam_rst`, feature 009) | now (adapter, 2026-09-02); `isanlp_rst` at migration |
| `pdtb/`, `sdrt/`, `toulmin/`, `walton/`, `dung/`, `ibis/` | One technique's provider, native contract, runtime assets, capability declaration | only on that technique's first implotion (FR-002) |
| `machine/` | Aggregate analysis contract (`machine/rdam`, import name `rdam`); cross-provider orchestration later | now (feature 007, 2026-09-02) |
| `ontology/` | Vendored Central distribution (read-only, `ontology/vendor/central-configs/`) + the `rdam` application profile (`ontology/schema/rdam.linkml.yaml`, bindings in `ontology/data/`) | now (feature 007, 2026-09-02) |
| `workbench/` | All candidates, corpora, experiments, training, evaluation, benchmarks, checkpoints, runs (FR-004) | now |
| `tests/` | Production verification, kept distinct from workbench evaluation (FR-007). Owns `tests/offline/research` too: that subtree is workbench-evaluation material located under `tests/`, and FR-007's distinction is satisfied within `tests/` by the subtree split and the separate `research-test` / `research-lint` tasks. One owner, no ambiguity — ruling recorded in [evidence/boundary-audit.md](../evidence/boundary-audit.md) | now |
| `tools/` | Production boundary inspection and release tooling | now |
| `specs/` | Planning material | now |
| `scripts/`, `docs/`, `models/` | Operational scripts, documentation (including `examples/`, the sample `.rs3` inputs and rendered illustrations), local model releases | now |
| `config/` | Repository configuration data for workbench and tests (`config/erst/`). The Central ontology lock moved into the package as a resource (`rst/isanlp_rst/ontology/central.lock.yaml`, feature 010) because production code must not resolve repository paths | now |
| `dist/` | Ignored build output: the release pair rebuilt from a tagged commit by `build-production`, never tracked (the committed record is the evidence JSON under `specs/004-production-api-contract/evidence/`) | now, ignored |
| `graphify-out/` | Generated knowledge-graph artifacts produced by the `graphify` tooling; neither production code nor workbench experimentation | now |
| repository root files | Packaging and lock (`pyproject.toml`, `pixi.lock`, `MANIFEST.in`), licensing (`LICENSE`, `LICENSE_MODELS`), documentation and agent instructions (`README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`), and `cleanup.sh` | now |

## Structural rules

1. A technique boundary IS the production boundary — no `production/` subdirectory
   (FR-003).
2. Boundary directories are never importable Python packages. Packages inside them carry
   namespaced import names (`isanlp_rst` under `rst/`); top-level import names `rst`,
   `pdtb`, `sdrt`, `toulmin`, `walton`, `dung`, `ibis` are never created. (`ibis` is the
   import name of the PyPI Ibis dataframe library; the rule removes the whole class of
   shadowing hazards.)
3. Each boundary declares exactly one canonical framework identity from
   `coe:artifact/narrative/analytical_frameworks_taxonomy` (FR-002; see
   [capability-declaration.md](capability-declaration.md)).
4. Exactly one `workbench/` exists (FR-004). No second experimentation root, per-boundary
   scratch area, or "temporary" candidate directory outside it.

## Import and distribution rules (SC-003)

1. No module inside a technique boundary or `machine/` imports `workbench.*`, directly or
   transitively (FR-006).
2. No distributable artifact (wheel or sdist member) contains a `workbench/` path
   (FR-006).
3. Enforcement: the `tools.production_boundary` inspection (pixi task
   `production-boundary`) is extended with both checks (research D5) and runs in the
   release evidence flow. Zero findings is the pass condition.

## Independence rules

1. Each available technique is independently callable (FR-012); the absence of any other
   technique's provider never blocks it (FR-030).
2. Replacing or withholding one technique's provider changes nothing in any unrelated
   technique's contract, capability result, or direct invocation (FR-030, SC-010).
3. A shared production abstraction is introduced only when at least two proven production
   callers need the same semantic contract with unambiguous ownership (FR-029). The
   aggregate contract in `machine/` is the single approved instance of this rule.

## Scale rule

The architecture serves one person on one local machine (FR-028, SC-011). No feature may
introduce multi-user, distributed, remote-control-plane, or enterprise infrastructure
without a new explicit requirement.
