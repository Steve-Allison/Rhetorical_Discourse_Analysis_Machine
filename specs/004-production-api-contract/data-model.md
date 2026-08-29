# Data Model: Production Contract 2.0.0

**Feature**: `004-production-api-contract`  
**Package release**: `isanlp_rst` 5.0.0  
**Serialized contract**: `isanlp_rst.production` 2.0.0

## Modelling rules

1. Every persisted value is a strict, frozen, closed Pydantic model. Nested
   mutable containers and non-finite numbers are forbidden.
2. Every variant uses an explicit literal discriminator. State-dependent
   optional-field bags are forbidden.
3. Every top-level record separates `semantic` values from `execution` values.
4. Semantic digests are SHA-256 over RFC 8785 canonical bytes of the documented
   semantic projection. Digests and execution values are excluded from that
   projection.
5. All ordered tuples preserve meaningful source or processing order. A
   collection is sorted only when its contract declares order semantically
   irrelevant.
6. Coverage is represented by exact integer counts. A floating display ratio
   may be derived but does not participate in semantic identity.
7. A provider value has one canonical serialized location. Convenience views
   are computed rather than duplicated.

## Contract envelope

Every public persisted record has the following outer shape.

| Field | Type | Meaning |
|---|---|---|
| `contract` | literal `isanlp_rst.production` | Contract family |
| `contract_version` | semantic version | Exact serialized schema version |
| `kind` | literal discriminator | Record type dispatched before payload parsing |
| `semantic` | kind-specific model | Values that determine meaning and semantic identity |
| `execution` | kind-specific model | Facts about this execution only |
| `semantic_digest` | SHA-256 identity | Recomputable digest of contract, version, kind, and semantic value |

Capabilities and failures use the same envelope. A capability description has
an empty or minimal execution section. A failure semantic section contains
stable failure meaning and completed-stage evidence; local traceback data is
never serialized.

## Core identities

### `SemanticVersion`

A validated normalized `major.minor.patch` string. Pre-release or local
versions are not accepted for released public contract versions. Package
versions continue to follow PEP 440 through package metadata.

### `Sha256Identity`

| Field | Type | Constraint |
|---|---|---|
| `algorithm` | literal `sha256` | No algorithm ambiguity |
| `hex_digest` | 64-character lowercase hex | Exact SHA-256 output |

The public JSON rendering uses one object form rather than accepting both
prefixed strings and objects.

### `ExactCoverage`

| Field | Type | Constraint |
|---|---|---|
| `covered_units` | non-negative integer | Units explained by the named category |
| `total_units` | non-negative integer | Shared denominator |
| `unit` | enum | `characters`, `items`, `segments`, or `anchors` |

`covered_units <= total_units`. Complete coverage is represented exactly by
equal integers, including `0/0` for a genuinely empty domain. Display ratios
are computed and never hashed.

## Source and inventory

### `SourceArtifact`

The current six-form submission boundary remains. It contains raw submitted
content plus declared identity and acquisition facts. Raw bytes may be retained
in memory for processing, but top-level failure serialization never includes
them.

Required semantic fields:

- source form: `text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, or
  `doclang_archive`;
- declared artifact identifier and origin when provided;
- media type and encoding where meaningful;
- raw-byte SHA-256 identity;
- source-form-specific declared contract/version facts.

### `SourceSummary`

A safe, persistable summary of the submitted artifact: source form, declared
identity, origin classification, media type, byte length, and byte digest. It
never contains raw source text.

### `SourceContractIdentity`

| Field | Type | Meaning |
|---|---|---|
| `adapter` | stable identifier | Internal adapter that interpreted the source |
| `adapter_contract_version` | semantic version | Provider interpretation contract |
| `upstream_format` | optional stable identifier | Docling, DocLang, Markdown, or plain/presegmented source family |
| `upstream_version` | optional string | Version genuinely present or used during interpretation |
| `schema_identity` | optional SHA-256 identity | Exact schema/contract bytes when applicable |
| `assumptions` | tuple of stable identifiers | Explicit interpretation assumptions actually applied |

### `ContentRepresentation`

A discriminated union preserving the meaningful representation genuinely
harvested from the source:

- `TextRepresentation`: text, language when known, and semantic role;
- `TableRepresentation`: ordered rows/cells, spans, headers, and cell links;
- `ListRepresentation`: ordered items, nesting, and marker semantics;
- `MetadataRepresentation`: typed key/value entries with source ordering;
- `AnnotationRepresentation`: note, caption, footnote, or other labelled
  annotation content;
- `MediaReferenceRepresentation`: media identity, caption/description when
  present, and source reference;
- `StructureRepresentation`: heading/container identity, label, and child
  relationships;
- `CrossReferenceRepresentation`: source item, target identity, and relation.

No representation fabricates values absent from the source. Format-specific
implementation classes remain private.

### `SourceAnchor`

A discriminated union for text spans, page/bounding boxes, source paths,
document item identifiers, table coordinates, and archive members. Every anchor
is bound to one source artifact identity and validates its own bounds.

### `Disposition`

| Field | Type | Meaning |
|---|---|---|
| `decision` | enum | `primary`, `retained`, `duplicate`, `transformed`, or `rejected_invalid` |
| `reason` | stable enum | Provider-owned reason for the decision |
| `primary_segment_ids` | tuple of identifiers | Primary representation links, if any |
| `retained` | boolean derived invariant | True exactly for accessible non-primary content |
| `duplicate_of` | optional item identifier | Canonical item when decision is `duplicate` |
| `transformation_ids` | tuple of identifiers | Applied transformation records |

Valid unsupported-for-analysis content uses `retained`, never
`rejected_invalid`. A duplicate must name exactly one canonical item.

### `ContentInventoryItem`

| Field | Type | Meaning |
|---|---|---|
| `item_id` | stable identifier | Deterministic within the source identity and contract |
| `classification` | stable content-class enum | Provider content class |
| `origin` | typed origin | Author/source/layer when genuinely known |
| `representation` | `ContentRepresentation` | Accessible content and meaningful structure |
| `anchors` | non-empty tuple of `SourceAnchor` | Trace to submitted source |
| `parent_id` | optional item identifier | Structural parent |
| `child_ids` | ordered tuple | Structural children |
| `relationships` | ordered tuple | Other provider-observed relations |
| `disposition` | `Disposition` | Exactly one final provider decision |

The final disposition is embedded once in the item. `PreparationOutcome`
exposes computed views such as `retained_items` and `dispositions`, but those
views are not separately persisted authorities.

### `TransformationRecord`

| Field | Type | Meaning |
|---|---|---|
| `transformation_id` | stable identifier | Referenced by affected items/segments |
| `kind` | stable enum | Normalization or derivation actually applied |
| `algorithm_version` | semantic version | Exact provider algorithm contract |
| `input_item_ids` | ordered tuple | Inputs |
| `output_segment_ids` | ordered tuple | Outputs |
| `parameters` | closed typed union | Only parameters meaningful to that transformation |
| `semantic_digest` | SHA-256 identity | Recomputable transformation identity |

## Preparation

### `PreparationPolicy`

The existing policy becomes a complete public semantic value. It contains
classification, duplicate precedence, primary-selection, normalization,
retention, and invalid-item rules. Defaults are explicit after validation.

### `PlanningPolicy`

| Field | Type | Meaning |
|---|---|---|
| `algorithm` | stable identifier | Subdivision strategy |
| `algorithm_version` | semantic version | Exact strategy contract |
| `capacity_margin` | exact integer rule | Deterministic allowance from parser capacity |
| `boundary_preference` | ordered enum tuple | Permitted split boundaries in priority order |

It participates in semantic identity whenever a parser capacity is supplied.

### `PreparedSegment`

One ordered parser-ready segment with normalized text, source anchors,
contributing inventory item identifiers, structural boundary identity, and
transformation links.

### `PreparedRstDocument`

The complete ordered primary discourse plus source mapping, structural
boundaries, and safe source summary. It contains no retained-only item content;
that content remains accessible in the inventory.

### `AnalysisUnit`

One capacity-safe deterministic slice of prepared segments:

- unit identifier and order;
- inclusive segment range;
- exact estimated parser demand and capacity;
- boundary reason;
- recombination predecessor/successor references.

### `AnalysisPlan`

| Field | Type | Meaning |
|---|---|---|
| `status` | `not_planned`, `single_unit`, or `subdivided` | Explicit plan state |
| `parser_capacity` | optional `ParserCapacity` | Supplied capacity, absent only for `not_planned` |
| `policy` | `PlanningPolicy` | Policy used or default policy declared for later use |
| `units` | ordered tuple of `AnalysisUnit` | Empty only for `not_planned` or empty primary discourse |
| `recombination` | typed plan | Complete deterministic assembly relationships |
| `semantic_digest` | SHA-256 identity | Recomputable plan identity |

### `PreparationSemanticEvidence`

Contains:

- `SourceSummary` and `SourceContractIdentity`;
- `PreparationPolicy` and `PlanningPolicy`;
- complete ordered inventory;
- explicit transformations;
- `PreparedRstDocument`;
- `AnalysisPlan`;
- exact inventory, primary, retained, and mapping coverage;
- stable warnings whose meaning affects interpretation.

### `PreparationExecutionEvidence`

Contains only execution facts such as adapter package versions, preparation
duration, host-independent execution identifier, and optional diagnostic mode.
Local paths and raw text are excluded.

### `PreparationOutcome`

A `kind=preparation_outcome` contract envelope with preparation semantic and
execution evidence. It is returned by `prepare()` and therefore constitutes the
explicit intentional-non-analysis outcome. It validates:

- every item has exactly one disposition;
- every relationship target exists;
- duplicate links are acyclic and resolve to a canonical item;
- primary and retained coverage is complete;
- segment/source mappings reconstruct prepared text;
- plan units cover each prepared segment exactly once when planned.

## Parser capability and identity

### `ParserCapacity`

An existing provider-owned value describing maximum segments/tokens or other
capacity units used by planning. Capacity units and estimation algorithm are
explicit.

### `ModelIdentityState`

Enum:

- `immutable_release`;
- `mutable_instance`;
- `unidentified`;
- `not_configured`.

### `ModelIdentity`

A discriminated union:

- `ImmutableModelReleaseIdentity`: release identifier, manifest identity,
  exact byte inventory, architecture/capacity identity, and model semantic
  digest;
- `MutableModelIdentity`: safe instance description and explicit reason durable
  identity is unavailable;
- `UnidentifiedModelIdentity`: provider type and reason identity cannot be
  established;
- `NoModelIdentity`: parser not configured.

Only `immutable_release` is eligible for durable semantic caching.

### `CompositeAnalysisIdentity`

One closed semantic record for every component that affected the result:

| Field | Type | Meaning |
|---|---|---|
| `primary_parser` | `ModelIdentity` | Primary tree parser release/instance |
| `segmenter` | typed component identity | Segmenter model/rule identity actually used |
| `marker_refiner` | typed component identity or `not_used` | Marker/rule refinement algorithm and policy |
| `erst_detector` | typed component identity or `not_used` | Signal detector/primer identity |
| `erst_scorer` | typed component identity or `not_used` | Secondary-edge scorer and checkpoint |
| `erst_decoder` | typed component identity or `not_used` | Constraint decoder and policy version |
| `calibration` | typed component identity or `not_used` | Temperature/calibration parameters and digest |
| `relation_inventory` | typed component identity | Relation label scheme and inventory digest |
| `ontology_mapping` | typed component identity or `not_used` | Mapping algorithm, ontology version, and digest |
| `semantic_digest` | SHA-256 identity | Recomputable identity over all components |

Each component state is explicit: `immutable_release`, `mutable_instance`,
`unidentified`, or `not_used`. Durable caching requires every participating
semantic component to have immutable identity.

### `SourceFormCapability`

Reports source form, availability, required extra, missing distributions,
accepted media types, and preparation support without importing its adapter.

### `ProductionCapabilities`

A `kind=capabilities` envelope containing:

- installed package version;
- write contract and readable contract versions;
- source-form capabilities, including unavailable forms;
- lifecycle operations and success/failure kinds;
- parser capacity and identity state when a parser descriptor is supplied;
- supported output formalisms and evidence-detail levels, plus stable reasons
  for any unavailable decision-evidence capability;
- model-free discovery guarantee;
- canonicalization, persistence, and cache guarantees;
- semantic-cache eligibility plus stable reason;
- optional extra name and missing distributions.

## Analysis

### `OutputFormalism`

Closed enum: `rst_tree` or `erst_graph`. The selected value constrains whether
secondary-edge evidence may be present. Free-form output strings are invalid.

### `EvidenceDetailPolicy`

Closed enum:

- `decision_complete`: selected decisions, provider-computed confidence and
  uncertainty, refinement, supporting evidence, and receipts;
- `normalized_distributions`: all decision-complete values plus finite
  normalized provider-computed distributions genuinely available from the
  selected backend.

The policy never authorizes raw tensors, embeddings, activations, unrestricted
charts, training-only fields, or workbench records.

### `AnalysisPolicy`

| Field | Type | Meaning |
|---|---|---|
| `output_formalism` | `OutputFormalism` | Required output graph formalism |
| `evidence_detail` | `EvidenceDetailPolicy` | Returned decision-evidence level |
| `marker_refinement` | closed policy | Whether and how marker refinement may alter model decisions |
| `validation` | `ValidationPolicy` | Required validation checks and policy version |
| `relation_interpretation` | closed policy | Relation scheme and ontology mapping behaviour |
| `lossy_input` | literal `forbid` or explicit closed policy | Handling of truncation/capping/approximation; production default is `forbid` |
| `policy_version` | semantic version | Exact provider policy contract |
| `semantic_digest` | SHA-256 identity | Recomputable policy identity |

Resolved defaults are returned as complete values. A policy that changes
returned semantic evidence changes request and cache identity.

### `AnalysisRequest`

The complete resolved semantic request embedded in an analysis outcome:

- source and preparation semantic identities;
- complete `AnalysisPolicy`;
- analysis plan and parser capacity identities;
- `CompositeAnalysisIdentity`;
- analysis pipeline and production contract write versions;
- semantic request identity.

It contains no cache directory, device, timing, or other execution-only value.

### `AnalysedToken`

Token identifier/order, exact token text used by inference, character range in
the analysed text, source anchors, sentence/paragraph membership, and any
normalization/transformation links.

### `AnalysedEdu`

EDU identifier/order, exact analysed text, ordered token identifiers,
sentence/paragraph membership, prepared segment links, and complete source
anchors.

### `AnalysisSubstrateTransformation`

A typed record for any authorized transformation between prepared and analysed
content: algorithm/version, inputs/outputs, exact parameters, affected ranges,
source anchors, fidelity classification, and semantic digest. Silent
truncation, capping, approximate token allocation, or dropped content is
invalid. With the default `lossy_input=forbid`, a lossy transformation cannot be
constructed.

### `AnalysedDocument`

Contains ordered `AnalysedToken` and `AnalysedEdu` values, exact
token-to-EDU/sentence/paragraph mappings, structural boundaries, prepared
segment mapping, source anchors, substrate transformations, fidelity status,
coverage, and semantic digest. It is the document actually passed to inference,
not a reconstruction from the returned tree.

### `AnalysisStatus`

Exactly two analysis-success statuses:

- `analysed`;
- `empty_primary_discourse`.

Intentional non-analysis is represented by returning `PreparationOutcome` from
`prepare()`. Provider unavailability and failed processing are typed failures,
not analysis successes. This keeps all documented analysis statuses reachable
and exclusive.

### `AnalysisAnchor`

Links an EDU, node, primary edge, secondary edge, decision, or supporting signal
to analysed tokens/EDUs, prepared segments, and source anchors. Relation and
secondary-edge anchors contain distinct source and target endpoint anchors;
supporting signal anchors are linked separately. Every analysed value has
reconstructable, in-bounds coverage.

### `ScoreValue`

Finite provider-computed score plus `confidence_kind`, declared range,
calibration identity when applicable, and producing component identity. A raw
number without meaning is invalid.

### `NormalizedDistribution`

Ordered labelled `ScoreValue` entries whose normalized probabilities are
finite, in range, and sum to one within the contract tolerance. It is present
only under `normalized_distributions` and only when the backend genuinely
produces it.

### `RelationInterpretation`

Raw label, declared relation scheme and inventory identity, optional selected
ontology concept, mapping status (`mapped`, `identity_only`, `not_mapped`, or
`not_available`), mapping algorithm/version, ontology version/digest, and
calibration/confidence semantics. Copying a raw label into a concept field is
`identity_only`, not proven ontology mapping.

### `SegmentationDecisionEvidence`

Boundary identity, selected boundary state, provider confidence, optional
normalized boundary distribution, affected analysed tokens, resulting EDU
links, and producing component identity.

### `PrimaryStructureDecisionEvidence`

Stable decision identity linked to the resulting node/primary edges, analysed
span, selected split or attachment, nuclearity, relation interpretation,
provider confidence, normalized split entropy when produced, optional split,
relation, and nuclearity distributions, and producing component identity.

### `RefinementRecord`

Stable identity, decision kind, complete before/after values, trigger signal or
rule identities and anchors, policy/algorithm identity, affected graph element
identifiers, explanation code, and semantic digest. A revised value must differ
from the before value and neither value may be omitted.

### `PrimaryInferenceEvidence`

Contains complete segmentation decisions, primary structure decisions, and
refinement records at the selected evidence level. Every final primary node and
edge links to its creating decision; every returned refinement links to the
decision it changed.

### `ErstCandidateDecision`

Candidate identity, source and target node identifiers, supporting signal
identifiers, edge probability, selected relation interpretation and relation
probability, joint selection score, calibration identity, decision
(`accepted` or stable rejection reason), decoder order, and produced secondary
edge identifier when accepted.

### `ErstDecodeReceipt`

The provider decoder's complete stable receipt: policy/version, ordered
candidate decision identities, input/accepted/rejected counts, constraint check
counts, rejection-reason counts, deterministic ordering identity, warnings,
and digest.

### `ErstCompletionEvidence`

Contains detector signals with candidate/edge back-links, candidate decisions
at the selected evidence level, the complete decode receipt, scorer/calibration
identity, relation inventory identity, and semantic digest. Every accepted edge
links to its candidate and supporting signals; no returned signal is orphaned.

### `RecombinationReceipt`

Contains ordered local analysis unit and local result identities, complete
local-to-global segment/node/edge mappings, boundary and nuclear-spine inputs,
deterministic stitching decisions, warnings, timings, policy/version, and
semantic digest. Full local graphs are not duplicated by default.

### `ValidationCheckReceipt`

Stable check identifier, required/advisory classification, outcome, exact
counts, affected identifiers, and stable warning/error code. It contains no
free-form private source text.

### `ValidationReceipt`

Validation policy/version, ordered `ValidationCheckReceipt` values, overall
`passed` disposition, graph/anchor/evidence coverage counts, warnings, and
semantic digest. A successful outcome requires every required check to pass.

### `InferenceEvidence`

A safe completed-stage record containing `AnalysisRequest`, analysed-document
identity, composite analysis identity, unit identities, primary/eRST evidence
digests, output summaries, and unit-completion counts. It does not claim that
unvalidated parser output is a valid analysis.

### `AnalysisSemanticEvidence`

Contains:

- complete `PreparationOutcome`;
- complete resolved `AnalysisRequest` and `AnalysisPolicy`;
- complete `AnalysedDocument`;
- complete immutable or explicitly unstable `CompositeAnalysisIdentity`;
- analysis status;
- validated `RstAnalysis` for `analysed` only;
- primary inference evidence and eRST completion evidence as selected by the
  output formalism;
- complete both-endpoint analysis and supporting-signal anchors;
- recombination receipt when units were assembled;
- complete validation receipt;
- cache request identity and semantic result identity.

The analysis semantic projection embeds the preparation semantic value, not
merely its digest. Preparation execution evidence remains exposed through the
nested outcome but is excluded from analysis semantic identity.

### `AnalysisExecutionEvidence`

Contains execution identifier, timing, device, cache hit/miss/bypass status,
cache entry identity where applicable, unit execution receipts, recombination
timings, and software release provenance. It cannot change the semantic digest.

### `AnalysedOutcome`

`kind=analysed_outcome`, status `analysed`, with a complete validated
`RstAnalysis` and complete analysis anchors.

### `EmptyPrimaryAnalysisOutcome`

`kind=empty_primary_analysis_outcome`, status
`empty_primary_discourse`, with the full successful preparation outcome, model
identity and execution facts, but no fabricated discourse tree or anchors.

### `ProductionAnalysisOutcome`

The discriminated union of the two success variants. `analyse()` returns this
type or raises `ProductionIngestError`.

## Failure

### `LifecycleStage`

Ordered enum:

1. `acquisition`;
2. `classification`;
3. `preparation`;
4. `planning`;
5. `inference`;
6. `validation`;
7. `assembly`;
8. `persistence`;
9. `cache_retrieval`.

The order constrains which completed evidence a failure may carry.

### `Retryability`

Enum: `retryable`, `not_retryable`, or `unknown`. A stable category defines
the default; construction rejects contradictory overrides.

### `SafeDiagnosticContext`

A discriminated, allowlisted union for safe counts, stable identifiers,
contract versions, expected/actual classifications, missing distribution
names, cache identities, and source byte digests. It forbids arbitrary mapping
values, raw text, local private paths, environment variables, and traceback
frames.

### `SafeCause`

Contains only provider error category, safe exception type name, stable message
template identifier, and optional nested safe cause. `str(exception)` and
`repr(exception)` are never copied automatically.

### `CompletedStageEvidence`

Discriminated variants enforce monotonic evidence:

- `NoCompletedEvidence`;
- `AcquisitionCompletedEvidence` with `SourceSummary`;
- `InventoryCompletedEvidence` with source contract and complete inventory;
- `PreparationCompletedEvidence` with full `PreparationOutcome`;
- `InferenceCompletedEvidence` with preparation plus safe
  `InferenceEvidence`, but no claimed validated analysis;
- `ValidationCompletedEvidence` with a complete validated analysis draft;
- `AssemblyCompletedEvidence` with the complete production outcome that failed
  only during persistence.

A failure-stage validator permits only evidence from a strictly earlier stage.
Cache-retrieval failures carry the safe cache identity and, when independently
available, the original semantic request identity; corrupt cached payloads do
not become completed outcomes.

### `SafeCompletedStageEvidence`

The deterministic default-serialization projection of completed evidence. It
preserves provider identity, classification, structure, anchors,
relationships, dispositions, counts, and semantic digests while replacing
private representation values with `RedactedContentRepresentation` containing
the representation kind, byte/character length, and SHA-256. The projection is
typed and reloadable; it cannot be mistaken for complete in-memory evidence.

### `ProductionFailure`

An immutable in-memory discriminated hierarchy by failed stage and stable
category. It may retain complete `CompletedStageEvidence`, including a full
`PreparationOutcome`, because the caller needs the provider evidence that
completed before failure. Common semantic fields are:

- failed stage;
- stable category and code;
- retryability;
- safe human message template and parameters;
- typed safe diagnostic context;
- typed safe causal chain;
- completed-stage evidence.

Provider unavailability is a specific category used for no configured parser,
missing optional distribution, unavailable immutable release, or unsupported
runtime capability. Malformed input and internal processing failure remain
distinct categories.

### `SafeProductionFailureRecord`

The default closed persisted failure envelope. It contains the stable failure
meaning and `SafeCompletedStageEvidence`. Default `serialize_contract()` maps
an in-memory `ProductionFailure` to this record before canonicalization. It is
the failure type accepted by default reload and must never contain raw private
source or prepared text.

### `DiagnosticProductionFailureRecord`

A separately discriminated persisted envelope that may contain complete
private completed evidence. Construction and serialization require an explicit
`DiagnosticPolicy(include_private_content=True)`. Its kind and schema make the
privacy change unambiguous. It remains closed and never admits arbitrary
tracebacks, locals, environment variables, or exception strings.

### `ProductionIngestError`

An exception wrapper with one immutable `failure: ProductionFailure` attribute.
`__str__` and `repr` are safe by construction. The original in-process cause is
linked using `raise ... from ...` but never automatically serialized.

## Public-surface and distribution models

### `PublicSurfaceEntry`

| Field | Type | Meaning |
|---|---|---|
| `qualified_name` | string | Canonical symbol identity |
| `public_import` | optional string | Supported import path |
| `kind` | enum | Function, class, protocol, enum, alias, exception, schema, or resource |
| `status` | `supported`, `deprecated`, or `internal` | Contract classification |
| `introduced` | package version | First supported release |
| `deprecated` | optional package version | Deprecation release |
| `removal` | optional package version | Planned/actual removal release |
| `schema_id` | optional URI | Serialized membership |
| `documentation_anchor` | optional stable anchor | Public documentation projection |
| `compatibility` | stable enum | Compatibility guarantee |

Signatures and schema fingerprints are derived during reconciliation rather
than duplicated as editable authority.

### `PublicSurfaceInventory`

The versioned machine-readable membership and classification authority. It
validates unique names/imports and coherent deprecation periods. Reconciliation
joins it with runtime exports, signatures, enum values, generated schemas, and
documentation.

### `ArtifactReceipt`

Filename, kind, size, SHA-256, wheel tags when applicable, and PyPA build-report
facts for one wheel or sdist.

### `VerificationReceipt`

Named check, status, exact command, tool/runtime identity, evidence digest, and
completion timestamp. Timestamp is execution evidence and does not define
artifact identity.

### `DistributionReceipt`

The strict canonical release receipt uses the separate contract
`isanlp_rst.release_receipt` 1.0.0 rather than pretending to be a runtime ingest
outcome. It contains:

- receipt schema name/version;
- package name/version and public contract write/read versions;
- source VCS, exact source commit, clean state, tree identity, and commit-derived
  `SOURCE_DATE_EPOCH`;
- Python implementation/version/build details;
- build frontend/backend/version, platform, and lock digest;
- wheel and sdist artifact receipts;
- all required verification receipts.

`release-receipt.sha256` is the detached digest because a receipt cannot contain
its own digest.

## Relationships

```text
SourceArtifact
  -> SourceSummary + SourceContractIdentity
  -> ContentInventoryItem[*]
       -> ContentRepresentation
       -> SourceAnchor[*]
       -> Disposition
       -> TransformationRecord[*]
  -> PreparedRstDocument
  -> AnalysisPlan
  -> PreparationOutcome
       -> ProductionAnalysisOutcome
            -> AnalysisRequest + AnalysisPolicy
            -> AnalysedDocument
            -> CompositeAnalysisIdentity
            -> RstAnalysis
            -> PrimaryInferenceEvidence
            -> ErstCompletionEvidence
            -> AnalysisAnchor[*]
            -> RecombinationReceipt
            -> ValidationReceipt

Any lifecycle stage
  -> ProductionFailure
       -> CompletedStageEvidence from earlier stages only
       -> ProductionIngestError

PublicSurfaceInventory
  -> runtime exports + signatures + schemas + documentation reconciliation

source commit
  -> wheel + sdist
  -> DistributionReceipt
  -> dist/5.0.0 promotion commit
```

## State transitions

```text
submitted
  -> acquired
  -> inventoried
  -> prepared
       -> returned as PreparationOutcome              # intentional non-analysis
       -> empty primary -> EmptyPrimaryAnalysisOutcome
       -> planned -> inferred -> validated -> assembled
            -> AnalysedOutcome
            -> persisted/cached only after validation

Any transition
  -> ProductionFailure(failed_stage, completed_evidence)
  -> ProductionIngestError
```

Invalid parser output never transitions to an analysis outcome. A cache hit is
accepted only after envelope, version, request identity, semantic digest, and
all outcome invariants validate.

## Invariant and mutation matrix

| Changed value | Identity that must change |
|---|---|
| Raw source bytes or declared source identity | Source, preparation, analysis, request, and cache identities |
| Source contract identity | Preparation, analysis, request, and cache identities |
| Preparation or planning policy | Plan when affected, preparation, analysis, request, and cache identities |
| Inventory representation, disposition, transformation, or prepared discourse | Preparation, analysis, and cache identities |
| Analysis plan or parser capacity | Plan, analysis request, result, and cache identities |
| Immutable model identity | Analysis request, result, and cache identities |
| Output formalism, evidence detail, refinement, validation, relation, or loss policy | Analysis request, result, and cache identities |
| Analysed tokens, EDUs, boundaries, mappings, or fidelity transformations | Analysis request, result, and cache identities |
| Participating segmenter, marker, eRST, decoder, calibration, relation-inventory, or ontology component identity | Analysis request, result, and cache identities |
| Primary decision, confidence, uncertainty, distribution, or refinement evidence | Analysis result and cache identities |
| eRST candidate, signal, score, calibration, decision, or decoder receipt | Analysis result and cache identities |
| Recombination mapping/decision or validation receipt | Analysis result and cache identities |
| Validated RST/eRST analysis or anchors | Analysis result identity |
| Timing, host, device, cache-hit status, or local execution identifier | No semantic identity |

Every row requires a positive mutation test. The final row requires negative
controls proving semantic bytes remain identical.
