# Tasks: Clean Production Codeline Separation

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`

**Tests**: Required by the specification. Boundary negative tests are written before enforcement; parity evidence is frozen before moves.

## Phase 1: Baseline and Setup

**Purpose**: Preserve authoritative pre-split behavior and create the offline namespace without changing runtime semantics.

- [X] T001 Record current branch, tracked/untracked state, Pixi version, Python version, package build metadata, and released model locations in `specs/003-production-codeline-split/evidence/baseline-environment.json`
- [X] T002 Freeze current supported public runtime imports and training-only import paths in `specs/003-production-codeline-split/evidence/public-import-baseline.json`
- [X] T003 Freeze representative raw-text, predefined-EDU, serialization, warning, deterministic-failure, CPU, and available-MPS results in `specs/003-production-codeline-split/evidence/parity-baseline.json`
- [X] T004 Freeze every available released model file identity and loading route in `specs/003-production-codeline-split/evidence/model-baseline.json`
- [X] T005 Create the canonical `offline_workbench/` package structure and document its relationship to retained `research_harness/` in `offline_workbench/README.md`

---

## Phase 2: Foundational Ownership and Boundary Authority

**Purpose**: Create the one causal classification and gate before moving code.

- [X] T006 Add strict ownership, artifact, model-release, promotion, and parity models in `tools/production_boundary/contracts.py`
- [X] T007 Add the exhaustive path and dependency authority in `tools/production_boundary/authority.py`
- [X] T008 Add AST-based direct/transitive import closure and complete-path reporting in `tools/production_boundary/imports.py`
- [X] T009 Add wheel/sdist membership, dependency, cache/local-data, and secret-pattern inspection in `tools/production_boundary/artifacts.py`
- [X] T010 Add the single routine boundary command in `tools/production_boundary/__main__.py`
- [X] T011 [P] Add failing direct, indirect, dependency, forbidden-member, unmatched, and ambiguous negative cases in `tests/test_production_boundary.py`
- [X] T012 Make the valid current target authority and every seeded negative case pass/fail for the right reason using `tests/test_production_boundary.py`

**Checkpoint**: One ownership authority covers every relevant member and dependency; the gate can explain any forbidden path.

---

## Phase 3: User Story 1 - Install and Run Only Production (P1)

**Goal**: The installable artifact contains only production runtime code and dependencies and runs without the repository.

**Independent Test**: Inspect wheel and sdist, install the wheel outside the repository, and execute production imports/routes with no offline source available.

- [X] T013 [US1] Extract legacy-load leaf records from both `isanlp_rst/*_parser/data_manager.py` modules into `isanlp_rst/model_loading/parser_input.py` and adapt `isanlp_rst/universal_parser/inventory.py` without unsafe compatibility imports
- [X] T014 [US1] Move DMRST corpus preparation from `isanlp_rst/dmrst_parser/data_manager.py` and `isanlp_rst/dmrst_parser/src/corpus/` to `offline_workbench/corpus/dmrst/` and update canonical consumers
- [X] T015 [US1] Move UniRST corpus preparation from `isanlp_rst/universal_parser/data_manager.py` and `isanlp_rst/universal_parser/src/corpus/` to `offline_workbench/corpus/unirst/` and update canonical consumers
- [X] T016 [P] [US1] Move EDU training dataset/parsers from `isanlp_rst/segmentation/dataset.py` to `offline_workbench/training/segmentation/dataset.py` and leave `isanlp_rst/segmentation/` runtime-only
- [X] T017 [US1] Split runtime eRST pair encoding from fitting-only dataset behavior across `isanlp_rst/erst/pair_encoding.py` and `offline_workbench/training/erst/dataset.py`; update `isanlp_rst/english/erst/completer.py`
- [X] T018 [US1] Move eRST corpus loading and sampling from `isanlp_rst/erst/corpus.py` and `isanlp_rst/erst/sampling.py` to `offline_workbench/corpus/erst/`; split train-derived relation inventory construction from runtime relation resolution
- [X] T019 [US1] Remove evaluation exports from `isanlp_rst/__init__.py` and move `isanlp_rst/eval/` canonically to `offline_workbench/evaluation/rst/` with test/workbench imports updated
- [X] T020 [US1] Move both `multiple_runs.py` modules and parser `training_manager.py` modules into `offline_workbench/training/parsers/`; retain only inference-required parser architecture/data/metric functions in production
- [X] T021 [US1] Remove offline exports from `isanlp_rst/erst/__init__.py` and `isanlp_rst/segmentation/__init__.py`; add explicit offline migration mapping in `docs/production-offline-boundary.md`
- [X] T022 [US1] Split production and optional-format dependencies from offline dependencies in `pyproject.toml`; define independently solvable Pixi `production` and `offline` environments and their exact commands
- [X] T023 [US1] Restrict Setuptools package discovery/package data in `pyproject.toml` and add `MANIFEST.in` so wheel and sdist publish the same production boundary
- [X] T024 [US1] Add production import and representative route smoke in `tools/production_boundary/production_smoke.py`
- [X] T025 [US1] Build wheel/sdist and make member/dependency inspection pass with zero offline content
- [X] T026 [US1] Install the exact wheel outside the repository and pass core plus optional production smoke routes without source-tree leakage

**Checkpoint**: A clean installed production artifact performs analysis without any offline code, dependency, or repository path.

---

## Phase 4: User Story 2 - One Coherent Offline Workbench (P1)

**Goal**: Every retained corpus/training/evaluation/research command uses the one offline environment and production-owned shared contracts.

**Independent Test**: Recreate the offline environment and start each retained command to its bounded smoke/quarantine point.

- [X] T027 [US2] Update all repository scripts, tests, and `research_harness/` imports to canonical `offline_workbench` paths
- [X] T028 [US2] Add explicit offline command registry and bounded import/dependency/quarantine smoke in `offline_workbench/smoke.py`
- [X] T029 [US2] Migrate nested `research_harness` Pixi tasks/dependencies into the root offline feature, then remove `research_harness/pixi.toml` and `research_harness/pixi.lock`
- [X] T030 [US2] Prove corpus, parser training, segmenter training, eRST training, evaluation, research, and benchmark command categories start correctly or retain their prior explicit quarantine state

**Checkpoint**: There is one offline environment and no duplicated shared implementation.

---

## Phase 5: User Story 3 - Preserve Production Behavior (P1)

**Goal**: The structural split changes no released-model or analysis behavior.

**Independent Test**: Compare the exact clean-install candidate against the frozen baseline and identical model bytes.

- [X] T031 [US3] Add post-split parity runner and strict comparison in `tools/production_boundary/parity.py`
- [X] T032 [US3] Verify public production imports and document only offline import migrations in `docs/production-offline-boundary.md`
- [X] T033 [US3] Compare model selection, prepared input, output serialization, warnings, failures, CPU, and available-MPS results against `parity-baseline.json`
- [X] T034 [US3] Prove every released checkpoint loads without trainer, optimizer, corpus, evaluation, or research modules in `sys.modules`

**Checkpoint**: Zero unexplained parity difference and identical released model bytes.

---

## Phase 6: User Story 4 - Enforce the Boundary Continuously (P1)

**Goal**: One fast local gate prevents regression and reports complete paths.

**Independent Test**: Run the valid gate, then every seeded negative mutation.

- [X] T035 [US4] Wire `production-boundary` as the one routine Pixi task and measure it below ten seconds
- [X] T036 [US4] Prove direct, transitive, offline-dependency, wheel-member, and sdist-member mutations each fail with their complete path
- [X] T037 [US4] Prove a newly added, correctly classified production module is accepted without another module allowlist

---

## Phase 7: User Story 5 - Promote Models Explicitly (P2)

**Goal**: Only verified immutable release bundles cross from offline work into production.

**Independent Test**: Promote a candidate locally, load it in clean production, and reject loose/partial/changed/incompatible inputs.

- [X] T038 [US5] Split eRST bundle creation from validation/loading across `offline_workbench/promotion/erst.py` and `isanlp_rst/erst/checkpoint.py`
- [X] T039 [US5] Add general strict model-release manifest validation and production-store loading in `isanlp_rst/model_loading/release.py`
- [X] T040 [US5] Add atomic local promotion and Pydantic receipt creation in `offline_workbench/promotion/promote.py`
- [X] T041 [US5] Add valid promotion/load and loose, partial, changed, incompatible, symlink, and unpromoted rejection tests in `tests/test_model_promotion.py`
- [X] T042 [US5] Migrate every available released model asset through the promotion boundary byte-for-byte and record receipts in feature evidence

---

## Phase 8: Completion Candidate and Documentation

- [X] T043 Update `README.md` and `docs/production-offline-boundary.md` with one production path, one offline path, ownership rule, model promotion, and feature-002 independence
- [X] T044 Run focused tests, Ruff, Pyright, and full repository tests in dependency-aware order; fix every defect encountered
- [X] T045 Build one fresh wheel/sdist completion candidate and run artifact inspection, clean-install production acceptance, offline smoke, parity, model promotion/rejection, and boundary timing once against those exact bytes
- [X] T046 Record commands, actual outputs, artifact hashes, environment identities, parity receipt, promotion receipts, and any unavailable hardware/model evidence in `specs/003-production-codeline-split/evidence/completion.md`
- [X] T047 Run the Spec Kit convergence audit, append any genuinely unbuilt requirements to this file, implement them, and repeat until zero gap remains

## Dependencies and Execution Order

- T001-T004 precede all moves; T006-T012 precede artifact enforcement.
- US1 establishes the physical/install boundary and precedes US2-US5 final proof.
- T013 precedes removing data managers; T017 precedes moving the eRST dataset; T018 precedes moving eRST relation builders.
- T022-T023 precede T025-T026 and T029.
- T031 depends on baseline T003 and clean artifact T026.
- T038-T040 precede T041-T042.
- T045 uses one exact completion candidate after all implementation and focused checks.

## Implementation Standard

No task is complete because a file moved or a test was edited. Mark `[X]` only after its stated behavior is observed. Do not suppress import/type/lint failures, duplicate implementation between surfaces, regenerate parity expectations, or let an editable source tree count as clean-install proof.

## Phase 9: Convergence

- [X] T048 CRITICAL make ownership classification exhaustive and fail on unmatched or ambiguously matched relevant paths, with causal negative tests, per FR-001 and SC-001 (contradicts)
- [X] T049 Add production-only clean-wheel acceptance for every parser variant, raw/pre-segmented analysis, optional format adapter, hierarchy, serialization/reload, eRST runtime, and available CPU/MPS route per FR-029, FR-030, and SC-005 (partial)
- [X] T050 Make a verified immutable release the sole supported local-model input and reject direct loose `model_dir` loading before predictor construction per FR-032, FR-035, and SC-010 (contradicts)
- [X] T051 Integrate exact wheel/sdist member and metadata-dependency receipts into the completion boundary command per FR-028 and FR-041 (partial)
- [X] T052 Extend pre/post-split parity to provenance, serialization/reload, and representative optional-format behavior per FR-021 and SC-006 (partial)
- [X] T053 Exercise each retained offline command to a bounded start or record its explicit pre-existing quarantine state in a strict receipt per FR-031 and SC-008 (partial)
- [X] T054 Prove core-only and formats-enabled production installs independently with no offline packages available per FR-043 and SC-016 (partial)
