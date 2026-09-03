# Tasks: IBIS Provider

**Input**: Design documents from `/specs/012-ibis-provider/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/native-result.md](contracts/native-result.md)

**Tests**: Required; direct-construction counterexamples precede implementation.

## Phase 1: Authority and foundational tests

- [X] T001 Reconcile Feature 012 authority and design artifacts in `specs/012-ibis-provider/`
- [X] T002 Add failing native-constructor and duplicate-link cases in `tests/ibis/test_grammar.py`

## Phase 2: User Story 1 — Native gIBIS validation (Priority: P1)

**Independent Test**: Exhaustive grammar-table and malformed construction tests agree.

- [X] T003 [US1] Enforce node, link, structure, uniqueness, grammar, and attachment invariants in `rdam/ibis/grammar.py`
- [X] T004 [US1] Run the exhaustive IBIS grammar suite and fix demonstrated defects

## Phase 3: User Story 2 — Non-judgemental map (Priority: P2)

**Independent Test**: Representative maps and payload round trips are exact and deterministic.

- [X] T005 [US2] Verify map content, gap observations, ordering, and round trip in `tests/ibis/test_grammar.py`

## Phase 4: User Story 3 — Aggregate IBIS provider (Priority: P3)

**Independent Test**: Supplied, derived, malformed, text-only, and formalism cases remain distinct.

- [X] T006 [US3] Complete declaration, lineage, failure, and formalism coverage in `tests/ibis/test_provider.py`

## Phase 5: Completion

- [X] T007 Run the Feature 012 quickstart plus complete suite, Markdown, ontology, and both environment boundaries; record output in `specs/012-ibis-provider/evidence/gates.md`
- [X] T008 Run cross-artifact analysis, resolve findings, mark complete, and check every task
- [X] T009 Stage all Feature 012 files, commit, push, and verify local HEAD equals upstream

## Dependencies

T001 fixes authority; T002 must fail before T003. T004–T006 validate each independent
story. T007–T009 are sequential completion and delivery.
