# Feature Specification: Shared Runtime Hardening

**Feature Branch**: `018-shared-runtime-hardening`

**Created**: 2026-09-03

**Status**: Complete

**Input**: Owner-approved Feature 018 plan to remediate shared services while explicitly deferring the universal source pipeline.

## User Scenarios & Testing

### User Story 1 - Trust Immutable Native Records (Priority: P1)

As the machine owner, I can retain a result or request without caller mutation changing its meaning or digest later.

**Independent Test**: Construct nested payloads from mutable dictionaries/lists, mutate both the originals and exposed containers, and verify the record and canonical bytes remain unchanged.

**Acceptance Scenarios**:

1. **Given** nested caller containers, **When** a contract model validates them, **Then** it owns a recursive immutable copy with the same JSON representation.
2. **Given** a historical native result without `source_revision`, **When** it loads, **Then** its original `1.0.0` bytes round-trip exactly.
3. **Given** aggregate and RST records, **When** canonical bytes are calculated, **Then** both use the same RFC 8785/SHA-256 kernel.

### User Story 2 - Receive Coherent Provider Identity and Failures (Priority: P1)

As a caller, I receive complete source/model provenance and identical LLM input/error semantics from every LLM-backed technique.

**Independent Test**: Inspect all seven production declarations and exercise null, blank, malformed-model, and LLM-error cases across PDTB, SDRT, Toulmin, and Walton.

**Acceptance Scenarios**:

1. **Given** a newly available provider, **When** its declaration validates, **Then** its source revision is non-empty.
2. **Given** a bare model name, **When** it is configured, **Then** its canonical identity is `openai:<model>` everywhere.
3. **Given** null or blank text, **When** an LLM provider validates it, **Then** it returns `text_required` or `empty_source_text` respectively, before client construction.

### User Story 3 - Run Independent Techniques Safely in Parallel (Priority: P1)

As an analyst, I receive faster independent analysis without nondeterministic result ordering or hidden failure conversion.

**Independent Test**: Force reverse completion order, overlap different providers, invoke one provider instance concurrently, and inject typed and unexpected failures.

**Acceptance Scenarios**:

1. **Given** independent requested techniques, **When** analysis runs, **Then** at most the configured workers overlap and the default is four.
2. **Given** completion in any order, **When** the aggregate is returned, **Then** upstream results are first and requested outcomes and lineage retain request order.
3. **Given** a shared provider instance, **When** separate machines call it concurrently, **Then** its calls are serialized.
4. **Given** an unexpected implementation exception, **When** one task fails, **Then** pending tasks are cancelled and the original exception propagates.

### User Story 4 - Reuse Exact Successful Results Explicitly (Priority: P2)

As the machine owner, I can opt into a local persistent cache without risking stale, corrupt, failed, or irreproducible reuse.

**Independent Test**: Exercise every cache-key input, single flight, clean/dirty revisions, corruption, atomic permissions, and failed/unavailable outcomes.

**Acceptance Scenarios**:

1. **Given** no cache directory, **When** the machine runs, **Then** no persistent cache is read or written.
2. **Given** a clean exact revision and identical request/declaration, **When** a successful result already exists, **Then** it is digest- and contract-validated and reused.
3. **Given** a dirty, missing, or unknown revision, **When** analysis runs, **Then** caching is bypassed.
4. **Given** a corrupt or request-incompatible entry, **When** it is read, **Then** it is deleted with a warning and recomputed.
5. **Given** concurrent identical misses, **When** they complete, **Then** one provider call is made and waiters recheck the cache.

## Requirements

### Functional Requirements

- **FR-001**: One machine-owned implementation MUST define canonical JSON projection, RFC 8785 bytes, SHA-256 semantic identity, byte/file SHA-256, and I-JSON validation.
- **FR-002**: Native payloads and structured inputs MUST be copied and recursively immutable while retaining native JSON mapping/list equality and wire types.
- **FR-003**: `Machine.providers` MUST expose an immutable mapping.
- **FR-004**: Aggregate/native contract version MUST remain `1.0.0`, and pre-018 canonical bytes MUST remain compatible.
- **FR-005**: Persisted provenance MUST keep `source_revision` optional for historical records.
- **FR-006**: Every newly constructed available provider declaration MUST carry a non-empty source revision.
- **FR-007**: Generic installed-version, build/checkout revision, provider provenance, source-file identity, typed failure, text validation, and LLM-error conversion MUST have one shared owner and no provider base class.
- **FR-008**: Existing provider `source_identity()` functions MUST remain compatibility wrappers.
- **FR-009**: Null LLM text MUST map to `text_required`; blank text MUST map to `empty_source_text`; RST and Dung/IBIS input semantics MUST remain unchanged.
- **FR-010**: One model-identity parser MUST serve configuration, capability, client construction, provider identity, and provenance.
- **FR-011**: Bare names MUST normalize to OpenAI; supported explicit prefixes MUST remain unchanged; malformed/unsupported identities MUST be unavailable until attempted construction raises a precise configuration error.
- **FR-012**: One `asyncio.timeout` wall-clock budget MUST cover transport retries, output retries, backoff, and the active request; external cancellation MUST propagate unchanged.
- **FR-013**: Provider SDK retries MUST be disabled and provider HTTP timeouts MUST not exceed the shared deadline.
- **FR-014**: Lazy agent construction MUST be thread-safe.
- **FR-015**: Frozen `ExecutionPolicy` MUST default to four workers/no cache and accept worker counts from one through seven.
- **FR-016**: Independent techniques MUST execute concurrently with deterministic upstream/outcome/lineage order.
- **FR-017**: Typed provider failures MUST remain isolated; unexpected defects MUST propagate after pending cancellation.
- **FR-018**: Calls to one provider instance MUST serialize across concurrent machine use while different providers may overlap.
- **FR-019**: Persistent caching MUST be opt-in through an explicit directory and cache only successful native results.
- **FR-020**: Cache identity MUST include source, technique, formalism, structured input, derivation, provider contract, complete provenance, and model identity.
- **FR-021**: Dirty, missing, empty, and unknown source revisions MUST bypass caching.
- **FR-022**: Cache misses for one key MUST use in-process single flight with a post-lock cache recheck.
- **FR-023**: Cache writes MUST be atomic with owner-only directory/file permissions.
- **FR-024**: Every hit MUST validate envelope, digest, declaration, request, and source; invalid entries MUST be removed, warned, and recomputed.
- **FR-025**: Failed and unavailable outcomes MUST never be cached.
- **FR-026**: Graphify query timestamps MUST be ignored and absent from version control.
- **FR-027**: This feature MUST NOT change `specs/017-universal-source-pipeline/`, create `rdam/ingest/`, or alter Docling, DocLang, Markdown, harvest, preparation, or source-pipeline behavior.

## Success Criteria

- **SC-001**: Deep-mutation tests cannot change a validated record or its digest.
- **SC-002**: Historical no-revision fixture and all existing `1.0.0` serialization tests round-trip byte-identically.
- **SC-003**: All seven production providers expose a source revision; all four LLM providers pass one consistency suite.
- **SC-004**: Deadline, cancellation, retry-budget, ordering, overlap, isolation, and provider-lock tests are deterministic and network-free.
- **SC-005**: Cache tests cover hits, misses, every key component, bypass, validation, corruption recovery, permissions, atomic cleanup, single flight, and non-caching outcomes.
- **SC-006**: New shared-runtime modules sustain 100% statement and branch coverage.
- **SC-007**: The deterministic mutation gate kills every required critical mutant.
- **SC-008**: All owner-specified repository, stress, production-boundary, build, artifact, and clean-install gates report zero failures, subject only to explicitly reported local model prerequisites.

## Scope Boundary

Technique-native schemas, RST inference behavior, universal source preparation, format parsing, trained models, publication, distributed cache infrastructure, TTLs, and multi-user/enterprise mechanisms are unchanged or excluded.
