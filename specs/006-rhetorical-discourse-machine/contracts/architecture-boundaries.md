# Contract: Architecture Boundaries and Ownership

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-002..FR-007, FR-028..FR-030, SC-001, SC-003

Every follow-on feature and every future change to this repository is bound by the rules
below. A violation is a defect, not a style choice.

## Boundary roster (SC-001 — every owner named, none ambiguous)

| Boundary | Owner of | Exists |
|---|---|---|
| `rst/` | The canonical `isanlp_rst` RST/eRST provider package | at migration |
| `pdtb/`, `sdrt/`, `toulmin/`, `walton/`, `dung/`, `ibis/` | One technique's promoted provider, native contract, runtime assets, capability declaration | only on that technique's first promotion (FR-002) |
| `machine/` | Aggregate analysis contract; cross-provider orchestration | feature 007+ |
| `ontology/` | Vendored Central distribution (read-only) + the `rdam` application profile | feature 007+ |
| `workbench/` | All candidates, corpora, experiments, training, evaluation, benchmarks, checkpoints, runs, promotion evidence (FR-004) | now |
| `tests/` | Production verification, kept distinct from workbench evaluation (FR-007) | now |
| `tools/` | Production boundary inspection and release tooling | now |
| `specs/` | Planning material | now |
| `scripts/`, `docs/`, `models/` | Operational scripts, documentation, local model releases | now |

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
