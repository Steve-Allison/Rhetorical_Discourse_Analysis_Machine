# Tasks: Toulmin Provider

**Input**: Design documents from `/specs/013-toulmin-provider/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/native-result.md](contracts/native-result.md)

**Tests**: Required by the specification. Existing tests are audited and extended; new
failure-mode tests precede their implementation fixes.

## Phase 1: Setup

- [X] T001 Record the existing `rdam/toulmin/` and `tests/toulmin/` implementation-to-requirement map in `specs/013-toulmin-provider/evidence.md`

## Phase 2: Foundational

- [X] T002 Add independently observable output-attempt and transport-attempt evidence to the shared extraction contract in `rdam/_llm.py` and its causal tests
- [X] T003 Add failing simulated transient-transport tests for bounded attempts, retry classification, deadline, Retry-After handling, and no implicit provider retries in `tests/toulmin/test_provider.py`
- [X] T004 Implement the shared transient-boundary policy in `rdam/_llm.py` and make the tests from T003 pass without network access

## Phase 3: User Story 1 — Complete Native Layouts (Priority: P1)

**Independent Test**: `pixi run pytest tests/toulmin/test_argument.py -q`

- [X] T005 [US1] Audit and complete core-triad, optional-element, multiple-layout, empty-analysis, and payload round-trip coverage in `tests/toulmin/test_argument.py` and `rdam/toulmin/argument.py`

## Phase 4: User Story 2 — Validated Outcomes (Priority: P2)

**Independent Test**: deterministic model proposals and all typed failures pass in
`tests/toulmin/test_provider.py` with real model requests disabled.

- [X] T006 [US2] Add deterministic valid-proposal and malformed-proposal machine tests to `tests/toulmin/test_provider.py`, including attempt evidence and zero partial results
- [X] T007 [US2] Reconcile `rdam/toulmin/provider.py` with the native-result contract so success and failure preserve complete attempt evidence and model provenance

## Phase 5: User Story 3 — Independent Capability (Priority: P3)

**Independent Test**: declaration inspection constructs no client and withholding Toulmin
changes no unrelated serialized capability.

- [X] T008 [US3] Complete declaration, provenance, lazy-client, machine integration, and provider-independence tests in `tests/toulmin/test_provider.py`

## Phase 6: Polish and Cross-Cutting

- [X] T009 Run the feature quickstart, `pixi run lint`, `pixi run typecheck`, and `pixi run -e default production-boundary`; record exact results in `specs/013-toulmin-provider/evidence.md`
- [X] T010 Run `$speckit-analyze` over Feature 013 and resolve every finding before marking the feature complete

## Dependencies

T001 precedes all edits. T002–T004 are foundational and precede T006–T007. T005 is
independent after T001. T008 follows the provider contract. T009–T010 run last.

## Implementation Strategy

Preserve already-correct native behaviour, write causal tests for the uncovered retry
and evidence contract, fix the shared boundary once, then certify the technique in
isolation and through the machine.
