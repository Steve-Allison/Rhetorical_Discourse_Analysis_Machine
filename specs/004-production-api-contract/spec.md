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
4. **Given** a successful primary analysis, **When** a consumer inspects any selected discourse decision, **Then** it can identify the analysed tokens and EDUs, selected split, relation, nuclearity, confidence semantics, uncertainty, and any post-model refinement that determined the returned graph.
5. **Given** a successful eRST completion, **When** a consumer inspects an accepted secondary edge, **Then** it can trace the edge to both endpoints, supporting signals, edge and relation scores, joint selection score, calibration identity, and the decoder receipt that proves the accepted graph satisfied its constraints.
6. **Given** a subdivided analysis, **When** a consumer inspects the result, **Then** it can trace every local unit into the recombined document graph and inspect the deterministic recombination receipt without requiring duplicate full local graphs.
7. **Given** two evidence-detail policies over the same source and immutable model, **When** the requests are compared, **Then** each request records its resolved policy and has a distinct semantic request and cache identity whenever the returned evidence differs.
8. **Given** a caller already has an `RstDocument`, **When** it uses the canonical parser analysis operation directly, **Then** it receives the exact analysed substrate, graph, decision evidence, component identity, and validation/recombination receipts without using production ingest or private imports.

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
- A parser backend emits a complete decoded tree but an adapter attempts to return only its root or another lossy projection.
- Tokenization, EDU capping, context-window truncation, or approximate token-to-source mapping would alter the analysed substrate.
- A relation marker refines a model relation, nuclearity, concept, or confidence after inference.
- An eRST candidate has supporting signals but is rejected, or an accepted edge has multiple supporting signals.
- A decoder accepts no secondary edges but still completes constraint evaluation successfully.
- Two output formalisms or evidence-detail policies would produce different semantic results from otherwise identical inputs.
- A relation label is returned without a declared relation scheme, confidence meaning, calibration identity, or ontology-mapping provenance.
- A model release is validated and reported in provenance, but the runtime loads tokenizer, configuration, or weight bytes from another location or revision.
- A parser adapter fills an unanalysed suffix with midpoint splits, default relations or nuclearities, or fabricated character offsets.
- Capability discovery advertises an archived or deliberately unavailable parser family as an active production backend.

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
- **FR-047**: Every analysis request MUST select a closed, typed output formalism and resolved analysis policy rather than relying on an unvalidated string or hidden backend default.
- **FR-048**: The resolved analysis policy MUST expose output formalism, marker-refinement policy, evidence-detail policy, validation policy, relation-interpretation policy, and every other provider setting that can change the semantic result or returned evidence.
- **FR-049**: The default evidence-detail policy MUST be decision-complete: it MUST expose the selected decision, its provider-computed confidence and uncertainty, and the evidence needed to explain that decision without requiring full model tensors or complete probability charts.
- **FR-050**: A caller MUST be able to request normalized provider-computed score distributions through an explicit evidence-detail policy when those distributions are genuinely produced and can be retained without changing inference mathematics.
- **FR-051**: Any evidence-detail choice that changes returned semantic evidence MUST participate in semantic request, result, and cache identity.
- **FR-052**: Every analysed result MUST expose the exact analysed document substrate, including ordered tokens, EDUs, sentence and paragraph boundaries, token-to-EDU mapping, source anchors, and fidelity or transformation records for the values actually supplied to inference.
- **FR-053**: Context-window truncation, EDU capping, uniform or approximate token allocation, or any other lossy analysis-substrate transformation MUST NOT occur silently; it MUST either fail closed or be explicitly authorized, represented, anchored, and included in semantic identity.
- **FR-054**: Primary inference evidence MUST preserve, for each selected structural decision, the selected split or attachment, relation, nuclearity, provider-computed confidence values, uncertainty values such as normalized split entropy when produced, and stable links to the resulting nodes and edges.
- **FR-055**: When normalized split, relation, nuclearity, or segmentation-boundary distributions are requested and genuinely produced, they MUST be returned in a typed, finite, normalized representation linked to the selected decision.
- **FR-056**: Any marker, rule, ontology, or other post-model refinement MUST preserve a typed before-and-after record containing the original model decision, revised decision, triggering evidence, policy and algorithm identity, and affected graph elements.
- **FR-057**: eRST completion evidence MUST preserve candidate identity, supporting signal identities, edge probability, selected relation and relation probability, joint selection score, calibration identity, decoder policy identity, and the complete provider decoder receipt for accepted and rejected decisions at the declared evidence level.
- **FR-058**: Accepted secondary edges MUST link to both discourse endpoints and every supporting signal, and every returned supporting signal MUST identify the candidates or accepted edge decisions it supports so no public signal is orphaned.
- **FR-059**: Model identity MUST be composite when production analysis uses multiple learned or rule-governed components, covering primary parser, segmenter, marker refinement, eRST detector/scorer, decoder, calibration, relation inventory, and ontology mapping whenever each component participates.
- **FR-060**: Every successful analysis MUST expose a typed validation receipt containing validation policy and version, stable check identifiers, per-check outcomes or counts, overall disposition, warnings, and a recomputable receipt digest.
- **FR-061**: Every multi-unit analysis MUST expose a typed recombination receipt containing local unit result identities, local-to-global node/edge/segment mappings, boundary and nuclear-spine inputs used for stitching, deterministic decisions, warnings, timings, and recomputable identity.
- **FR-062**: Analysis anchors for relations and secondary edges MUST cover both endpoints and any supporting signal anchors; a parent-only or source-only endpoint projection is insufficient.
- **FR-063**: Every returned relation and confidence MUST declare its relation scheme, confidence kind, calibration identity when applicable, and ontology-mapping provenance; an ontology concept MUST NOT be presented as mapped when the provider only copied a raw relation label.
- **FR-064**: No production parser adapter MAY discard decoded tree depth, decision scores, boundary scores, unit mappings, decoder receipts, or other provider-owned inference evidence required by this contract; adapters MUST prove lossless handoff from backend output to the public contract.
- **FR-065**: Raw tensors, embeddings, hidden activations, unrestricted cubic parsing charts, training-only gold labels, research-corpus records, and private workbench state MUST remain internal unless a future provider-owned requirement explicitly promotes a bounded value.
- **FR-066**: When the provider does not genuinely compute a named evidence value, the contract MUST represent that capability as unavailable or the value as not produced; it MUST NOT fabricate, approximate, or infer provider evidence merely to populate a field.
- **FR-067**: Conformance tests MUST audit each production backend and every primary-to-eRST, marker-refinement, subdivision, recombination, validation, serialization, and cache handoff for retained decision evidence and fail on any unexplained loss.
- **FR-068**: The public parser facade MUST expose one canonical typed parser-analysis result containing the exact analysed substrate, validated graph, primary and eRST decision evidence, composite component identity, refinements, recombination receipt when applicable, validation receipt, and semantic identity; a graph-only parser operation MAY remain as an explicitly documented convenience projection but MUST NOT be the authority used by production ingest.
- **FR-069**: Every immutable model or component identity claimed by a result MUST identify the exact tokenizer, configuration, weights, calibration, inventory, rules, and ontology bytes actually loaded for that execution; validating one release while loading another artifact or remote revision MUST fail closed.
- **FR-070**: The production parser MUST NOT synthesize midpoint splits, default relation or nuclearity labels, sequential character offsets, or any other apparently analysed decision for content the model did not analyse; missing alignment or capacity-safe coverage MUST produce a typed failure unless an explicit loss policy represents the exact transformation without fabricating inference evidence.
- **FR-071**: Capability discovery and the public-surface inventory MUST distinguish the active ModernBERT production backend from archived or deliberately unavailable parser families and MUST NOT advertise a family, release, evidence level, or output formalism that the installed runtime cannot execute through the canonical typed parser-analysis operation.

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
- **Parser Analysis Result**: The provider-owned result returned for an already-constructed `RstDocument`, containing the exact analysed substrate, validated graph, decision evidence, component identity, refinements, optional recombination receipt, validation receipt, execution facts, and semantic identity without source-ingest preparation evidence.
- **Analysis Policy**: The closed caller-selected and fully resolved semantic policy for output formalism, evidence detail, refinement, validation, relation interpretation, and loss handling.
- **Analysed Document**: The exact ordered tokens, EDUs, boundaries, mappings, source anchors, and fidelity records actually supplied to analysis.
- **Primary Inference Evidence**: Decision-linked segmentation, tree, split, relation, nuclearity, confidence, uncertainty, distribution, and refinement evidence produced by the primary pipeline.
- **eRST Completion Evidence**: Candidate, signal, score, calibration, decoder, acceptance/rejection, and constraint-receipt evidence produced by secondary-edge completion.
- **Composite Analysis Identity**: The exact identity of every learned, rule-based, calibrated, decoded, relation-inventory, and ontology component that affected the result.
- **Recombination Receipt**: The deterministic account of how local analysis units map into the final document graph.
- **Validation Receipt**: The typed check-by-check evidence that the assembled analysis satisfied the selected production validation policy.
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
- **SC-017**: Across every production backend fixture, 100% of returned discourse nodes and edges trace to the exact analysed tokens and EDUs and to the provider decisions that created or refined them.
- **SC-018**: Loss-audit mutation tests detect 100% of deliberately removed decoded spans, selected scores, boundary scores, refinement records, signal links, decoder receipts, recombination mappings, and validation checks.
- **SC-019**: Every accepted secondary edge in the eRST conformance corpus has two valid endpoint anchors, at least one valid support path when supporting signals exist, and score semantics that reproduce its recorded decoder ordering inputs.
- **SC-020**: Every post-model refinement fixture preserves both the original and revised decision with the exact triggering evidence and algorithm identity; zero overwritten decisions lack provenance.
- **SC-021**: Every subdivided conformance fixture maps 100% of local nodes, edges, and segments into exactly one final result location and reproduces the recombination receipt digest.
- **SC-022**: Every successful analysis exposes a validation receipt whose overall disposition agrees with every required check and whose digest recomputes from exposed values.
- **SC-023**: Decision-complete and distribution-requested evidence policies each round-trip deterministically, and changing policy changes semantic request/cache identity in 100% of mutation tests where returned evidence differs.
- **SC-024**: Installed-contract inspection finds zero public raw tensors, embeddings, hidden activations, unrestricted parsing charts, training-only gold fields, or private research/workbench values.
- **SC-025**: A direct parser consumer explains every returned node, primary edge, secondary edge, refinement, and validation/recombination decision using one public parser-analysis result and zero private imports; production ingest embeds that same semantic parser result rather than reconstructing it from a graph-only projection.
- **SC-026**: For every immutable production fixture, byte-inventory validation proves that every loaded tokenizer, configuration, weight, calibration, relation-inventory, rule, and ontology component matches the exact component identity reported in the result; deliberate path or revision substitution fails in 100% of mutation tests.
- **SC-027**: Capacity, truncation, alignment, and capability mutation tests produce zero fabricated parser decisions and zero advertised-but-unexecutable parser families or evidence levels.

## Assumptions

- The product remains a solo, local Python library rather than a hosted or multi-user service.
- Feature 002's production ingest behaviour remains the baseline unless this specification explicitly strengthens the public contract.
- Parser mathematics and trained architecture remain unchanged by this feature.
- “Complete evidence” means evidence `isanlp_rst` genuinely creates, consumes, validates, or derives as provider authority.
- Decision-complete evidence is the default balance: retain selected decisions, their confidence and uncertainty, and explanatory receipts; expose normalized distributions only when explicitly requested and genuinely produced.
- Scientific internals that do not constitute stable production evidence remain private even when they are temporarily available during inference.
- Downstream projects translate the provider contract into their own domain-specific reporting and unavailable/non-use semantics.
- Raw source text is omitted from default failure diagnostics; an explicitly enabled diagnostic mode may be evaluated during planning.
- Durable local release artifacts are intentionally version-controlled so development machines can consume the same immutable build without rebuilding.
- The current contract change is expected to require a new major package version and a new serialized contract version; planning will determine the exact versions after compatibility analysis.
- If implementation touches Docling or DocLang interpretation, fixtures, harvest, boundaries, or documentation, current upstream specifications and package releases will be reverified before those changes are designed or made.
