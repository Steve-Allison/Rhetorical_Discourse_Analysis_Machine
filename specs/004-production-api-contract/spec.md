# Feature Specification: World-Class Production API Contract

**Feature Branch**: `not-created (no before-specify branch hook configured)`  
**Created**: 2026-08-29  
**Status**: Draft  
**Input**: User description: "Make the isanlp_rst API state of the art and world-class, exposing the complete provider-owned contract that downstream projects need without shaping the provider around any one consumer."

## Scope Authority

This feature governs the production-facing `isanlp_rst` API: source submission and preparation, parser capability and model identity, RST/eRST analysis, provenance, retained side-channel content, typed failures, deterministic persistence, contract evolution, and installable distribution.

It supersedes Feature 002 only where that feature's public contract is incomplete or contradicts this specification. Feature 002 remains authoritative for production ingest behaviour, source-spec currency, and separation of production code from research and training code.

The contract is provider-owned. It exposes evidence that `isanlp_rst` genuinely creates or uses; it does not reproduce a downstream project's schema, workflow state, or invented evidence. Removed format-specific public entry points remain removed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consume a complete analysis result (Priority: P1)

A downstream application submits a supported source and receives one self-contained result from which it can inspect the source identity, preparation decisions, retained content, discourse analysis, anchors, model identity, execution facts, and semantic identity without private imports or a second reconstruction pass.

**Why this priority**: A trustworthy, complete result is the core product boundary. If consumers must infer or recreate provider evidence, the API is not a dependable contract.

**Independent Test**: Analyse a representative source from each supported source form, serialize and reload the result, and verify that every provider-owned fact needed to explain the result remains available and internally consistent.

**Acceptance Scenarios**:

1. **Given** a valid source with primary discourse and retained non-primary material, **When** analysis succeeds, **Then** the result exposes the complete preparation and analysis evidence, including accessible retained content and its disposition.
2. **Given** a successful result, **When** a consumer recomputes its documented semantic digests from the exposed semantic values, **Then** every digest matches.
3. **Given** a serialized successful result, **When** it is reloaded in a compatible runtime, **Then** its semantic meaning, status, evidence, and digests are unchanged.

---

### User Story 2 - Inspect preparation before analysis (Priority: P1)

A caller prepares a source independently of model inference and receives the complete preparation outcome, including source contract, inventory, dispositions, transformations, structural mapping, coverage, and any analysis subdivision plan that can be determined from the supplied parser capability.

**Why this priority**: Preparation is a public lifecycle stage, not a hidden implementation detail. It must be inspectable and usable independently if the API exposes it.

**Independent Test**: Prepare the same source with and without a supplied parser capability and verify that preparation evidence is complete, deterministic, and explicit about whether an analysis plan was produced.

**Acceptance Scenarios**:

1. **Given** a supported source, **When** it is prepared without model inference, **Then** every inventoried item has an identity, classification, disposition, and traceable relation to the prepared primary discourse or retained side-channel material.
2. **Given** a parser capability with a finite analysis capacity, **When** the source requires subdivision, **Then** the preparation outcome exposes the complete deterministic subdivision plan before inference begins.
3. **Given** a source that contains no analysable primary discourse, **When** it is prepared, **Then** the outcome remains successful and explicitly records the empty-primary condition and all retained content.

---

### User Story 3 - Diagnose failures with completed evidence (Priority: P1)

A caller receives a typed production failure that identifies the failed lifecycle stage and preserves safe evidence from every completed stage, without leaking private source text or fabricating evidence that was never produced.

**Why this priority**: A production contract is incomplete if its failure path discards the evidence required to explain non-use or remediation.

**Independent Test**: Induce one failure at each lifecycle stage and verify the error category, failed stage, retryability, causal chain, safe context, and completed-stage evidence.

**Acceptance Scenarios**:

1. **Given** preparation completed and analysis then fails, **When** the typed failure is returned, **Then** it includes the complete preparation outcome and no claimed analysis result.
2. **Given** malformed or unsupported input fails before inventory completion, **When** the failure is inspected, **Then** it contains only evidence genuinely completed before the failure.
3. **Given** source text contains private material, **When** any failure is rendered or serialized, **Then** raw private text is absent unless the caller explicitly opted into a documented diagnostic mode.

---

### User Story 4 - Rely on a stable, versioned contract and durable distribution (Priority: P1)

A downstream project installs an immutable `isanlp_rst` distribution built from a named source revision and can determine whether its public contract is compatible before processing data.

**Why this priority**: Source code that cannot be installed reproducibly, or incompatible behaviour published under an unchanged version, is not a usable production API.

**Independent Test**: On a second development machine, install the repository's committed distribution artifact, verify its receipt and source revision, import the declared public surface, and run the contract conformance suite without rebuilding.

**Acceptance Scenarios**:

1. **Given** a committed release artifact and receipt, **When** it is installed on another supported machine, **Then** its package version, contract version, artifact digest, and source revision match the receipt.
2. **Given** a breaking public-contract change, **When** a distribution is produced, **Then** it has a new major package version and no incompatible artifact shares the previous version.
3. **Given** runtime and serialized contract versions, **When** compatibility is checked, **Then** the result is explicit before source processing begins.

---

### User Story 5 - Discover capabilities before expensive work (Priority: P2)

A caller discovers supported source forms, lifecycle operations, contract versions, parser constraints, optional features, and persistence guarantees without loading a model or analysing a source.

**Why this priority**: Capability discovery prevents trial-and-error integration and makes optional boundaries honest.

**Independent Test**: In an offline process with no model loaded, query capabilities and verify they accurately predict acceptance or rejection of representative requests.

**Acceptance Scenarios**:

1. **Given** a core installation, **When** capabilities are queried, **Then** discovery performs no model download, network access, or analysis.
2. **Given** an optional source dependency is absent, **When** capabilities are queried, **Then** the source form and unavailable extra are reported without breaking the core import.
3. **Given** a mutable parser instance, **When** capabilities are queried, **Then** the result explicitly states whether model identity and semantic caching are stable enough for production use.

---

### User Story 6 - Retain valid non-primary discourse material (Priority: P2)

A caller can retrieve valid source material that `isanlp_rst` intentionally does not analyse—such as metadata, notes, captions, table content, or other side channels—together with its classification, anchors, and disposition.

**Why this priority**: Correctly excluding content from RST analysis must not make that content disappear from the provider's source account.

**Independent Test**: Ingest a mixed-content fixture and prove that every valid source item is either represented in primary discourse or returned as accessible retained material with an explicit disposition.

**Acceptance Scenarios**:

1. **Given** valid side-channel content, **When** preparation completes, **Then** the content remains accessible in a typed representation and is linked to its source location.
2. **Given** a structured table or hierarchy excluded from primary discourse, **When** retained material is inspected, **Then** its meaningful structure is preserved rather than flattened into an unexplained digest.
3. **Given** duplicate content, **When** one representation is suppressed, **Then** the result identifies the canonical item and records the duplicate relationship.

### Edge Cases

- The source is empty, whitespace-only, or contains only retained side-channel content.
- Identical source bytes are supplied with different declared identities or source contracts.
- A serialized result uses an invalid, unsupported, or future contract version.
- Source structure is deeply nested, discontinuous, duplicated, or contains overlapping representations.
- A source exceeds parser capacity by a large margin and requires many deterministic analysis units.
- Returned anchors are missing, duplicated, outside their source bounds, or do not reconstruct the analysed text.
- The parser returns a disconnected, cyclic, multi-rooted, or otherwise invalid discourse graph.
- A parser instance is mutable or its model identity cannot be established.
- A persisted result is truncated, corrupt, or has a semantic digest that does not match its exposed values.
- Failure occurs during acquisition, classification, preparation, planning, inference, validation, assembly, persistence, or cache retrieval.
- Optional source dependencies are missing while the core package remains installed.
- Documentation, runtime exports, serialized schemas, statuses, or error categories drift apart.
- A development checkout is dirty while an immutable release artifact must still identify exactly what it contains.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose one canonical production lifecycle covering source submission, preparation, optional planning, analysis, validation, persistence, and typed failure reporting.
- **FR-002**: Every public production symbol MUST be classified as supported, deprecated, or internal, and the documented public inventory MUST match runtime exports.
- **FR-003**: All supported source forms MUST enter through the same source-artifact boundary and produce the same categories of public evidence.
- **FR-004**: Preparation MUST expose a complete public inventory of every valid content item discovered in the submitted source.
- **FR-005**: Every inventory item MUST expose provider-owned identity, content classification, authorship or origin when known, representation type, meaningful structure, source anchors, and final disposition.
- **FR-006**: Valid non-primary material MUST remain accessible through the public result in a typed representation; an identifier or digest alone is insufficient.
- **FR-007**: A preparation outcome MUST expose the source contract identity, selected preparation policy, full inventory, dispositions, duplicate relationships, transformations, prepared primary discourse, source mapping, structural boundaries, coverage values, warnings, and semantic identity.
- **FR-008**: When parser capacity is supplied and subdivision is required, preparation MUST expose the complete deterministic subdivision plan before inference.
- **FR-009**: An analysis outcome MUST retain the complete preparation outcome and add analysis status, validated discourse analysis, analysis anchors, model identity, execution facts, and cache provenance.
- **FR-010**: Provider-owned values used to make or explain a production decision MUST be exposed as inspectable typed values, not only as opaque digests.
- **FR-011**: Every published semantic digest MUST be deterministically recomputable from documented exposed semantic values.
- **FR-012**: Successful outcomes MUST fail closed when required evidence is incomplete, contradictory, or cannot be validated.
- **FR-013**: Analysis statuses MUST be mutually exclusive, semantically defined, reachable through documented behaviour, and exercised by conformance tests.
- **FR-014**: The contract MUST distinguish at least successful analysis, successful empty-primary preparation, intentional non-analysis, provider unavailability, and failed processing without conflating them.
- **FR-015**: Production failures MUST use a typed hierarchy that exposes the failed lifecycle stage, stable error category, retryability, causal chain, safe diagnostic context, and evidence from completed stages.
- **FR-016**: A failure MUST NOT claim evidence for a stage that did not complete.
- **FR-017**: Default failure rendering and serialization MUST NOT disclose raw private source text.
- **FR-018**: Multi-unit analysis MUST NOT return or cache partial success as a complete production result.
- **FR-019**: Public preparation outcomes, analysis outcomes, retained content, capability descriptions, and completed-stage failures MUST support deterministic serialization and compatible reload.
- **FR-020**: Serialized contracts MUST separate semantic values, which determine meaning and cache identity, from execution values, which record a particular run.
- **FR-021**: Every serialized public contract MUST carry an explicit contract version and documented compatibility rules.
- **FR-022**: Package versions MUST follow semantic compatibility: any breaking public-contract change MUST use a new major package version, and incompatible artifacts MUST NOT reuse a package version.
- **FR-023**: The system MUST expose offline, model-free capability discovery for supported source forms, lifecycle operations, contract versions, parser constraints, optional features, and persistence guarantees.
- **FR-024**: Capability discovery MUST distinguish immutable production parser configurations from mutable or unidentified parser instances.
- **FR-025**: Format-specific adapters MUST remain internal implementation details while preserving their meaningful source semantics in the shared public evidence model.
- **FR-026**: Preparation policies and analysis-planning policies MUST be explicit, inspectable, and included in semantic identity whenever they can change results.
- **FR-027**: Valid unsupported-for-analysis material MUST be retained with an explicit disposition rather than silently dropped or reported as analysed.
- **FR-028**: Meaningful table, hierarchy, list, caption, note, metadata, and cross-reference structure MUST be preserved when the source format exposes it.
- **FR-029**: This feature MUST NOT change trained model architecture, inference mathematics, or scientific interpretation merely to simplify the API.
- **FR-030**: The production API MUST remain suitable for one person on one local machine and MUST NOT require services, network access, research workbenches, training code, or enterprise infrastructure.
- **FR-031**: Core package import and capability discovery MUST remain usable when optional source-format dependencies are absent.
- **FR-032**: Public documentation and examples MUST use exact runtime symbol names, enum values, signatures, statuses, error types, contract versions, and supported workflows.
- **FR-033**: Removed format-specific public entry points MUST NOT be restored as compatibility aliases.
- **FR-034**: The provider contract MUST NOT contain fields whose only authority is a downstream project's schema, workflow, or reporting requirement.
- **FR-035**: A downstream consumer MUST be able to integrate using only installed public exports and serialized public values, without importing private modules or reconstructing provider evidence.
- **FR-036**: Contract conformance MUST be verified against a clean installed distribution, not only an editable source checkout.
- **FR-037**: Conformance fixtures MUST cover every supported source form, mixed primary and retained content, empty-primary content, subdivision, cache hit and miss, serialization round-trip, optional dependency absence, and failure at every lifecycle stage.
- **FR-038**: Contract tests MUST verify field meaning, provenance, invariants, and cross-field consistency rather than symbol existence alone.
- **FR-039**: A machine-readable public-surface inventory MUST reconcile documentation, runtime exports, serialized payloads, statuses, error categories, and compatibility guarantees.
- **FR-040**: Semantically identical requests using an immutable model identity and policy MUST produce identical semantic outcomes and cache identities.
- **FR-041**: Any change to source identity, source contract, preparation policy, prepared discourse, analysis plan, model identity, or validated analysis MUST change the corresponding semantic identity.
- **FR-042**: Release artifacts intended for local cross-machine consumption MUST be durable repository content and MUST NOT require a separate rebuild on each development machine.
- **FR-043**: Every release artifact MUST have a machine-readable receipt containing package version, public contract version, source revision, clean-or-dirty source state, build environment identity, artifact filename, artifact digest, and verification results.
- **FR-044**: A release artifact MUST be built from an immutable, identified source revision; uncommitted source changes MUST NOT be silently incorporated into a release artifact.
- **FR-045**: State-of-the-art claims MUST be bounded to the production API contract and supported by a dated comparison with current production-library practices for typed contracts, provenance, deterministic persistence, capability discovery, compatibility, and failure semantics.
- **FR-046**: Any gap identified by that comparison MUST be resolved in the specification, explicitly rejected with rationale, or recorded as a named open decision before planning completes.

### Key Entities *(include if feature involves data)*

- **Public Surface Inventory**: The machine-readable authority for supported public symbols, statuses, errors, payloads, versions, and guarantees.
- **Source Artifact**: The submitted content plus its declared identity, source form, origin, media type, and acquisition facts.
- **Source Contract Identity**: The versioned semantics used to interpret a source, including relevant upstream format identity when applicable.
- **Content Inventory Item**: One discovered source item with classification, structure, anchors, representation, provenance, relationships, and disposition.
- **Preparation Policy**: The inspectable rules that determine classification, duplicate handling, primary-discourse selection, transformations, and retention.
- **Preparation Outcome**: The complete, serializable account of inventory, decisions, prepared discourse, retained material, mapping, coverage, planning, and semantic identity.
- **Analysis Plan**: The deterministic mapping from prepared discourse to one or more parser-capacity-safe analysis units and their recombination boundaries.
- **Model Identity and Capability**: Immutable model-release identity and the constraints or supported behaviours that affect preparation, analysis, and semantic caching.
- **Production Analysis Outcome**: The validated discourse result together with the full preparation outcome, status, anchors, model identity, execution facts, and cache provenance.
- **Completed-Stage Failure**: A typed failure that names the failed stage and safely retains evidence from prior completed stages.
- **Capability Description**: The offline declaration of supported source forms, operations, versions, optional features, and parser requirements.
- **Distribution Receipt**: The machine-readable link among source revision, package and contract versions, built artifacts, digests, environment, and verification evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every conformance fixture, 100% of valid discovered source items are publicly inspectable and have exactly one final disposition.
- **SC-002**: For every successful analysed result, 100% of analysed segments and discourse nodes have valid, in-bounds, reconstructable source anchors.
- **SC-003**: Every successful preparation reports complete primary-discourse and retained-content coverage; any unexplained coverage deficit prevents success.
- **SC-004**: An independent consumer can answer what was received, retained, transformed, analysed, excluded, and why using only one public result or one completed-stage failure.
- **SC-005**: Every induced lifecycle failure retains all and only the safe evidence completed before the failed stage, with the expected stable category and retryability.
- **SC-006**: Automated reconciliation finds zero mismatches among documented symbols, runtime exports, enum values, signatures, serialized fields, statuses, and error categories.
- **SC-007**: Every documented analysis status is produced by at least one conformance test, and no production execution produces an undocumented status.
- **SC-008**: Repeated cached and uncached runs of the same immutable semantic request produce byte-equivalent canonical semantic payloads and identical semantic digests.
- **SC-009**: Changing any semantic input named in FR-041 changes the relevant semantic identity in 100% of contract mutation tests.
- **SC-010**: A clean installation of the built core distribution imports, reports capabilities, serializes contracts, and runs core conformance tests without research, training, or optional source-format packages.
- **SC-011**: A representative downstream adapter completes integration using zero private `isanlp_rst` imports and zero consumer-side reconstruction of provider evidence.
- **SC-012**: A second supported development machine installs and verifies the repository's committed artifact and receipt without rebuilding it.
- **SC-013**: Artifact inspection finds zero cases where incompatible public contracts share the same package version.
- **SC-014**: On the reference local development machine, preparation excluding model inference completes within 2 seconds for a 100,000-character source and within 15 seconds for a 1,000,000-character source, measured over five runs after one warm-up, with every run meeting the threshold.
- **SC-015**: The dated production-library comparison covers every practice named in FR-045 and leaves zero unclassified gaps.
- **SC-016**: Direct inspection of every release artifact and receipt finds zero missing required fields, digest mismatches, unidentified source states, or unverified compatibility claims.

## Assumptions

- The product remains a solo, local Python library rather than a hosted or multi-user service.
- Feature 002's production ingest behaviour remains the baseline unless this specification explicitly strengthens the public contract.
- Parser mathematics and trained architecture remain unchanged by this feature.
- “Complete evidence” means evidence `isanlp_rst` genuinely creates, consumes, validates, or derives as provider authority.
- Downstream projects translate the provider contract into their own domain-specific reporting and unavailable/non-use semantics.
- Raw source text is omitted from default failure diagnostics; an explicitly enabled diagnostic mode may be evaluated during planning.
- Durable local release artifacts are intentionally version-controlled so development machines can consume the same immutable build without rebuilding.
- The current contract change is expected to require a new major package version and a new serialized contract version; planning will determine the exact versions after compatibility analysis.
- If implementation touches Docling or DocLang interpretation, fixtures, harvest, boundaries, or documentation, current upstream specifications and package releases will be reverified before those changes are designed or made.
