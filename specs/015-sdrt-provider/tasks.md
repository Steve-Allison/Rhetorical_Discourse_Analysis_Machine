# Tasks: SDRT Provider

**Input**: Design documents from `/specs/015-sdrt-provider/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/native-result.md](contracts/native-result.md)

**Tests**: Required. Causal deterministic tests precede implementation.

## Phase 1: Setup and Authority

- [x] T001 Verify primary SDRT graph and right-frontier authority and record the contract decisions in `research.md`
- [X] T002 Create the production/test package surfaces under `rdam/sdrt/` and `tests/sdrt/`

## Phase 2: User Story 1 — Native SDRS Graph (Priority: P1)

- [X] T003 [US1] Add causal native-model tests for EDU/CDU scope, non-adjacent attachment, coordinating/subordinating edges, and payload fidelity in `tests/sdrt/test_graph.py`
- [X] T004 [US1] Implement the native SDRS models and serialization in `rdam/sdrt/graph.py`

## Phase 3: User Story 2 — Invalid SDRS Refusal (Priority: P2)

- [X] T005 [US2] Extend `tests/sdrt/test_graph.py` with exact-span, reference, membership cycle, relation cycle, connectivity, mixed-class, and right-frontier failures
- [X] T006 [US2] Complete deterministic validation and stable native error classification in `rdam/sdrt/graph.py` and `rdam/sdrt/provider.py`
- [X] T007 [US2] Add deterministic valid/malformed model, retry evidence, and zero-partial-result tests in `tests/sdrt/test_provider.py`

## Phase 4: User Story 3 — Independent Provider (Priority: P3)

- [X] T008 [US3] Implement the declaration, provenance, lazy analyst, and typed outcomes in `rdam/sdrt/provider.py` and exports in `rdam/sdrt/__init__.py`
- [X] T009 [US3] Prove zero-client capability inspection and unrelated-provider independence in `tests/sdrt/test_provider.py`

## Phase 5: Integration and Proof

- [X] T010 Integrate `SdrtProvider` into the supported seven-technique production composition owned by Feature 006
- [X] T011 Run the quickstart, focused tests, lint, typecheck, and production-boundary gate; record exact output in `evidence.md`
- [X] T012 Run `$speckit-analyze`, resolve all findings, and mark the feature complete

## Phase 6: Current Convergence and Delivery

- [X] T013 Add failing non-integer EDU-offset coercion cases in `tests/sdrt/test_graph.py`
- [X] T014 Enforce strict integer source offsets in `rdam/sdrt/graph.py`
- [X] T015 Re-run focused, static, boundary, Markdown, ontology, fast, and complete gates; append exact current results to `specs/015-sdrt-provider/evidence.md`
- [X] T016 Re-run cross-artifact analysis and resolve all findings
- [X] T017 Stage all Feature 015 files, commit, push, and verify local HEAD equals upstream

## Dependencies

T001 precedes original contract work. T003 precedes T004; T005 precedes T006; T007
precedes T008. T010 follows provider completion. T013–T017 are the current sequential
convergence pass.

## Implementation Strategy

Prove the native graph invariants in isolation, add the LLM boundary without weakening them, then expose the provider only through the canonical production composition.
