# Tasks: Walton Provider

**Input**: Design documents from `/specs/014-walton-provider/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/native-result.md](contracts/native-result.md)

**Tests**: Required and catalogue-exhaustive.

## Phase 1: Setup

- [X] T001 Record the existing `rdam/walton/` and `tests/walton/` requirement map in `specs/014-walton-provider/evidence.md`

## Phase 2: Foundational

- [X] T002 Confirm Feature 013's shared output/transport attempt contract is complete and cover Walton consumption of it in `tests/walton/test_provider.py`

## Phase 3: User Story 1 — Native Scheme Instances (Priority: P1)

**Independent Test**: exhaustive catalogue and exact-role matrix in
`tests/walton/test_schemes.py`.

- [X] T003 [US1] Audit and complete exhaustive scheme identity, name, role, question, valid-instance, missing-role, unknown-role, and blank-role tests in `tests/walton/test_schemes.py`
- [X] T004 [US1] Reconcile the versioned catalogue and exact-role validator in `rdam/walton/schemes.py` with the native-result contract

## Phase 4: User Story 2 — Critical Questions (Priority: P2)

**Independent Test**: none/one/all addressed cases produce the exact open complement for
every scheme.

- [X] T005 [US2] Complete exhaustive addressed/open complement, source-note, duplicate-index, range, and no-invented-answer tests in `tests/walton/test_schemes.py`

## Phase 5: User Story 3 — Independent Evidenced Outcomes (Priority: P3)

**Independent Test**: deterministic model seams cover valid, empty, malformed,
unavailable, and exhausted attempts without a live request.

- [X] T006 [US3] Complete deterministic result, failure, attempt-evidence, capability, provenance, lazy-client, and independence tests in `tests/walton/test_provider.py`
- [X] T007 [US3] Reconcile `rdam/walton/provider.py` with the native-result and shared attempt contracts

## Phase 6: Polish and Cross-Cutting

- [X] T008 Run the feature quickstart, `pixi run lint`, `pixi run typecheck`, and `pixi run -e default production-boundary`; record exact results in `specs/014-walton-provider/evidence.md`
- [X] T009 Run `$speckit-analyze` over Feature 014 and resolve every finding before completion

## Phase 7: Current Convergence and Delivery

- [X] T010 Add failing direct-catalogue and open-question-note counterexamples in `tests/walton/test_schemes.py`
- [X] T011 Enforce native `Scheme` invariants and forbid notes on open critical questions in `rdam/walton/schemes.py`
- [X] T012 Re-run focused, static, boundary, Markdown, ontology, fast, and complete gates; append exact current results to `specs/014-walton-provider/evidence.md`
- [X] T013 Re-run cross-artifact analysis and resolve all findings
- [X] T014 Stage all Feature 014 files, commit, push, and verify local HEAD equals upstream

## Dependencies

T001 precedes the original audit. T002 precedes provider evidence work. T003 precedes
T004; T005 follows the catalogue contract; T006 precedes T007. T010–T014 are the
current sequential convergence pass.

## Implementation Strategy

Prove the whole catalogue rather than examples, inherit the corrected shared transient
boundary, and certify the provider independently and through the machine.
