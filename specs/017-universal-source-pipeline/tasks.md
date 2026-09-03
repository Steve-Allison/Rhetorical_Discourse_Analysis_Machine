---

description: "Task list for feature 017 — universal source pipeline"
---

# Tasks: Universal Source Pipeline

**Input**: Design documents from `specs/017-universal-source-pipeline/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included and mandatory. The project rule is that new code lands with its tests in
the same commit, and constitution principle IV requires every completion claim to cite a
check actually run. Every success criterion in the spec has at least one task here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: which user story the task serves (US1..US6)
- Every task names its exact file path

## Path Conventions

Single package at the repository root: production code in `rdam/`, tests in `tests/`,
tooling in `tools/`, specs in `specs/`. All Python runs through pixi.

## How to read the ordering

The stories in this feature are **not independent**, and the tasks do not pretend they are.
They share one relocation and one projection model, so that shared work is in Phase 2
(Foundational) where it blocks everything.

Phase 2 ends with the single most important gate in the feature: **T024**, where RST's
declared requirement reproduces today's policy exactly and `rst-baseline compare` proves the
projection model is behaviour-preserving. Nothing else moves onto the projection model until
that passes. If T024 fails, the design is wrong and stopping there is cheap.

---

## Phase 1: Setup

**Purpose**: capture what must not regress, and build the two fixtures without which two
correctness claims cannot be tested at all.

- [ ] T001 Capture the pre-change RST baseline with `pixi run rst-baseline capture` and commit the evidence file it names
- [ ] T002 Record the pre-change gate state — test count, `production-boundary` verdict, and the seven technique capability states — in `specs/017-universal-source-pipeline/evidence/baseline.md`
- [ ] T003 [P] Create a tabular-evidence fixture in `tests/fixtures/pipeline/tabular-evidence.md` — a short argued document whose only quantitative grounds are inside a Markdown table
- [ ] T004 [P] Create a multi-party transcript fixture in `tests/fixtures/pipeline/transcript.md` with at least three named speakers, one speaker appearing under two spellings, and at least two turns that are deliberately unattributable
- [ ] T005 [P] Create a Docling JSON fixture carrying a table with merged cells and no header row in `tests/fixtures/pipeline/merged-table.docling.json`

**Checkpoint**: the regression baseline is recorded and the fixtures that make SC-004,
SC-007 and SC-008 testable exist.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: relocate ingest, generalise the contracts that lie about their scope, add the
requirement and projection model, and prove it preserves RST behaviour.

**⚠️ CRITICAL**: no user story work begins until T024 passes.

### Relocation (plan step 1)

- [ ] T006 Move `rdam/rst/ingest/` to `rdam/ingest/` with `git mv`, preserving history, including the `contracts/` sub-package
- [ ] T007 Rewrite intra-package imports inside `rdam/ingest/**` from `rdam.rst.ingest` to `rdam.ingest`
- [ ] T008 Create the re-export `rdam/rst/ingest.py` exposing the previous public surface unchanged, so `from rdam.rst.ingest import ...` keeps working (FR-002)
- [ ] T009 [P] Update the import site in `rdam/rst/parser.py`
- [ ] T010 [P] Update the import site in `rdam/rst/provider.py`
- [ ] T011 [P] Update the import site in `rdam/rst/cli.py`
- [ ] T012 [P] Update the import site in `rdam/rst/doclang/__init__.py`
- [ ] T013 [P] Update the import site in `rdam/rst/markdown/__init__.py`
- [ ] T014 Update test imports across `tests/` to `rdam.ingest`, leaving at least one test importing `rdam.rst.ingest` deliberately so the re-export stays covered
- [ ] T015 Add the `rdam.ingest` ownership rule and confirm the dependency direction in `tools/production_boundary/authority.py`; assert the machine layer imports no technique sub-package (FR-003)
- [ ] T016 **Gate**: `pixi run lint && pixi run typecheck && pixi run test && pixi run -e default production-boundary`, then `pixi run rst-baseline compare` — must report zero analytical differences

### Renaming what understates its scope (plan step 2)

- [ ] T017 Rename `PreparedRstDocument` to `PreparedDocument` in `rdam/ingest/contracts/preparation.py`, retaining `PreparedRstDocument` as an alias (FR-006)
- [ ] T018 Rename `ParserCapacity` to `AnalysisCapacity` in `rdam/ingest/contracts/preparation.py`, retaining `ParserCapacity` as an alias, and rename `AnalysisPlan.parser_capacity` to `capacity` with the old attribute preserved
- [ ] T019 [P] Add `tests/ingest/test_contract_aliases.py` proving each alias resolves to the renamed type and that persisted payloads are unchanged
- [ ] T020 **Gate**: full suite plus `rst-baseline compare` — still zero analytical differences

### Requirement and projection contracts (plan step 3)

- [ ] T021 Add `ContentRequirement`, `RepresentationProjection`, and `UnmetRequirement` to `rdam/ingest/contracts/preparation.py` per [data-model.md](data-model.md), including the validator that a requirement admitting `TABLE` or `TABLE_CELL` must declare a `TableRepresentation` projection
- [ ] T022 Add `SourceProjection` to `rdam/ingest/contracts/preparation.py` carrying `projection_identity`, `requirement_id`, `prepared_document`, `analysis_plan`, `transformations`, and `unmet_requirements`
- [ ] T023 Implement `rdam/ingest/projection.py` — `project(inventory, requirement) -> SourceProjection`, a pure deterministic function whose identity is the digest of the inventory identity and the requirement digest (FR-013)

### The behaviour-preservation proof (plan step 4)

- [ ] T024 Declare the RST requirement in `rdam/rst/provider.py` reproducing `DEFAULT_PREPARATION_POLICY.primary_classes` exactly, route RST through `project()`, then run **`pixi run rst-baseline compare`** — **zero analytical differences is the gate for the entire projection model** (FR-005, SC-010). Also run `pixi run test-all` and `pixi run smoke`, because this touches the predictor stack

**Checkpoint**: ingest is the machine's, the contracts name what they model, projections
exist, and RST is provably unchanged. User story work can begin.

---

## Phase 3: User Story 1 — Analyse a Real Document (Priority: P1) 🎯 MVP

**Goal**: the machine accepts a file or bytes, inventories once, and hands every requested
technique its projection.

**Independent Test**: analyse a Markdown file for two techniques and receive two native
results and one preparation receipt — impossible today, because `AggregateRequest` cannot
name a file.

### Tests for User Story 1

- [ ] T025 [P] [US1] Add `tests/machine/test_source_entry_points.py` asserting `for_source` and `for_bytes` build a valid request, that `source_id` equals the digest of the bytes, and that constructing performs no inventory and loads no model (FR-008)
- [ ] T026 [P] [US1] Add `tests/machine/test_all_source_forms.py` asserting every form `describe_capabilities()` reports available is analysable, and that an unavailable form fails typed and staged (SC-001, FR-027)
- [ ] T027 [P] [US1] Add `tests/machine/test_inventory_once.py` asserting inventory and disposition execute exactly once for aggregates naming one through seven techniques (SC-002)

### Implementation for User Story 1

- [ ] T028 [US1] Add `SourceArtifactRef` and the `for_source` / `for_bytes` constructors to `rdam/contracts.py`, with the validator that exactly one of `text` or `source_artifact` is present for a text-analysing request
- [ ] T029 [US1] Add `projection: SourceProjection | None` to `ProviderRequest` in `rdam/contracts.py`, always `None` for structured-input techniques (FR-018)
- [ ] T030 [US1] Add `preparation: PreparationReceipt | None` to `AggregateAnalysis` in `rdam/contracts.py` (FR-011)
- [ ] T031 [US1] Implement inventory-once-then-project in `rdam/machine.py`: inventory the source once per aggregate, compute one projection per distinct requirement digest, and pass each provider its projection (FR-009, SC-003)
- [ ] T032 [US1] Carry the preparation receipt onto the aggregate in `rdam/machine.py`, including one entry per distinct projection produced

**Checkpoint**: a real document can be analysed. This is the MVP — stop and validate here.

---

## Phase 4: User Story 2 — Each Technique Sees What It Can Analyse (Priority: P1)

**Goal**: Toulmin and Walton see the tables their grounds live in; RST still does not.

**Independent Test**: analyse `tests/fixtures/pipeline/tabular-evidence.md` for RST and
Toulmin — the table reaches Toulmin anchored to its cells and does not reach RST.

### Tests for User Story 2

- [ ] T033 [P] [US2] Add `tests/ingest/test_projection_determinism.py` asserting `project()` is pure — identical inputs give an identical `projection_identity` — and that identical requirements share one projection object
- [ ] T034 [P] [US2] Add `tests/ingest/test_projection_invariants.py` asserting, across all six source forms, that every projection's segments are contiguous, reconstruct its prepared text exactly, and name their contributing items and anchors (SC-005)
- [ ] T035 [P] [US2] Add `tests/ingest/test_table_linearisation.py` asserting a linearised table names its `TransformationRecord`, that every admitted unit has a derivation, and that merged-cell and headerless tables from `tests/fixtures/pipeline/merged-table.docling.json` linearise without loss (SC-006)
- [ ] T036 [P] [US2] Add a case to `tests/toulmin/test_provider.py` asserting grounds from the tabular fixture anchor to `TableCoordinateAnchor` (SC-004)
- [ ] T037 [P] [US2] Add a case to `tests/rst/test_provider.py` asserting RST's projection still does not admit tables (SC-004)

### Implementation for User Story 2

- [ ] T038 [US2] Add the table-linearisation kind to `TransformationParameters` in `rdam/ingest/contracts/preparation.py`, with layout and header-repetition options
- [ ] T039 [US2] Implement table linearisation in `rdam/ingest/projection.py`, emitting a `TransformationRecord` per table and preserving cell-level anchors on the produced segments (FR-015, FR-016)
- [ ] T040 [US2] Replace the single global partition in `rdam/ingest/policy.py` with per-requirement admission, keeping `DEFAULT_PREPARATION_POLICY` as RST's requirement
- [ ] T041 [P] [US2] Declare the Toulmin requirement in `rdam/toulmin/provider.py` — admits tables, captions and list items; consumes its projection instead of `request.text`
- [ ] T042 [P] [US2] Declare the Walton requirement in `rdam/walton/provider.py` — same admission plus attribution-bearing content for the expert-opinion scheme
- [ ] T043 [P] [US2] Declare the PDTB requirement in `rdam/pdtb/provider.py` with `normalization="preserve"`, so surface connectives survive verbatim
- [ ] T044 [P] [US2] Declare the SDRT requirement in `rdam/sdrt/provider.py`, admitting turns and setting `requires_speaker_identity=True`
- [ ] T045 [US2] Confirm `rdam/dung/provider.py` and `rdam/ibis/provider.py` declare no requirement and receive no projection (FR-018), with an assertion in `tests/machine/test_inventory_once.py`
- [ ] T046 [US2] **Gate**: each migrated provider's own suite green; native result contracts unchanged

**Checkpoint**: the correctness gap that justified this feature is closed. Toulmin no longer
receives a claim with its evidence removed.

---

## Phase 5: User Story 3 — Dialogue Keeps Its Speakers (Priority: P2)

**Goal**: SDRT knows who said what, and nothing is ever invented.

**Independent Test**: analyse `tests/fixtures/pipeline/transcript.md` — every turn resolves
or is explicitly unresolved, and the deliberately unattributable turns produce zero invented
speakers.

### Tests for User Story 3

- [ ] T047 [P] [US3] Add `tests/ingest/test_speakers.py` asserting `resolved` requires a participant id, `unresolved` forbids one, and `SpeakerCoverage` reconciles exactly (`resolved + unresolved == turns`)
- [ ] T048 [P] [US3] Add a case asserting two participants sharing a display name remain distinct participants
- [ ] T049 [P] [US3] Add a case asserting **zero invented speakers** on the unattributable turns (SC-008)
- [ ] T050 [P] [US3] Add a case to `tests/sdrt/test_provider.py` asserting a provider declaring `requires_speaker_identity` is told when the source cannot supply it, via `unmet_requirements` (FR-019)

### Implementation for User Story 3

- [ ] T051 [US3] Add `SpeakerIdentity` and `SpeakerCoverage` to `rdam/ingest/contracts/source.py` and `preparation.py` per [data-model.md](data-model.md), with the resolution validator
- [ ] T052 [US3] Add `speaker: SpeakerIdentity | None` to `ContentInventoryItem`, populated for `TURN` items and absent otherwise
- [ ] T053 [US3] Implement `rdam/ingest/speakers.py` — source-derived resolution only, never inferred, recording evidence for both resolved and unresolved outcomes (FR-022)
- [ ] T054 [US3] Wire speaker resolution into inventory construction and carry `SpeakerCoverage` into the preparation receipt (FR-021)

**Checkpoint**: SDRT's native object is properly represented.

---

## Phase 6: User Story 4 — One Preparation, Not Seven (Priority: P2)

**Goal**: inventory once, plan per requirement.

**Independent Test**: two providers declaring different capacity units over one source each
receive a plan valid for their own capacity, from one inventory.

### Tests for User Story 4

- [ ] T055 [P] [US4] Add `tests/ingest/test_per_requirement_capacity.py` asserting two requirements with different `CapacityUnit` values each produce a valid plan from one inventory (SC-009)
- [ ] T056 [P] [US4] Add a case asserting subdivision respects each requirement's `boundary_preference` and that recombination stays lossless (FR-025)
- [ ] T057 [P] [US4] Add a case to `tests/machine/test_inventory_once.py` asserting two techniques' results reference the same inventory items by identity (SC-003)

### Implementation for User Story 4

- [ ] T058 [US4] Move planning to per-requirement in `rdam/ingest/subdivision.py`, planning against `requirement.capacity` rather than a single parser capacity (FR-023)
- [ ] T059 [US4] Ensure the capacity estimator names its algorithm and version in every plan, so a plan is reproducible and a change of estimator is visible (FR-024)

**Checkpoint**: preparation cost is paid once and planning is correct for every technique.

---

## Phase 7: User Story 5 — Do Not Pay Twice (Priority: P3)

**Goal**: an unchanged question against an unchanged configuration costs nothing.

**Independent Test**: analyse twice with a cache configured; the second run performs zero
model requests.

### Tests for User Story 5

- [ ] T060 [P] [US5] Add `tests/llm/test_cache.py` asserting a repeat hit performs zero model requests under `ALLOW_MODEL_REQUESTS = False` and returns a semantically identical result (SC-011)
- [ ] T061 [P] [US5] Add one miss case per element of the analytical identity — source, projection, provider id, contract version, model identity, instructions identity (SC-012)
- [ ] T062 [P] [US5] Add cases asserting a corrupt entry, a truncated entry, and a contract-stale entry each cause re-analysis rather than an error or a wrong answer (FR-031)
- [ ] T063 [P] [US5] Add a case asserting nothing is written when no cache directory is configured (FR-030)

### Implementation for User Story 5

- [ ] T064 [US5] Add `AnalyticalIdentity` to `rdam/_llm.py` composing the six elements per [contracts/execution-and-cache.md](contracts/execution-and-cache.md)
- [ ] T065 [US5] Implement cache lookup and store at the model boundary in `rdam/_llm.py`, reusing the `ProductionIngestCache` discipline — content-addressed path, atomic write, integrity validation on load, corrupt entry treated as a miss
- [ ] T066 [US5] Thread an optional cache directory from the machine to model-backed providers in `rdam/machine.py`, defaulting to none

**Checkpoint**: iterating on a document no longer re-bills every call.

---

## Phase 8: User Story 6 — Independent Techniques Do Not Queue (Priority: P4)

**Goal**: elapsed time is the slowest provider, not the sum. **Measure before relying.**

**Independent Test**: four model-backed techniques complete in materially less wall-clock
time than the sum, with identical outcomes.

### Tests for User Story 6

- [ ] T067 [US6] Add the R8 stress test to `tests/stress/test_concurrency_stress.py` running the **real** `PredictorDMRST` and `PredictorUniRST` concurrently, on **CPU and MPS**, asserting byte-identical trees against a sequential baseline — this settles the open risk before anything depends on it
- [ ] T068 [P] [US6] Add `tests/machine/test_concurrency_equivalence.py` asserting concurrent and sequential aggregates over one request have identical semantic digests (SC-014)
- [ ] T069 [P] [US6] Add a case asserting one provider failing concurrently does not disturb another's success (FR-033)
- [ ] T070 [P] [US6] Add a case asserting a non-`ProviderError` exception still propagates as a bug and is not relabelled as a provider failure (FR-036)
- [ ] T071 [P] [US6] Add a wall-clock case asserting four model-backed techniques complete materially faster than the serial sum (SC-013)

### Implementation for User Story 6

- [ ] T072 [US6] Implement bounded `ThreadPoolExecutor` execution in `rdam/machine.py`, keeping outcomes keyed by technique so completion order cannot reach the result (FR-032)
- [ ] T073 [US6] Record the T067 measurement in `specs/017-universal-source-pipeline/evidence/parser-concurrency.md`, and **if and only if** it shows the parser is unsafe, serialise the RST provider behind a lock while the network-bound providers still run concurrently (FR-035)

**Checkpoint**: latency is proportional to the slowest technique, with the parser decision
made on evidence rather than hope.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T074 Implement anchor-based alignment across techniques and add `tests/machine/test_alignment.py` reporting two techniques' findings over one source span **without merging their formalisms** (FR-037, SC-015)
- [ ] T075 [P] Update `README.md` — the machine accepts documents; capability and projection sections
- [ ] T076 [P] Update `CLAUDE.md` — `rdam.ingest` is the machine-level source authority
- [ ] T077 [P] Update `.claude/rules/architecture.md` — package layout and the dependency direction
- [ ] T078 [P] Update the remaining referencing documents under `docs/` and `specs/`
- [ ] T079 Assert zero suppressions: `grep -rn "type: ignore\|pyright: ignore\|noqa" rdam tests tools` must return no matches (SC-017)
- [ ] T080 **Full gates**: `pixi run lint`, `typecheck`, `test`, `mdlint`, `-e default production-boundary`, `ontology-validate`, `test-all`, `smoke`
- [ ] T081 Confirm all seven techniques still report `available` and record the final gate evidence in `specs/017-universal-source-pipeline/evidence/gates.md` (SC-016)
- [ ] T082 Run every scenario in [quickstart.md](quickstart.md) and record the observed results, distinguishing verified from unverified

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Phase 2
- **US2 (Phase 4)**: depends on Phase 3 — providers need projections routed to them
- **US3 (Phase 5)**: depends on Phase 2; T050 additionally needs T044 from US2
- **US4 (Phase 6)**: depends on Phase 3
- **US5 (Phase 7)**: depends on Phase 3 — the cache key includes the projection identity
- **US6 (Phase 8)**: depends on Phase 3
- **Polish (Phase 9)**: depends on all stories

### The one gate that matters most

**T024** is the pivot. It proves the projection model reproduces RST's existing behaviour
exactly, before any other technique moves onto it. Everything from Phase 3 onward assumes it
passed. If it fails, stop — the design is wrong and nothing built on it will be right.

### Honest note on parallelism

The template's parallel-team strategy does not apply. This is one person on one machine
(constitution III), and these stories share a foundation rather than being independent
slices. `[P]` here means *these files do not conflict*, which is useful for batching within a
sitting — not that stories can be staffed concurrently.

### Parallel Opportunities

- T003, T004, T005 — three fixtures, three files
- T009 through T013 — five independent import sites
- T033 through T037 — five test files, no shared state
- T041 through T044 — four providers, four files
- T060 through T063 — cache cases in one new file, written together
- T075 through T078 — four documentation targets

---

## Parallel Example: User Story 2

```bash
# The four provider requirement declarations touch four separate files:
Task: "Declare the Toulmin requirement in rdam/toulmin/provider.py"
Task: "Declare the Walton requirement in rdam/walton/provider.py"
Task: "Declare the PDTB requirement in rdam/pdtb/provider.py"
Task: "Declare the SDRT requirement in rdam/sdrt/provider.py"

# Its five test files are likewise independent:
Task: "tests/ingest/test_projection_determinism.py"
Task: "tests/ingest/test_projection_invariants.py"
Task: "tests/ingest/test_table_linearisation.py"
Task: "tests/toulmin/test_provider.py — tabular grounds case"
Task: "tests/rst/test_provider.py — tables still not admitted"
```

---

## Implementation Strategy

### MVP (through Phase 3)

1. Phase 1 — baseline and fixtures
2. Phase 2 — relocation, contracts, and **T024's proof**
3. Phase 3 — entry points and inventory-once
4. **STOP and VALIDATE**: a real document is analysable by multiple techniques

That is a genuine increment: five of six source forms become reachable and preparation is
shared. But it is **not** a stopping point for correctness — at the end of Phase 3, Toulmin
still receives the RST projection and will still confabulate grounds on tabular evidence.

### The first point at which the machine is correct

**End of Phase 4.** Until each technique receives what its formalism can analyse, the
pipeline is delivering wrong analyses that look right. Phase 4 is not optional polish; it is
the reason this feature was not split.

### Incremental delivery thereafter

Phase 5 (speakers) → Phase 6 (planning) → Phase 7 (cache) → Phase 8 (concurrency) → Phase 9
(alignment and documentation). Each adds value without disturbing what came before, and each
ends with its own gate.

---

## Notes

- Commit after each task or logical group; the tree is green at every checkpoint by design
- Never suppress a checker — make the underlying statement true instead (constitution II)
- Tests use `FunctionModel` with `ALLOW_MODEL_REQUESTS = False`; the real model only behind
  `-m slow`; parser concurrency behind `-m stress`
- `rst-baseline compare` runs at T016, T020, and T024. Zero analytical differences each time
- The regression bar: the recorded baseline test count, all seven techniques `available`,
  and `production-boundary` reporting `valid: true`
