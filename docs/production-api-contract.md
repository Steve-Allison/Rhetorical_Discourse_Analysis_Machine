# Production API contract

`rdam` exposes one analysis engine through Python, the `rdam` command and
optional loopback HTTP. All three use `Machine`, immutable requests/configuration,
and the same canonical codecs. `rdam.ingest` supplies shared preparation;
`rdam.rst.Parser` remains the native parser facade. Its nested serialized family
is `isanlp_rst.production` 2.0.0, independent of the machine envelope version.
There is no downstream-specific adapter or recreated consumer data model.

The exact symbol and resource authority is the packaged
`rdam/ingest/public-surface.json`. `rdam.ingest.__all__`, installed
imports, JSON Schemas, the console command, and the loopback endpoints are
reconciled against that file by the production-contract tests.

## Operations

At the aggregate boundary, `AggregateRequest.for_text`, `.for_source`, and
`.for_bytes` construct immutable requests. `Machine.analyse` inventories once,
projects once per distinct provider requirement, and returns separate native
outcomes plus full `MachinePreparation` evidence. `.for_edus` preserves exact EDUs;
`.for_structured` identifies a supplied Dung/IBIS bundle without invented text.
`Machine.prepare(PreparationRequest)` performs no inference. `PreparedDocument` and `AnalysisCapacity`
are the canonical Python names; the plan field is `capacity`. The previous
ingest import path and contract-field aliases are not accepted.

| Operation | Exact return | Success states | Failure |
|---|---|---|---|
| `production_machine(*, config=None)` | `Machine` | configured providers, no inference | invalid configuration |
| `Machine.prepare(request)` | `MachinePreparation` | complete inventory and selected projections | `OperationError` for expected preparation failure |
| `Machine.analyse(request)` | `AggregateAnalysis` | `complete`, `partial`, `unsuccessful` | typed per-technique outcomes; unexpected defects propagate |
| `Machine.capabilities()` | `MachineCapabilities` | source forms, providers, effective configuration, contracts | no model probe or inference |
| `serialize(record)` / `load(payload)` | canonical `bytes` / typed record | digest-checked current or historical record | damaged/unsupported record |
| `select_analysis(analysis, *, techniques)` | `AnalysisView` | whole selected outcomes and original context | invalid selection |
| `summarise(record)` | `str` | readable saved-record summary | unsupported record |
| `SourceArtifact.from_path(path, *, source_form=None, original_source=None, conversion_provenance=())` | `SourceArtifact` | one validated source identity | constructor error before the service boundary |
| `ProductionIngestor.prepare(source, *, policy=None, planning_policy=None, capacity=None)` | `PreparationOutcome` | complete preparation, including empty or retained-only primary discourse | `ProductionIngestError` |
| `ProductionIngestor.analyse(source, *, policy=None, planning_policy=None, analysis_policy=None, cache_directory=None, diagnostic_policy=None)` | `ProductionAnalysisOutcome` | `AnalysedOutcome` or `EmptyPrimaryAnalysisOutcome` | `ProductionIngestError` |
| `Parser.analyse_document(document, *, analysis_policy=None)` | `ParserAnalysisResult` | validated parser-owned result | typed provider or validation failure through production ingest |
| `describe_capabilities(parser=None)` | `ProductionCapabilities` | model-free or configured-parser capability evidence | contract validation error |
| `serialize_contract(value, *, diagnostic_policy=None)` | canonical `bytes` | RFC 8785 record; a `ProductionFailure` becomes a safe failure by default | serialization error |
| `load_contract(payload)` | `PersistedContract` | strict supported-version record | unsupported family, version, kind, or invalid record |

All service constructor and option arguments are keyword-only. A `None` policy
means the complete documented default is selected and embedded in the result.

## Closed state and policy values

| Contract | Values |
|---|---|
| `SourceForm` | `text`, `edus`, `markdown`, `docling_json`, `doclang_xml`, `doclang_archive` |
| `AnalysisStatus` | `analysed`, `empty_primary_discourse` |
| `OutputFormalism` | `rst_tree`, `erst_graph` |
| `EvidenceDetailPolicy` | `decision_complete`, `normalized_distributions` |
| `ModelIdentityState` | `immutable_release`, `mutable_instance`, `unidentified`, `not_configured` |
| `CacheEligibilityState` | `eligible`, `ineligible` |
| `LifecycleStage` | `acquisition`, `classification`, `preparation`, `planning`, `inference`, `validation`, `assembly`, `persistence`, `cache_retrieval` |
| `FailureCategory` | `provider_unavailable`, `malformed_input`, `unsupported_input`, `identity_contradiction`, `validation_failure`, `internal_processing_failure`, `persistence_failure`, `corrupt_cache_entry` |
| `Retryability` | `retryable`, `not_retryable`, `unknown` |

There is no `not_analysed` success status. Calling `prepare()` is the explicit
intentional non-analysis operation. Asking for analysis without an available
parser is a typed failure.

## Persisted records and schemas

| Discriminator | Python record | Committed schema |
|---|---|---|
| `capabilities` | `ProductionCapabilities` | `capabilities.schema.json` |
| `preparation_outcome` | `PreparationOutcome` | `preparation-outcome.schema.json` |
| `parser_analysis_result` | `ParserAnalysisResult` | `parser-analysis-result.schema.json` |
| `analysed_outcome` | `AnalysedOutcome` | `analysed-outcome.schema.json` |
| `empty_primary_analysis_outcome` | `EmptyPrimaryAnalysisOutcome` | `empty-primary-analysis-outcome.schema.json` |
| production outcome union | `ProductionAnalysisOutcome` | `production-analysis-outcome.schema.json` |
| `safe_production_failure` | `SafeProductionFailureRecord` | `safe-production-failure.schema.json` |
| `diagnostic_production_failure` | `DiagnosticProductionFailureRecord` | `diagnostic-production-failure.schema.json` |

Schemas are Draft 2020-12 serialization-mode projections. They and the public
surface are generated from runtime models and must be byte-identical to their
committed package resources.

Machine records additionally publish validation and serialization schemas as
`machine-{name}.{mode}.schema.json`. Discover names through `rdam schema` help
and contract metadata; retrieve one with `rdam schema request`. Native output
schemas include every formalism, corrected Toulmin/Walton v2 and historical v1;
`dung-input` and `ibis-input` describe supplied structures. Machine aggregate,
native envelope and capabilities write v2 and read v1 without upgrading its
meaning. Request, configuration, preparation, view and operation-error contracts
are independently versioned at v1. Raw source bytes use canonical padded base64.

The aggregate `reading_guide` is directly consumable by AI: each entry identifies
its native formalism/version, JSON pointers, section availability, evidence
meaning and interpretation limits. Read requested outcomes separately from
`upstream_results`; retained successes cannot improve `status`. Walton records
every catalogue question as addressed/open/not_assessable. Toulmin records
explicit/reconstructed/undetermined warrant origin. Evidence uses exact Unicode
character spans; `supporting_passage` does not mean a finding was quoted verbatim.
Neither guide text nor a valid span proves truth or argument strength.

## Evidence retained in one analysis outcome

An `AnalysedOutcome` contains the full nested `PreparationOutcome`, not a
receipt-only substitute. It then exposes:

- the resolved analysis request and policy;
- the exact analysed tokens, EDUs, sentence and paragraph boundaries, token
  mappings, source anchors, and fidelity declarations;
- the final `RstAnalysis` graph;
- every primary segmentation, split, relation, nuclearity, confidence,
  entropy, and requested distribution decision returned by the active parser;
- marker-refinement before/after records and trigger evidence;
- eRST signals, candidates, scores, calibration, accepted and rejected
  decisions, signal back-links, and decoder receipt when eRST is selected;
- identities for the primary parser, segmenter, marker refiner, eRST detector,
  scorer, decoder, calibration, relation inventory, and ontology mapping;
- exact loaded-component receipts and runtime-byte agreement for immutable
  releases;
- complete local-to-global mappings and a recombination receipt for subdivided
  analysis;
- both-endpoint relation anchors, supporting-signal anchors, and check-by-check
  validation evidence;
- semantic request/result identities, execution evidence, and cache status.

Provider data is not dropped merely because no current downstream consumer uses
it. Provider attributes on inventoried items are retained as closed string
pairs; native page, page-box, coordinate-box, item, table-coordinate,
archive-member, source-path, and text-span anchors remain typed.

The public contract intentionally excludes tensors, embeddings, activations,
unrestricted score charts, training labels, workbench types, and fabricated
decisions. Those are implementation or offline research state, not stable
production evidence.

## Validation rules

Before success, the provider verifies source and semantic identities, complete
inventory disposition, exact preparation coverage, plan completeness, runtime
component identity, primary-tree connectedness and acyclicity, source-anchor
reconstruction, decision-to-graph links, multi-unit recombination, and cache
binding.

Secondary eRST edges use exactly four formal constraints:

1. sufficient supporting signal;
2. no self-loop;
3. both endpoints exist;
4. no duplicate directed pair.

Cycles, crossings, overlap, and unrestricted secondary degree are permitted.

## Failure and privacy contract

`ProductionIngestError.failure` is the immutable in-memory truth. It carries a
stable stage, category, code, retryability, safe cause chain, allowlisted
context, and the strongest completed-stage evidence that precedes the failure.
Python exception chaining retains the original cause in memory.

`serialize_contract(failure)` always emits a separately discriminated safe
record. It excludes raw source/prepared text, arbitrary exception strings,
tracebacks, locals, environment values, and private paths while retaining
semantic identities, counts, anchor counts, and typed redaction counts. Full
diagnostic persistence requires an explicit
`DiagnosticPolicy(include_private_content=True)` supplied to serialization.

## Capability truth

`describe_capabilities()` is offline and model-free. It probes distribution
metadata without importing optional adapters and reports all six source forms,
including unavailable ones and their `formats` requirement. Without a parser,
both RST and eRST are explicitly unavailable and durable caching is ineligible.

A configured parser advertises only a formalism and evidence level it can
execute through canonical `ParserAnalysisResult`. Archived DMRST and UniRST
families are not presented as active ModernBERT production capabilities.
Mutable or unidentified parsers can analyse but cannot claim immutable runtime
identity or durable semantic-cache eligibility.

## Installed projections

`rdam analyse source.md --techniques rst,toulmin,walton` invokes the same
`Machine.analyse` contract as Python. `rdam prepare` inventories without
inference. `rdam summary analysis.json` and `rdam view analysis.json --techniques
walton` read saved results without rerunning models or resolving configuration.
`rdam capabilities`, `rdam schema request` and `rdam version` support discovery.

Files or stdin (`-`) are accepted. Canonical JSON goes to stdout, safe diagnostics
to stderr. Analysis exits: 0 complete, 3 partial, 4 unsuccessful; operational
error 1, invalid input 2, interrupt 130, broken pipe 141. File publication is
atomic, no-clobber by default; `--force` never permits overwriting an input alias.
For full flag syntax and defaults, use each command's `--help`.

The optional `rdam[http]` service binds only to `127.0.0.1` or `::1`:

| Endpoint | Contract |
|---|---|
| `POST /v1/prepare` | `PreparationRequest` → `MachinePreparation` |
| `POST /v1/analyse` | `AggregateRequest` → `AggregateAnalysis` |
| `POST /v1/view` | `ViewRequest` → `AnalysisView` |
| `POST /v1/summary` | saved supported record → readable text |
| `GET /v1/capabilities` | `MachineCapabilities` |
| `GET /v1/version` | installed package and contract versions |
| `GET /v1/schemas/{record}?mode=validation` | generated JSON Schema; serialization mode also supported |

One POST is admitted at a time. Body limits/deadlines apply before execution;
discovery stays responsive. Disconnect does not pretend to cancel an already
running native thread; its slot remains held and shutdown drains accepted work.
Application failures use `OperationFailure`; pre-ASGI HTTP-parser rejections are
server responses, not RDAM JSON. Arbitrary exception text does not cross either
boundary. All analytical completion states return HTTP 200; inspect `status`.

## Compatibility

Python symbols follow package SemVer. The unified command replaces the old
RST-only command without a compatibility wrapper. The nested RST production
2.0.0 contract and machine v1/v2 contracts are version-dispatched independently.
Unsupported future versions and unknown discriminators fail before payload use.
Removed format-specific parse functions and envelopes have no compatibility
aliases.
