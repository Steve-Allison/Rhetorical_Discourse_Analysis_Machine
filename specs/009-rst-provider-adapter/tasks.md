# Tasks: RST Provider Adapter

**Input**: Design documents from `/specs/009-rst-provider-adapter/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/rst-adapter.md](contracts/rst-adapter.md)

**Tests**: Required. Release and failure counterexamples precede provider changes.

## Phase 1: Setup

- [X] T001 Reconcile obsolete `rst/rdam_rst` paths and current acceptance evidence in `specs/009-rst-provider-adapter/spec.md` and `specs/009-rst-provider-adapter/evidence/gates.md`

## Phase 2: Foundational tests

- [X] T002 Add a tiny valid immutable DMRST release fixture plus malformed, incompatible, corrupt, and unsafe-release capability counterexamples in `tests/rst/test_provider.py`
- [X] T003 Add failing changed-after-declaration release-load and validated-licence provenance tests in `tests/rst/test_provider.py`

## Phase 3: User Story 1 — Truthful lazy capability (Priority: P1)

**Goal**: Published and local RST configurations report capability truthfully without constructing a parser.

**Independent Test**: `pixi run pytest tests/rst/test_provider.py -q -m "not slow" -k "Configuration or local"`

- [X] T004 [US1] Cache complete local immutable-release validation and parser-family resolution in `rdam/rst/provider.py`
- [X] T005 [US1] Derive local weights licence only from the validated release and preserve cheap published-version capability in `rdam/rst/provider.py`

## Phase 4: User Story 2 — Exact native RST result and failures (Priority: P2)

**Goal**: Valid analysis retains the canonical RST outcome verbatim and expected release/ingest defects remain typed.

**Independent Test**: deterministic guards and envelope tests pass; no model loads for rejected input.

- [X] T006 [US2] Translate expected local release revalidation failures to non-retryable `model_release_invalid` outcomes in `rdam/rst/provider.py`
- [X] T007 [US2] Verify production-ingest failure mapping, formalism selection, exact opaque payload, and aggregate identity agreement in `tests/rst/test_provider.py`

## Phase 5: User Story 3 — Independent aggregate integration (Priority: P3)

**Goal**: RST/eRST capability and execution remain independent inside the seven-provider machine.

**Independent Test**: `pixi run pytest tests/rst tests/machine -q -m "not slow"`

- [X] T008 [US3] Prove RST capability inspection and production-machine construction load no parser/client and withholding RST changes no other capability bytes in `tests/rst/test_provider.py` and `tests/machine/test_machine.py`

## Phase 6: Completion

- [X] T009 Run the Feature 009 quickstart, RST adapter/machine tests, production API contract, fast suite, lint, strict typecheck, Markdown, boundary, and import gates; record exact output in `specs/009-rst-provider-adapter/evidence/gates.md`
- [X] T010 Run cross-artifact consistency analysis, resolve all findings, and mark Feature 009 complete in `specs/009-rst-provider-adapter/tasks.md`

## Dependencies

T001 establishes current authority. T002–T003 precede T004–T006. T007 validates the
completed adapter, T008 validates aggregate independence, and T009–T010 run last.

## Implementation strategy

Make capability truthful before touching runtime translation, preserve the canonical RST
envelope, and prove independence at both adapter and aggregate boundaries.
