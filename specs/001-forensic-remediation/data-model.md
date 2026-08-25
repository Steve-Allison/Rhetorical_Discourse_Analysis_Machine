# Data Model

All production request/result/config/status/receipt/evidence/report boundaries below are Pydantic 2
models with `extra="forbid"`, immutable/frozen configuration where mutation is not part of the
contract, explicit schema versions, and JSON-safe fields. Internal hot-path candidates may remain
`@dataclass(frozen=True, slots=True)`.

## Format projection

### ProjectedTreeNode

| Field | Type | Invariant |
|---|---|---|
| `node_id` | non-negative integer | Stable within one projection only |
| `kind` | `edu`, `span`, or `multinuclear_group` | Matches tree role |
| `text` | string | Exact `source_text[char_span[0]:char_span[1]]` |
| `char_span` | pair of non-negative integers | Half-open; start <= end |
| `edu_span` | pair of positive integers | One-based inclusive; start <= end |
| `leaf_ordinal` | positive integer or null | Present exactly for EDUs |
| `descendant_leaf_ids` | non-empty tuple of node IDs | Ordered by document occurrence |

Internal nodes derive `char_span` and `edu_span` from the first/last descendant leaf. No format
adapter may synthesize these fields.

### FormatRstAnalysis

Existing public analysis extended so every serialized EDU and relation requires `text`, `char_span`,
and `edu_span`. Envelope schema values are format-specific: Docling `1.2`, DocLang `1.1`, Markdown
`1.1`. A shared conversion produces canonical `RstAnalysis`.

## Signal and candidate domain

### DiscourseSignal

| Field | Type | Invariant |
|---|---|---|
| `signal_id` | non-empty string | Unique per document |
| `signal_type` | non-empty string | Current eRST type |
| `signal_subtype` | non-empty string | Current eRST subtype |
| `token_anchors` | non-empty tuple of token indexes | Ordered; overlap with other signals allowed |
| `char_spans` | non-empty tuple of half-open spans | Exact source anchors |
| `confidence` | float [0,1] | Calibrated detector confidence or 1.0 for gold |
| `detector` | name/version/revision record | No unversioned detector provenance |
| `compatible_relations` | tuple of raw relation labels | Learned from train only for predicted generation |

### SecondaryEdgeCandidate (internal)

Immutable dataclass containing document ID, ordered source/target node IDs, exact node/head/context
spans, signal IDs, direction, distance, primary path, existing primary relation(s), raw relation
hypothesis, structural features, and optional gold annotation. Equality/hash exclude gold annotation
for candidate-identity tests. Candidate existence is determined before gold is attached.

### SecondaryRelationPrediction

Contains candidate identity, no-edge probability, raw GUM relation probability inventory, selected
raw label, derived ontology concept, calibrated confidence, and decoder decision/reason.

### ErstDecodeReceipt

Records input candidate count, streamed batch count, accepted/rejected counts by formal reason, output
edge identities, decoder configuration hash, and peak resource evidence. Rejection reasons are only
`insufficient_signal`, `self_loop`, `invented_node`, and `duplicate_directed_pair`.

## Corpus boundaries

### CorpusLoadFailure

| Field | Type | Invariant |
|---|---|---|
| `source_path` | relative path | Never an unbounded absolute/private root |
| `document_id` | string or null | Null only if identity cannot be parsed |
| `failure_type` | enum | Stable machine-readable category |
| `message` | sanitized string | No corpus text or secrets |
| `exception_type` | string | Exact exception class |

### CorpusDocumentReceipt

Document ID, relative source path, source SHA-256, corpus revision, licence class, official partition,
node/EDU/primary-edge/secondary-edge/signal/candidate counts, raw relation inventory, and success.

### CorpusLoadReceipt

Schema/package/corpus revision, corpus-root fingerprint (not path), accepted document receipts,
failures, aggregate counts, and receipt hash. Valid state requires at least one accepted document,
non-zero candidates, and zero failures when `fail_on_error=True`.

### SplitManifest

Contains corpus revision, exact upstream `splits.md` hash, partition-to-document mapping,
partition-to-source-hash mapping, per-partition counts, disjointness proof, and manifest SHA-256.
Validation rejects document or source-hash overlap and any source not named by the official authority.

## Experiment boundaries

### ExperimentProtocol

Frozen schema containing:

- protocol/schema/package versions and immutable source/model revisions;
- candidate generator, signal detector, feature, raw label, scorer, and decoder schema hashes;
- split/corpus hashes and licence policy;
- screening/final seeds and finalist rule;
- threshold/calibration selection restricted to dev;
- ablation matrix;
- gold/gold and predicted/predicted evaluation settings;
- bootstrap resamples (10,000), pairing unit (document), Holm correction;
- resource and device measurement definitions;
- selection thresholds;
- test-access policy and one-time evaluation rule.

The model validates that test/test2 paths are absent from training/tuning inputs.

### ExperimentRunReceipt

Run ID, protocol hash, architecture/config hash, seed, permitted partitions, hardware/software identity,
start/end time, step counts, checkpoint/prediction/scorer hashes, governed metrics, calibration,
latency/RSS/MPS memory, completion state, failures, and reproducibility command. A successful training
receipt requires positive candidates, positive steps, a present validated checkpoint, and scorer
output.

### StatisticalComparison

Champion/baseline IDs, paired document set hash, metric deltas, 10,000-resample interval, uncorrected
and Holm-corrected p-values, calibration/resource deltas, and deterministic statistic seed.

### ChampionManifest

Frozen protocol hash, selected run/config family, finalist evidence hashes, dev-only selection reason,
and champion-manifest SHA-256. Creation is the capability token required by final evaluation.

### FinalEvaluationReceipt

Champion hash, one-time nonce persisted locally, untouched test/test2 input hashes, governed outputs,
metrics, resource evidence, comparison, and completion timestamp. Validation prevents a second final
evaluation for the same protocol/champion workspace.

### SelectionDecision

One boolean/result per selection threshold, evidence hash per result, overall `selected` or
`no_selection`, and an allowed-actions list. `selected` is valid only when all booleans are true.

## Checkpoint boundary

### ErstCheckpointManifest

| Group | Required content |
|---|---|
| Identity | manifest schema, package 4.0.0, architecture, immutable HF/upstream revisions |
| Integrity | every relative file path, byte size, SHA-256; no unlisted files |
| Construction | bundled model/tokenizer/config and strict state-dictionary targets |
| Features | signal/candidate/raw-relation/ontology/decoder schema and hashes |
| Research | corpus/split/protocol/champion/run/final-evaluation hashes |
| Metrics | governed secondary metrics, calibration, latency, RSS, CPU/MPS parity |
| Licences | code, model base, annotations, underlying-text policy, private-only flag |
| Provenance | producer/version/source commit/created time/private HF revision |

Required bundle members include manifest JSON, signal detector safetensors/config, scorer
safetensors/config, graph component safetensors/config when present, tokenizer files, calibration JSON,
raw relation inventory, ontology mapping, decoder config, and test vector/expected graph. A component
that has no learned state has a config and explicit `state_file: null`; it cannot disappear silently.

## State transitions

```text
corpus_source
  -> CorpusLoadReceipt(valid)
  -> SplitManifest(disjoint)
  -> repository scorer contract(valid)
  -> ExperimentProtocol(frozen)
  -> reference receipts(complete)
  -> architecture receipts(complete)
  -> ChampionManifest(dev only)
  -> FinalEvaluationReceipt(one time)
  -> SelectionDecision
      -> no_selection -> corrected 4.0.0 without canonical checkpoint
      -> selected -> ErstCheckpointManifest -> strict reload parity -> private immutable HF revision
```

Any invalid or absent boundary object stops the transition; callers cannot substitute a path, raw
dictionary, or inferred success.
