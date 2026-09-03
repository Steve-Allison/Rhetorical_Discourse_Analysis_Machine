# Research: Repository Migration

## Decision 1 — Keep one derived identity authority

**Decision**: Read distribution name, version, and the sole wheel package directory from
`pyproject.toml`; derive filenames and the release tag in `ReleaseIdentity`.

**Rationale**: A rename is safe only when build, validation, install, and boundary tools
cannot retain competing package/version literals.

**Alternatives considered**: Constants in each tool were rejected because they drift;
dynamic installed metadata was rejected for source builds because it can describe the
active editable environment instead of the selected source revision.

## Decision 2 — Preserve contracts, not obsolete import names

**Decision**: Use `rdam` for distribution, import, CLI, and provider identity. Retain
`isanlp_rst.production` and related immutable schema/runtime identifiers at their current
versions.

**Rationale**: Import identity and persisted contract identity are different facts. A
package rename does not authorize silently breaking stored records or model manifests.

**Alternatives considered**: Shipping a compatibility `isanlp_rst` package and renaming
unversioned persisted contracts were rejected as duplicate authority and silent breakage.

## Decision 3 — Compare analytical meaning field by field

**Decision**: Preserve serialized baseline records and classify every changed leaf as
execution, package identity, package source identity, derived digest, or analytical;
fail if any analytical difference exists.

**Rationale**: Byte equality cannot survive an intentional package/version rename, while
semantic-digest equality alone cannot explain an allowed difference. Classified leaf
comparison makes the exception narrow and auditable.

**Alternatives considered**: Blanket digest exceptions and regenerated baselines were
rejected because they could hide analytical regressions.

## Decision 4 — Treat historical release evidence as immutable

**Decision**: Validate current mechanisms with tests and boundary checks while retaining
the tracked 6.0.0 release records exactly as historical evidence.

**Rationale**: Rebuilding an untagged later commit is not the 6.0.0 release. Updating its
records would make a false release claim and create self-referential commit evidence.

**Alternatives considered**: Retagging or overwriting 6.0.0 evidence was rejected; a new
versioned release is outside this feature and requires an explicit user request.
