# Tasks: Rhetorical Discourse Analysis Machine Architecture

**Input**: Design documents from `/specs/006-rhetorical-discourse-machine/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: Not requested. Feature 006 ships governance artifacts; its verification is the
audit evidence and gates below, per [quickstart.md](quickstart.md).

**Organization**: Tasks are grouped by user story. Feature 006's own scope boundaries
(spec §Scope Boundaries) exclude file moves, provider implementation, and the aggregate
runtime — where a story's full realisation lives in a named follow-on feature, its 006
tasks are the audits and governance bindings that are implementable now, and the phase
says so explicitly.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US5)

## Phase 1: Setup

**Purpose**: Evidence home for this feature's audits.

- [ ] T001 Create `specs/006-rhetorical-discourse-machine/evidence/` with a one-paragraph `README.md` stating what each evidence file proves and which success criterion it serves

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites for the audits.

No foundational tasks. The spec, plan, contracts, data model, and quickstart are complete
and committed (`79ae5b6`, `9a3dd14`); the canonical framework identities are registered
and pushed in Central_Configs (`9c48ca6`). Nothing blocks the story phases.

**Checkpoint**: Story phases can proceed in any order; all are independent.

---

## Phase 3: User Story 1 — Preserve Trusted RST Analysis (Priority: P1) 🎯 MVP

**Goal**: The preservation contract provably matches the real supported RST surface, so
the migration feature inherits an accurate, disputable-by-no-one baseline definition.

**Independent Test**: `evidence/rst-surface-audit.md` maps every row of
[contracts/rst-preservation.md](contracts/rst-preservation.md) to the actual public
symbol, pixi task, or serialization it names, with zero unmatched rows in either
direction.

### Implementation for User Story 1

- [ ] T002 [US1] Audit the preserved-surface table in `specs/006-rhetorical-discourse-machine/contracts/rst-preservation.md` against the real public API: read `isanlp_rst/__init__.py`, `isanlp_rst/parser.py`, `isanlp_rst/ingest/__init__.py`, `isanlp_rst/contracts/__init__.py`, and `isanlp_rst/cli.py` exports and confirm every contract row names a real, currently supported surface; record the row-by-row result in `specs/006-rhetorical-discourse-machine/evidence/rst-surface-audit.md`
- [ ] T003 [US1] Verify the equivalence commands exist and are green today: run `pixi run test` and `pixi run production-boundary` (both light, no model loads or MPS use), and confirm `test-all`, `production-api-contract`, and `smoke-full-mps` are defined in `pyproject.toml`; record commands and observed results in `specs/006-rhetorical-discourse-machine/evidence/rst-surface-audit.md`. Heavy and MPS-using suites are recorded as defined-and-deferred to the migration feature's baseline capture — the 20-epoch ModernBERT convergence run (task-636) is live on this machine's MPS, and nothing in feature 006 may compete with or touch it (FR-026)

**Checkpoint**: The preservation contract is evidence-backed, not aspirational.

---

## Phase 4: User Story 2 — Production/Workbench Separation (Priority: P2)

**Goal**: Every current top-level path has exactly one owner under the boundary roster,
and the separation gate's current state is recorded with its feature-007 extension gap
named.

**Independent Test**: `evidence/boundary-audit.md` assigns 100% of repository top-level
paths to one roster row (SC-001), shows zero technique directories exist (SC-007), and
records the `production-boundary` run output.

### Implementation for User Story 2

- [ ] T004 [P] [US2] Enumerate every top-level repository path (`ls -d */` plus root files) and assign each to exactly one row of `specs/006-rhetorical-discourse-machine/contracts/architecture-boundaries.md`; flag any path with no owner or two candidate owners as a defect to resolve in the same pass; record the complete table in `specs/006-rhetorical-discourse-machine/evidence/boundary-audit.md`
- [ ] T005 [P] [US2] Run `pixi run production-boundary` and record its output in `specs/006-rhetorical-discourse-machine/evidence/boundary-audit.md`, together with the explicit statement that the workbench-import and distributable-member checks of research decision D5 are acceptance items of the aggregate-contract feature, not yet implemented

**Checkpoint**: SC-001's "zero ambiguous owners" is demonstrated for the current tree.

---

## Phase 5: User Story 3 — Independent Native Analyses (Priority: P3)

**Goal**: The identity binding is verified end-to-end against the live canonical
taxonomy, so no follow-on feature can discover a dangling `coe:` identifier.

**Independent Test**: `evidence/identity-binding-audit.md` shows all eight identifiers
(seven techniques + eRST) named in
[contracts/capability-declaration.md](contracts/capability-declaration.md) resolving to
concepts in the pushed Central_Configs taxonomy.

### Implementation for User Story 3

- [ ] T006 [US3] Resolve every `coe:` identifier listed in `specs/006-rhetorical-discourse-machine/contracts/capability-declaration.md` against `/Users/steveallison/AI_Projects+Code/Central_Configs/ontology/data/domains/narrative/analytical_frameworks.yaml` at origin-pushed `main`; confirm concept ids, labels, and scheme membership match exactly; record the mapping and the Central commit hash in `specs/006-rhetorical-discourse-machine/evidence/identity-binding-audit.md`

**Checkpoint**: FR-002's binding is verified against the live authority, pre-vendoring.

---

## Phase 6: User Story 4 — Promotion on Evidence (Priority: P4)

**Goal**: The promotion-evidence contract is grounded against the promotion machinery
that already exists, so the workbench-promotion-system feature starts from a truthful
gap list instead of a blank page.

**Independent Test**: `evidence/promotion-gap-audit.md` lists, for each evidence class
in [contracts/promotion-evidence.md](contracts/promotion-evidence.md), whether the
existing flow already produces it, partially produces it, or lacks it — every claim
citing the file inspected.

### Implementation for User Story 4

- [ ] T007 [US4] Read `workbench/promotion/modernbert.py`, `workbench/experiments/central_ledger.py`, and the `promote-model` pixi task in `pyproject.toml` in full; map what the existing promotion flow records against each evidence class of `specs/006-rhetorical-discourse-machine/contracts/promotion-evidence.md` (output quality, calibration, latency/resources, compatibility, provenance, licensing); record the per-class verdict with file:line citations in `specs/006-rhetorical-discourse-machine/evidence/promotion-gap-audit.md` as the declared input to the workbench-promotion-system feature

**Checkpoint**: FR-027 honoured — existing artifacts assessed, not presumed complete.

---

## Phase 7: User Story 5 — Evolve One Technique at a Time (Priority: P5)

**Goal**: The machine architecture becomes durable repository governance, so every
future session inherits the boundary rules without reading feature 006.

**Independent Test**: `.claude/rules/architecture.md` and `CLAUDE.md` describe the
machine architecture with the spec and contracts as cited authority; `pixi run mdlint`
green over the changed docs.

### Implementation for User Story 5

- [ ] T008 [US5] Add a "Machine architecture (feature 006)" section to `.claude/rules/architecture.md`: the boundary roster, boundaries-on-promotion rule, no-top-level-import-name rule, identity binding, analysis-only scope, and the follow-on feature order — each rule citing `specs/006-rhetorical-discourse-machine/` as authority rather than restating it as a competing source
- [ ] T009 [US5] Update `CLAUDE.md`'s "Active roadmap" section to record the machine direction: 006 planned, the three architecture features preceding migration, the provider order (Dung → IBIS → SDRT → Toulmin/Walton → PDTB-if-ever), and the FR-026 migration block while workbench runs are live

**Checkpoint**: Governance docs and spec agree, with one authority.

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Gates and cross-artifact closure.

- [ ] T010 [P] Run `pixi run mdlint` and confirm green over all evidence and governance docs added by T001–T009; record the summary line in `specs/006-rhetorical-discourse-machine/evidence/README.md`
- [ ] T011 Run `$speckit-analyze` for cross-artifact consistency across spec.md, plan.md, and tasks.md; resolve any findings in the same pass (FR-025's consistency-check obligation for this feature)
- [ ] T012 Append a completion note to `specs/006-rhetorical-discourse-machine/checklists/requirements.md` recording which success criteria are demonstrated now (SC-001, SC-007 via T004; identity binding via T006) and which are deferred to their named follow-on features with the deferral authority (spec §Scope Boundaries)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first — every audit writes into `evidence/`.
- **Foundational (Phase 2)**: empty; nothing blocks.
- **User Stories (Phases 3–7)**: all independent of each other; any order. T002 before T003 (same evidence file); T004 and T005 parallel until their shared file merge; T008 before T009 (CLAUDE.md cites the rules file).
- **Polish (Phase 8)**: T010 after all doc-writing tasks; T011 after tasks.md is final; T012 last.

### User Story Dependencies

None between stories. Each story's audit stands alone and is independently checkable
against its evidence file.

### Live-run constraint (FR-026)

The 20-epoch ModernBERT training run (task-636) is executing on this machine until its
final evaluation, receipt, promotion, and clean-room certification complete under the
004/005 workstream. Every task in this file is read-only toward `workbench/` (T007 reads
files; nothing writes) and uses no MPS or heavy compute; if in doubt on any task, wait
for the run to finish. Migration remains blocked until the run's artifacts are
reconciled (SC-008).

### Parallel Opportunities

- T004 ∥ T005 (US2, different subject matter, merged into one file at completion).
- Phases 3, 5, 6 are fully independent of each other and of Phase 7.
- T010 is parallel-safe with T012 drafting.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001, then T002–T003.
2. **STOP and VALIDATE**: the preservation contract is evidence-backed — the single
   highest-value output, since every later feature leans on it.

### Incremental Delivery

Each story phase lands as one commit with its evidence file; the feature completes with
T011's consistency analysis and T012's honest criteria accounting. Total effort is
deliberately small: feature 006's heavy lifting was the specification and plan; these
tasks make its claims *verified* instead of *asserted*, which is what separates this
architecture from a diagram.

### Out of Scope (per spec §Scope Boundaries — not tasks, by design)

Repository migration and baseline capture (migration feature, gated by FR-026 — blocked
today by live workbench runs); aggregate contract, ontology vendoring, and the D5
boundary-check extension (aggregate-contract feature); promotion system implementation
(workbench-promotion feature); all provider work (technique features, on workbench
evidence).
