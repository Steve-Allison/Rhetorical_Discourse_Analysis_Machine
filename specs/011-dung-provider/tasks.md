# Tasks: Dung Abstract Argumentation Provider

**Input**: Design documents from `/specs/011-dung-provider/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/native-result.md](contracts/native-result.md)

**Tests**: Required; invariant counterexamples precede implementation changes.

## Phase 1: Authority and foundational tests

- [X] T001 Reconcile Feature 011 authority and design artifacts in `specs/011-dung-provider/`
- [X] T002 Add failing direct-construction and invalid-capacity counterexamples in `tests/dung/test_semantics.py` and `tests/dung/test_provider.py`

## Phase 2: User Story 1 — Exact supplied-framework evaluation (Priority: P1)

**Independent Test**: Known, exhaustive, seeded, malformed, and over-capacity cases satisfy the formal contract.

- [X] T003 [US1] Enforce identical framework invariants for direct and payload construction in `rdam/dung/semantics.py`
- [X] T004 [US1] Enforce a positive non-boolean exhaustive capacity in `rdam/dung/semantics.py` and `rdam/dung/provider.py`
- [X] T005 [US1] Run the full Dung semantics suite and fix demonstrated formal defects

## Phase 3: User Story 2 — Explicit lineage (Priority: P2)

**Independent Test**: Supplied, derived, and raw-text-only requests retain distinct typed outcomes.

- [X] T006 [US2] Verify supplied/derived lineage and missing-structure behaviour in `tests/dung/test_provider.py`

## Phase 4: User Story 3 — Aggregate provider (Priority: P3)

**Independent Test**: Declaration, provenance, formalism, failures, and native payload pass through `Machine`.

- [X] T007 [US3] Verify declaration and aggregate-machine integration in `tests/dung/test_provider.py`

## Phase 5: Completion

- [X] T008 Run the Feature 011 quickstart plus the complete suite, Markdown, ontology, and production-environment gates; record current output in `specs/011-dung-provider/evidence/gates.md`
- [X] T009 Run cross-artifact consistency analysis, resolve findings, mark the feature complete, and check every task
- [X] T010 Stage all Feature 011 files, commit, push, and verify local HEAD equals its upstream

## Dependencies

T001 fixes authority. T002 must fail before T003–T004. T005 validates exact semantics;
T006 and T007 then verify independent adapter stories. T008–T010 are sequential.
