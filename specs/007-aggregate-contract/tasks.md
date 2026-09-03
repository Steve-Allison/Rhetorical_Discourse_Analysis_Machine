# Tasks: Aggregate Analysis Contract

**Input**: Design documents from `/specs/007-aggregate-contract/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/aggregate-contract.md](contracts/aggregate-contract.md)

**Tests**: Required. Causal counterexamples precede each contract fix.

## Phase 1: Setup

- [X] T001 Reconcile the historical multi-package paths and current acceptance ledger in `specs/007-aggregate-contract/spec.md` and `specs/007-aggregate-contract/evidence/gates.md`

## Phase 2: Foundational contract tests

- [X] T002 [P] Add failing structured-input, capability-identity, and lineage-metadata counterexamples in `tests/machine/test_contracts.py`
- [X] T003 [P] Add failing success-envelope and typed-failure identity counterexamples in `tests/machine/test_machine.py`

## Phase 3: User Story 1 — Trustworthy aggregate records (Priority: P1)

**Goal**: Every caller-supplied request, capability record, and lineage reference is internally truthful.

**Independent Test**: `pixi run pytest tests/machine/test_contracts.py -q`

- [X] T004 [US1] Enforce canonical structured-input, capability, and exact lineage identities in `rdam/contracts.py`
- [X] T005 [US1] Verify canonical serialization still rejects duplicate keys, unknown versions, tampering, and non-canonical cross-field identities in `tests/machine/test_contracts.py` and `tests/machine/test_machine.py`

## Phase 4: User Story 2 — Isolated provider execution (Priority: P2)

**Goal**: A provider can neither misidentify a result/failure nor suppress or contaminate another provider's outcome.

**Independent Test**: `pixi run pytest tests/machine/test_machine.py -q`

- [X] T006 [US2] Validate provider result contract version/provenance and typed-failure technique/provider/operation in `rdam/machine.py`
- [X] T007 [US2] Prove the supported seven-provider composition is complete, lazy, no-retry, and independent in `tests/machine/test_machine.py`

## Phase 5: User Story 3 — Canonical identity and production boundary (Priority: P3)

**Goal**: Aggregate identities derive from Central and production remains one clean `rdam` distribution.

**Independent Test**: ontology, framework, import-closure, artifact-membership, and ownership tests pass together.

- [X] T008 [P] [US3] Verify all eight framework identities and seven provider bindings against the vendored Central projection in `tests/machine/test_frameworks.py`
- [X] T009 [P] [US3] Verify one-owner, no-workbench-import, and one-wheel-root rules in `tests/integration/test_production_boundary.py` and `tests/production_boundary/`

## Phase 6: Completion

- [X] T010 Run the Feature 007 quickstart, focused tests, full fast suite, lint, strict typecheck, Markdown, ontology, production-boundary, and import gates; record exact output in `specs/007-aggregate-contract/evidence/gates.md`
- [X] T011 Run cross-artifact consistency analysis, resolve all findings, and mark Feature 007 complete in `specs/007-aggregate-contract/tasks.md`

## Dependencies

T001 establishes current authority. T002 and T003 are parallel failing-test tasks. T004
and T005 complete US1 before T006–T007 complete US2. T008 and T009 are independent after
the contract is stable. T010–T011 run last.

## Implementation strategy

Strengthen persisted/caller records first, then validate provider execution envelopes,
then certify ontology and distribution boundaries. Never reinterpret native payloads.
