# Contract: Execution, Cache, and Alignment

**Feature**: 017 | **Authority**: [spec.md](../spec.md) FR-028..FR-039, SC-011..SC-017

## Analytical identity

A result is determined by, and only by, these inputs. Anything that can change the result is
in the key; anything in the key can change the result.

| Element | Present for | Why it must be in the key |
|---|---|---|
| source identity | all | a different document |
| **projection identity** | all text techniques | same document, different admitted content, transformation, or segmentation. Under the projection model this replaces a bare "prepared content" element and is what makes the key correct |
| provider id | all | a different implementation |
| provider contract version | all | the provider's own output contract changed |
| model identity | model-backed | `gpt-5.6-sol` and `claude-opus-5` do not produce interchangeable analyses |
| instructions identity | model-backed | prompts are generated from the formalism; a scheme-table or element change changes the analysis |

The Toulmin and Walton providers already emit an `instructions_digest`; this contract lifts
that existing value into the key rather than inventing one.

## Cache behaviour

1. Caching is **opt-in** by configuration, matching
   `ProductionIngestor.analyse(..., cache_directory=None)`. With none configured the machine
   behaves exactly as today and writes nothing (FR-030).
2. A cache answers only on an exact match of every element of the analytical identity. Any
   difference is a miss. No near-match, no partial reuse, and no time-to-live — the key is
   content-addressed, so a stale hit is impossible by construction (FR-029).
3. Writes are atomic and integrity-checked, following `ProductionIngestCache` (FR-031).
4. On load, the stored result must re-validate against its own contract and its recomputed
   digest must match. A corrupt, truncated, or contract-stale entry is a **miss** — the
   analysis is performed again. Never an error, never a wrong answer.
5. A hit returns a semantically identical result and performs **zero** model requests
   (SC-011).

## Concurrent execution

1. Independent providers MAY execute concurrently, in-process, using a bounded thread pool
   (FR-032, FR-039). No distributed execution, work queue, scheduler, or remote control
   plane.
2. Concurrency MUST NOT change outcome semantics (FR-033):
   - exactly one outcome per requested technique;
   - one provider's failure never suppresses another's success;
   - the machine still never retries.
3. Concurrent and sequential execution of one request MUST produce **identical aggregate
   semantic digests** (FR-034, SC-014). Outcomes are keyed by technique and the aggregate
   validator already forbids duplicates, so completion order cannot leak into the result —
   this makes that a checked property rather than an argument.
4. A provider whose runtime is not safe in parallel MUST be identified **by measurement**
   and serialised (FR-035). It MUST NOT be run concurrently on the assumption that it is
   fine.
5. A non-`ProviderError` exception is a bug and MUST still propagate natively. Running
   concurrently MUST NOT capture it and relabel it as a provider failure (FR-036).

## Semantic identity versus execution evidence

Native payloads retain their complete provider-owned result, including execution evidence.
`NativeTechniqueResult.artifact_digest` verifies that complete envelope. Its
`semantic_digest` excludes only the payload paths explicitly named by that provider in
`execution_fields`; paths must exist and be unique. RST declares its native execution,
timing, timestamp, and unit-duration fields. Analytical text, trees, anchors, and validation
remain part of semantic identity. The aggregate hashes result semantic identities, so run
timing cannot make sequential and concurrent aggregates analytically different.

## The RST parser measurement

The 2026-09-04 stress run passed eight real CPU/MPS cases: both DMRST and UniRST,
at predictor and full-provider boundaries, including concurrent cold initialization.
See [parser-concurrency.md](../evidence/parser-concurrency.md) for the command and limits.
The declaration permits concurrent CPU/MPS RST inference. Other devices and eRST
completion remain serialized because this experiment does not establish their safety.

### Historical starting point

Established from `tests/stress/test_concurrency_stress.py` on 2026-09-03:

| Proven thread-safe | Not established |
|---|---|
| `ProductionIngestor.prepare()` — 30 sources, 16 workers (built with `parser=None`) | `PredictorDMRST` and `PredictorUniRST` under concurrency |
| `NeuralSecondaryEdgeScorer` forward pass — 16 tasks, 8 workers, CPU, `float32` | any concurrent execution on **MPS** |
| BLAKE3, SHA-256, RFC 8785 digests | — |

Preparation being already proven thread-safe is what makes inventory-once-then-project safe
regardless of how this resolves.

Settled by **experiment before reliance**: a stress test runs the real parser concurrently
with model-backed providers, on CPU and on MPS, asserting byte-identical trees against a
sequential baseline. If it fails, the RST provider is serialised behind a lock while the four
network-bound providers still run concurrently — retaining nearly all the benefit, since RST
is the only local-compute provider.

## Alignment

1. Every projection's segments anchor into the **one** inventory. Results from different
   techniques over one source are therefore alignable on source anchors (FR-037).
2. Alignment MUST NOT merge formalisms. Reporting an RST relation and a Toulmin ground over
   the same span is two native findings sharing a coordinate — not a combined structure, not
   a shared vocabulary, not a new theory (006 FR-013).
3. This is the machine's payoff: seven analyses of one source,
   comparable on the source. SC-015 demonstrates it by reporting two techniques' findings
   over one span.

## Boundaries

1. The machine MUST NOT derive one technique's input from another technique's output.
   Cross-technique consumption stays caller-declared with recorded lineage (FR-038, 006
   FR-015). This feature does not automate it.
2. Providers remain synchronous. Concurrency is achieved around the existing `Provider`
   protocol, not by rewriting it — no provider changes to gain it.
