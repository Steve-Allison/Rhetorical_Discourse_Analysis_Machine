# Research: RST Provider Adapter

## D1 — Canonical adapter boundary

**Decision**: `rdam.rst.provider.RstProvider` is the only machine-facing adapter and
delegates analysis to `ProductionIngestor` and `Parser` public contracts.

**Rationale**: The single-package ruling superseded the historical `rdam_rst`
distribution. Recreating it would duplicate authority.

**Alternatives considered**: A second adapter package or direct predictor calls would
bypass the canonical production contract.

## D2 — Published and local capability

**Decision**: A known published parser version is available without a network/model
probe. A local release is available only after `load_model_release` validates safe
identity, strict manifest, compatibility, membership, sizes, and hashes. That validation
is cached once per provider; inference construction remains deferred.

**Rationale**: Manifest presence alone does not establish that a release can run and can
misreport corrupt, incompatible, malformed, or path-escaping releases as available.

**Alternatives considered**: Presence-only inspection is false confidence. Revalidating
multi-gigabyte hashes on every declaration is correct but needlessly expensive.

## D3 — Local licence provenance

**Decision**: A valid local release reports the licence from its validated manifest. An
invalid local release reports an explicit unknown/unavailable licence rather than
claiming the published-model licence.

**Rationale**: Provenance must describe the configured weights, not a fallback family.

**Alternatives considered**: Parsing an invalid manifest for its licence would trust the
same unvalidated control file that made the release unavailable.

## D4 — Failure translation

**Decision**: Expected immutable-release validation failures become one non-retryable
`model_release_invalid` provider failure. Production-ingest failures preserve their code,
retryability, stage, and category. Unexpected internal exceptions still propagate.

**Rationale**: Expected configuration/media failures belong to the public failure
algebra; broad exception catching would hide defects.

**Alternatives considered**: Letting `ModelReleaseError` escape violates provider
isolation. Catching every exception violates the no-relabelled-bugs rule.

## D5 — Native payload and formalisms

**Decision**: The adapter retains the serialized `rdam.rst` production outcome verbatim.
`rst_tree` and `erst_graph` keep separate canonical identities and capability states.

**Rationale**: The adapter coordinates contracts; it does not own or reinterpret RST.
