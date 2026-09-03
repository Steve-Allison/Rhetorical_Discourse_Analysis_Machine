# Research: Aggregate Analysis Contract

## D1 — Current topology

**Decision**: The aggregate authority is the root `rdam` package; all seven providers are
subpackages in the same distribution.

**Rationale**: This is the 2026-09-02 owner ruling already implemented by Feature 010 and
completed by Feature 006.

**Alternatives considered**: Restoring `machine/rdam` or separate provider distributions
would create duplicate authority and violate the current package boundary.

## D2 — Provider trust boundary

**Decision**: The machine validates both success and typed-failure envelopes against the
provider declaration. Success identity includes provider id, contract version,
provenance, source, declared formalism, and formalism technique. Failure identity includes
the boundary technique, provider id, and `analyse` operation.

**Rationale**: Provider output is untrusted until it satisfies its own declaration. A
misidentified failure must not silently become another technique's outcome.

**Alternatives considered**: Trusting typed models alone is insufficient because their
fields can be internally valid but belong to a different provider or technique.

## D3 — Request and lineage integrity

**Decision**: Structured inputs are valid only for the two declared structured-input
techniques. Persisted capability entries must use canonical identities and the canonical
structured-input flag. Every lineage reference must exactly match both its consumer and
upstream result identities, provider contracts, and model identity.

**Rationale**: Digests establish artifact identity but do not make surrounding metadata
truthful. Cross-field agreement must be enforced at the aggregate boundary.

**Alternatives considered**: Allowing arbitrary structured input for future techniques
would add hypothetical configurability and weaken the current contract.

## D4 — Native payload and execution semantics

**Decision**: Native payloads remain opaque and byte-semantically preserved. The machine
does not retry, derive, merge, or suppress provider results.

**Rationale**: Each analytical theory owns its result shape and retry policy. The
aggregate owns only coordination, identity, and explicit outcomes.

**Alternatives considered**: A common node/edge model would collapse theory-native
semantics; orchestration-generated derivations remain outside this feature.

## D5 — Ontology and production boundary

**Decision**: Continue deriving the packaged identity projection from the vendored
Central taxonomy and enforce one production import root, `rdam/`.

**Rationale**: This preserves one canonical ontology authority and one distributable
production boundary.

**Alternatives considered**: Hand-maintained identifiers or per-provider wheels would
duplicate authority.
