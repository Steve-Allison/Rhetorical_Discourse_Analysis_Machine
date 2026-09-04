# Production API contract

`rdam` exposes one machine-owned production source API at
`rdam.ingest`, plus the `rdam.rst.Parser` facade. The serialized family
is `isanlp_rst.production` 2.0.0 — the contract identifier is unchanged by the package
rename. The package does not expose a CSM-specific adapter or recreate downstream data
models.

The exact symbol and resource authority is the packaged
`rdam/ingest/public-surface.json`. `rdam.ingest.__all__`, installed
imports, JSON Schemas, the console command, and the loopback endpoints are
reconciled against that file by the production-contract tests.

## Operations

At the aggregate boundary, `AggregateRequest.for_text`, `.for_source`, and
`.for_bytes` construct immutable requests. `Machine.analyse` inventories once,
projects once per distinct provider requirement, and returns separate native
outcomes plus one `PreparationReceipt`. `PreparedDocument` and `AnalysisCapacity`
are the canonical Python names; the plan field is `capacity`. The previous
ingest import path and contract-field aliases are not accepted.

| Operation | Exact return | Success states | Failure |
|---|---|---|---|
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

`rdam-rst parse` uses `SourceArtifact`, an immutable model release, a closed
analysis policy, and `ProductionIngestor`. Canonical JSON is the same serialized
contract as Python. `summary` is labelled as presentation-only and never claims
contract completeness.

The optional local service binds only to `127.0.0.1`, `::1`, or `localhost`:

| Endpoint | Contract |
|---|---|
| `POST /analyse` | canonical analysis outcome or canonical safe failure |
| `GET /capabilities` | canonical `ProductionCapabilities` |
| `GET /health` | presentation health derived from capability identity |

One request invokes inference at most once. Malformed CLI and HTTP input is
also represented by a safe typed production failure; arbitrary exception text
does not cross either boundary.

## Compatibility

Python symbols follow package SemVer; 6.0.0 renamed the import path from
`isanlp_rst` to `rdam.rst` and the command from `isanlp-rst` to `rdam-rst` without
changing any serialized contract. The serialized 2.0.0 contract and schemas are
version-dispatched independently. The 6.0.0 write version reads 2.0.0 only.
Unsupported future versions and unknown discriminators fail before payload use.
Removed format-specific parse functions and envelopes have no compatibility
aliases.
