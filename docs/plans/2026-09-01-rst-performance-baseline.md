# RST Performance Baseline and Targets

**Date**: 2026-09-01 · **Status**: drafted, blocked on preconditions · **Owner ruling
needed**: ratify the proposed ceilings after the baseline lands (§4).

## 1. Purpose and preconditions

Define what "performant" means for the RST analysis process, measure the truth, and
gate all optimisation on the measurements. Today no inference performance target exists
anywhere in the repository and no end-to-end parse throughput has ever been recorded as
evidence — the only measured surface is ingest preparation
(`specs/004-production-api-contract/evidence/performance.json`: ~13ms/100k chars,
~118ms/1M chars against 2s/15s thresholds).

Preconditions — all must hold before any measurement run:

- [ ] The ModernBERT convergence run (task-636), its promotion, and clean-room
      certification are complete under the 004/005 workstream; zero training or
      evaluation processes live on the machine.
- [ ] The promoted release id and its store path are recorded (the measurement targets
      the promoted release, not a checkpoint).
- [ ] `scripts/bench.py` and `scripts/benchmark_modernbert.py` are read in full at
      their post-004/005 committed state before use — both are modified in that
      workstream's working tree at drafting time, so their current shape is
      unverified here. Extend the existing harness where coverage is missing; do not
      author a parallel one.

## 2. Workloads (the measured surface)

| ID | Workload | Input | Primary metric |
|---|---|---|---|
| W1 | Interactive single doc | ~1k chars, plain text | warm p50/p95 latency, end-to-end `analyse_source` |
| W2 | Medium document | ~10k chars, Markdown | warm p50/p95 latency |
| W3 | Megadoc via subdivision | ≥100k chars (reuse the megadoc stress fixtures) | wall-clock; subdivision overhead share |
| W4 | Corpus throughput, cache cold | 25+ mixed-form docs | docs/min, chars/sec, peak RSS |
| W5 | Cache-warm repeat | same corpus as W4, unchanged sources | per-doc latency; measured cache benefit vs W4 |
| W6 | Cold start | fresh process | model load + first-call time |
| W7 | Dtype matrix | W1+W2 inputs on the promoted ModernBERT release | fp32 vs bf16 vs fp16 on MPS, plus CPU fp32 fallback |

Every run records: repository commit, model release id, device, dtype, macOS and torch
versions, warmup runs discarded, and ≥5 measured runs per case (matching the
established preparation-evidence protocol).

## 3. Metrics

- Latency: p50 and p95 wall-clock per workload (warm, post-warmup).
- Throughput: characters/sec and EDUs/sec (W3, W4).
- Memory: peak RSS per workload; W3 additionally checked against the memory-leak
  stress expectations.
- Cache: W5/W4 latency ratio — the first recorded measurement of what the
  fingerprinted cache actually buys.
- Dtype: W7 speed deltas *and* the topology-equivalence check from
  `tests/test_integration.py` — a faster dtype that breaks bit-equivalent topology is
  not a candidate. **The standing "fp32 beats bf16 on Apple Silicon" guidance was
  measured on the retired xlm-roberta models at ~1k-char inputs and is void for
  ModernBERT until W7 re-measures it.**

## 4. Targets — protocol, then numbers

**Protocol**: baseline first, thresholds second. The baseline run records reality with
no pass/fail. Thresholds then take two forms:

1. **Regression guards** (mechanical, no ruling needed): every later measurement must
   stay within **1.2× the ratified baseline** per workload metric, enforced the same
   way the preparation thresholds already are.
2. **Absolute ceilings** (owner-ratified): the following are *proposals* grounded in
   usability, not measurements — ratify, tighten, or discard each once the baseline
   shows what the hardware actually does:

| Workload | Proposed ceiling (p95 unless stated) |
|---|---|
| W1 interactive single doc, warm | ≤ 2s |
| W2 medium doc, warm | ≤ 10s |
| W3 megadoc | ≤ 5 min wall-clock, RSS bounded per stress expectations |
| W5 cache-warm repeat | ≤ 250ms per doc |
| W6 cold start | ≤ 30s |

## 5. Execution checklist (post-preconditions)

- [ ] Read `scripts/bench.py` and `scripts/benchmark_modernbert.py` in full; map
      existing coverage against W1–W7; extend the harness for gaps (likely W4/W5
      corpus+cache runs and end-to-end `analyse_source` timing).
- [ ] Run the matrix on the promoted release; write results as release evidence
      (`isanlp_rst.release_evidence.performance` schema, alongside the 004 pattern)
      plus a human summary in this plan's companion results file.
- [ ] Bring the baseline and the §4 table for owner ratification; codify ratified
      thresholds as an automated check in the same style as
      `production-ingest-performance`.
- [ ] Feed the ratified figures into the 006 promotion contract's latency/resource
      evidence class as the RST provider's recorded values.

## 6. Optimisation decision rule

No optimisation lands without a workload measurably missing its ratified target or a
measured win on a real workload. Candidate levers, in expected order of value, each
gated on the baseline:

1. **Pipeline parallelism for corpus workloads (W4)**: parallel CPU-side preparation
   feeding a serialized MPS inference queue — MPS is effectively single-stream, so
   parallel *inference* is not the lever; keeping the stream fed is.
2. **Dtype selection from W7 evidence** (topology-equivalence constrained).
3. **Cache hit-path verification from W5** — if the warm ratio is poor, profile
   fingerprinting and deserialization before touching anything else.
4. **Batch sizing / encoder-window tuning within the sliding-window path** — only
   with W2/W3 evidence, and never altering inference mathematics.
5. **`torch.compile` evaluation** — last, measured, and only if MPS support proves
   stable for the promoted model.

## 7. Out of scope

Trained architecture and inference mathematics are untouchable under optimisation
(constitution II; spec 006 FR-011). No performance change ships as a side effect of
repository migration — migration's SC-002 equivalence baseline and this performance
baseline are separate instruments and must not be mixed.
