# Tasks: Repository Migration

**Input**: Design documents from `/specs/010-repository-migration/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/migration-contract.md](contracts/migration-contract.md)

**Tests**: Required. Identity counterexamples precede any release-identity change.

## Phase 1: Setup

- [X] T001 Reconcile the historical migration ledger into current decision-closed authority in `specs/010-repository-migration/spec.md` and the Feature 010 design artifacts

## Phase 2: Foundational tests

- [X] T002 Add failing project/import/package/version identity counterexamples in `tests/production_boundary/test_identity.py`
- [X] T003 Verify current one-root ownership and artifact exclusion coverage in `tests/integration/test_production_boundary.py` and `tests/production_boundary/`

## Phase 3: User Story 1 — One production distribution (Priority: P1)

**Goal**: Every production and release tool derives one truthful `rdam` identity.

**Independent Test**: identity and production-boundary suites reject every contradictory topology.

- [X] T004 [US1] Enforce safe, PEP 440-valid agreement between project import identity and the sole wheel package in `tools/production_boundary/identity.py`
- [X] T005 [US1] Run identity, ownership, dependency, import, and artifact boundary tests and fix current defects in `tools/production_boundary/` only when demonstrated

## Phase 4: User Story 2 — RST analytical preservation (Priority: P2)

**Goal**: The migration commit is proven analytically equivalent to the immutable pre-migration baseline.

**Independent Test**: the immutable migration comparison reports no analytical differences,
and causal comparator tests reject analytical mutations.

- [X] T006 [US2] Validate immutable migration evidence and causal classification behaviour in `tests/production_boundary/test_rst_baseline.py` and `tools/production_boundary/rst_baseline.py`; do not recapture superseded formats or models

## Phase 5: User Story 3 — Reproducible package and installed boundary (Priority: P3)

**Goal**: Build mechanisms and installed acceptance remain reproducible, derived, and offline-clean.

**Independent Test**: production-boundary and reproducible-build suites pass without changing historical 6.0.0 evidence.

- [X] T007 [US3] Run reproducible-build, artifact-validation, installed-acceptance, source-boundary, and import gates in `tests/production_boundary/` and `tools/production_boundary/`

## Phase 6: Completion

- [X] T008 Run the Feature 010 quickstart, fast and complete suites, Ruff, strict Pyright, Markdown, ontology, boundary, and import gates; record exact output in `specs/010-repository-migration/evidence/gates.md`
- [X] T009 Run cross-artifact consistency analysis, resolve all findings, mark Feature 010 complete in `specs/010-repository-migration/spec.md`, and confirm every task in `specs/010-repository-migration/tasks.md` is checked
- [X] T010 Stage all Feature 010 files, commit them as one coherent change, push the current branch, and verify local HEAD equals its upstream

## Dependencies

T001 establishes current authority. T002 must fail before T004. T003 and T005 certify
the one-package boundary. T006 is independent after authority is fixed. T007 follows the
identity implementation. T008–T010 run sequentially last.

## Implementation strategy

Strengthen the one identity authority first, then prove semantic preservation and
packaging boundaries. Retain historical release evidence and make no new release claim.
