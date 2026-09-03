# Data Model: Universal Source Pipeline

**Feature**: 017 | **Date**: 2026-09-03 | **Sources**: [spec.md](spec.md), [research.md](research.md)

Every record is a strict contract model — frozen, `extra="forbid"`, RFC 8785 canonical JSON
with a self-checking semantic digest — matching the existing ingest and machine contracts.
Nothing here constrains a technique's native result payload.

## Unchanged, and load-bearing

These already exist and are the foundation the feature stands on. They are listed because
the design depends on their guarantees, not because they change.

| Entity | Guarantee relied upon |
|---|---|
| `ContentInventoryItem` | every source item typed (`ContentClass`), anchored (≥1 `SourceAnchor`), placed in the tree (`parent_id`/`child_ids`), and dispositioned |
| `ContentRepresentation` | nine discriminated kinds; `TableRepresentation` carries per-cell geometry; `CrossReferenceRepresentation` carries target and relation |
| `SourceAnchor` | eight kinds including `TableCoordinateAnchor(row, column)` — the mechanism that makes cell-level traceability possible |
| `PreparedSegment` | carries `contributing_item_ids` **and** `source_anchors`; text length must equal its range |
| prepared document validator | segments contiguous, canonically ordered, and reconstructing the text exactly |
| `TransformationRecord` | maps `input_item_ids → output_segment_ids` with discriminated parameters and a digest |
| `ExactCoverage` | exhaustive accounting over inventory, primary, retained, mapping |

## New entities

### ContentRequirement

What one provider declares it can analyse. A property of the technique's formalism, not a
caller preference (FR-012).

| Field | Type | Rules |
|---|---|---|
| `requirement_id` | `str` | stable, provider-owned, e.g. `rst/authored-prose-v1` |
| `admitted_classes` | tuple[ContentClass, ...] | non-empty; the classes this technique can analyse |
| `representation_projections` | tuple[RepresentationProjection, ...] | how each non-text representation becomes analysable text; a representation with no projection is not admitted |
| `capacity` | AnalysisCapacity | unit, maximum, and the estimator that measures demand |
| `boundary_preference` | tuple[BoundaryPreference, ...] | non-empty, unique; where subdivision may cut |
| `normalization` | `preserve \| unicode_nfc \| line_endings_lf` | PDTB relies on `preserve` — surface connectives must survive verbatim |
| `requires_speaker_identity` | `bool` | SDRT and Walton declare true |
| `semantic_digest` | Sha256Identity | self-checking; half of a projection's identity |

Validation: `admitted_classes` unique; every projection names a representation kind at most
once; a requirement that admits `TABLE` or `TABLE_CELL` must declare a projection for
`TableRepresentation`, so admitting a table without saying how to read it is unrepresentable.

### RepresentationProjection

How one non-text representation is rendered analysable.

| Field | Type | Rules |
|---|---|---|
| `representation_kind` | `str` | the discriminator of the representation it applies to |
| `parameters` | TransformationParameters | discriminated; includes the new table-linearisation kind |

The projection is recorded as a `TransformationRecord` whenever it is applied, so nothing
enters a projection without a derivation (FR-015).

### AnalysisCapacity

Generalises the existing `ParserCapacity`, whose name is narrower than what it models
(FR-006). Same fields; `ParserCapacity` is retained as an alias.

| Field | Type | Rules |
|---|---|---|
| `unit` | CapacityUnit | `edu_count \| token_count \| segment_count` — all three already exist |
| `maximum` | `int` | > 1 |
| `estimation_algorithm` | `str` | named, so a plan is reproducible |
| `estimation_version` | SemanticVersion | a change of estimator is visible |
| `source` | `str` | where the limit comes from — a model context window, a parser limit |

### SourceProjection

The deterministic view of one inventory through one requirement (FR-013).

| Field | Type | Rules |
|---|---|---|
| `projection_identity` | Sha256Identity | digest of inventory identity + requirement digest. Two aggregates sharing this value received byte-identical input |
| `requirement_id` | `str` | which requirement produced it |
| `prepared_document` | PreparedDocument | text, contiguous segments, structural boundaries |
| `analysis_plan` | AnalysisPlan | planned against **this** requirement's capacity |
| `transformations` | tuple[TransformationRecord, ...] | every projection applied |
| `unmet_requirements` | tuple[UnmetRequirement, ...] | what the requirement asked for and the source could not supply (FR-019) |

Validation: the prepared document's existing invariants hold unchanged — segments
contiguous, ordered, reconstructing the text exactly, each naming its contributing items and
anchors. Every segment whose content did not come from a `TextRepresentation` must name a
transformation in `transformations`.

**Sharing**: within one aggregate, providers whose `requirement.semantic_digest` matches
receive the same `SourceProjection` object. Projection is computed once per distinct
requirement, never once per provider (SC-003).

### UnmetRequirement

Something declared and not suppliable — reported, never silently substituted (FR-019).

| Field | Type | Rules |
|---|---|---|
| `aspect` | `speaker_identity \| admitted_class \| capacity` | what could not be met |
| `detail` | `str` | non-empty; what specifically was missing |
| `affected_item_ids` | tuple[str, ...] | the inventory items concerned, where applicable |

### SpeakerIdentity

Who produced a turn. A validated field, never an untyped attribute (FR-020).

| Field | Type | Rules |
|---|---|---|
| `resolution` | `resolved \| unresolved` | explicit; there is no third state and no default |
| `participant_id` | `str \| None` | stable within one source; required when resolved, absent when unresolved |
| `display_name` | `str \| None` | as the source gives it; two participants may share one display name and still be distinct participants |
| `evidence` | `str` | non-empty; how the attribution was determined, or why it could not be |

Validation: `resolved` requires `participant_id`; `unresolved` forbids it. **A speaker is
never inferred by a model** (FR-022) — `evidence` records a source-derived determination or
an explicit failure to make one.

Carried on `ContentInventoryItem` as `speaker: SpeakerIdentity | None`, populated for `TURN`
items and absent otherwise.

### SpeakerCoverage

Accounting, in the receipt (FR-021).

| Field | Type | Rules |
|---|---|---|
| `turn_count` | `int` | ≥ 0 |
| `resolved_count` | `int` | ≥ 0 |
| `unresolved_count` | `int` | ≥ 0 |
| `distinct_participants` | `int` | ≥ 0 |

Validation: `resolved_count + unresolved_count == turn_count`. Exhaustive, like the existing
coverage records — no turn may go unaccounted.

### AnalyticalIdentity

The complete set of inputs determining a result, and therefore exactly what a cache key must
cover (FR-028).

| Element | Present for |
|---|---|
| source identity | all |
| **projection identity** | all text techniques — this is what makes the key correct under the projection model |
| provider id | all |
| provider contract version | all |
| model identity | model-backed only |
| instructions identity | model-backed only |

A cache answers only on an exact match of every element present. Any difference is a miss;
there is no near-match and no partial reuse.

## Changed entities

### AggregateRequest

Stays declarative data — it describes what to analyse, never the result of analysing it
(research R6).

| Field | Change |
|---|---|
| `source_artifact` | **new**, `SourceArtifactRef \| None`. Mutually exclusive with `text` |
| everything else | unchanged |

New constructors beside `for_text()`: `for_source(path)` and
`for_bytes(payload, source_form, source_name)`. Validation: `source.source_id` equals the
digest of the supplied bytes. Constructing performs no preparation and loads no model
(FR-008).

### ProviderRequest

| Field | Change |
|---|---|
| `projection` | **new**, `SourceProjection \| None`. Present for text techniques; always `None` for structured-input techniques (FR-018) |
| everything else | unchanged |

### AggregateAnalysis

| Field | Change |
|---|---|
| `preparation` | **new**, `PreparationReceipt \| None`. One per aggregate (FR-011) |
| everything else | unchanged |

### PreparationReceipt

Extends the existing preparation evidence with what the projection model adds.

| Field | Rules |
|---|---|
| `inventory_coverage`, `primary_coverage`, `retained_coverage`, `mapping_coverage` | unchanged, exhaustive |
| `speaker_coverage` | **new**, `SpeakerCoverage \| None` — present when the source has turns |
| `projections` | **new**, one entry per distinct projection produced, each naming its requirement and identity |
| `transformations` | unchanged in kind; now also carries table linearisations |

## State and invariants

**Inventory lifecycle**: `SourceArtifactRef → ContentInventory + receipt`, **once** per
aggregate (FR-009, SC-002). There is no path by which a second inventory of one aggregate
can occur.

**Projection lifecycle**: `(inventory, requirement) → SourceProjection`, pure and
deterministic. Same inputs, same `projection_identity`, always. Computed once per distinct
requirement within an aggregate.

**Derivation invariant**: every unit of content in a projection traces to either a
`TextRepresentation` item directly, or a `TransformationRecord` naming its input items
(SC-006). Nothing appears without a derivation.

**Speaker invariant**: every turn is `resolved` or `unresolved`; the counts reconcile to the
turn count; nothing is inferred (SC-007, SC-008).

**Cache lifecycle**: `miss → analyse → store`, or `hit → return`. No expiry and no
invalidation pass — a changed input yields a different key, so the old entry is simply never
addressed again.

**Concurrency invariant**: outcomes are keyed by technique and the aggregate validator
already forbids duplicates, so completion order cannot reach the result. FR-034 makes this a
checked property: concurrent and sequential aggregates must have identical semantic digests.

**Boundary invariant**: no projection reaches a structured-input provider; no provider
receives another provider's output. Cross-technique consumption stays caller-declared with
recorded lineage (FR-038).

**Alignment invariant**: every projection's segments anchor into the one inventory, so
results from different techniques over one source are alignable on source anchors without
their formalisms being merged (FR-037, SC-015).

## Relationships

```text
AggregateRequest 1—0..1 SourceArtifactRef
AggregateRequest —(Machine.analyse, exactly once)→ ContentInventory + PreparationReceipt
ContentInventory —* ContentInventoryItem —0..1 SpeakerIdentity   (turns only)
ContentInventory × ContentRequirement —(pure)→ SourceProjection
SourceProjection —1..*→ ProviderRequest        (shared by identical requirements)
SourceProjection —*→ TransformationRecord —> ContentInventoryItem (inputs)
AggregateAnalysis 1—0..1 PreparationReceipt —* SpeakerCoverage, projection entries
AnalyticalIdentity —addresses→ CacheEntry —holds→ NativeTechniqueResult
NativeTechniqueResult —anchors→ ContentInventoryItem   (the alignment path)
```
