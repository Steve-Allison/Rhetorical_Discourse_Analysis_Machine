# Research: Clean Production Codeline Separation

## 1. One root Pixi workspace and lock, two named environments

**Decision**: Define `production` and `offline` environments in root `pyproject.toml` using Pixi features. Production installs only runtime dependencies; offline adds test, training, evaluation, and research dependencies. Remove the nested `research_harness` manifest and lock after command parity.

**Rationale**: Current Pixi supports feature-scoped dependencies/tasks and multiple named environments in one manifest, including omission of default features. This gives independent environment resolution with one lock and no nested-authority drift.

**Rejected**: Separate root/workbench manifests; containers; one combined development environment.

## 2. Production owns shared runtime contracts

**Decision**: Keep request/result/serialization contracts, runtime configurations, safe load-time records, and minimal model architecture definitions in `isanlp_rst`. Offline code imports them. Experiment records, corpus receipts, fitting state, metrics, and selection records live offline.

**Rationale**: Released-model loading is production behavior. Moving load-required classes offline reverses the dependency; copying them creates drift. Production ownership avoids a third distribution.

**Rejected**: A third shared package; production compatibility imports into offline code; duplicated model definitions.

## 3. Classify by executable use, not historical names

**Decision**: Runtime predictor imports and safe checkpoint reconstruction determine production ownership. Relation-inventory import and parser-input leaf records stay production even if historically embedded in data managers. Trainers, corpus conversion, prepared-example loading, optimizers, fitting metrics, and run orchestration move offline.

**Rationale**: Existing `data_manager.py`, `dataset.py`, `relations.py`, and parser trees contain mixed responsibilities. Names are not evidence.

**Rejected**: Whole-folder exclusion; keeping mixed modules merely because entry points can be hidden.

## 4. One ownership authority drives every gate

**Decision**: Add one declarative authority whose ordered path and dependency rules classify every member as `production`, `offline`, `repository`, or `generated`. Derive the production source set from build configuration and validate actual archives. Report the complete import chain to forbidden targets.

**Rationale**: Separate source, wheel, and sdist allowlists would drift. Rules fail on unmatched or ambiguous ownership.

**Rejected**: Documentation-only tables; duplicate allowlists; graph infrastructure.

## 5. Wheel and sdist are equally production artifacts

**Decision**: Setuptools publishes only `isanlp_rst*`. `MANIFEST.in` prunes offline code, tests, scripts, specs, caches, local data, checkpoints, and generated evidence from the sdist while retaining build metadata and runtime resources. Validate both archives member by member.

**Rationale**: Wheel cleanliness does not imply sdist cleanliness. Current Setuptools supports explicit package include/exclude and package-data declarations.

**Rejected**: `.gitignore` as publication policy; wheel-only inspection; dropping sdist.

## 6. Optional formats remain production options

**Decision**: Core production imports without Docling/DocLang/Markdown extras. Each optional adapter declares only its runtime dependency. No offline dependency enters format extras.

**Rationale**: Optional formats are product capabilities, not development machinery.

**Rejected**: Making every format mandatory; classifying adapters as offline.

## 7. Model promotion is filesystem-based and fail-closed

**Decision**: Production retains manifest validation and safe loading. Offline creates a candidate and atomically promotes a byte-identical, content-addressed release directory plus strict promotion receipt. Production accepts only a validated release with task, architecture, compatibility, provenance, licence, integrity, and test-vector evidence.

**Rationale**: Existing eRST safetensors bundles already establish the correct local pattern. Released assets are wrapped or migrated, never retrained.

**Rejected**: Hosted registry; mutable symlink authority; loose experiment directories; re-evaluation as a structural prerequisite.

## 8. Parity is frozen evidence

**Decision**: Capture pre-move request identity, model-byte hashes, prepared inputs, serialized results, warnings, deterministic failures, and available device results. Compare clean-install output exactly except for explicitly pre-existing numerical tolerances.

**Rationale**: Regenerating expectations after a move can bless regressions.

**Rejected**: Unit tests alone; snapshot regeneration; retraining; moving network revisions.
