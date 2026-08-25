# Data Model: Production Source Ingest

**Feature**: 002 Production Source Ingest

**Contract family**: `isanlp_rst_ingest` version 1

## Design rules

- Runtime ingest models are strict, frozen Pydantic models with explicit schema
  versions. Unknown fields fail validation.
- Source identity, semantic identity, and execution observations are separate.
- Every validated source item is represented and receives exactly one final
  disposition. Absence is never represented by an invented value.
- All prepared and analysed content is traceable to source anchors or is marked
  explicitly as synthetic.
- Semantic digests use canonical JSON with sorted, explicit fields. Timestamps,
  paths, timings, cache state, and machine observations never affect them.
- Gold annotations and promotion metrics are repository-only evidence models;
  they are not part of the production contract family.

## Enumerations

### `SourceForm`

`text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, `doclang_archive`

### `AuthorshipRole`

`authored`, `machine_generated`, `transcribed`, `unknown`

### `ContentClass`

`title`, `heading`, `paragraph`, `list_item`, `turn`, `caption`, `table`,
`table_cell`, `code`, `formula`, `raw_markup`, `picture`,
`picture_description`, `note`, `navigation`, `metadata`, `furniture`,
`background`, `invisible`, `group`, `field`, `asset`, `other`

### `DispositionKind`

`primary`, `side_channel`, `excluded`, `transformed`, `deduplicated`, `rejected`

### `AnalysisStatus`

`analysed`, `not_analysed`, `empty_primary_discourse`

### `SegmentKind`

`source`, `separator`, `macro_representation`

### `AnchorKind`

`character`, `byte`, `line`, `item`, `xml_path`, `json_pointer`, `page`,
`time`, `bounding_box`, `table_coordinate`, `quote`

### `StructureKind`

`document`, `section`, `heading`, `paragraph`, `list`, `list_item`, `turn`,
`slide`, `page`, `table`, `row`, `cell`, `group`, `field`, `range`

### `CacheStatus`

`disabled`, `miss`, `hit`, `written`

### `FailureStage`

`read`, `identify`, `validate`, `inventory`, `policy`, `prepare`, `verify`,
`cache`, `analyse`, `anchor`, `serialize`

## Production entities

### `SourceArtifact`

Immutable bytes and caller-supplied provenance for one analysis request.

| Field | Meaning |
|---|---|
| `schema_version` | Source-artifact contract version |
| `source_id` | Canonical digest over the complete immutable source identity |
| `source_name` | Submitted human-readable name and required identity input |
| `source_form` | Frozen `SourceForm`; no later re-detection |
| `media_type` | Declared or deterministically inferred media type |
| `raw_sha256` | Digest of exact submitted bytes or canonical EDU array |
| `raw_size_bytes` | Exact submitted size |
| `raw_bytes` / `edus` | Exactly one source payload representation |
| `original_source` | Optional URI/path/reference; included in identity when supplied |
| `conversion_provenance` | Ordered upstream activities; included in identity when supplied |

Invariants:

- Payload digest and size are verified at construction.
- `source_id` covers payload, name, form, original-source identity, conversion
  provenance, and raw upstream contract declaration when available.
- A path is read once and closed before the artifact is returned.
- Plain text and Markdown bytes require a declared encoding or strict UTF-8.
- Presegmented EDUs retain boundaries exactly; empty EDUs fail validation.
- A filename extension is an identification signal, never proof of validity.

### `SourceContractIdentity`

The exact source contract under which validation succeeded.

| Field | Meaning |
|---|---|
| `family` | `plain_text`, `markdown`, `docling`, or `doclang` |
| `raw_declared_schema` | Schema name/version read before normalization, when available |
| `accepted_schema` | Schema identity returned by the current validator |
| `validator_distribution` | Installed validator distribution |
| `validator_version` | Exact installed version |
| `validator_digest` | Digest of the adapter and validation semantics |
| `validation_profile` | Explicit settings such as full Schematron and empty namespace acceptance |

### `NativeAnchor`

One strongest-available address into the immutable source artifact. It may
combine selectors rather than relying on one fragile coordinate.

Fields include `artifact_id`, `item_id`, optional `parent_item_id`, native
reference/JSON pointer/XML path, byte/character/line range, page/time/bounding
box/table coordinate, exact quote with prefix/suffix, and structure ancestry.
Every coordinate declares its reference text and end convention.

### `ContentInventoryItem`

One complete item discovered after successful source validation and before
relevance policy.

| Field | Meaning |
|---|---|
| `item_id` | Stable identity derived from source-native identity or path |
| `parent_id` / `child_ids` | Complete recursive structure |
| `content_class` | Typed source role |
| `authorship_role` | Authorship assessment and its basis |
| `content_layer` | Native layer, when present |
| `text` / `text_sha256` | Exact source text, when the item owns text |
| `native_anchors` | One or more source selectors |
| `attributes` | Whitelisted semantic source attributes |
| `inventory_adapter` | Adapter identity used to produce the item |

Inventory reconciliation must prove that every validator-visible top-level
collection member and every traversed descendant is accounted for exactly once.

### `Disposition`

The policy decision for one inventory item.

| Field | Meaning |
|---|---|
| `item_id` | Inventory item receiving the decision |
| `kind` | Exactly one `DispositionKind` |
| `reason_code` | Stable machine-readable reason |
| `policy_rule_id` | Named rule responsible for the decision |
| `prepared_segment_ids` | Derived segments, if primary/transformed |
| `side_channel_id` | Retained representation, if applicable |
| `replaced_by_item_id` | Canonical duplicate, if deduplicated |

`transformed` records both the source item and every transformation; it is not a
license to overwrite or lose the original. `rejected` aborts the request.

### `PreparationPolicy`

An immutable, named policy: `name`, semantic `version`, `rules`, duplicate
behavior, normalization behavior, supported content classes, capacity policy,
and canonical `policy_digest`. The production default is
`authored_prose_v1`. There is no partial or best-effort mode.

### `DuplicateFinding`

Evidence reported before any optional deduplication: exact normalized digest,
ordered item IDs, source scopes, comparison basis, and proposed/final action.
The default policy reports exact repetitions but retains authored prose.

### `PreparedSegment`

One ordered interval in prepared text.

| Field | Meaning |
|---|---|
| `segment_id` | Stable semantic identity |
| `kind` | Source, separator, or macro representation |
| `prepared_range` | Half-open character interval in prepared text |
| `source_item_id` / `source_range` | Required for source-derived text |
| `original_text` | Exact source substring for round-trip verification |
| `transformation_ids` | Ordered reversible transformation ledger |
| `native_anchors` | Strongest source anchors |
| `structure_path` | Canonical structural ancestry |

Synthetic separators and macro representations have no source range and must be
excluded from source-coverage numerators.

### `PreparedRstDocument`

The one canonical parser input and its complete preparation evidence:

- `text` and the corresponding strict `RstDocument`;
- ordered `PreparedSegment` values with contiguous prepared ranges;
- canonical structure tree and primary inventory item IDs;
- retained side-channel records;
- source, prepared-text, and structural coverage values;
- deterministic `semantic_digest`.

Every prepared character belongs to exactly one segment. Every primary source
character is represented exactly once unless a receipted reversible
transformation maps it otherwise.

### `AnalysisUnit` and `SubdivisionPlan`

`AnalysisUnit` describes one recursively analysed structural range: stable unit
ID, parent/children, structure kind/path, prepared output range, optional
context-only range, source item IDs, parser capacity basis, and local/macro
analysis status. `SubdivisionPlan` freezes the ordered tree of units and its
algorithm/version digest.

Sibling output ranges are ordered, non-overlapping, and complete for the parent.
Context may overlap for analysis, but context-only EDUs never appear twice in
the final tree.

### `AnalysisAnchor`

Maps each final EDU, relation, and tree node to prepared ranges, source segment
IDs, native anchors, and whether it arose from local or macro analysis. A
relation anchor is the ordered union of descendant EDU anchors; a macro node
also links to the explicit macro representation that produced it.

### `PreparationReceipt`

Deterministic semantic evidence embedded in every result:

- source and accepted-contract identity;
- inventory and per-disposition counts plus complete item ledger;
- preparation policy and transformation digests;
- duplicate findings and actions;
- source, prepared-text, structural, and analysis-anchor coverage;
- subdivision plan digest and parser/model release digest;
- pipeline and result-contract versions;
- cache fingerprint and final semantic digest.

### `ExecutionReceipt`

Non-semantic observation: run ID, UTC timestamp, duration by stage, peak RSS,
cache status, cache path identifier, warnings, and host/runtime versions. It is
excluded from semantic equality and result cache identity.

### `ProductionAnalysisResult`

The successful `isanlp_rst_ingest` v1 envelope: source summary, prepared
document, analysis status, final RST/eRST result when present, complete analysis
anchors, `PreparationReceipt`, and `ExecutionReceipt`.

An empty primary discourse returns `empty_primary_discourse` with full inventory
and coverage evidence; it never fabricates an EDU or tree.

### `ProductionIngestFailure`

A strict failure envelope or exception payload containing `stage`, stable
`code`, artifact/item identity, violated expectation, safe detail, and causal
exception class. It also carries immutable diagnostic evidence from every
completed stage, including any available inventory/disposition totals and
warnings, without representing that evidence as a successful preparation
receipt. A failed request emits no success result and no reusable cache entry.

## State transition

```text
read -> identify -> validate -> inventory -> apply policy -> prepare
     -> verify coverage -> cache lookup -> analyse -> anchor -> persist result
```

Any failure terminates the transition. Cache lookup occurs only after current
validation, inventory, preparation, and coverage verification have succeeded.

## Repository-only promotion entities

These schemas belong under `tools/production_ingest` or the feature evidence
directory and must never be imported by `isanlp_rst`:

- `GoldSourceManifest`: frozen source identity, form, provenance class, risks,
  licence/redistribution status, and expected-evidence references.
- `GoldExpectation`: adjudicated inventory/disposition/structure/coverage/anchor
  expectations and optional EDU/RST gold annotation.
- `CandidateRun`: immutable code, wheel, model, policy, machine, and input IDs.
- `SourceGateResult`: per-source gate outcomes before any aggregate.
- `PromotionDecision`: ordered gate results, failures, inspection record, dated
  SOTA comparison, and explicit pass/fail with no waiver field.
