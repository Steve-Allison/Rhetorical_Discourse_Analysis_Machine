# Data Model: Unified Machine Interfaces

**Status**: Normative design for Feature 019; not the current runtime schema.

The tables specify fields and invariants, not a second implementation. Python
models are the implementation authority; installed JSON Schemas are generated
from their validation/serialization modes. JSON uses arrays for Python tuples.
All new value models are immutable, strict and closed to unknown fields.
Native technique payloads remain governed by their own contracts.

## 1. Public record registry

| Contract | Write version | Public Python type | Read policy |
|---|---|---|---|
| `rdam.request` | `1.0.0` | `AggregateRequest` | v1 only; there was no previously registered persisted request |
| `rdam.preparation_request` | `1.0.0` | `PreparationRequest` | v1 only |
| `rdam.configuration` | `1.0.0` | `MachineConfig` | v1 only |
| `rdam.preparation` | `1.0.0` | `MachinePreparation` | v1 only |
| `rdam.aggregate` | `2.0.0` | `AggregateAnalysis` | v1 retained as a distinct historical model; v2 current |
| `rdam.capabilities` | `2.0.0` | `MachineCapabilities` | v1 historical; v2 current |
| `rdam.native_result` | `2.0.0` | `NativeTechniqueResult` | v1 retained as HistoricalNativeTechniqueResult; new evidence typing in v2 |
| `rdam.operation_error` | `1.0.0` | `OperationFailure` | v1 only |
| `rdam.version` | `1.0.0` | `VersionInfo` | v1 only |
| `rdam.analysis_view` | `1.0.0` | `AnalysisView` | v1 only; derived from aggregate v2 |
| `rdam.view_request` | `1.0.0` | `ViewRequest` | v1 only |

All rows carry literal `contract` and `contract_version`. Existing
`isanlp_rst.production` records and their identifiers remain unchanged. Dispatch
is by `(contract, version)`, never one shared version constant across unrelated
records. Unknown versions fail explicitly; no silent coercion or migration.
`load()`/`serialize()` support result-like records; dedicated request/config
loaders narrow the accepted union and never execute source paths.

## 2. MachineConfig

| Field | Type | Meaning/default |
|---|---|---|
| `llm` | `LlmSettings` | Shared LLM settings |
| `technique_models` | closed object with optional `pdtb`, `sdrt`, `toulmin`, `walton` string fields | Model overrides; absent means shared model |
| `rst` | `RstSettings` | RST-specific model and analysis defaults |
| `dung_capacity` | strict positive integer | Derived from `rdam.dung.semantics.DEFAULT_CAPACITY`, currently 14 |
| `execution` | `ExecutionSettings` | `max_workers` and `cache_directory` matching existing ExecutionPolicy |

`LlmSettings` fields: `model: str | None = None`, `output_retries: int >= 0`,
`transport_retries: int >= 0`, `transport_deadline_seconds: finite float > 0`.
Retry/deadline defaults derive from `_llm` constants at composition, currently
2, 2, 60 seconds. Null model resolves once from `RDAM_LLM_MODEL`, otherwise the
existing package default; it never means to select a model anew on each call.
Bare model names normalize using the existing model-identity parser. Malformed
explicit model identities are configuration errors; a valid configured identity
with no usable credential is a capability limitation, not a configuration typo.

`RstSettings` fields:

| Field | Type | Meaning/default |
|---|---|---|
| `model` | `PublishedRstModel \| LocalRstModel \| null` | Null resolves the existing published default, not an unidentified backend |
| `relinventory` | nonempty string or null | Explicit native inventory; provider default if absent |
| `device` | nonempty validated device string | `auto`; include existing `cpu`, `mps`, `cuda`, `cuda:N` semantics |
| `erst_checkpoint` | Path or null | Existing bundle resolution; no new download behavior |
| `default_formalism` | `rst_tree \| erst_graph` | `rst_tree`; request formalism overrides this default explicitly |
| `evidence_detail` | `decision_complete \| normalized_distributions` | Existing default |
| `marker_refinement` | `evidence_preserving \| disabled` | Existing default |

`PublishedRstModel = {kind: "published", version: nonempty str}`.
`LocalRstModel = {kind: "local_release", store: Path, release_id: nonempty str}`.
These variants cannot coexist. Local release ids are a single directory member,
not paths (`/`, `\\`, `.` and `..` components rejected). No silent fallback from
an invalid local release to published weights. Provider-known unsupported model
versions yield unavailable capability, not an invented default.

`ExecutionSettings = {max_workers: strict int 1..number_of_boundaries,
cache_directory: Path | null}`. Default workers derive from ExecutionPolicy;
default cache is off. The primary composition uses this aggregate cache only;
it does not also enable an unrequested RST-private cache. Direct lower-level
provider APIs remain available independently.

Resolution order: package defaults < existing model environment fallback <
explicit config values < exact CLI flag overrides. A technique-specific model
wins over the shared model regardless of whether the shared value came from a
file or flag. A technique-specific flag overrides that technique's file value.
Null/absence is not allowed to erase an explicitly supplied value ambiguously.
The loader resolves relative file paths against the config file's directory;
CLI path overrides and Python Path arguments resolve against cwd at construction.
No ancestor config search, URL interpolation, shell expansion or `${...}` expansion.
The existing credential-only `.env` behavior remains documented; credentials,
raw API keys and arbitrary provider base URLs are not config fields.

## 3. ProviderConfiguration and cache binding

Each declaration gains `configuration: ProviderConfiguration`:

- `settings: Mapping[str, JsonValue]`: deeply frozen, fully resolved non-secret
  settings produced by that provider, not an arbitrary caller-supplied bag.
- `identity: Sha256Identity`: recomputed from canonical settings; a mismatch fails.
- `cache_eligible: bool` and `cache_reason: str`: provider-declared, validated
  against the known identity state, not inferred from mere model availability.

Production providers construct this record from the closed settings above and
their existing native policy/model metadata. Custom Python providers must declare
their actual settings and cache policy; the generic machine never fabricates them.
An empty settings object is valid for a genuinely unconfigurable provider such as
IBIS; it is not a fallback for an undeclared RST/Dung/LLM configuration.

The hash includes model identity, effective retry/deadline settings, RST
inventory/device/eRST bundle identity and evidence/refinement defaults, or Dung
capacity, as applicable, plus extraction-schema and evidence-selection-policy
identities for the corrected providers. The request's resolved formalism remains a separate
cache-key input. Local RST model paths resolve to manifest/member identities;
path strings alone do not certify immutable weights. If an eRST bundle or
published model cannot be bound to immutable model bytes, RST aggregate-cache
eligibility is false. Available analysis is still allowed. Existing mutable
model/provider cache rules must not be weakened.

The cache key adds the provider configuration identity to its existing source,
projection, structured input, derivation, provider/version/provenance,
instructions and model inputs. Workers, output path, HTTP port and cache directory
are operational settings, excluded from analytical identity. Device is retained
conservatively: this feature does not assume every device produces equal labels.
Native payload changes are limited to the corrections in
[contracts/native-integrity.md](contracts/native-integrity.md); aggregate v2
records configuration beside each newly executed outcome. Standalone historical
native results acquire no invented configuration or evidence classification.

## 4. AggregateRequest

Retain the existing semantic fields:

| Field | Type | Invariant |
|---|---|---|
| `source` | `SourceIdentity` | Binds the source represented below |
| `text` | string or null | Exact text; mutually exclusive with source artifact |
| `source_artifact` | `SourceArtifactRef` or null | Immutable fully materialized source, not a filesystem handle |
| `techniques` | nonempty unique tuple of boundary Technique | Explicit caller order |
| `structured_inputs` | tuple of StructuredInput | At most one per requested Dung/IBIS boundary |
| `formalisms` | tuple of FormalismChoice | At most one per requested boundary |
| `upstream_results` | tuple of current or HistoricalNativeTechniqueResult | Exact retained results, same source, no collision with newly requested boundaries |

Add only literal contract/version, not a second set of transport source fields.
For text techniques exactly one of text/artifact is mandatory. Structured-only
requests may carry neither. `text=""` is present input, not omission. Source
digests are checked against bytes/UTF-8 text. Duplicate boundary checks map eRST
to RST before checking collisions, without altering native result identities.

Retain `for_text`, `for_source`, `for_bytes`. Add `for_edus` and
`for_structured(structured_inputs, *, techniques=None, source=None,
source_name=None, upstream_results=(), formalisms=())`:

1. Without an explicit source/upstream, derive `source_id` from canonical JSON
   `{"kind":"rdam.structured_source","version":"1.0.0","inputs":[...]}`.
   Entries contain `technique` and the exact payload, sorted by boundary name;
   payload arrays retain order. Model settings and requested missing structures
   do not change this source identity. At least one supplied structure is needed.
2. Default techniques are the explicitly supplied structures in caller order;
   providing `techniques` permits requested missing-structure outcomes.
3. With supplied upstream results, use their unique shared SourceIdentity and
   require explicit `derived_from` for each claimed derivation. An explicit source
   must equal it. Without upstream, an explicitly declared SourceIdentity is
   allowed for externally identified structures; it is not asserted to be the
   canonical bundle hash. No invented derivation in either case.
4. Empty Dung argument lists remain invalid under the current native contract;
   an empty set of stable extensions is a valid result. Do not conflate them.

## 5. Request wire representation

`serialize_request(request) -> bytes` and `load_request(bytes | str)` are shared
by CLI/HTTP and available to Python. Canonical UTF-8 JSON uses RFC 8785. The
SourceArtifact field `raw_bytes` is standard padded RFC 4648 base64 in JSON,
annotated `contentEncoding: base64`; Python still exposes bytes. Its decoder
requires valid alphabet/padding and verifies decoded size/digest. No inferred
UTF-8 serialization of archives; no double base64 or alternative binary field.
The actual model's JSON-mode serializer/validator owns this, so generated
validation/serialization schemas describe the real codec.

Requests must contain contract/version and required semantic fields; derived
artifact ids may be omitted only where constructors currently compute them.
If supplied, derived values must validate. Persisted results, by contrast, must
contain required digests; the reader must not repair a damaged saved result by
silently recomputing a missing digest. Unknown keys, duplicate keys at any depth,
trailing documents, non-finite numbers, invalid Unicode and invalid enum/strict
types fail before machine execution. Unknown native fields are governed by the
native validator, not silently deleted by transport code.

## 6. PreparationRequest and MachinePreparation

`PreparationRequest`: contract/version, `source: SourceIdentity`, exactly one of
`text: str | null` / `source_artifact: SourceArtifactRef | null`, and
`techniques: tuple[Technique,...] = ()`. Constructors mirror analysis source
constructors; selected techniques are unique ordered boundaries. No structured
payloads, upstream results or analysis formalisms are accepted here.

`MachinePreparation`:

| Field | Type | Meaning |
|---|---|---|
| `source` | SourceIdentity | Same submitted byte identity |
| `preparation` | existing PreparationSemanticEvidence | Complete canonical policies, inventory, default prepared document, warnings, coverage and plan |
| `projections` | tuple of SourceProjection | One per distinct selected requirement |
| `bindings` | tuple of PreparationBinding | One per selected boundary, in order |
| `semantic_digest` | Sha256Identity | Hash of all fields except this digest |

`PreparationBinding` is a discriminated union:

- `projected`: `technique`, full `requirement: ContentRequirement`,
  `projection_identity: Sha256Identity`, and standing `capability: CapabilityState`.
- `not_applicable`: `technique` and `reason="structured_input"`.
- `unavailable`: `technique` and `reason="not_implemented"` for an unregistered
  custom Machine boundary. An unavailable model alone does not prevent a provider
  from declaring a requirement and obtaining an inspectable projection.

The new preparation record contains one canonical inventory, not duplicate
persisted inventory/receipt copies. A private conversion derives the existing
provider-facing PreparationReceipt from this data without re-harvesting. Receipt
validation, mappings, policies and all projection derivations must reconcile.
The source input is not replayable by passing this output to analyse; that union
branch is intentionally absent. Semantic preparation omits timings and UUIDs,
so equivalent model-free requests can serialize identically.

## 7. AggregateAnalysis v2

| Field | Type | Meaning |
|---|---|---|
| `source` | SourceIdentity | Common source |
| `requested_techniques` | nonempty unique boundary tuple | Newly requested scope |
| `outcomes` | tuple of v2 Outcome | Exactly requested scope, in its order |
| `upstream_results` | tuple of current or HistoricalNativeTechniqueResult | Carried verbatim, not counted as new outcomes |
| `configurations` | tuple of BoundaryConfiguration | One per requested registered provider, in request order |
| `lineage` | tuple of existing ProviderDependencyReference | Validates consumers against outcomes and upstream against retained records |
| `preparation` | MachinePreparation or null | Absent only when no document material was supplied |
| `status` | `complete \| partial \| unsuccessful` | Derived and checked, never caller-asserted truth |
| `reading_guide` | `AnalysisReadingGuide` | Inline native interpretation and evidence-navigation metadata; see contracts/ai-usage.md |
| `semantic_digest` | Sha256Identity | Binds all semantic fields with native semantic identities |

`BoundaryConfiguration = {technique, provider_id, configuration}`. Unregistered
providers have no fabricated configuration; unavailable registered ones retain
their declared settings. V2 success is `{kind:"result", technique: boundary,
result: NativeTechniqueResult}`; unavailable and failed retain their existing
boundary-bearing shapes. Success boundary/formalism must agree with the provider
declaration; eRST is explicitly RST's formalism, never an eighth boundary.

Let N be the requested count and S the count of result outcomes:
`S=N => complete`; `0<S<N => partial`; `S=0 => unsuccessful`.
A valid empty-primary RST result is a result, but remains explicitly
`empty_primary_discourse` in its native payload and summary. Completion means
requests were answered, not that the document necessarily contained arguments.

`outcome_for(boundary)` searches only requested outcomes. Retained results use
explicit `upstream_results`; do not overload lookup. A request collision between
retained eRST and requested RST is invalid. Native payloads and historical
native semantic/artifact digests remain untouched.

V1 reader returns a historical type preserving original bytes/identities.
It exposes no derived v2 status/requested scope. Summary reports
`requested scope: unknown (legacy record)` rather than fabricating it.

## 8. MachineCapabilities v2

Retain all seven ordered TechniqueCapability records. Add:

- `source_forms: tuple[SourceFormCapability,...]`, reused from model-free ingest
  discovery rather than copied optional-package rules.
- `configurations: tuple[BoundaryConfiguration,...]` for registered providers.
- `contracts: tuple[ContractSupport,...]` with `contract`, `write_version`,
  `read_versions` and installed schema record names.
- `http_available: bool`, derived from optional dependency presence.
- `model_probe: Literal["not_performed"]` and `semantic_digest` over the record.

Capability means configured/declaratively runnable, not live credentials or
remote model reachability tested. It may validate local release metadata and
hashes, but performs no tensor loading, model construction or network call.

## 9. OperationFailure and VersionInfo

OperationFailure fields: contract/version; `operation` in
`configuration|capabilities|prepare|analyse|summary|view|schema|version|serve|publish`;
`category` in `invalid_request|source_unavailable|preparation_failed|
dependency_unavailable|busy|internal_error|output_error|interrupted`;
stable snake-case `code`; `retryability` from the existing enum;
safe `message` selected from a catalog; `issues: tuple[InputIssue,...] = ()`;
`completed_result_identity: Sha256Identity | null = null` for publication failure.
Also include `publication_state: not_published|published|unknown|null`, null for
non-publication errors. Post-commit fsync/delivery failure must not claim the
previous file was restored; the state and result identity describe what is known.
InputIssue has JSON-pointer `path`, stable `code`, and allowlisted `expected`
type/enum description, never a copy of rejected input. No raw exception strings,
tracebacks, source snippets, model prompts or private paths.

`OperationError` is the public exception for expected pre-result operation
failures and carries this record. ProviderError remains per-technique and is
folded by Machine. Unexpected exceptions continue to propagate in direct Python;
only the CLI/HTTP outer boundary translates them to a safe internal error and
non-success status, preserving exception chaining internally without logging it.

VersionInfo fields: contract/version, `package: "rdam"`, installed `version`,
and `contracts: tuple[ContractSupport,...]`. Version data derives from installed
metadata and the shared registry; no manually copied package version.

## 10. AI-consumption records

The exact guide and view fields/invariants are defined once in
[contracts/ai-usage.md](contracts/ai-usage.md). They are typed, closed models in
`rdam/interpretation.py`, included in the shared registry and generated schemas.
Provider declarations additionally carry their native interpretation descriptors;
the generic machine binds those descriptions to outcomes without importing
technique implementations. Guides never enter a native inference cache key:
cached native results acquire the current compatible guide when aggregated.
Descriptor identity participates in the outer aggregate digest. Historical
aggregate v1 stays readable but cannot be selected as a v2 AnalysisView.

## 11. Testing

[contracts/analytical-quality.md](contracts/analytical-quality.md) specifies
ordinary regression tests, focused real-model checks and cold critique. No
additional evaluation records, review-state models or approval schema are needed.
