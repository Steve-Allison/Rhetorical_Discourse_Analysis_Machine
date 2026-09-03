# Contract: Standardised Production Patterns

These patterns are shared semantics with one owner, not copy-and-paste templates.

| ID | Pattern | Canonical owner | Consumers |
|---|---|---|---|
| P1 | Closed typed provider declarations, capabilities, native results, outcomes, and lineage | `rdam/contracts.py` | all providers and the machine |
| P2 | RFC 8785/I-JSON canonical serialization and SHA-256 semantic identity | `rdam/_canonical.py`, `rdam/serialization.py` | aggregate records, RST records, and provider provenance |
| P3 | Side-effect-free capability inspection, bounded parallel execution, and deterministic explicit outcomes | `rdam/machine.py`, `rdam/_execution.py` | all seven technique boundaries |
| P4 | Exact source identity and source-preserving native payloads | `rdam/contracts.py`; provider-native validators | every text-backed provider |
| P5 | Typed failure with mandatory retryability; unexpected internal bugs propagate | `rdam/contracts.py`, `rdam/machine.py` | every provider |
| P6 | Canonical model identity and one wall-clock budget over bounded transport/output attempts, with no provider-SDK implicit retry | `rdam/_llm.py` | PDTB, SDRT, Toulmin, Walton |
| P7 | Universal structured-source inventory, preparation, anchors, subdivision, and cache | `rdam/rst/ingest/` | the RST provider |
| P8 | Immutable local model releases, device handling, and compatibility redeclaration | `rdam/rst/model_loading/` | local RST families |
| P9 | Canonical framework identity projection from vendored Central authority | `rdam/frameworks.py`, `rdam/resources/` | every declaration/formalism |
| P10 | Production/workbench source and artifact separation | `tools/production_boundary/` | repository and release gates |
| P11 | Recursively immutable native JSON inputs/payloads with unchanged wire types | `rdam/_immutable_json.py`, `rdam/contracts.py` | aggregate requests and native results |
| P12 | Installed/build/checkout revision plus composed provider provenance/failures | `rdam/_provenance.py`, `rdam/_provider_provenance.py` | all seven providers |
| P13 | Clean-revision-only opt-in native-result cache with atomic writes and per-key single flight | `rdam/_result_cache.py`, `rdam/machine.py` | aggregate execution |

## Reuse rule

A second caller reuses a shared pattern only when its semantic contract matches. Native
technique models are deliberately not standardized: SDRS graphs, PDTB relations,
Toulmin layouts, Walton schemes, Dung extensions, IBIS structures, and RST trees retain
their own meanings.

## Model boundary

The machine itself never retries. `StructuredAnalyst` owns only model-boundary retries:

- structured-output validation attempts are bounded by the agent output budget;
- transport attempts cover only enumerated transient statuses/errors;
- exponential backoff uses full jitter and honours `Retry-After`;
- one `asyncio.timeout` budget covers backoff, transport, output validation, and the active request;
- provider clients are constructed with implicit retries disabled;
- success and exhaustion expose separate observed attempt counts.

Deterministic native validation is never retried by the machine and never repaired.

Feature 018 does not generalize P7: universal source preparation and format handling remain
deferred to Feature 017 and are not cache/execution responsibilities.
