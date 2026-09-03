# Contract: Source Pipeline

**Feature**: 017 | **Authority**: [spec.md](../spec.md) FR-001..FR-027, SC-001..SC-010

## Ownership and direction

1. Canonical source ingest is **machine-level**, at `rdam.ingest`, owned by the machine and
   not by any technique (FR-001).
2. The dependency direction is **machine → ingest** and **provider → ingest**. The machine
   layer MUST NOT import from a technique sub-package (FR-003), enforced by the production
   boundary gate walking imports from `rdam`.
3. `rdam.rst.ingest` remains importable with the same public names (FR-002), as a re-export
   with no independent behaviour — one canonical authority per governed fact.
4. Persisted identifiers do not move with the package: `isanlp_rst.production` 2.0.0, the
   schema `$id`s, and the runtime contract names are unchanged (FR-004). They name stored
   contracts, not module paths.
5. Contracts named for one technique are renamed to what they model, with the old names
   retained as aliases (FR-006): `PreparedRstDocument` → `PreparedDocument`,
   `ParserCapacity` → `AnalysisCapacity`. No consumer breaks, and the contract stops
   understating its own scope.

## Entry points

| Constructor | Accepts |
|---|---|
| `AggregateRequest.for_text(text, techniques, ...)` | a `str` — unchanged |
| `AggregateRequest.for_source(path, techniques, ...)` | a filesystem path |
| `AggregateRequest.for_bytes(payload, source_form, source_name, techniques, ...)` | bytes plus a declared form |

1. Constructing a request performs **no** inventory, loads no model, and touches no network
   (FR-008). Building a request in order to ask what is available must stay cheap.
2. `source.source_id` MUST equal the digest of the supplied bytes.
3. A request naming a text-analysing technique carries exactly one of `text` or
   `source_artifact` — never both, never neither.
4. A request naming only structured-input techniques needs neither.

## Accepted source forms

1. The machine accepts every form `describe_capabilities()` reports available. That report
   is the **single authority**; no second list exists in the machine layer (FR-026).
2. A form whose optional dependency is absent is reported unavailable there, and requesting
   it produces a typed, staged failure — never a partial analysis, never a silent fallback
   to another form (FR-027).
3. Core imports remain usable without the `formats` extra. Its absence reduces the available
   forms; it never breaks the machine.

## The inventory

1. Source inventory and disposition run **exactly once per aggregate request**, in
   `Machine.analyse()`, regardless of how many techniques are requested (FR-009).
2. The inventory stays complete: every item classified, dispositioned, anchored, and placed
   in the tree, with exact coverage accounting and **no valid content discarded** (FR-010).
   This is the existing guarantee, preserved.
3. The aggregate carries one preparation receipt for the whole request (FR-011).
4. The inventory is the shared source input. This is what the owner ruling means in
   practice: every technique is prepared from one inventory, built once.

## Projections

1. Each provider declares a **content requirement**: admitted classes, representation
   projections, capacity, boundary preferences, normalization, and whether speaker identity
   is required (FR-012).
2. A requirement is a property of the technique's **formalism**, not a caller-supplied
   option. RST does not admit tables because a table is not rhetorical prose; Toulmin admits
   them because grounds live there. Neither is a preference.
3. A projection is a **deterministic function of `(inventory, requirement)`**, identified by
   a digest of both (FR-013). Same inputs, same identity, always.
4. Providers whose requirement digests match receive **one shared projection**, computed
   once (SC-003).
5. Every projection preserves the existing invariants unchanged (FR-014): segments
   contiguous, canonically ordered, reconstructing the prepared text exactly, each naming
   its `contributing_item_ids` and its `source_anchors`.
6. Content admitted by transforming a non-text representation MUST be recorded as a
   `TransformationRecord` naming its input items and output segments (FR-015). **Nothing
   appears in a projection without a traceable derivation.**
7. Table content admitted to a projection retains **cell-level traceability**, so a result
   derived from a cell anchors to that cell's `TableCoordinateAnchor` (FR-016).
8. A provider receives exactly what its requirement admits — no more, no less (FR-017).
9. Structured-input techniques (Dung, IBIS) declare no requirement and receive no projection
   (FR-018).
10. Where a requirement declares something the source cannot supply, it is reported to the
    provider and recorded in the receipt as an unmet requirement (FR-019). It is never
    silently substituted, padded, or omitted.

## Speaker identity

1. Turn content carries a **validated** `SpeakerIdentity`, not an untyped attribute
   (FR-020).
2. Resolution is explicit: `resolved` with a participant id, or `unresolved`. There is no
   third state and no default.
3. Resolution is accounted in the receipt — turns, resolved, unresolved, distinct
   participants — and the counts must reconcile exactly (FR-021).
4. **A speaker is never invented** (FR-022). No model infers attribution. An unresolvable
   speaker is recorded as unresolved, with evidence saying why.
5. A provider declaring `requires_speaker_identity` is told when the source cannot supply
   it, rather than silently receiving anonymous turns.

## Capacity and planning

1. Planning is **per requirement**, against that requirement's declared capacity and unit
   (FR-023) — not against one parser capacity. `CapacityUnit` already offers `edu_count`,
   `token_count`, and `segment_count`.
2. Capacity estimation names its algorithm and version, so a plan is reproducible and a
   change of estimator is visible (FR-024).
3. Subdivision respects the requirement's boundary preferences and recombination stays
   lossless (FR-025).

## Preservation

1. RST's requirement reproduces today's policy exactly. `pixi run rst-baseline compare`
   MUST report **zero analytical differences** (FR-005, SC-010). Differences classified as
   execution, package identity, package source identity, or derived digest are expected —
   the package moved. An analytical difference fails the feature.
2. The six providers built in features 013–016 keep their native result contracts. Only
   their input changes.
3. All seven techniques still report `available`, and the suite still passes (SC-016).
