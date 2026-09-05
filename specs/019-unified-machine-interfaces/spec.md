# Feature Specification: Unified Machine Interfaces

**Feature Directory**: `specs/019-unified-machine-interfaces`

**Feature Branch**: No new branch; planning on existing `master`.

**Created**: 2026-09-04

**Status**: Implementation authorised; baseline work started.

**Input**: One analysis engine with primary Python and unified `rdam` command-line interfaces, plus optional local HTTP parity. Explicit techniques and model configuration; files or stdin; complete canonical JSON; separate summaries; truthful failure/partial-success signals; caller-supplied Dung/IBIS structures; no `rdam-rst` compatibility wrapper. Owner requested a carefully reviewed, world-class API and CLI design.

**Quality floor**: World-class is mandatory for every artifact and stage: planning,
research, contracts, implementation, tests, documentation and verification. No
stage may knowingly defer its own correctness to a later polishing pass. Passing
a checklist, schema or numerical threshold is necessary evidence where specified,
not a substitute for reviewing the actual work or repairing a known defect.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Integrate once through the machine (Priority: P1)

Steve configures the machine, selects techniques, and receives their complete native analyses through the Python API. Source acquisition, preparation, selection, configuration and failure semantics have one authority shared by every interface.

**Why this priority**: The other interfaces must project a coherent public API rather than repair its omissions independently.

**Independent Test**: A direct caller discovers capabilities, prepares a source without inference, and analyses an explicit selection with real providers and independently inspectable results.

**Acceptance Scenarios**:

1. **Given** configured and unconfigured providers, **when** capabilities are requested, **then** all seven boundaries and accepted source forms are reported without loading weights, constructing model clients or making network calls.
2. **Given** one source and several techniques, **when** analysis runs, **then** the source is inventoried once, identical content requirements share a projection, and requested outcomes retain their order and native evidence.
3. **Given** explicit per-technique configuration, **when** a result is persisted, **then** the effective non-secret configuration and its relationship to model identity and cache identity are recoverable.
4. **Given** eRST is selected through RST, **when** the result is inspected by requested boundary, **then** RST has one outcome containing the unchanged eRST native formalism.

### User Story 2 - Use one predictable terminal command (Priority: P1)

Steve and his agents use `rdam` to discover, prepare, analyse, inspect schemas and read summaries. Scripts can distinguish an analysis result from diagnostics without terminal-dependent behavior.

**Why this priority**: The terminal is a primary product interface, not a demonstration wrapper.

**Independent Test**: An installed CLI subprocess consumes a file and stdin, emits a loadable canonical result, and reports each documented completion class through the specified exit status.

**Acceptance Scenarios**:

1. **Given** a document path and explicit techniques, **when** analysis is requested, **then** one complete canonical result is written to stdout or the selected output file; diagnostics use stderr.
2. **Given** non-text stdin, **when** its source form is omitted, **then** no content sniffing silently changes the documented stdin interpretation; explicit form selection is available.
3. **Given** an existing output file or an output path naming an input, **when** a command runs, **then** it cannot destroy the input or overwrite the existing result without the specifically documented authorization.
4. **Given** a saved result, **when** a summary is requested, **then** no analysis or model invocation occurs and the original full result remains unchanged.
5. **Given** help or a usage error, **when** displayed in a terminal or pipeline, **then** grammar, examples, error destinations and exit behavior are consistent and require no interactive prompt.

### User Story 3 - Supply formal structures explicitly (Priority: P1)

Steve supplies a Dung framework or IBIS graph, optionally alongside a document and other techniques. If a structure was derived from an earlier native result, he records that derivation explicitly.

**Why this priority**: Formal structures are not interchangeable with prose; inventing them silently changes the analysis.

**Independent Test**: Valid and invalid caller-owned Dung/IBIS fixtures traverse all interfaces, including structured-only requests with no fabricated document.

**Acceptance Scenarios**:

1. **Given** only explicit structures, **when** analysis runs, **then** source identity binds those structures without inserting dummy text or running source inventory.
2. **Given** a missing structure, **when** its technique is requested, **then** its outcome explicitly reports missing structured input; other valid requested outcomes survive.
3. **Given** a retained upstream result and a failing newly requested technique, **when** overall status is computed, **then** retained success cannot count as newly requested success.
4. **Given** a declared derivation, **when** its source or upstream identity is inconsistent, **then** the request is rejected before execution rather than inventing lineage.

### User Story 4 - Call the same machine over local HTTP (Priority: P2)

A local application submits the same requests and consumes the same records without importing Python. Starting the server is optional; its configuration is explicit and fixed for its lifetime.

**Why this priority**: HTTP extends access without creating a second analysis service or configuration authority.

**Independent Test**: A real loopback server processes the same serialized request as the Python and CLI paths, preserving analytical outcomes and documented operational differences.

**Acceptance Scenarios**:

1. **Given** the same configuration and materialized request, **when** submitted through each interface, **then** analytical results, boundary assignments, diagnostics and completion classification agree.
2. **Given** malformed framing, unsupported media, excessive input or an unexpected internal defect, **when** HTTP handles the request, **then** the response follows an explicit safe error contract and cannot report successful analysis.
3. **Given** a valid aggregate with some or no requested successes, **when** returned over HTTP, **then** transport success remains distinguishable from the aggregate's analytical completion status.
4. **Given** a request containing a local path or URL as provenance, **when** HTTP processes it, **then** the server does not read or fetch that location.

### User Story 5 - Consume the analysis directly with AI (Priority: P1)

Steve gives the canonical result to an AI consumer without translating internal
schemas or scraping a prose summary. The result explains the native analytical
roles, evidence coordinates, reported states and limitations inline.

**Why this priority**: Machine-readable syntax alone does not make an analysis
safe or immediately intelligible to another model.

**Independent Test**: A schema-driven consumer follows the inline guide to each
native result and its source evidence, with no repository lookup, inferred
assessment or further model call.

**Acceptance Scenarios**:

1. **Given** any supported native result, **when** delivered in the aggregate,
   **then** its purpose, role meanings, evidence references and limitations are
   available inline, while the native record remains unchanged.
2. **Given** missing assessments, inferred relations, literal matches or rejected
   candidates, **when** consumed, **then** these cannot be relabelled as explicit
   source assertions, assessed negatives, calibrated certainty or accepted edges.
3. **Given** a large saved aggregate, **when** a technique subset is explicitly
   selected, **then** whole selected outcomes are retained and all excluded
   outcomes are identified; the original completion status is not recalculated.
4. **Given** instructions embedded in source content, **when** exposed to an AI,
   **then** the contract identifies that content as untrusted evidence, not
   operational instructions or permission to invoke tools.
5. **Given** an omitted Walton assessment, an ungrounded claim of an explicit
   Toulmin warrant, or an incidental source match for a metadata label, **when**
   a provider validates its proposed result, **then** it rejects or explicitly
   represents the unresolved state under the corrected native contract; no
   presentation warning substitutes for fixing the underlying data.
6. **Given** a structurally valid analysis citing a genuine but irrelevant or
   misattributed passage, **when** analytical quality is evaluated, **then** the
   source-support error is detected independently of quotation validity.
7. **Given** an empty result, all-open assessments or excessive abstention,
   **when** tested against source-grounded expectations,
   **then** missing findings and incorrect states fail the relevant checks.
8. **Given** an implementation candidate, **when** tested and cold-critiqued,
   **then** actual outputs and concrete errors are inspected and substantiated
   defects are repaired; no owner-annotation or certification workflow is needed.

### Edge Cases

- Empty text, retained-only content, empty projections and valid empty analytical findings remain distinct from missing input and failures. Empty Dung/IBIS structures remain subject to their native validators.
- Unknown/duplicate techniques, repeated singleton options, ambiguous source selection, invalid JSON, duplicate object keys, non-finite numbers, invalid Unicode and malformed base64 are rejected consistently.
- Equivalent source bytes with different declared names/origins are not falsely asserted to be identical provenance-bearing records.
- Model resolution failure, invalid per-technique options, optional extras missing, eRST unavailable and invalid model releases remain explicit.
- A typed provider failure preserves valid siblings; an internal programming defect is not downgraded to an ordinary provider failure.
- Output publication failure, broken pipe, interruption, disk exhaustion and source/output aliasing cannot turn truncated bytes into a successful persisted record.
- No inferred retries, hidden model fallback, model-download-on-help, browser-triggered local analysis or unbounded request admission.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Python, CLI and HTTP MUST use one machine and one set of validated semantic request/result contracts; interfaces MUST NOT implement analysis logic.
- **FR-002**: Analysis MUST require a nonempty, ordered, unique explicit technique selection; unknown selections and configuration typos MUST fail before inference.
- **FR-003**: Machine configuration MUST express shared LLM selection, per-technique overrides and all existing public RST model/policy controls without requiring callers to construct internal adapters. Effective settings and precedence MUST be explicit.
- **FR-004**: Configuration MUST be immutable after machine construction; credentials MUST stay outside request/result/configuration files and must not appear in diagnostics. No implicit retry or fallback model is permitted.
- **FR-005**: Capabilities MUST report every technique, source form, relevant formalism, missing dependency and configuration limitation without constructing a model client, loading weights, analysing or accessing a network.
- **FR-006**: Preparation MUST be a public model-free operation exposing complete inventory, policies, warnings, retained content, anchors and any explicitly selected provider projections. It MUST NOT be misrepresented as analysis or as a replay cache.
- **FR-007**: Analysis MUST use one source inventory and one projection per distinct declared requirement per invocation; preparation and analysis MUST share this implementation.
- **FR-008**: All current source forms MUST remain available subject to their declared optional dependencies. File, bytes, text and EDU constructors MUST share source identity, validation and form-selection rules.
- **FR-009**: Request serialization MUST preserve binary sources, exact source metadata, structured inputs, formalism choices and explicit upstream lineage. Remote transport MUST never interpret provenance as permission to read a file or fetch a URL.
- **FR-010**: Every requested boundary MUST have exactly one outcome in request order; native result technique/formalism identity MUST remain unchanged, including eRST under RST.
- **FR-011**: A persisted aggregate MUST identify newly requested boundaries separately from retained upstream results and classify completion as complete, partial or unsuccessful using only newly requested outcomes.
- **FR-012**: Dung and IBIS MUST accept only explicit caller-supplied structures; structured-only requests MUST have truthful deterministic identity without dummy prose. Mixed requests MUST preserve explicit lineage and distinct native payloads.
- **FR-013**: CLI and HTTP failures MUST distinguish invalid requests, source/preparation failures, unavailable providers, typed provider failures, internal defects and output/transport failures. Safe machine-readable diagnostics MUST exclude private source content, secrets and arbitrary exception text.
- **FR-014**: The unified `rdam` CLI MUST expose capabilities, preparation, analysis, saved-result summaries, schema discovery, version and optional local serving. The old `rdam-rst` installed command MUST be removed, not wrapped.
- **FR-015**: CLI input grammar MUST define mutually exclusive source modes, stdin ownership, explicit source form selection, literal paths, technique/formalism selection and structured-input files. No shell expansion or implicit remote fetch is permitted inside the program.
- **FR-016**: Machine-output commands MUST emit one canonical JSON record, with only documented framing, to stdout or the selected file. Diagnostics MUST use stderr; redirection and terminal detection MUST NOT change analytical data.
- **FR-017**: CLI exit statuses MUST distinguish complete analysis, partial analysis, no requested successes, invalid invocation/request, operational/internal failure and user interruption. Nonzero analytical outcomes MUST still retain their complete canonical result.
- **FR-018**: File output MUST be atomic and no-clobber by default, require explicit replacement authorization, reject input/output aliasing, and preserve prior files on failure before publication. A failure after atomic publication MUST report the actual publication state without claiming rollback. Publication errors MUST never be written over the intended result file.
- **FR-019**: Summaries MUST be explicit, deterministic presentation views of a validated saved result, identify incomplete outcomes and native formalisms, preserve full-result access, and perform no inference.
- **FR-020**: HTTP MUST expose equivalent capabilities, preparation, analysis, schemas and version under explicit versioned routes, use one immutable configured machine, and separate HTTP status from analytical completion.
- **FR-021**: The optional server MUST bind only to loopback, reject browser-originated mutation and invalid host/framing/media requests, impose documented body/read/admission limits, and neither serve arbitrary files nor enable permissive cross-origin access.
- **FR-022**: Public record versions, canonicalization, binary encoding and unknown-field behavior MUST be explicit. Existing supported saved results MUST remain readable without invented historical request metadata; old command/API routes need no compatibility wrapper.
- **FR-023**: Result-affecting configuration MUST participate in provider cache identity and be recoverable with results; operational-only variation MUST NOT masquerade as analytical disagreement.
- **FR-024**: Help, examples, schemas and installed entry points MUST describe the same accepted grammar and contracts. Python and CLI use MUST not require running HTTP or installing a separate service architecture.
- **FR-025**: Parity acceptance MUST exercise real internal code through Python, installed CLI subprocesses and real loopback HTTP. External model test doubles MUST be confined to genuinely external boundaries; live/model-backed proof MUST remain separately identified.
- **FR-026**: Verification MUST cover all seven technique boundaries, all current source forms, eRST, each completion/failure class, structured lineage, output safety, core-only installation and formats installation. A skipped external/model test MUST NOT count as verified parity.
- **FR-027**: Delivery MUST preserve analysis-only scope, native evidence, original licensing, the production/workbench boundary and solo-local simplicity; no authentication platform, job service, publication destination or release process is introduced.
- **FR-028**: The canonical aggregate MUST be immediately interpretable by an AI through an inline versioned reading guide describing each native formalism, analytical roles, source coordinates, validation scope and limitations. External documentation MUST NOT be required for basic interpretation.
- **FR-029**: AI-facing descriptions MUST distinguish model interpretation, supplied structures, deterministic computation and source evidence; they MUST preserve native assessment states and never invent confidence, explicitness, abstention, truth, argument strength or cross-technique consensus.
- **FR-030**: An explicit, deterministic saved-analysis selection operation MUST preserve whole selected native outcomes, full evidence context, original analytical status and excluded-outcome identities. It MUST perform no inference, ranking or silent truncation and MUST be equivalent through Python, CLI and HTTP.
- **FR-031**: Walton MUST report exactly one explicit assessment for each critical question of every returned scheme instance. Missing assessments MUST fail validation, not default to open; inability to assess MUST have an explicit state and reason. Addressed assessments MUST carry source-validated evidence, and all counts MUST reconcile with the explicit states.
- **FR-032**: Toulmin MUST record whether each warrant is model-assessed as explicitly stated, reconstructed or undetermined, preserve its source evidence and represent unresolved origin honestly. An explicit-origin assessment MUST cite validated source spans. Qualification counts MUST be named for what they actually measure.
- **FR-033**: Source alignment MUST use provider-declared source-bearing fields, distinguish exact quotation, supporting passage and literal occurrence, retain ambiguous multiple matches, and validate projection identity, coordinates, text and source anchors. Metadata labels and incidental matches MUST NOT become evidential support.
- **FR-034**: Corrected native contracts, prompts, schemas, serialization, caches, summaries and interpretation guides MUST change together under explicit versions. Historical results MUST remain readable as historical evidence; no migration may invent missing assessments, warrant origin or stronger source support.
- **FR-035**: Analytical testing MUST use source-grounded expectations and focused real-model cases, allowing defensible alternative readings. A cold-critic agent MUST inspect actual source/output pairs and relevant implementation/tests. No owner annotation, frozen corpus or bespoke evaluator is required.
- **FR-036**: Tests MUST check findings, Walton states, Toulmin origins, evidence relevance and appropriate unresolved states. Missing findings, provider failures, duplicates and indiscriminate abstention MUST NOT be accepted as successful analysis.
- **FR-037**: Adversarial tests MUST distinguish valid quotations from relevant support, speaker attribution, negation, hypothetical/quoted speech, incomplete context and reconstructed reasoning. Integration tests MUST exercise real production internals; only external boundaries may use test doubles.
- **FR-038**: Verification MUST report actual commands, model/settings, results and unresolved failures. Substantiated critic findings MUST be fixed and regression-tested. No new evaluation engine, approval schema, benchmark gate or certification exercise is required.

### Key Entities

- **Machine configuration**: immutable non-secret provider/model/policy choices plus separate execution settings.
- **Analysis request**: exact source identity and material, ordered requested boundaries, structured inputs, formalism choices and retained upstream results.
- **Preparation request/result**: exact source, optional projection selection, complete preparation evidence and explicit selection-to-projection mapping; no native analysis.
- **Aggregate analysis**: requested scope, ordered boundary outcomes, retained upstream results, unchanged native payloads, effective configuration and derived completion status.
- **Capabilities**: model-free description of source forms, technique/formalism availability and public contract versions.
- **Operation error**: safe structured failure for operations that produced no valid aggregate or failed to publish one.
- **Summary**: derived readable view referring to a validated persisted record, not another analytical result.
- **Reading guide / analysis view**: inline native interpretation metadata and an explicitly selected, loss-declared presentation record; neither is a new analytical formalism.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every active acceptance-matrix row identifies its input, expected outcome and verification route; all required rows pass before feature completion. Interface parity claims require the corresponding executed parity checks.
- **SC-002**: Every completed analysis has exactly one outcome per requested boundary in the specified order; no retained upstream success changes the completion class.
- **SC-003**: Equivalent configured requests produce equal analytical projections across all three interfaces; deterministic model-free cases additionally produce identical canonical bytes apart from documented framing.
- **SC-004**: Help, version, schema discovery, capability discovery and preparation perform zero model-client constructions, weight loads and network calls.
- **SC-005**: Every failure-class and output-safety scenario has an observable expected status; input bytes always remain unchanged, prior output survives rejection/pre-publication failure, and post-publication failure reports the published or uncertain state honestly.
- **SC-006**: Every normative request/configuration field and command option has schema/help documentation and positive/negative acceptance coverage; there are no silently ignored controls.
- **SC-007**: A fresh core installation can discover capabilities and run structured analysis through Python and CLI; adding only the HTTP extra enables the same operations over HTTP without format extras. A formats installation exercises every supported source form.
- **SC-008**: For a single invocation, evidence proves one inventory pass and no repeated inference introduced by rendering, serialization, summaries or interface adaptation.
- **SC-009**: Every supported native formalism has an inline guide whose present-section pointers resolve and whose epistemic examples pass the AI-consumption matrix; selected native records retain their original canonical bytes and every excluded outcome is named.
- **SC-010**: Regression fixtures reproduce the three identified weaknesses before implementation and reject the same invalid proposals afterward; positive, uncertain and historical cases pass through real providers and all three interfaces without fabricated evidence or stale-cache reuse.
- **SC-011**: Required native integrity and adversarial regression cases pass; deliberately invalid proposals fail for the expected reasons.
- **SC-012**: Focused real-model cases are executed and cold-critiqued against source; substantiated errors are repaired and affected tests rerun. Skipped model cases are not reported as passed.
- **SC-013**: Completion reports actual implementation, parity, model and installed-package checks and any remaining failures. Passing tests do not waive a known defect.

## Clarifications

### Session 2026-09-04

- Owner clarification: “the api should be producing the analysis in a suitable way for instant AI usage, right?” Incorporated as US5, FR-028–FR-030 and SC-009. “Instant” means directly interpretable, not a latency guarantee or a promise to fit every model context window.
- Owner direction: “add fixes to the plan for implementation”. Native-contract corrections are required scope (FR-031–FR-034, SC-010), not limitations to explain away. Necessary version changes are planned; implementation is not authorized by this planning instruction.
- Owner direction: strengthen the analytical-quality requirements and tests; “world-class rules apply to EVERYTHING: planning; implementation; tests; EVERYTHING”. Incorporated as the quality floor, FR-035–FR-038 and SC-011–SC-013. This is not authorization to change trained architectures, implement production code or accept weaker work under a different label.

- Latest owner direction: execute the full plan using Spec Kit. Remove the invented owner-review/evaluation machinery; use ordinary tests and cold-critic agents. This supersedes the earlier evaluation requirements and related historical checklist wording; no checklist marker is changed.

## Assumptions

- Owner-approved scope is one person on one machine; Python and CLI are primary and HTTP is optional but fully included in this feature.
- Full production implementation is authorised by the subsequent owner instruction. Commits, branch changes, tagging and external publication remain outside this request.
- Trained architectures, inference mathematics and native framework distinctions are retained. Native evidence/assessment contracts and their validation change where required by FR-031–FR-034; transports preserve the corrected records without reinterpretation. Existing source-format semantics are not redesigned.
- Current model availability is not assumed. Model-free and model-backed verification are separate; configured local artifacts and opted-in external credentials are prerequisites for the corresponding implementation checks.
- Preparation is an inspection operation in this feature. Persisted preparation replay, asynchronous jobs, multi-document batching and cross-technique derivation are not newly introduced by these interface requirements.
