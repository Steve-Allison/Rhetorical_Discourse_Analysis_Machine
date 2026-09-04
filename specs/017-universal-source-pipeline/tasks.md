---

description: "Task list for feature 017 — universal source pipeline"
---

# Tasks: Universal Source Pipeline

**Input**: Design documents from `specs/017-universal-source-pipeline/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Included and mandatory. The project rule is that new code lands with its tests in
the same commit, and constitution principle IV requires every completion claim to cite a
check actually run. Every FR and every SC has at least one task.

**Revised 2026-09-03** after cross-artifact analysis. Three capabilities the plan treated as
future work — concurrency, per-provider serialisation, and a result cache — already exist in
the tree. They are not ticked off: an implementation whose safety rests on an untested
assumption is not finished. Phase 8 audits them against this specification instead of
building them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: which user story the task serves (US1..US6)
- Every task names its exact file path

## Path Conventions

Single package at the repository root: production code in `rdam/`, tests in `tests/`,
tooling in `tools/`. All Python runs through pixi.

## How to read the ordering

The stories are **not independent** and the tasks do not pretend they are. They share one
relocation and one projection model, so that shared work is in Phase 2 where it blocks
everything.

Phase 2 ends with the most important gate in the feature: **T029**, where RST's declared
requirement reproduces today's policy exactly and `rst-baseline compare` proves the
projection model is behaviour-preserving. Nothing else moves onto it until that passes. If
T029 fails, the design is wrong and stopping there is cheap.

---

## Phase 1: Setup

**Purpose**: re-measure what must not regress, and build the fixtures without which three
correctness claims cannot be tested at all.

- [X] T001 **Re-measure** the Context table in [spec.md](spec.md) and record the result in `specs/017-universal-source-pipeline/evidence/baseline.md`: ingest module count, `rst.ingest` reference count, `AggregateRequest` entry points, current test count, the seven capability states, and the boundary verdict. **Do not carry forward any number from the specification** — the earlier draft's counts had already gone stale once
- [X] T002 Capture the pre-change RST baseline with `pixi run rst-baseline capture` and commit the evidence file it names. **Execution exception:** capture and repeat comparison verified; no commit under the confirmed no-commit plan. See `evidence/baseline.md`.
- [X] T003 [P] Create a tabular-evidence fixture in `tests/fixtures/pipeline/tabular-evidence.md` — a short argued document whose only quantitative grounds sit inside a Markdown table
- [X] T004 [P] Create a multi-party transcript fixture in `tests/fixtures/pipeline/transcript.md` with at least three named speakers, one speaker under two spellings, and at least two deliberately unattributable turns
- [X] T005 [P] Create a Docling JSON fixture with merged cells and no header row in `tests/fixtures/pipeline/merged-table.docling.json`

**Checkpoint**: the regression bar is measured rather than remembered, and SC-004, SC-007
and SC-008 are testable.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: relocate ingest, generalise the contracts that understate their scope, add the
requirement and projection model, and prove it preserves RST behaviour.

**⚠️ CRITICAL**: no user story work begins until T029 passes.

### Relocation (plan step 1)

- [X] T006 Move `rdam/rst/ingest/` to `rdam/ingest/` with `git mv`, preserving history, including the `contracts/` sub-package
- [X] T007 Rewrite intra-package imports inside `rdam/ingest/**` from `rdam.rst.ingest` to `rdam.ingest`
- [X] T008 Remove `rdam/rst/ingest.py` and its compatibility re-exports; `rdam.ingest` is the only ingest surface (FR-002; owner ruling 2026-09-04). Verify absence in `tests/ingest/test_canonical_surface.py`
- [X] T009 [P] Update the import site in `rdam/rst/parser.py`
- [X] T010 [P] Update the import site in `rdam/rst/provider.py`
- [X] T011 [P] Update the import site in `rdam/rst/cli.py`
- [X] T012 [P] Update the import site in `rdam/rst/doclang/__init__.py`
- [X] T013 [P] Update the import site in `rdam/rst/markdown/__init__.py`
- [X] T014 Update active imports across `tests/`, `tools/`, and `scripts/` to `rdam.ingest`; tests assert the historical module is absent
- [X] T015 Add the `rdam.ingest` ownership rule in `tools/production_boundary/authority.py` and assert the machine layer imports no technique sub-package (FR-001, FR-003)
- [X] T016 Add `tests/ingest/test_persisted_identifiers.py` asserting **directly** that `isanlp_rst.production` is still 2.0.0, that every schema `$id` is byte-identical to its recorded value, and that every runtime contract name is unchanged (FR-004, SC-018). The baseline comparison classifies *analytical* difference and would not catch identifier drift
- [X] T017 Add `tests/ingest/test_inventory_completeness.py` asserting exact coverage across all six source forms — every item classified, dispositioned and accounted, zero valid content discarded (FR-010, SC-019)
- [X] T018 **Gate**: `pixi run lint && pixi run typecheck && pixi run test && pixi run -e default production-boundary`, then `pixi run rst-baseline compare` — zero analytical differences. Reverified after the owner-approved no-compatibility change; see `evidence/baseline.md`

### Renaming what understates its scope (plan step 2)

- [X] T019 Rename `PreparedRstDocument` to `PreparedDocument` in `rdam/ingest/contracts/preparation.py`, with no alias (FR-006)
- [X] T020 Rename `ParserCapacity` to `AnalysisCapacity` in `rdam/ingest/contracts/preparation.py`, with no alias, and use `AnalysisPlan.capacity` in Python and JSON without accepting the old field
- [X] T021 [P] Add `tests/ingest/test_canonical_contracts.py` proving canonical exports, JSON round trips, and rejection of old fields. Historical evidence files remain unchanged; the comparator reports the exact approved rename separately
- [X] T022 **Gate**: full suite plus `rst-baseline compare` — still zero analytical differences. Clean-break full run: 1,571 passed, 56 skipped; latest fast run including the final comparator test: 1,490 passed. See `evidence/baseline.md`

### Requirement and projection contracts (plan step 3)

- [X] T023 Add `ContentRequirement`, `RepresentationProjection`, and `UnmetRequirement` to `rdam/ingest/contracts/preparation.py` per [data-model.md](data-model.md), including the validator that a requirement admitting `TABLE` or `TABLE_CELL` must declare a `TableRepresentation` projection (FR-012)
- [X] T024 Add a `parallel_safety` declaration to `ContentRequirement` or the provider declaration in `rdam/contracts.py`, so a provider states whether it may be invoked concurrently (FR-040)
- [X] T025 Add `SourceProjection` to `rdam/ingest/contracts/preparation.py` carrying `projection_identity`, `requirement_id`, `prepared_document`, `analysis_plan`, `transformations`, and `unmet_requirements`
- [X] T026 Implement `rdam/ingest/projection.py` — `project(inventory, requirement) -> SourceProjection`, pure and deterministic, identified by the inventory identity plus the requirement digest (FR-013)
- [X] T027 [P] Add `tests/machine/test_no_cross_technique_derivation.py` asserting the machine never derives one technique's input from another's output, and that a provider request carries only what the caller declared (FR-038)
- [X] T028 [P] Add `tests/machine/test_execution_boundaries.py` asserting execution stays in-process — no distributed executor, queue, or scheduler is introduced — and that `ExecutionPolicy.max_workers` remains bounded (FR-039)

### The behaviour-preservation proof (plan step 4)

- [X] T029 Declare the RST requirement in `rdam/rst/provider.py` reproducing `DEFAULT_PREPARATION_POLICY.primary_classes` exactly, route RST through `project()`, then run **`pixi run rst-baseline compare`** — **zero unexplained regressions, with source-ID and DocLang table corrections independently proven and separately reported**, per the owner-approved FR-005 / SC-010. Also run `pixi run test-all` and `pixi run smoke`, because this touches the predictor stack. Final proof: 1,713 passed / 56 skipped; smoke 41 passed / 54 skipped; comparison exit 0. See `evidence/gates.md`

**Checkpoint**: ingest is the machine's, the contracts name what they model, projections
exist, the persisted identifiers are pinned, and RST behaviour is preserved apart from
the independently verified, owner-approved source corrections.

**Reopened 2026-09-04:** T029 passed at the projection-foundation checkpoint, but
subsequent correctness repairs change file-origin source identities and DocLang table
geometry. The current comparator rejects those differences. Historical evidence is
unchanged; no baseline exception has been approved. T029 remains open until that conflict
is resolved and the final comparison is rerun. See `evidence/gates.md`.

**Owner decision, 2026-09-04 (supersedes the reopened decision above):** retain both
correctness repairs and the untouched historical baseline. Final T029 acceptance is the
revised FR-005 / SC-010: independently verify each correction, reject every unexplained
regression, and do not describe corrected records as analytically equivalent. The
comparison-only implementation and adversarial tests are named in the plan's final
verification repair. T029 is closed only after the fresh comparison and final gates pass.

**Closed, 2026-09-04:** the source-based comparison, deliberate-corruption tests, fresh
full suite, smoke checks, and remaining gates passed. All **91 of 91** tasks are complete.
Corrected records remain explicitly non-equivalent; historical baseline files are untouched.

---

## Phase 3: User Story 1 — Analyse a Real Document (Priority: P1) 🎯 MVP

**Goal**: the machine accepts a file or bytes, inventories once, and hands every requested
technique its projection.

**Independent Test**: analyse a Markdown file for two techniques and receive two native
results and one preparation receipt — impossible today.

### Tests for User Story 1

- [X] T030 [P] [US1] Add `tests/machine/test_source_entry_points.py` asserting `for_source` and `for_bytes` build a valid request, `source_id` equals the digest of the bytes, and constructing performs no inventory and loads no model (FR-007, FR-008)
- [X] T031 [P] [US1] Add `tests/machine/test_all_source_forms.py` asserting every form `describe_capabilities()` reports available is analysable, and an unavailable form fails typed and staged (SC-001, FR-027)
- [X] T032 [P] [US1] Add to the same file an assertion that **no second source-form list exists** anywhere in the machine layer — the capability report is the sole authority (FR-026)
- [X] T033 [P] [US1] Add `tests/machine/test_inventory_once.py` asserting inventory and disposition execute exactly once for aggregates naming one through seven techniques (FR-009, SC-002)

### Implementation for User Story 1

- [X] T034 [US1] Add `SourceArtifactRef` and the `for_source` / `for_bytes` constructors to `rdam/contracts.py`, with the validator that exactly one of `text` or `source_artifact` is present for a text-analysing request
- [X] T035 [US1] Add `projection: SourceProjection | None` to `ProviderRequest` in `rdam/contracts.py`, always `None` for structured-input techniques (FR-018)
- [X] T036 [US1] Add `preparation: PreparationReceipt | None` to `AggregateAnalysis` in `rdam/contracts.py` (FR-011)
- [X] T037 [US1] Implement inventory-once-then-project in `rdam/machine.py`: inventory the source once per aggregate, compute one projection per distinct requirement digest, pass each provider its projection (FR-009, SC-003)
- [X] T038 [US1] Carry the preparation receipt onto the aggregate in `rdam/machine.py`, with one entry per distinct projection produced

**Checkpoint**: a real document can be analysed. MVP — stop and validate.

---

## Phase 4: User Story 2 — Each Technique Sees What It Can Analyse (Priority: P1)

**Goal**: Toulmin and Walton see the tables their grounds live in; RST still does not.

**Independent Test**: analyse `tests/fixtures/pipeline/tabular-evidence.md` for RST and
Toulmin — the table reaches Toulmin anchored to its cells and does not reach RST.

### Tests for User Story 2

- [X] T039 [P] [US2] Add `tests/ingest/test_projection_determinism.py` asserting `project()` is pure — identical inputs give an identical `projection_identity` — and identical requirements share one projection object (FR-013, SC-003)
- [X] T040 [P] [US2] Add `tests/ingest/test_projection_invariants.py` asserting, across all six source forms, that segments are contiguous, reconstruct the prepared text exactly, and name their contributing items and anchors (FR-014, SC-005)
- [X] T041 [P] [US2] Add `tests/ingest/test_table_linearisation.py` asserting a linearised table names its `TransformationRecord`, every admitted unit has a derivation, and merged-cell and headerless tables linearise without loss (FR-015, SC-006)
- [X] T042 [P] [US2] Add a case to `tests/toulmin/test_provider.py` asserting grounds from the tabular fixture anchor to `TableCoordinateAnchor` (FR-016, SC-004)
- [X] T043 [P] [US2] Add a case to `tests/rst/test_provider.py` asserting RST's projection still does not admit tables, and that each provider receives exactly what its requirement admits (FR-017, SC-004)

### Implementation for User Story 2

- [X] T044 [US2] Add the table-linearisation kind to `TransformationParameters` in `rdam/ingest/contracts/preparation.py`, with layout and header-repetition options
- [X] T045 [US2] Implement table linearisation in `rdam/ingest/projection.py`, emitting a `TransformationRecord` per table and preserving cell-level anchors (FR-015, FR-016)
- [X] T046 [US2] Replace the single global partition in `rdam/ingest/policy.py` with per-requirement admission, keeping `DEFAULT_PREPARATION_POLICY` as RST's requirement
- [X] T047 [P] [US2] Declare the Toulmin requirement in `rdam/toulmin/provider.py` — admits tables, captions and list items; consumes its projection instead of `request.text`
- [X] T048 [P] [US2] Declare the Walton requirement in `rdam/walton/provider.py` — same admission plus attribution-bearing content for the expert-opinion scheme
- [X] T049 [P] [US2] Declare the PDTB requirement in `rdam/pdtb/provider.py` with `normalization="preserve"`, so surface connectives survive verbatim
- [X] T050 [P] [US2] Declare the SDRT requirement in `rdam/sdrt/provider.py`, admitting turns and setting `requires_speaker_identity=True`
- [X] T051 [US2] Confirm `rdam/dung/provider.py` and `rdam/ibis/provider.py` declare no requirement and receive no projection (FR-018), asserted in `tests/machine/test_inventory_once.py`
- [X] T052 [US2] **Gate**: each migrated provider's own suite green; native result contracts unchanged

**Checkpoint**: the correctness gap that justified this feature is closed.

---

## Phase 5: User Story 3 — Dialogue Keeps Its Speakers (Priority: P2)

**Goal**: SDRT knows who said what, and nothing is invented.

**Independent Test**: analyse `tests/fixtures/pipeline/transcript.md` — every turn resolves
or is explicitly unresolved, and the unattributable turns produce zero invented speakers.

### Tests for User Story 3

- [X] T053 [P] [US3] Add `tests/ingest/test_speakers.py` asserting `resolved` requires a participant id, `unresolved` forbids one, and `SpeakerCoverage` reconciles exactly (FR-020, FR-021, SC-007)
- [X] T054 [P] [US3] Add a case asserting two participants sharing a display name remain distinct participants
- [X] T055 [P] [US3] Add a case asserting **zero invented speakers** on the unattributable turns (FR-022, SC-008)
- [X] T056 [P] [US3] Add a case to `tests/sdrt/test_provider.py` asserting a provider declaring `requires_speaker_identity` is told when the source cannot supply it, via `unmet_requirements` (FR-019)

### Implementation for User Story 3

- [X] T057 [US3] Add `SpeakerIdentity` and `SpeakerCoverage` to `rdam/ingest/contracts/source.py` and `preparation.py`, with the resolution validator (FR-020)
- [X] T058 [US3] Add `speaker: SpeakerIdentity | None` to `ContentInventoryItem`, populated for `TURN` items and absent otherwise
- [X] T059 [US3] Implement `rdam/ingest/speakers.py` — source-derived resolution only, never inferred, recording evidence for resolved and unresolved alike (FR-022)
- [X] T060 [US3] Wire speaker resolution into inventory construction and carry `SpeakerCoverage` into the receipt (FR-021)

**Checkpoint**: SDRT's native object is properly represented.

---

## Phase 6: User Story 4 — One Preparation, Not Seven (Priority: P2)

**Goal**: inventory once, plan per requirement.

**Independent Test**: two providers with different capacity units over one source each
receive a plan valid for their own capacity, from one inventory.

### Tests for User Story 4

- [X] T061 [P] [US4] Add `tests/ingest/test_per_requirement_capacity.py` asserting two requirements with different `CapacityUnit` values each produce a valid plan from one inventory (FR-023, SC-009)
- [X] T062 [P] [US4] Add a case asserting subdivision respects each requirement's `boundary_preference` and recombination stays lossless (FR-025)
- [X] T063 [P] [US4] Add a case to `tests/machine/test_inventory_once.py` asserting two techniques' results reference the same inventory items by identity (SC-003)

### Implementation for User Story 4

- [X] T064 [US4] Move planning to per-requirement in `rdam/ingest/subdivision.py`, planning against `requirement.capacity` (FR-023)
- [X] T065 [US4] Ensure the capacity estimator names its algorithm and version in every plan (FR-024)

**Checkpoint**: preparation is paid once and planning is correct for every technique.

---

## Phase 7: User Story 5 — Do Not Pay Twice (Priority: P3)

**Goal**: bring the existing cache up to the analytical identity this specification defines.

**Note**: `rdam/_result_cache.py` and `Machine._cache_key` already exist, single-flighted
and validated on load. This phase closes the gaps rather than building from nothing.

### Tests for User Story 5

- [X] T066 [P] [US5] Add `tests/llm/test_cache.py` asserting a repeat hit performs zero model requests under `ALLOW_MODEL_REQUESTS = False` and returns a semantically identical result (SC-011)
- [X] T067 [P] [US5] Add one miss case per element of the analytical identity — source, **projection**, provider id, contract version, model identity, instructions identity (FR-029, SC-012)
- [X] T068 [P] [US5] Add `tests/llm/test_cache_key_completeness.py` pinning the transitive relationship the current key relies on: changing a provider's `INSTRUCTIONS` **must** change `provenance.source_revision` and therefore the key. A refactor moving instructions out of the digested files would otherwise make stale entries answerable (FR-043)
- [X] T069 [P] [US5] Add cases asserting a corrupt, truncated, or contract-stale entry each cause re-analysis rather than an error or a wrong answer (FR-031)
- [X] T070 [P] [US5] Add a case asserting nothing is written when no cache directory is configured (FR-030)

### Implementation for User Story 5

- [X] T071 [US5] Add the projection identity to `_cache_key` in `rdam/machine.py` so that a change of admitted content or segmentation is a miss, and align the key with the `AnalyticalIdentity` entity in [data-model.md](data-model.md) element for element (FR-028)
- [X] T072 [US5] Document in `rdam/_result_cache.py` which elements of the analytical identity are covered directly and which transitively, referencing the test that pins each

**Checkpoint**: the cache key is correct under the projection model and its completeness is
asserted rather than inherited.

---

## Phase 8: User Story 6 — Independent Techniques Do Not Queue (Priority: P4)

**Goal**: **audit and complete** concurrency that is already shipped.

**Note**: `Machine.analyse` already runs providers in a bounded `ThreadPoolExecutor` with
contextvars propagation, ordered re-assembly, and per-provider locks. None of it has been
measured against the parser, and none of it has been exercised on MPS. Existing is not
finished.

### Tests for User Story 6

- [X] T073 [US6] Add the parser-concurrency stress test to `tests/stress/test_concurrency_stress.py` running the **real** `PredictorDMRST` and `PredictorUniRST` concurrently, on **CPU and MPS**, asserting byte-identical trees against a sequential baseline. **This measures behaviour that is already live** (FR-035)
- [X] T074 [P] [US6] Add `tests/machine/test_concurrency_equivalence.py` asserting independent providers do execute concurrently and in-process, and that concurrent and sequential aggregates over one request have identical semantic digests (FR-032, FR-034, SC-014)
- [X] T075 [P] [US6] Add a case asserting one provider's **typed failure** never suppresses another's success, and a separate case asserting a **non-`ProviderError` bug** propagates natively and is not relabelled — the two are different rules (FR-033, FR-036, FR-042)
- [X] T076 [P] [US6] Add `tests/machine/test_provider_lock_lifetime.py` asserting a provider is not retained after collection, including the path where a provider cannot be weak-referenced (FR-041, SC-020)
- [X] T077 [P] [US6] Add a case asserting no provider is serialised without a `parallel_safety` declaration, and that a provider declaring itself safe is not locked (FR-040, SC-020)
- [X] T078 [P] [US6] Add a wall-clock case asserting four model-backed techniques complete materially faster than the serial sum (SC-013)

### Implementation for User Story 6

- [X] T079 [US6] Replace the blanket lock in `rdam/machine.py` with serialisation driven by each provider's declared `parallel_safety`, so the reader can see which provider needs it and why (FR-040)
- [X] T080 [US6] Close the retention path in `_provider_lock` in `rdam/machine.py`: a provider that cannot be weak-referenced must not be held in a module-global dict for the life of the process (FR-041)
- [X] T081 [US6] State the bug-versus-typed-failure rule explicitly in the `rdam/machine.py` module docstring — a typed failure never suppresses a success; a bug is fail-fast and may abandon in-flight work (FR-042)
- [X] T082 [US6] Record the T073 measurement in `specs/017-universal-source-pipeline/evidence/parser-concurrency.md`, and set the RST provider's declared parallel safety from that evidence (FR-035)

**Checkpoint**: concurrency is not merely present but measured, declared, and leak-free.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T083 Implement anchor-based alignment across techniques and add `tests/machine/test_alignment.py` reporting two techniques' findings over one source span **without merging their formalisms** (FR-037, SC-015)
- [X] T084 [P] Update `README.md` — the machine accepts documents; capability, projection, and execution-policy sections
- [X] T085 [P] Update `CLAUDE.md` — `rdam.ingest` is the machine-level source authority
- [X] T086 [P] Update `.claude/rules/architecture.md` — package layout, dependency direction, execution and cache policy
- [X] T087 [P] Update the remaining referencing documents under `docs/` and `specs/`
- [X] T088 Assert zero suppressions: `grep -rn "type: ignore\|pyright: ignore\|noqa" rdam tests tools` returns no matches (SC-017)
- [X] T089 **Full gates**: `pixi run lint`, `typecheck`, `test`, `mdlint`, `-e default production-boundary`, `ontology-validate`, `test-all`, `smoke`
- [X] T090 Confirm all seven techniques still report `available`, compare against the T001 measurement, and record final evidence in `specs/017-universal-source-pipeline/evidence/gates.md` (SC-016)
- [X] T091 Run every scenario in [quickstart.md](quickstart.md) and record observed results, distinguishing verified from unverified

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Phase 2
- **US2 (Phase 4)**: depends on Phase 3 — providers need projections routed to them
- **US3 (Phase 5)**: depends on Phase 2; T056 additionally needs T050
- **US4 (Phase 6)**: depends on Phase 3
- **US5 (Phase 7)**: depends on Phase 3 — the cache key includes the projection identity
- **US6 (Phase 8)**: independent of the projection work; **T073 may be run first at any time**
- **Polish (Phase 9)**: depends on all stories

### The one gate that matters most

**T029** is the pivot. Its original checkpoint proved the projection model preserved RST's
behaviour before other techniques moved onto it. Its final, owner-approved acceptance
additionally proves the source corrections independently and rejects unexplained regressions.
Everything from Phase 3 onward assumes this gate passes. If it fails, stop.

### The task worth doing out of order

**T073** measures concurrency that is already shipped. It does not depend on any other task
in this feature and it closes a standing correctness debt. Run it early regardless of where
Phase 8 sits in the plan.

### Honest note on parallelism

The template's parallel-team strategy does not apply. One person, one machine
(constitution III), and these stories share a foundation. `[P]` means *these files do not
conflict* — useful for batching within a sitting, not for staffing stories concurrently.

### Parallel Opportunities

- T003, T004, T005 — three fixtures
- T009 through T013 — five independent import sites
- T039 through T043 — five test files
- T047 through T050 — four providers
- T066 through T070 — cache cases
- T074 through T078 — concurrency audit cases
- T084 through T087 — four documentation targets

---

## Implementation Strategy

### Do first, out of sequence

**T073.** Concurrency and per-provider locking are live in `rdam/machine.py` today and have
never been measured against the parser or on MPS. That is a standing debt in the current
tree, independent of this feature.

### MVP (through Phase 3)

Phase 1 → Phase 2 (including **T029's proof**) → Phase 3. **STOP and VALIDATE**: a real
document is analysable by multiple techniques.

Genuine value — five of six source forms become reachable and preparation is shared. But
**not** a stopping point for correctness: at the end of Phase 3, Toulmin still receives the
RST projection and will still confabulate grounds on tabular evidence.

### The first point at which the machine is correct

**End of Phase 4.** Until each technique receives what its formalism can analyse, the
pipeline delivers wrong analyses that look right. Phase 4 is not optional polish; it is the
reason this feature was not split.

### Thereafter

Phase 5 (speakers) → Phase 6 (planning) → Phase 7 (cache) → Phase 8 (concurrency audit) →
Phase 9 (alignment and documentation). Each adds value without disturbing what came before,
and each ends with its own gate.

---

## Notes

- Commit after each task or logical group; the tree is green at every checkpoint by design
- Never suppress a checker — make the underlying statement true instead (constitution II)
- Tests use `FunctionModel` with `ALLOW_MODEL_REQUESTS = False`; the real model only behind
  `-m slow`; parser concurrency behind `-m stress`
- `rst-baseline compare` runs at T018, T022, and T029. T018/T022 preserve their historical
  zero-analytical-difference results; final T029 uses the approved FR-005 / SC-010 proof
- The regression bar is whatever **T001 measures**, not any number written in these documents
