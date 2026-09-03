# Feature Specification: Rhetorical Discourse Analysis Machine Architecture

**Feature Branch**: `006-rhetorical-discourse-machine`

**Created**: 2026-08-31

**Status**: Draft

**Amended 2026-09-02**: the promotion-evidence system was removed by owner ruling. It was never requested and it gated working analysers behind an evaluation ceremony, making the machine report `unavailable` for techniques that ran correctly. User Story 4, FR-022, FR-023, the `PromotionDecision` entity, and `contracts/promotion-evidence.md` are deleted; FR-021 is reduced to provider provenance. Capability now means one thing: the provider can run. Specs 002-005 keep their original wording as a dated historical record.

**Amended 2026-09-02 (second ruling)**: the LLM-based techniques are not optional. As originally written every success criterion could be satisfied with four of the seven techniques absent — Scope Boundaries excluded the providers, FR-018 let PDTB and SDRT sit in the workbench indefinitely, and the provider-order assumption made PDTB conditional on "a concrete need". That let *not building them* score as a pass. FR-031 and FR-032 now require all seven, SC-012 makes 7/7 the bar, and the escapes are closed.

**Input**: User description: "Transform the complete project into the Rhetorical_Discourse_Analysis_Machine. Preserve the current isanlp_rst implementation as the independent RST production provider, keep all experimentation and training in one protected top-level workbench, give every discourse technique its own pure production boundary and native output, and expose the independent analyses downstream without flattening their theories."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preserve Trusted RST Analysis During the Transition (Priority: P1)

As the machine owner, I can reorganize the project around multiple discourse-analysis techniques without losing, weakening, or silently changing the RST and eRST analysis that already works.

**Why this priority**: The existing RST capability is the only established production provider. The broader machine has no value if its creation damages that capability or changes its public meaning.

**Independent Test**: Capture the supported RST production contract and representative results before migration, repeat the same public operations after migration, and verify that every request, success, failure, capability, serialization, and semantic result remains equivalent.

**Acceptance Scenarios**:

1. **Given** a supported RST production request before the transition, **When** the same request is submitted after the transition, **Then** the caller receives an equivalent native RST or eRST result through the same supported public import surface.
2. **Given** an existing RST consumer, **When** the project is reorganized, **Then** the consumer does not need to import an experimental module or adopt a new theory-neutral result in place of its native RST result.
3. **Given** an RST parser or model with established inference behaviour, **When** the repository architecture changes, **Then** its trained architecture, inference mathematics, relation meanings, and evidence semantics remain unchanged unless a separately approved feature explicitly changes and validates them.

---

### User Story 2 - Keep Production and Experimentation Unambiguously Separate (Priority: P2)

As the machine owner, I can identify production code immediately while every candidate library, corpus, notebook, training run, evaluation, benchmark, and checkpoint remains contained in one top-level workbench.

**Why this priority**: The machine will evaluate techniques with very different maturity, dependencies, and evidence. A strict boundary prevents experimental state from becoming an accidental runtime dependency or an implied production endorsement.

**Independent Test**: Classify every project-owned path and dependency as production, workbench, test, specification, tool, or generated material; verify that every item has exactly one owner and that no production import or distributable member crosses into the workbench.

**Acceptance Scenarios**:

1. **Given** any experimental or training artifact, **When** its owner is resolved, **Then** it resolves under the single top-level `workbench/` boundary and not under a technique's production boundary.
2. **Given** any production technique, **When** its transitive imports and distributable members are inspected, **Then** none originate from `workbench/`.
3. **Given** a technique with no production implementation, **When** production capabilities are reported, **Then** that technique is explicitly unavailable rather than represented by a stub, placeholder, or fabricated result.

---

### User Story 3 - Obtain Independent Native Analyses (Priority: P3)

As a downstream consumer, I can request one or more supported analyses and receive each technique's native result independently, so the meaning unique to RST, PDTB, SDRT, Toulmin, Walton, Dung, or IBIS is preserved.

**Why this priority**: These techniques describe different objects and operate at different levels. Flattening them into one invented graph would discard distinctions the machine exists to expose.

**Independent Test**: Submit a request for multiple available techniques, inspect each returned result against its native contract, and verify that serializing or bundling it does not remove, rename, or reinterpret native structures.

**Acceptance Scenarios**:

1. **Given** two available techniques, **When** both are requested, **Then** each returns a separately typed and versioned native result.
2. **Given** one successful provider and one unavailable or failed provider, **When** both are requested, **Then** the successful result remains available and the other provider has an explicit typed status.
3. **Given** a formal technique that consumes structured arguments rather than raw text, **When** it uses another analysis as input, **Then** the resulting artifact identifies that dependency without merging the two native outputs.

---

### User Story 4 - Evolve One Technique at a Time (Priority: P4)

As the machine owner, I can add, replace, or withhold one discourse technique without forcing unrelated providers to change or implying that every technique has reached production maturity.

**Why this priority**: The ecosystem is fragmented and techniques will mature at different rates. Independent boundaries allow rigorous incremental adoption without a monolithic release or shared hidden dependency.

**Independent Test**: Mark one technique unavailable or replace its provider and verify that every other provider's contract, capability, direct invocation, and native result remains unchanged.

**Acceptance Scenarios**:

1. **Given** no production-quality implementation for a named technique, **When** the machine reports capabilities, **Then** it reports that technique as unavailable with a stable reason.
2. **Given** a provider is replaced, **When** unrelated techniques are invoked, **Then** their outputs and public contracts remain unchanged.
3. **Given** a capability proposed for reuse by multiple techniques, **When** only one proven caller exists, **Then** it remains owned by that technique or the workbench rather than becoming a premature shared production subsystem.

### Edge Cases

- Active training, evaluation, checkpoint writing, or result collation is still running when repository migration is proposed.
- A technique has corpus readers or annotation tooling but no credible raw-input inference provider.
- A package installs successfully but performs model downloads, network access, or expensive initialization during import.
- A candidate works only on an unsupported runtime or requires dependencies forbidden at the production boundary.
- One provider fails after other requested providers have completed successfully.
- Two techniques use similar terms such as relation, support, claim, or argument but assign them different semantics.
- A Dung or IBIS request lacks the structured input required by that framework.
- A result depends on an upstream provider whose version, model identity, or source anchors are missing.
- A provider's licence permits experimentation but not the intended production distribution.
- An existing RST consumer imports the canonical `isanlp_rst` package while the physical source location changes.
- A production directory exists for a technique that has no implementation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST adopt `Rhetorical_Discourse_Analysis_Machine` as its complete project identity while retaining an explicit record of `isanlp_rst` as the RST provider package and historical source project.
- **FR-002**: The target architecture MUST define distinct top-level production boundaries named `rst/`, `pdtb/`, `sdrt/`, `toulmin/`, `walton/`, `dung/`, and `ibis/`, each corresponding one-to-one with a canonical framework concept in the Central_Configs ontology (`coe:artifact/narrative/analytical_frameworks_taxonomy`); each boundary's capability declaration MUST reference its canonical `coe:` framework identifier. A boundary directory is created only when its technique first gains a provider; until then the boundary exists as an approved name, not a directory.
- **FR-003**: A technique boundary MUST be the production boundary itself and MUST NOT contain a redundant `production/` subdirectory.
- **FR-004**: The project MUST retain exactly one top-level `workbench/` as the canonical home for all development experiments, candidate implementations, corpora, training, evaluation, benchmarks, checkpoints, and runs across every technique.
- **FR-005**: Production technique boundaries MUST contain only production runtime code, native contracts, required runtime assets, and directly applicable production documentation or tests.
- **FR-006**: Production code and production distributions MUST NOT import, execute, or package workbench material.
- **FR-007**: Production verification MUST remain under a separate top-level `tests/` boundary and MUST distinguish production-contract tests from workbench evaluation.
- **FR-008**: The current `isanlp_rst` implementation MUST remain the canonical RST and eRST provider package under the `rst/` production boundary.
- **FR-009**: The supported public import name `isanlp_rst` and its canonical production-ingest contract MUST remain available after physical relocation.
- **FR-010**: The machine-facing RST adapter MUST consume the supported `isanlp_rst` public contract and MUST NOT duplicate, reinterpret, or bypass the provider's preparation, analysis, capability, serialization, validation, failure, or provenance authority.
- **FR-011**: Repository migration MUST preserve existing RST/eRST result semantics, validation rules, failure algebra, source anchors, model identity, and serialized-contract compatibility.
- **FR-012**: Each discourse technique MUST be independently callable when available and MUST own a separately versioned native result contract.
- **FR-013**: The aggregate machine result MUST preserve each native technique result without flattening distinct theories into a universal node-and-edge vocabulary.
- **FR-014**: An aggregate request MUST preserve successful provider results when another requested provider is unavailable or fails, and MUST represent each unavailable or failed provider explicitly.
- **FR-015**: When one technique consumes another technique's result, the consumer result MUST identify the exact upstream artifact and provider identity while keeping both native outputs separate.
- **FR-016**: Dung analysis MUST be represented as formal evaluation of a supplied or explicitly derived argument-and-attack framework, not as unsupported raw-text inference.
- **FR-017**: IBIS analysis MUST be represented as a typed issue-position-argument structure; any automated extraction into that structure MUST be separately identified and evaluated.
- **FR-018**: PDTB and SDRT corpus readers, annotation utilities, and research parsers MUST remain workbench resources; they are not providers. This does not defer the techniques: SDRT and PDTB each MUST receive an end-to-end production provider under FR-031.
- **FR-019**: Claim-and-premise extraction alone MUST NOT be represented as complete Toulmin analysis or complete Walton-scheme analysis.
- **FR-020**: Every production provider MUST expose an explicit capability state and stable unavailability reasons; the machine MUST NOT use production stubs, dummy analyses, or fabricated structures for an unavailable technique.
- **FR-021**: A production provider MUST record its own provenance: the package, version, source identity, model identity where applicable, and the licence its code and any model weights carry.
- **FR-024**: Each technique MUST receive its own decision-closed Spec Kit feature before implementation begins for that technique.
- **FR-025**: The aggregate analysis contract and RST provider adapter features MUST be specified and cross-artifact consistency checked before repository migration begins. Each technique provider feature MUST be decision-closed before that technique's implementation begins.
- **FR-026**: Repository migration MUST NOT begin while protected workbench processes are active or while their checkpoints, run records, and outputs have not been safely reconciled.
- **FR-027**: Existing Features 004 and 005, their checked tasks, and their generated or untracked artifacts MUST NOT be treated as complete solely because they exist or contain completion markers.
- **FR-028**: The architecture MUST remain a single-person, single-machine system and MUST NOT introduce team, multi-user, distributed, or enterprise infrastructure without a separate explicit requirement.
- **FR-029**: A shared production abstraction MUST be introduced only when at least two proven production callers require the same semantic contract and ownership can remain unambiguous.
- **FR-030**: Absence of a technique implementation MUST NOT prevent direct use of any other available production provider.
- **FR-031**: All seven techniques — RST, PDTB, SDRT, Toulmin, Walton, Dung, and IBIS — MUST have a production provider. The machine is incomplete until every one of them reports `available`. `unavailable(not_implemented)` is a statement of outstanding work; it MUST NOT be treated as an acceptable end state, a passing result, or a satisfied requirement, and no technique may be dropped, deferred indefinitely, or declared optional without an explicit owner ruling recorded in this specification.
- **FR-032**: Toulmin, Walton, and SDRT are expected to require LLM-based inference. An LLM-based provider is a required production provider on the same footing as a deterministic one: the absence of a classical algorithm is not grounds for omitting the technique, deferring it, or substituting claim-and-premise extraction for it (FR-019). Such a provider MUST declare the model it calls as part of its provenance (FR-021) and MUST classify its failures under the same retryability contract as every other provider.

### Key Entities

- **Technique Production Boundary**: The exclusive production home for one discourse framework, including its native contract, provider, required runtime assets, and capability declaration.
- **Workbench**: The single non-production authority for candidates, corpora, experiments, training, evaluation, benchmarks, checkpoints, and run evidence across all techniques.
- **Provider**: An independently callable implementation that accepts its declared input, returns its technique-native result, reports capabilities, and owns its runtime provenance and failure contract.
- **Native Technique Result**: A versioned result whose entities and relationships retain the semantics of exactly one discourse or argumentation framework.
- **Aggregate Analysis**: A collection of independent provider outcomes with source identity, native results, per-provider statuses, provenance, and explicit dependency lineage; it is not a replacement theory.
- **Provider Dependency Reference**: A traceable declaration that one provider consumed a specific output from another provider.
- **Migration Safety State**: The evidence that protected workbench activity has stopped and its current artifacts have been reconciled before repository movement begins.

### Scope Boundaries

This feature defines the complete machine architecture, ownership rules, migration invariants, and feature roadmap. It does not:

- move or rename current source files;
- reorganize, execute, pause, or inspect active workbench workloads;
- implement the aggregate analysis contract or orchestration runtime;
- implement the PDTB, SDRT, Toulmin, Walton, Dung, or IBIS providers — each is **required** by FR-031 and is built in its own named follow-on feature, not omitted;
- retrain, reevaluate, package, or publish an RST model;
- certify Features 004 or 005 as complete;
- create placeholder production implementations for future techniques;
- include framework-guided composition or generation: the machine is permanently analysis-only, and generation belongs to downstream consumers (skills and other projects) of its native analyses;
- release or publish any code, model, or artifact.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The approved target layout assigns all seven discourse techniques, the shared workbench, production verification, machine aggregation, and planning material to exactly one named top-level boundary with zero ambiguous owners.
- **SC-002**: After eventual migration, 100% of the supported pre-migration RST public operations and persisted contract kinds pass equivalence checks against the captured pre-migration baseline.
- **SC-003**: After eventual migration, automated boundary inspection reports zero production imports from `workbench/` and zero workbench members in production distributions.
- **SC-004**: For every multi-technique request exercised in acceptance testing, 100% of successful native outputs survive aggregation without lost fields or changed semantic values.
- **SC-005**: Acceptance testing demonstrates every combination of provider success, unavailability, and failure without one provider suppressing another provider's successful result.
- **SC-006**: 100% of available providers report their own provenance — package, version, source identity, model identity where applicable, and licence.
- **SC-007**: Zero unavailable techniques are represented by stubs, dummy outputs, or fabricated discourse structures.
- **SC-012**: `Machine.capabilities()` reports all seven techniques `available`. Any technique reporting `unavailable(not_implemented)` means the machine is incomplete and this specification is not met — however green every other gate is.
- **SC-008**: Repository migration begins only after a current check confirms zero protected workbench processes and a complete inventory of active checkpoints, run records, and outputs has been reconciled.
- **SC-009**: Each planned follow-on capability has its own decision-closed Spec Kit feature and passes cross-artifact consistency analysis before implementation begins.
- **SC-010**: A new or replacement provider for one technique can be withheld without changing the direct invocation, native contract, or capability result of any unrelated available technique.
- **SC-011**: The machine remains operable by one person on one local machine without requiring a remote service, multi-user control plane, or distributed runtime for its core architecture.

## Assumptions

- The project remains one repository operated by one person on one local machine.
- The current production RST/eRST authority remains the supported `isanlp_rst` public contract unless a separate approved feature changes it.
- Feature 006 is an architecture feature; provider implementation begins in later technique-specific features. Those features are obligations created by FR-031, not options: 006 is not satisfied while any of them is unwritten or unbuilt.
- The follow-on feature family is: aggregate analysis contract, RST provider adapter, repository migration, Dung provider, IBIS provider, SDRT provider, Toulmin provider, Walton provider, PDTB provider, and cross-provider orchestration. Repository migration is its own decision-closed feature carrying the RST baseline capture, migration safety state, packaging verification, and project identity adoption obligations — the last including sibling-repo reference updates and per-project memory/settings path migration (research D3 migration-feature notes).
- Provider order — not provider optionality (FR-031). All seven are required; the order reflects owner need and build sequence: Dung and IBIS first (formal, deterministic, verifiable by proof and property test), then SDRT (meeting and talk transcripts are multi-party dialogue — SDRT's native object), then Toulmin and Walton (LLM-based), then PDTB last. Last means last, not conditional.
- Canonical framework identities live in the Central_Configs ontology (`coe:artifact/narrative/analytical_frameworks_taxonomy`, registered 2026-08-31 by `coe:decision/rdam-006/narrative/analytical_frameworks`). The machine vendors the Central distribution and references `coe:` identifiers for framework identity only; native technique inventories and result semantics are provider-owned and are never constrained to Central's simplified vocabulary profiles.
- Technique boundary directories are not importable Python packages. Packages inside a boundary carry namespaced import names (`isanlp_rst` under `rst/`); top-level import names such as `ibis` or `rst` are never created, so established PyPI import names are never shadowed.
- Native contracts for structured-input techniques (Dung, IBIS) accept constructed instances per FR-016/FR-017; this is an analytical requirement and does not reintroduce generation into scope.
- Standalone analytical authority (owner ruling 2026-09-01, superseding the same-day division-of-labour wording): the machine is the estate's standalone centre of excellence for discourse and argumentation analysis. It is the sole authority for technique-native structures — RST/eRST trees, Dung argumentation frameworks, IBIS structures, SDRT graphs, and any future technique result, at every capability tier including heavy LLM-assisted analysis — and it delivers findings downstream through its supported public contracts to whichever consumers exist, without privileging any of them. No consumer's needs shape the machine's contracts, semantics, or feature roadmap: contracts derive from each technique's native theory and this specification. Consumers own their own integration against the public contracts.
- Existing Features 004 and 005 remain separate authorities whose current completion state requires independent convergence evidence.
- No new shared production `argument_mining/` boundary is assumed. Shared production ownership may be introduced later only if multiple proven providers require the same stable semantic contract.
- Current workbench training and experimentation remain protected until the user explicitly confirms that migration work may inspect and move their artifacts.
