# Data Model: Production Codeline Separation

All persisted boundary objects are strict Pydantic models. JSON is canonicalized with sorted keys before hashing.

## OwnershipClass

Values: `production`, `offline`, `repository`, `generated`.

## OwnershipRule

- `rule_id`: stable identifier
- `pattern`: repository-relative POSIX path pattern
- `ownership`: ownership class
- `reason`: concise responsibility statement
- `publishable`: true only for permitted production members

Invariant: every relevant member matches exactly one effective rule; ambiguity or no match fails.

## DependencyRule

- `distribution`: normalized distribution name
- `ownership`: production or offline
- `reason`: actual consumer
- `optional_capability`: optional production extra or null

Invariant: each dependency has one ownership; production closure cannot contain offline dependencies.

## BoundaryViolation

- `violation_kind`: unmatched ownership, ambiguous ownership, forbidden import, forbidden dependency, forbidden artifact member, or missing runtime member
- `root`: production root module/artifact
- `path`: complete ordered import or ownership path
- `detail`: precise cause

## ArtifactReceipt

- artifact path, kind, and SHA-256
- member count and production/forbidden members
- declared dependencies
- validity

Invariant: valid only with zero forbidden members/dependencies and all required runtime resources.

## ModelReleaseManifest

- schema version, release ID, task, architecture
- runtime contract and compatibility range
- immutable source identity and revision
- complete file path/role/size/SHA-256 inventory
- licence source and use restrictions
- available evaluation evidence, explicitly nullable with reason
- creation time and producer version

Invariant: paths are relative, unique, non-symlinked, fully inventoried, and immutable by digest.

## PromotionReceipt

- candidate and release paths plus manifest hashes
- verified files and checks
- promotion time and producer version
- success/failure fields

State transition: `candidate -> verified -> atomically promoted`; failure leaves no partial release.

## ParityCase and ParityReceipt

`ParityCase` records case ID, model identity, input/prepared-input digests, route, expected output/warning/failure digest, device, and any pre-existing tolerance.

`ParityReceipt` records baseline/candidate artifact hashes, case results, unexplained differences, and success. Success requires identical released model bytes and zero unexplained difference.
