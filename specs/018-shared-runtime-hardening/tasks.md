# Tasks: Shared Runtime Hardening

**Input**: Design documents from `/specs/018-shared-runtime-hardening/`

**Tests**: Required; causal regressions and mutation killers precede certification.

## Phase 1: Authority and Canonical Integrity

- [X] T001 Create Feature 018 decision authority and lock the Feature 017/source-pipeline exclusion
- [X] T002 Add one canonical JSON/I-JSON/SHA-256 kernel and preserve RST/machine byte identity
- [X] T003 Add recursively immutable copied JSON containers and causal mutation/digest tests
- [X] T004 Preserve historical `1.0.0` no-source-revision fixture readability

## Phase 2: Shared Provider Runtime

- [X] T005 Move generic revision resolution to the machine layer with RST compatibility re-exports
- [X] T006 Add composition helpers for provenance, source identity, typed failures, text validation, and LLM conversion
- [X] T007 Require source revision on every newly available declaration and cover all seven production providers
- [X] T008 Standardize PDTB, SDRT, Toulmin, and Walton text/error semantics without changing RST/Dung/IBIS semantics

## Phase 3: LLM Correctness

- [X] T009 Implement canonical bare/explicit/malformed model identity behavior across configuration, capability, clients, IDs, and provenance
- [X] T010 Run transport/output retries and active requests under one async wall-clock timeout with cancellation propagation
- [X] T011 Disable SDK retries, align HTTP timeouts, add direct `httpx2` dependency, and lock lazy agent construction

## Phase 4: Parallel Execution and Cache

- [X] T012 Export and validate `ExecutionPolicy` with four-worker/no-cache defaults
- [X] T013 Execute techniques concurrently with stable upstream/outcome/lineage ordering and native unexpected-exception propagation
- [X] T014 Serialize calls to one provider instance across machines when declared `serialized`, preserving Feature 017's approved concurrent-provider behavior
- [X] T015 Implement complete content-addressed cache identity and dirty/missing/unknown revision bypass
- [X] T016 Implement per-key single flight, atomic owner-only writes, full hit validation, corruption recovery, and success-only caching
- [X] T017 Add causal parallel/cache regression tests for every locked invariant

## Phase 5: Tooling and Documentation

- [X] T018 Add focused shared-runtime test and 100% branch-coverage Pixi tasks
- [X] T019 Add deterministic isolated-workspace mutation tests for all seven critical mutations, with passing unmodified baselines and causal failure verdicts
- [X] T020 Update Feature 006 shared-pattern and architecture ownership documents
- [X] T021 Remove and ignore the Graphify query timestamp
- [X] T022 Refresh Graphify and prove all production nodes resolve under `rdam/` with no obsolete source paths

## Phase 6: Certification

- [ ] T023 Run lint, typecheck, test, stress, shared-runtime coverage/mutation, production API/boundary/import, build/artifact/clean-install, and diff checks against the corrected source
- [X] T024 Run `test-all` if the configured local model releases are available; otherwise record the exact prerequisite
- [ ] T025 Record exact current gate output in `evidence.md` and complete the feature

## Dependencies

T001 precedes implementation. T002-T004 precede cache identity. T005-T011 precede production source-revision coverage. T012-T17 precede mutation/coverage gates. T018-T022 precede final certification. T023-T025 run last.
