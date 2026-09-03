# Tasks: PDTB Provider

**Input**: Design documents from `/specs/016-pdtb-provider/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/native-result.md](contracts/native-result.md)

**Tests**: Required. Causal deterministic tests precede implementation.

## Phase 1: Setup and Authority

- [x] T001 Verify the official PDTB-3 relation types, argument rules, signal fields, and sense hierarchy in `research.md`
- [X] T002 Create the production/test package surfaces under `rdam/pdtb/` and `tests/pdtb/`

## Phase 2: User Story 1 — Native PDTB-3 Relations (Priority: P1)

- [X] T003 [US1] Add tests for all seven relation types, multiple senses, discontinuous spans, and Arg1/Arg2 direction in `tests/pdtb/test_relations.py`
- [X] T004 [US1] Implement the exact sense/type enums, native relations, and payload serialization in `rdam/pdtb/relations.py`

## Phase 3: User Story 2 — Exact Native Refusal (Priority: P2)

- [X] T005 [US2] Add span mismatch/overlap, unknown sense, duplicate ID, and type/evidence mismatch tests in `tests/pdtb/test_relations.py`
- [X] T006 [US2] Complete deterministic native and exact-source validation in `rdam/pdtb/relations.py`
- [X] T007 [US2] Add deterministic valid/malformed model, retry evidence, and zero-partial-result tests in `tests/pdtb/test_provider.py`

## Phase 4: User Story 3 — Independent Provider (Priority: P3)

- [X] T008 [US3] Implement declaration, provenance, lazy analyst, and typed outcomes in `rdam/pdtb/provider.py` and exports in `rdam/pdtb/__init__.py`
- [X] T009 [US3] Prove zero-client capability inspection and unrelated-provider independence in `tests/pdtb/test_provider.py`

## Phase 5: Integration and Proof

- [X] T010 Integrate `PdtbProvider` into Feature 006's supported seven-technique production composition
- [X] T011 Run quickstart, focused tests, lint, typecheck, and production-boundary gate; record exact output in `evidence.md`
- [X] T012 Run `$speckit-analyze`, resolve all findings, and mark the feature complete

## Phase 6: Current Contract Convergence

- [x] T013 [US2] Add causal counterexamples for silently normalized span text, coerced offsets, and mutable validated collections in `tests/pdtb/test_relations.py`
- [x] T014 [US2] Preserve proposed quote bytes, require strict integer offsets, and make validated PDTB collections immutable in `rdam/pdtb/relations.py`
- [x] T015 Run the focused PDTB suite and static checks; resolve every failure
- [x] T016 Run all repository certification gates and append exact current proof to `evidence.md`
- [x] T017 Re-run cross-artifact analysis, resolve every finding, and complete the clean delivery audit

## Dependencies

T001 precedes all contract work. T003 precedes T004; T005 precedes T006; T007 precedes T008. T010 follows provider completion. T011–T012 establish the original delivery. T013 precedes T014; T015–T017 run last.

## Implementation Strategy

Freeze and test the official native vocabulary first, make source/evidence invariants causal, then attach the shared LLM boundary and production composition.
