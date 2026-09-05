# Contract: Python API and Shared Operations

**Status**: Proposed public API for Feature 019, not executable current syntax.

## Public surface

The root `rdam` exports the machine, request/config/result types, existing native
result types, and shared serialization/summary/schema functions. No second
orchestrator, provider-specific CLI or compatibility façade is introduced.

```python
production_machine(*, config: MachineConfig | None = None) -> Machine

Machine.capabilities() -> MachineCapabilities
Machine.prepare(request: PreparationRequest) -> MachinePreparation
Machine.analyse(request: AggregateRequest) -> AggregateAnalysis

load_config(path: Path | str) -> MachineConfig
serialize_config(config: MachineConfig) -> bytes
load_request(payload: bytes | str) -> AggregateRequest
serialize_request(request: AggregateRequest) -> bytes
load_preparation_request(payload: bytes | str) -> PreparationRequest
serialize_preparation_request(request: PreparationRequest) -> bytes

load(payload: bytes | str) -> PersistedRecord
serialize(record: PersistedRecord) -> bytes
summarise(record: AggregateAnalysis | HistoricalAggregateAnalysis
          | MachinePreparation | MachineCapabilities) -> str
schema(record_name: str, *, mode: Literal["validation", "serialization"]
       = "validation") -> Mapping[str, JsonValue]
version_info() -> VersionInfo
select_analysis(analysis: AggregateAnalysis, *,
                techniques: tuple[Technique, ...]) -> AnalysisView
```

These signatures define shape and ownership, not full implementation bodies.
Current native results use the corrected v2 envelope and applicable versioned
provider contracts in [native-integrity.md](native-integrity.md); presentation
preservation means keeping those produced records intact, not retaining defects.
The public `production_machine(model=..., execution_policy=...)` arguments are
replaced by MachineConfig in the same feature; update current consumers and docs
in the implementation pass. No deprecated forwarding arguments are added.
Direct `Machine(providers, execution_policy=...)` remains supported for custom
Python compositions, using actual provider declarations for configuration.

Importing `rdam`, requesting help/version/schema, or constructing a source
request must not import HTTP dependencies, load weights or create LLM clients.
Configuration model definitions must not import a technique implementation;
composition performs lazy technique-specific default/policy resolution.

## One execution path

```text
Python request ───────────────┐
CLI acquisition → request ───┼─→ Machine.prepare / Machine.analyse
HTTP decode → same request ──┘       │
                         shared ingest + native providers
                                    │
                         typed record → shared serializer
```

Source acquisition is allowed only in explicit Python/CLI path constructors.
The shared source constructor owns suffix inference, including `.txt`/`.text`,
and the current format inference rules. Unknown suffixes require `source_form`.
The request loader cannot read disk or dereference a URL. A materialized request
continues to analyse its captured bytes if its original file changes.

`prepare` inventories once and derives selected projections with no inference.
`analyse` calls the same internal preparation function once, then executes
requested providers. It does not call a public prepare method and then reharvest
again inside analysis. RST consumes the resulting provider projection through
its prepared path; native content admission and evidence remain provider-owned.
No document material for a structured-only request means no inventory call.

Default `prepare` selects no provider projections; `techniques=()` is legal only
for preparation. It returns all canonical preparation evidence, not only prose.
Requested structured techniques have `not_applicable` preparation bindings.
Unavailable model configuration can still produce a projection from a declared
content requirement; the binding explicitly retains the capability limitation.
Preparation never claims that a model has accepted or analysed the source.

## Requests and configuration

The exact fields, defaults, binary encoding, identities and version registry are
normative in [data-model.md](../data-model.md). No transport adds another meaning.
MachineConfig remains fixed; request formalism selection overrides the configured
default formalism only. RST evidence/refinement choices are configured defaults
and must reach the actual native AnalysisPolicy rather than be dropped by the
provider. Its existing validation, relation-interpretation and losslessness
defaults are preserved; lower-level Python policy APIs are not removed.

LLM retry budgets are explicit existing provider behavior. The machine and its
adapters add no retry, inferred technique, fallback model or automatic derivation.
The effective per-boundary configuration is recorded even for a registered but
unavailable provider. Credentials and transport resource limits are not analysis
request fields.

## Outcomes and errors

Analysis returns aggregate v2 with request-ordered boundary outcomes and separate
retained results. `status` and `outcome_for` are defined by that requested scope.
Native empty-primary RST and a Dung result with no stable extensions are valid
results, not failures. Missing structured input is unavailable; a malformed
native structure accepted as JSON is a typed provider failure, not a made-up
structure. Shell input acquisition errors and malformed request envelopes happen
before provider execution.

Expected source/configuration/preparation errors cross the common operation
boundary as OperationError with a safe OperationFailure. A provider's typed
ProviderError becomes its failed outcome. An unexpected programming exception
propagates natively in Python; it is not wrapped inside a successful aggregate.
Pending work is cancelled where possible, already-running threads finish under
existing semantics, and no aggregate is returned. Do not claim thread preemption.

Serialization validates identities and field invariants before emitting bytes.
Request/config validation and record digest verification are shared by all
interfaces. A stored result missing a required digest is invalid, not repaired.
Canonical output uses no trailing LF at the Python serializer boundary;
CLI adds exactly one LF, HTTP returns the unframed bytes.

## Summary and schema contracts

`summarise` is a pure projection of an already validated record. It reports:

- Contract/version and source name/identity, escaping terminal control characters.
- Aggregate requested count and completion status; one row per requested outcome
  with boundary, state, returned native formalism, provider/model identity, or
  failure/unavailability code and retryability.
- Separate retained upstream count and identities, never counted as new results.
- Preparation inventory/primary/retained coverage, source warnings and projection
  bindings. No ungrounded narrative explanation or newly inferred argument.
- Full result semantic identity so the view cannot be mistaken for the result.
- `empty_primary_discourse` when RST's native result explicitly declares it.
- Unknown requested scope for v1; no inferred complete/partial classification.

This is an analytical run summary, not a newly generated prose interpretation.
It never reloads configuration, calls a provider or alters the stored record.
No native schema is mined opportunistically for optional counts.

Schema names are exactly the registry keys: `request`, `preparation-request`,
`configuration`, `preparation`, `aggregate`, `capabilities`, `native-result`,
`operation-error`, `version`, `analysis-view`, `view-request`, plus `dung-input` and `ibis-input` for caller-authored
structures. Native input schemas are projected from provider-owned validators;
semantic graph constraints that JSON Schema cannot express remain documented and
tested in native validation. Provider output schema names are `rst-result`,
`erst-result`, `pdtb-result`, `sdrt-result`, `toulmin-result`, `walton-result`,
`dung-result` and `ibis-result`; they describe the actual versioned native payloads,
including computed output fields, rather than reusing extraction-input schemas.
Historical variants append their explicit major version, such as
`native-result-v1` or `walton-result-v1`; current aliases resolve via the registry.
Do not pretend a schema replaces semantic/source validators.
Generated output uses Draft 2020-12, with ids under
`https://schemas.rdam.local/<contract>/<version>/<mode>.schema.json` for new
machine contracts only. Existing ingest schema ids are not renamed.

## Exact parity boundary

Equivalent means identical materialized request, source metadata, provider
configuration, source revision and external model response. Canonical byte
equality applies to equivalent deterministic records. Repeated model execution
may vary; analytical equality uses declared native execution-field exclusions,
not ad hoc removal of differing values. Changed origin/name is a documented
provenance difference even when the source bytes are identical.

HTTP configuration is selected at startup. An HTTP caller needing another model
starts another configuration sequentially; this feature adds no multi-model
pool, per-request machine factory or persistent job architecture.

## Direct AI use

Every v2 analysis already includes the inline reading guide; no extra call is
required for AI use. `select_analysis` is a pure, optional saved-record projection
for explicit technique selection, not a replacement analysis or prose summary.
Its full contract is [ai-usage.md](ai-usage.md). The public `ViewRequest` carries
`analysis` plus `techniques` for transport; `load_view_request` and
`serialize_view_request` use the same dedicated-codec conventions as requests.
