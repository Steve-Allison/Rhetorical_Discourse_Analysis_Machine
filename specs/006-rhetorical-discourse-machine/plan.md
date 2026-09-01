# Implementation Plan: Rhetorical Discourse Analysis Machine Architecture

**Branch**: `006-rhetorical-discourse-machine` | **Date**: 2026-09-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-rhetorical-discourse-machine/spec.md`

> Branch note: the repository works on `master`; the branch name above is the feature
> identifier Spec Kit derives from the feature directory, not a live git branch.

## Summary

Feature 006 is an architecture and governance feature. It produces no code and moves no
files. Its deliverables are the decision-closed target architecture for the
Rhetorical_Discourse_Analysis_Machine: the boundary layout and ownership rules, the
architecture-level data model and contracts every later feature implements against, the
RST-preservation obligations that make the eventual migration provably safe, and the
validation scenarios that measure the spec's success criteria. Implementation of
providers, the aggregate contract, and the physical migration happens in the eleven
follow-on features the spec enumerates, gated exactly as FR-024/FR-025 require.

## Technical Context

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"`; pixi-locked, verified in `pyproject.toml`)

**Primary Dependencies**: hatchling build backend; pixi two-environment topology (`default`/`offline` dev, `production` clean-room); Central_Configs ontology distribution (vendored in feature 007; canonical framework identities registered at Central `f701df7`, amended at `9c48ca6`, `coe:artifact/narrative/analytical_frameworks_taxonomy` — Central retired per-artifact `version` fields estate-wide at `59283fc`, so the taxonomy is identified by `id` and `last_updated`, not a version number; all three commits verified ancestors of `origin/main`)

**Storage**: repository files only (specs, contracts, vendored ontology data); no database

**Testing**: pytest via pixi tasks (`test`, `test-all`, `production-api-contract`); ruff; pyright Strict Mode A; `tools.production_boundary` inspection (existing `production-boundary` pixi task)

**Target Platform**: macOS arm64 (Apple-Silicon-first, MPS-aware, CPU fallback, explicit CUDA paths) — unchanged by this feature

**Project Type**: single-repository architecture/governance feature over an existing production Python library

**Performance Goals**: N/A for this feature. Binding behavioural goal: 100% equivalence of the supported pre-migration RST public surface after eventual migration (SC-002); no inference-performance change is permitted or sought (FR-011)

**Constraints**: `isanlp_rst` import name and public contract preserved across relocation (FR-009); production code never imports `workbench/` (FR-006); boundary directories exist only after first promotion (FR-002); migration blocked while protected workbench runs are live or unreconciled (FR-026 — four untracked ModernBERT run directories and a modified central ledger exist in the working tree today); machine is permanently analysis-only; boundaries bind to canonical `coe:` framework identifiers

**Scale/Scope**: one person, one machine (FR-028, SC-011); seven technique boundaries plus workbench, tests, machine aggregation, and planning material (SC-001); eleven follow-on features (repository migration named as its own feature per analysis finding I1)

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.1.0 before Phase 0; re-evaluated after Phase 1.*

| Principle | Compliance |
|---|---|
| I. Evidence Before Claims | PASS. Every decision in `research.md` cites the evidence inspected this session (file:line, command output, or Central_Configs commit); the one claim that cannot be verified until migration (hatchling `packages` path-mapping behaviour) is marked `ASSUMED` with its verification gate. |
| II. One Production Quality Bar | PASS. This feature ships governance artifacts, not code. The contracts it defines carry the single quality bar forward (e.g. `contracts/architecture-boundaries.md` §import rules); nothing weakens checks or alters trained architecture (FR-011 restated as a contract obligation). |
| III. Solo-Local Simplicity and Scope Fidelity | PASS. The architecture is explicitly single-person/single-machine (FR-028, SC-011); boundary directories are deferred until promotion precisely to avoid speculative structure; no multi-user, distributed, or enterprise machinery appears in any artifact. |
| IV. Honest Verification and Reproducible Evidence | PASS. `quickstart.md` defines runnable validation per success criterion, reusing real pixi gates (`production-boundary`, `production-api-contract`, `test-all`) and defining the pre-migration baseline capture that SC-002 comparison requires. No mocked internal behaviour. |
| V. Canonical Contracts and Current Specifications | PASS. One authority per fact: spec.md owns requirements; this plan derives; framework identity is owned by Central_Configs (`coe:` identifiers referenced, never redefined — Central's consumer contract, README §"Do not redefine"); native technique inventories are provider-owned and explicitly not constrained by Central's profiles. |
| Technical & Distribution Constraints | PASS. Two-environment pixi topology, ModernBERT flagship architecture, CC BY-NC weight licensing, and optional-extra boundaries are untouched; the promotion contract makes licensing a first-class evidence class (FR-021). |

**Post-Phase-1 re-check (2026-09-01)**: all six rows re-verified against the generated
artifacts; no violations. Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-rhetorical-discourse-machine/
├── spec.md              # decision-closed requirements (committed 79ae5b6)
├── checklists/requirements.md
├── plan.md              # this file
├── research.md          # Phase 0: eight resolved decisions
├── data-model.md        # Phase 1: architecture entities, states, validation rules
├── quickstart.md        # Phase 1: validation scenarios per success criterion
├── contracts/
│   ├── architecture-boundaries.md   # layout, ownership, import rules
│   ├── capability-declaration.md    # capability states + coe: identity binding
│   ├── rst-preservation.md          # preserved surface + equivalence obligations
│   ├── promotion-evidence.md        # evidence classes incl. formal techniques
│   └── standardised-patterns.md     # shared-pattern register: authority, adoption, FR-029 triggers
└── tasks.md             # Phase 2 ($speckit-tasks — not created here)
```

### Source Code (repository root)

Target layout this architecture defines. Nothing moves in feature 006; the migration
feature executes it under the rst-preservation contract. Directories marked *(on
promotion)* are approved names that exist only once their technique first promotes a
provider (FR-002); *(feature 007+)* marks structure created by later features.

```text
Rhetorical_Discourse_Analysis_Machine/   # project identity (FR-001); repo renamed at migration
├── rst/
│   └── isanlp_rst/          # canonical RST/eRST provider package — import name unchanged (FR-008/009)
├── machine/                 # aggregate analysis contract + cross-provider orchestration (feature 007+)
├── ontology/                # vendored Central distribution + rdam application profile (feature 007+)
├── pdtb/                    # (on promotion) — expected to remain a name only (PDTB deprioritised)
├── sdrt/                    # (on promotion)
├── toulmin/                 # (on promotion)
├── walton/                  # (on promotion)
├── dung/                    # (on promotion — first provider planned)
├── ibis/                    # (on promotion — second provider planned)
├── workbench/               # the single experimentation home (FR-004) — already exists
├── tests/                   # production verification (FR-007) — already exists
├── tools/                   # production boundary inspection — already exists; extended for SC-003
├── scripts/                 # operational scripts — already exists
├── specs/                   # planning material — already exists
├── docs/                    # documentation — already exists
└── models/                  # local model releases — already exists
```

**Structure Decision**: flat top-level technique boundaries exactly as FR-002 names them,
with `machine/` as the aggregate boundary (research.md D1) and `rst/` receiving the
existing `isanlp_rst` package unmodified (research.md D2). No boundary contains a
`production/` subdirectory (FR-003). Boundary directories are never importable packages;
the packages inside them carry namespaced import names, so top-level import names such as
`ibis` or `rst` are never created (spec Assumptions; `ibis` collides with the PyPI Ibis
dataframe library's import name).

## Complexity Tracking

No constitution violations to justify. Table intentionally empty.
