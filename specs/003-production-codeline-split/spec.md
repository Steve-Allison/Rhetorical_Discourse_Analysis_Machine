# Feature Specification: Clean Production Codeline Separation

**Feature Branch**: `codex/spec-kit-adoption`

**Created**: 2026-08-25

**Status**: Draft

**Input**: User request to split the production RST codeline cleanly from development, training, evaluation, and research machinery as a separate Spec Kit feature.

## Scope Authority

This feature creates an enforceable boundary between the code and dependencies required to analyse real production sources and everything used only to develop, train, evaluate, benchmark, or research models. The result remains one solo-local repository with two operational surfaces:

1. **Production runtime**: the installable RST/eRST analysis product, its public contracts, format adapters, released-model loading, and required runtime resources.
2. **Offline workbench**: corpus acquisition/preparation, model training, evaluation, research experiments, benchmarks, diagnostics, and other non-runtime tooling.

The dependency direction is one way: the offline workbench may use production contracts and runtime components; production must never import, package, install, discover, or execute offline-only code. Shared domain contracts remain owned by the production runtime so this feature does not create a third package merely to appear separated.

This feature moves and separates existing capabilities. It does **not** improve source ingest behavior, repair training data, retrain or select models, change parser architecture or inference mathematics, redesign evaluation methodology, or claim that existing training/evaluation results are correct. Those concerns belong to their own features.

## World-Class Separation Standard

For this small local project, world-class separation means the production artifact is minimal, complete, independently installable, behaviorally unchanged, and provably free of offline code and dependencies. The offline workbench remains easy for one person to run and can consume the production package without duplicating it.

The feature must not add enterprise release infrastructure, services, registries, containers, role systems, distributed execution, elaborate plugin frameworks, or multiple repositories. One repository, one production distribution, one offline workbench, one-way dependencies, and one local model-promotion boundary are sufficient.

Documentation or directory names alone do not constitute separation. Completion requires artifact inspection, clean-environment execution, transitive import proof, dependency proof, released-model parity, and enforcement that fails when a forbidden dependency is introduced.

## User Scenarios & Testing

### User Story 1 - Install and run only the production product (Priority: P1)

As the local RST user, I want to install the production product without training, evaluation, corpus, or research machinery so that the runtime is clear, minimal, and trustworthy.

**Why this priority**: A production codeline is not separate while offline modules or dependencies remain in its installable artifact or are required for normal analysis.

**Independent Test**: Build the production artifact, inspect every member and declared dependency, install it into a fresh production-only environment with no repository path available, and run every supported production import and representative analysis route.

**Acceptance Scenarios**:

1. **Given** the production artifact, **When** its contents are inspected, **Then** it contains every required runtime module/resource and zero corpus builders, trainers, evaluation harnesses, research systems, experiment configs, caches, tests, or local data.
2. **Given** a fresh machine-equivalent environment containing only production dependencies and released model assets, **When** representative text, pre-segmented, Markdown, Docling, DocLang, hierarchical, and eRST runtime routes execute, **Then** they complete without importing or locating the offline workbench.
3. **Given** the repository is unavailable on the import path, **When** the installed production package starts, **Then** no editable-install leakage or source-tree fallback is required.
4. **Given** a production user inspecting available commands and modules, **When** they enumerate the installed product, **Then** no training, corpus preparation, evaluation, or research entry point is presented as production capability.

---

### User Story 2 - Use one coherent offline workbench (Priority: P1)

As the solo model developer, I want training, evaluation, corpus preparation, benchmarks, and research tools available in one explicitly offline workspace that reuses the production contracts instead of being duplicated inside the product.

**Why this priority**: Separation must not delete or strand legitimate offline work, and parallel copies would immediately create drift.

**Independent Test**: Create the offline environment from its locked definition, use its declared commands from a clean process, and prove that it consumes the production package through the supported boundary while production remains unaware of the workbench.

**Acceptance Scenarios**:

1. **Given** the offline environment, **When** corpus preparation, training, evaluation, or research commands are invoked, **Then** their dependencies are available without being added to the production environment.
2. **Given** a domain contract needed by production and offline work, **When** both use it, **Then** there is one canonical production-owned definition rather than copied or translated alternatives.
3. **Given** an offline-only contract or experiment record, **When** its ownership is inspected, **Then** it remains in the offline workbench and is absent from the production public surface.
4. **Given** a known invalid or quarantined offline route, **When** separation is completed, **Then** it remains explicitly invalid or quarantined rather than being made to look successful for migration parity.

---

### User Story 3 - Preserve production behavior exactly through the split (Priority: P1)

As the product owner, I want the split to leave released-model analysis behavior unchanged so that structural cleanup does not silently change the product.

**Why this priority**: Moving model classes, contracts, resources, or imports can break checkpoint loading or alter results even when no inference code was intentionally changed.

**Independent Test**: Freeze representative pre-split production inputs, released model identities, serialized outputs, warnings, and failure behavior; run the same cases from the clean post-split production installation and compare them exactly or within an explicitly pre-existing numerical tolerance.

**Acceptance Scenarios**:

1. **Given** the same released model and production input, **When** pre-split and post-split analysis runs, **Then** model selection, prepared input, discourse output, serialization, provenance, and failure semantics are equivalent.
2. **Given** a released checkpoint whose model definition currently resides beside training code, **When** the split is performed, **Then** the minimal definition required for safe production loading remains available without the trainer, datasets, optimizer, or evaluation harness.
3. **Given** existing production public imports, **When** a clean production consumer runs, **Then** supported runtime imports remain available or have an explicit compatibility path that does not restore offline coupling.
4. **Given** an import path used only for training or research, **When** it changes, **Then** the offline migration is documented without treating that path as a production compatibility promise.

---

### User Story 4 - Enforce the boundary continuously (Priority: P1)

As the maintainer, I want a small automatic boundary check so that future work cannot accidentally pull training or research machinery back into production.

**Why this priority**: A one-time directory move will decay unless the actual artifact, import graph, and dependency closure are checked.

**Independent Test**: Run the boundary checks on the valid repository, then introduce a temporary forbidden production-to-offline import, offline-only dependency, and forbidden artifact member; prove each defect fails with the exact path or dependency named.

**Acceptance Scenarios**:

1. **Given** the production source set, **When** its direct and transitive imports are checked, **Then** every dependency resolves within the approved production surface or declared runtime dependency set.
2. **Given** a production module that imports offline code indirectly, **When** the boundary check runs, **Then** it fails and reports the complete offending path.
3. **Given** an offline-only package or file added to the production artifact, **When** artifact validation runs, **Then** publication fails and identifies the member.
4. **Given** a legitimate new production module, **When** it is classified and satisfies the boundary, **Then** the check accepts it without requiring duplicate allowlists or manual graph maintenance.

---

### User Story 5 - Promote model assets explicitly into production (Priority: P2)

As the local operator, I want a candidate model to cross from the offline workbench into production only as a verified immutable release bundle so that experiments cannot be served accidentally.

**Why this priority**: A code split remains porous if production can load loose experiment checkpoints, training directories, or mutable workbench state.

**Independent Test**: Create a candidate bundle in the offline workbench, verify and promote it locally, load it from a clean production environment, and prove that loose, incomplete, modified, or unpromoted candidates are rejected.

**Acceptance Scenarios**:

1. **Given** a complete candidate with required identity, compatibility, provenance, licensing, integrity, and evaluation evidence, **When** local promotion succeeds, **Then** production receives an immutable self-contained model release without training data or workbench code.
2. **Given** a loose experiment checkpoint or mutable training directory, **When** production attempts to load it, **Then** loading fails with a precise promotion-boundary error.
3. **Given** a promoted bundle whose bytes or manifest changed, **When** production validates it, **Then** it is rejected before inference.
4. **Given** the currently released model assets, **When** they are migrated, **Then** they receive the same verified production identity without being retrained or re-evaluated by this feature.

### Edge Cases

- Runtime model classes currently colocated with training loops, optimizers, datasets, or metrics.
- Legacy checkpoint deserialization that refers to historical module paths.
- Optional production formats whose dependencies should remain optional rather than becoming offline-only or mandatory.
- Runtime resources such as templates, styles, relation inventories, configuration defaults, and package metadata that can be omitted by an incorrect build.
- Modules with mixed runtime and offline responsibilities that cannot be classified without separating responsibilities.
- Circular imports exposed when offline modules move behind the production boundary.
- Tests that pass only because the repository root or editable source tree is on the import path.
- Type checking or test discovery that accidentally imports the offline workbench during production validation.
- Commands with similar names but different production and offline purposes.
- Model bundles with missing members, incompatible input contracts, stale hashes, ambiguous licensing, or experiment-only files.
- A development dependency also required at runtime, and a runtime dependency mistakenly assumed to be development-only.
- Generated files, caches, corpora, local checkpoints, secrets, and private evidence appearing in build outputs.
- Existing external consumers of training-only import paths that were never production API.
- Production source-ingest work from feature 002 landing before, during, or after this split.

## Requirements

### Functional Requirements

- **FR-001**: Every repository module, command, resource, configuration, and dependency MUST have exactly one declared ownership class: production runtime, offline workbench, repository-only validation/documentation, or generated/local artifact.
- **FR-002**: Ownership classification MUST be derived from actual runtime and workflow use, not directory names, provenance, or assumptions.
- **FR-003**: The production codeline MUST include only code, contracts, resources, and dependencies required to load released models and perform supported RST/eRST analysis.
- **FR-004**: The offline workbench MUST own corpus acquisition/preparation, training datasets, training loops, optimizers, model selection, evaluation/scoring harnesses, research systems, experiments, ablations, benchmarks, and non-production diagnostics.
- **FR-005**: Repository tests, specifications, documentation, build support, and local verification evidence MUST remain outside the production artifact even when they exercise production behavior.
- **FR-006**: Production-owned domain and serialization contracts MAY be consumed by the offline workbench; offline-only experiment, corpus, training, and evaluation contracts MUST NOT enter the production public surface.
- **FR-007**: The solution MUST retain one production distribution and one offline workbench in the same repository. It MUST NOT create a third shared distribution unless implementation planning proves that production ownership of shared contracts is impossible.
- **FR-008**: Production code MUST have zero direct or transitive imports from the offline workbench, repository scripts, tests, research harnesses, training managers, corpus builders, evaluation harnesses, or generated experiment outputs.
- **FR-009**: The offline workbench MAY depend on the production distribution and its public contracts; no reverse dependency is permitted.
- **FR-010**: Mixed-responsibility modules MUST be separated so that minimal runtime model definitions and inference behavior remain production-owned while datasets, optimization, fitting, scoring, and experiment orchestration remain offline-owned.
- **FR-011**: Separation MUST move canonical code rather than copy it. No production/offline duplicate implementation or synchronized mirror MAY be introduced.
- **FR-012**: The production artifact MUST exclude all offline modules, training/evaluation/research commands, corpora, prepared examples, experiment configurations, caches, tests, local checkpoints, secrets, and repository-only evidence.
- **FR-013**: The production artifact MUST include every runtime resource required for clean installation, model loading, format handling, visualization where publicly supported, serialization, and analysis.
- **FR-014**: Production dependencies MUST contain zero packages used only for corpus preparation, training, evaluation, research, benchmarking, notebook use, or development tooling.
- **FR-015**: Offline-only dependencies MUST be available through one separately locked offline environment that consumes the production distribution.
- **FR-016**: The production environment MUST remain separately locked and reproducible without resolving or installing the offline environment.
- **FR-017**: Normal production installation, import, and execution MUST succeed without the repository root, editable source tree, offline environment, network access, training corpora, or experiment artifacts.
- **FR-018**: All supported production entry points and public runtime imports MUST remain available after the split unless an explicit incompatibility is documented and approved before implementation.
- **FR-019**: Training-, evaluation-, corpus-, and research-only import paths are not production compatibility commitments; any moved offline path MUST receive a concise migration mapping for local use.
- **FR-020**: The split MUST NOT change trained architecture, model parameters, inference mathematics, default runtime behavior, public result meaning, or released model selection.
- **FR-021**: Pre-split and post-split production parity MUST cover imports, model loading, prepared model input, serialized output, deterministic failures, warnings, device selection, optional-format behavior, and representative CPU/MPS execution.
- **FR-022**: Existing released checkpoints MUST remain safely loadable without importing trainers, optimizers, datasets, corpus code, evaluation code, or research systems.
- **FR-023**: Unsafe or ambiguous legacy checkpoint loading MUST NOT be preserved merely for compatibility; affected assets MUST be migrated into a verified production bundle without changing their learned parameters.
- **FR-024**: Known-invalid, incomplete, or quarantined offline routes MUST remain visibly invalid, incomplete, or quarantined. Separation MUST NOT weaken their guards or fabricate success to claim migration parity.
- **FR-025**: Production boundary validation MUST inspect both declared dependencies and the actual direct/transitive import closure of every production module.
- **FR-026**: Boundary validation MUST derive the production source set from the production artifact authority and MUST NOT depend on a hand-maintained duplicate module list.
- **FR-027**: Boundary validation MUST report the complete offending import or dependency path and fail whenever production reaches an offline-owned component.
- **FR-028**: Artifact validation MUST inspect built distribution members and fail on every offline-owned, private, generated, cached, experimental, test, or secret-bearing member.
- **FR-029**: Clean-install validation MUST use the built production artifact in an environment with no repository path and no offline packages available.
- **FR-030**: Production verification MUST exercise all public parser variants, raw and pre-segmented text, supported format adapters, hierarchical analysis, serialization/reload, released-model loading, and supported device paths available on the local machine.
- **FR-031**: Offline verification MUST exercise each retained corpus, training, evaluation, research, and benchmark command far enough to prove correct imports, dependency resolution, production-contract access, and explicit quarantine state; it MUST NOT claim model or dataset correctness beyond that evidence.
- **FR-032**: One immutable model-release bundle MUST be the sole asset boundary from offline work into production.
- **FR-033**: A model-release bundle MUST identify its model task, immutable bytes, runtime input/output contract, architecture/configuration, released-model provenance, licence/use restrictions, compatibility range, and available evaluation evidence.
- **FR-034**: Promotion MUST verify every bundle member and required field before placing the bundle in the production model store; a partial or changed bundle MUST fail closed.
- **FR-035**: Production MUST reject loose experiment checkpoints, mutable training directories, unverified bundles, and model assets whose declared runtime contract is incompatible.
- **FR-036**: Promotion MUST be a direct local workflow. It MUST NOT require a model registry service, deployment platform, approval system, remote CI, or enterprise release process.
- **FR-037**: Existing released model assets MUST be migrated through the promotion boundary without retraining, model selection, or metric reinterpretation.
- **FR-038**: The production source-ingest behavior defined by feature 002 MUST remain independent of physical package location and MUST be hosted entirely within the production side when implemented.
- **FR-039**: Feature 003 MUST NOT implement feature 002 ingest improvements; it may move affected code only while proving pre-move/post-move behavioral parity.
- **FR-040**: Documentation MUST provide one production install/run path, one offline workbench setup/run path, the one-way dependency rule, the module-ownership authority, and the local model-promotion workflow.
- **FR-041**: The feature MUST add one fast boundary gate suitable for routine local use and one fresh clean-artifact validation for the exact completion candidate; it MUST NOT add elaborate multi-stage governance or redundant checking systems.
- **FR-042**: Completion MUST remove obsolete duplicate paths and references created by the split while preserving unrelated repository work.
- **FR-043**: Core production imports MUST remain usable without optional format or serialization capabilities installed; each optional production capability MUST declare only its own runtime dependencies and MUST NOT pull in the offline workbench.
- **FR-044**: Every publishable production artifact form, including built and source distributions, MUST satisfy the same membership, dependency, secret, local-data, and offline-code exclusions.

### Key Entities

- **Production Surface**: The complete transitively closed set of runtime modules, public contracts, resources, commands, and dependencies shipped to analyse sources.
- **Offline Workbench**: The non-production environment and codeline containing corpus, training, evaluation, research, benchmark, and diagnostic capabilities.
- **Ownership Authority**: The single classification of repository components and dependencies that determines production membership and boundary validation.
- **Production Artifact**: The independently installable distribution whose contents and dependencies define the actual production codeline.
- **Boundary Violation**: A direct or transitive path from production to an offline-owned component, forbidden dependency, or forbidden artifact member.
- **Model Release Bundle**: The immutable, self-contained, licensed, integrity-checked model asset accepted by production.
- **Promotion Receipt**: Evidence that a candidate bundle passed identity, integrity, compatibility, provenance, licence, and completeness checks before entering the production model store.
- **Parity Corpus**: A compact set of existing production requests, outputs, failures, and device cases used only to prove that the split did not change runtime behavior.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of repository modules, commands, resources, configurations, and declared dependencies have exactly one ownership classification, with zero unresolved mixed-ownership items at planning completion.
- **SC-002**: The built production artifact contains 100% of required runtime members and zero offline, corpus, training, evaluation, research, experiment, test, cache, local-data, or secret-bearing members.
- **SC-003**: The production dependency set contains zero offline-only dependencies, and a fresh production environment resolves without reading the offline environment definition.
- **SC-004**: Direct and transitive boundary analysis finds zero production-to-offline paths; seeded direct, indirect, dependency, and artifact violations are each detected with the complete offending path.
- **SC-005**: A clean installation from the built artifact, with the repository unavailable on the import path, passes 100% of the production acceptance routes required by FR-030.
- **SC-006**: Pre-split and post-split parity cases use identical released model bytes and produce equivalent prepared inputs, analysis results, serialization, provenance, warnings, failures, and available CPU/MPS behavior, with zero unexplained difference.
- **SC-007**: Every existing production public import is retained or has an explicitly approved compatibility decision; zero offline-only import path is reintroduced into production for compatibility.
- **SC-008**: Every retained offline command starts in the locked offline environment, resolves its production dependencies through the supported boundary, and either completes its bounded migration smoke or reports its pre-existing quarantine state accurately.
- **SC-009**: Production can load every currently released model through a verified production bundle while importing zero trainer, optimizer, dataset, corpus, evaluation, or research module.
- **SC-010**: Production rejects 100% of tested loose, incomplete, modified, incompatible, and unpromoted model candidates before inference.
- **SC-011**: Production and offline installations can be recreated independently using one documented command each, and the local promotion workflow completes with one documented command plus an inspectable receipt.
- **SC-012**: Repository search and built-artifact inspection find zero duplicated production/offline implementation introduced by the split and zero obsolete path created by the feature.
- **SC-013**: The routine boundary gate completes in under 10 seconds on the reference machine; the slower clean-artifact validation runs only for the exact completion candidate.
- **SC-014**: Feature 002 remains independently specifiable and implementable: feature 003 changes no production ingest semantics and feature 002 requires no offline workbench at runtime.
- **SC-015**: Final inspection demonstrates one repository, one production distribution, one offline workbench, one-way dependencies, one model-promotion boundary, and no enterprise or distributed infrastructure added by this feature.
- **SC-016**: Core production import and basic text analysis pass with zero optional format/serialization extras installed; enabling each supported optional production capability introduces zero offline-only dependency.
- **SC-017**: Inspection of every built and source production artifact finds identical boundary compliance: zero forbidden members, dependencies, secrets, corpora, local data, caches, or experiment assets.

## Assumptions

- This remains a solo project on one local machine; production separation is an installation and dependency boundary, not a team deployment process.
- One repository is retained. Splitting into multiple repositories would add coordination cost without improving the required runtime boundary.
- Production owns shared runtime/domain contracts. The offline workbench depends on them, avoiding a third shared package.
- Tests, documentation, specifications, and build tooling may exercise both surfaces from the repository but are not members of the production distribution.
- Offline development includes training, evaluation, research, corpus preparation, benchmarks, and diagnostics; it does not mean a lower code-quality standard.
- Existing released model bytes and inference behavior are authoritative for parity. This feature may repackage them safely but may not retrain or reinterpret them.
- Known defects discovered in offline workflows remain subject to the project's fix-forward rule, but the split must not broaden into a model-quality or dataset-remediation program.
- The production ingest feature may be implemented before or after this split. Its behavioral specification remains separate from physical codeline ownership.
- Model promotion is local filesystem workflow with immutable evidence; no hosted registry or deployment service is required.
