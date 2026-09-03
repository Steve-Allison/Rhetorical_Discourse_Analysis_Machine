# Feature Specification: Aggregate Analysis Contract

**Feature**: `007-aggregate-contract`

**Created**: 2026-09-02

**Reconciled**: 2026-09-03

**Status**: Complete

## User Story 1 — Receive trustworthy aggregate records (Priority: P1)

As an analyst, I can request several native techniques over one exact source and receive
one self-validating aggregate whose requests, outcomes, identities, and lineage cannot
contradict one another.

**Independent test**: Construct valid and adversarial requests, results, capability
records, and lineage references; valid records round-trip byte-identically and every
cross-field contradiction is refused.

### Acceptance scenarios

1. A text request is accepted only when its source digest matches the text.
2. Structured input is accepted only for a declared structured-input technique.
3. Every native result retains its exact provider-owned payload and source identity.
4. Every lineage reference exactly matches its carried consumer and upstream results.
5. Persisted records reject duplicate JSON keys, unknown contracts/versions, and digest tampering.

## User Story 2 — Run providers independently (Priority: P2)

As the machine owner, I can run any requested subset of providers and receive one
explicit outcome per represented technique without retries, suppression, or identity
contamination.

**Independent test**: Mix successful, unavailable, malformed, and failing deterministic
providers; each produces its own outcome and no provider changes another's declaration.

### Acceptance scenarios

1. Capability inspection constructs no inference model/client and calls no provider.
2. A missing, unavailable, or input-incomplete provider returns a stable unavailable outcome.
3. A typed provider failure suppresses no success and is invoked exactly once.
4. A success is accepted only when provider, contract, provenance, source, formalism, and technique match the declaration.
5. A typed failure is accepted only when technique, provider, and operation match the invoked provider; unexpected exceptions propagate as bugs.

## User Story 3 — Trust canonical identities and boundaries (Priority: P3)

As the machine owner, I can rely on every framework identity and production member being
derived from its canonical authority and confined to the one supported distribution.

**Independent test**: Regenerate the framework projection and inspect source/artifact
boundaries; projection bytes match Central and no production path reaches `workbench`.

### Acceptance scenarios

1. All seven boundaries and eRST resolve to canonical Central concepts without redefining their native inventories.
2. The production namespace is exactly root package `rdam` with technique subpackages.
3. Production imports never reach `workbench` directly or transitively.
4. A built wheel admits only `rdam/` and distribution metadata.

## Requirements

- **FR-001**: The machine MUST preserve each technique's native payload without normalization or merging.
- **FR-002**: Aggregate requests MUST bind all inputs and outcomes to one exact source identity.
- **FR-003**: Requested techniques, formalism choices, structured inputs, and upstream techniques MUST be unique.
- **FR-004**: Structured input MUST be accepted only for Dung and IBIS unless the canonical registry changes.
- **FR-005**: Capability records MUST list every boundary exactly once in canonical order with canonical CURIE and input mode.
- **FR-006**: Capability inspection MUST construct no model/client and invoke no analysis.
- **FR-007**: The machine MUST emit explicit result, unavailable, or failed outcomes and MUST NOT retry.
- **FR-008**: A provider result MUST agree with its declaration on provider id, contract version, provenance, formalism, technique, and source.
- **FR-009**: A typed provider failure MUST agree with the invoked provider's technique, provider id, and operation.
- **FR-010**: Unexpected provider exceptions MUST propagate without relabelling.
- **FR-011**: Explicit lineage MUST exactly identify carried consumer and upstream results; the machine MUST NOT infer derivations.
- **FR-012**: Canonical persistence MUST be digest-verified and reject duplicate keys and unsupported contracts or versions.
- **FR-013**: Framework identities MUST derive from the vendored Central taxonomy projection.
- **FR-014**: Production source MUST NOT import `workbench` and production artifacts MUST NOT contain it.
- **FR-015**: The supported composition MUST contain exactly RST, PDTB, SDRT, Toulmin, Walton, Dung, and IBIS while remaining lazy at construction.

## Success criteria

- **SC-001**: 100% of required cross-field contradiction classes have causal rejection tests.
- **SC-002**: Every requested/represented technique has exactly one independently inspectable outcome.
- **SC-003**: Withholding one provider changes zero serialized capability bytes for every other boundary.
- **SC-004**: Valid aggregate and capability records round-trip to byte-identical canonical JSON.
- **SC-005**: All eight framework identities equal the current vendored Central projection.
- **SC-006**: Production-boundary inspection reports zero ownership, import, dependency, or artifact violations.
- **SC-007**: The seven-provider production composition constructs zero inference clients/models.

## Scope

This feature owns aggregate contracts, coordination, identity projection, canonical
serialization, and production-boundary enforcement. Technique-native schemas and model
inference remain owned by their provider subpackages. Cross-provider derivation remains
caller-declared; the machine does not invent analytical transformations.
