# Implementation Plan: Universal Source Pipeline

**Branch**: `017-universal-source-pipeline` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/017-universal-source-pipeline/spec.md`

## Summary

Source preparation becomes the machine's, and becomes correct for seven techniques instead
of one.

The existing inventory is kept and promoted: it already classifies 23 content types, carries
nine discriminated representations including full table geometry, anchors through eight
anchor kinds, and accounts coverage exactly. What changes is that it stops producing a
single RST-shaped projection of itself. Each provider declares a **content requirement** —
the classes its formalism can analyse, how non-text representations project, its capacity
unit and maximum, its boundary preferences, and whether it needs speaker identity. A
projection is then a deterministic function of `(inventory, requirement)`; identical
requirements share one.

That closes two live correctness gaps rather than only a plumbing one: Toulmin and Walton
can see the tables their grounds live in, and dialogue keeps its speakers for SDRT. It also
makes the machine's real payoff reachable — seven analyses anchored into one inventory, and
therefore comparable on the source without ever being merged into a common formalism.

Around that: ingest moves to `rdam.ingest`, and the machine accepts files and bytes so all
six source forms become reachable. Concurrency, per-provider serialisation and a result
cache **already exist** in the tree; this feature audits them against the specification
rather than building them — adding the projection identity to the cache key, replacing the
blanket lock with declared parallel safety, and running the parser-concurrency measurement
that was never taken.

Ingest is **moved**, with callers updated to its canonical module and no compatibility
re-export (owner ruling, 2026-09-04). RST's requirement reproduces today's policy exactly, so the
classified baseline comparison can hold at zero analytical differences. Concurrency is
threads around the unchanged synchronous `Provider` protocol, so no provider is rewritten
to gain it.

## Technical Context

**Owner-approved final verification repair, 2026-09-04:** the historical zero-difference
gates below describe the original migration checkpoints. Final acceptance follows the
revised FR-005 / SC-010: independently prove the file-origin identity and DocLang table
corrections, report them separately, and require zero unexplained regressions. Keep the
historical baseline unchanged. `tools/production_boundary/baseline_corrections.py` owns
the source-based proofs; `rst_baseline.py` owns capture, comparison and reporting;
`tests/production_boundary/test_baseline_corrections.py` proves both acceptance and
rejection of deliberate corruptions. No production compatibility code is introduced.

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"`); PEP 649 deferred
annotations, PEP 695 generics and `type` aliases. No `from __future__ import annotations`.

**Primary Dependencies**: pydantic v2 (frozen, strict, `extra="forbid"` records), `rfc8785`
for RFC 8785 canonical JSON, pydantic-ai + openai at the LLM boundary, torch + transformers
for the RST parsers, and the optional `formats` extra (`docling-core`, `doclang`,
`markdown-it-py`, `mdit-py-plugins`).

**Storage**: local filesystem only — content-addressed cache directories and the immutable
model release store. No database.

**Testing**: pytest via pixi. Markers: default fast suite, `slow` (model loads), `stress`
(concurrency, megadoc, memory). Model doubles only at the genuinely external boundary
(Pydantic AI `FunctionModel` with `ALLOW_MODEL_REQUESTS = False`).

**Target Platform**: macOS on Apple Silicon, MPS-aware with CPU fallback and explicit CUDA
paths. One person, one local machine.

**Project Type**: single library distribution `rdam` 6.0.0, one wheel, every technique a
sub-package.

**Performance Goals**: an aggregate over four model-backed techniques completes in
materially less wall-clock time than the sum of the four run individually (SC-013); a
repeated identical analysis against a configured cache performs zero model requests
(SC-011). No throughput or concurrency-scale target — the scale ruling makes those
meaningless here.

**Constraints**: inventory runs exactly once per aggregate; zero analytical differences in
the RST baseline comparison; persisted contract identifiers unchanged **and asserted
directly**; nothing enters a projection without a recorded derivation; no invented speakers;
parallel safety declared rather than assumed; no checker suppressions; in-process only.

**Scale/Scope**: relocation of 25 modules / 10,477 lines with **111** code and 29 document
references; new requirement and projection contracts; a speaker contract; one new
transformation parameter kind; changes to `rdam/contracts.py`, `rdam/machine.py`,
`rdam/_llm.py`, and six of the seven providers. Baseline at the time of writing: **1596**
tests collected, all seven techniques available — re-measured at T001 rather than trusted.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|---|---|---|---|
| **I. Evidence Before Claims** | Claims grounded in evidence inspected now; sample scope retained; unverified hypotheses marked and dated | **PASS after correction** — an earlier draft asserted the machine had no concurrency, which had become false while this was being written. Every Context row was re-measured on 2026-09-03 and T001 re-takes them before implementation | **PASS** — R8 (parser concurrency on MPS) is carried as an open risk settled by experiment, and is now known to be a debt against *shipped* behaviour rather than planned behaviour |
| **II. One Production Quality Bar** | Modern Python 3.14, accurate types, no suppressions, no weakened tests; trained architecture and inference maths untouched | **PASS** — SC-017 forbids suppressions; FR-005 forbids analytical change | **PASS** — the relocation moves modules without touching inference maths; the baseline comparison enforces it |
| **III. Solo-Local Simplicity** | One person one machine; no multi-user, distributed, or hypothetical configurability; no silent scope reduction | **PASS** — FR-039 forbids distributed execution and queues | **PASS** — threads in one process; requirements are declared by providers from their formalism, not exposed as caller knobs, so no configurability is invented |
| **IV. Honest Verification** | Claims cite checks actually run; doubles only for genuinely external systems; verification proportional and dependency-aware | **PASS** — every SC names a runnable check | **PASS** — the model is the only mocked boundary; predictor-stack changes trigger `test-all` and `smoke` per the commands rule |
| **V. Canonical Contracts** | One canonical authority per governed fact; public contracts explicit and tested; upstream specs verified before format-native work | **PASS** — FR-001 gives ingest one owner; FR-026 keeps the capability report authoritative | **PASS** — one canonical import and type name; no compatibility shims or second source-form list |

**Also checked**: the import root stays `rdam` with seven native boundaries and no shared
formalism; production imports no offline or dev dependency; core imports stay usable
without the `formats` extra; secrets are never committed or printed.

**A note on scope, against principle III.** This feature is larger than a relocation, and
that is deliberate rather than accretive. Delivering the pipeline alone would hand all seven
techniques the RST projection, which produces confabulated Toulmin grounds and speaker-less
SDRT — analyses that look correct and are not. Under principle III, omitting required
behaviour is a defect, not simplicity. The projection model is the smallest design that
makes the pipeline correct for the machine that exists.

**Result: PASS, no violations. Complexity Tracking is therefore empty and omitted.**

## Project Structure

### Documentation (this feature)

```text
specs/017-universal-source-pipeline/
├── spec.md              # FR-001..FR-043, SC-001..SC-020
├── plan.md              # This file
├── research.md          # R1..R10, each with decision, rationale, rejected alternatives
├── data-model.md        # entities, fields, validation, state
├── quickstart.md        # a runnable check per success criterion
├── contracts/
│   ├── source-pipeline.md      # ownership, entry points, inventory, projection, speakers
│   └── execution-and-cache.md  # analytical identity, cache, concurrency, alignment
├── checklists/
│   └── requirements.md  # spec quality checklist
└── tasks.md             # Phase 2 — NOT created by this command
```

### Source Code (repository root)

```text
rdam/
├── contracts.py               AggregateRequest gains source-artifact entry points;
│                              ProviderRequest gains its projection; AggregateAnalysis
│                              gains the preparation receipt
├── machine.py                 inventories once, projects per requirement; ALREADY runs
│                              providers concurrently — this feature audits that
├── composition.py             assembles the seven providers; keeps concrete technique
│                              imports separate from generic orchestration
├── _execution.py              EXISTS — ExecutionPolicy(max_workers, cache_directory)
├── _result_cache.py           EXISTS — single-flighted, validated on load; gains the
│                              projection identity in its key
├── _provider_provenance.py    EXISTS — shared provider provenance and failure helpers
├── _llm.py                    EXISTS — transport retries, backoff, deadline, multi-provider
├── ingest/                    ← MOVED from rdam/rst/ingest (25 modules)
│   ├── contracts/
│   │   ├── source.py          + SpeakerIdentity on turn items
│   │   ├── preparation.py     + ContentRequirement, SourceProjection;
│   │   │                      + table-linearisation transformation parameters;
│   │   │                      PreparedRstDocument → PreparedDocument (no alias),
│   │   │                      ParserCapacity → AnalysisCapacity (no alias)
│   │   └── analysis, capabilities, failure, inference, legacy
│   ├── policy.py              per-requirement projection, replacing one global partition
│   ├── projection.py          ← NEW: deterministic (inventory, requirement) → projection
│   ├── speakers.py            ← NEW: resolution and coverage accounting
│   ├── cache.py  service.py  prepare.py  subdivision.py  recombination.py
│   ├── validation.py  serialization.py  capabilities.py  enrichment.py
│   └── parser_result.py  public_surface.py  _harvest.py
├── rst/
│   ├── provider.py            declares the RST requirement (today's policy, exactly)
│   ├── parser.py  cli.py      import sites updated
│   └── doclang/  markdown/    private decoding support, import sites updated
├── pdtb/  sdrt/  toulmin/  walton/   declare requirements; consume projections
│                              sdrt declares requires_speaker_identity
└── dung/  ibis/               unchanged — structured input only, no projection

tests/
├── ingest/                    projection determinism, sharing, transformation records
├── machine/                   inventory-once, per-requirement planning, concurrency equivalence
├── llm/                       cache hit, one miss per identity element, corrupt entry
├── {rst,pdtb,sdrt,toulmin,walton,dung,ibis}/   per-provider re-verification
├── fixtures/                  + a tabular-evidence document, + a multi-party transcript
└── stress/                    ← R8: the real parser concurrent, CPU and MPS

tools/production_boundary/     ownership authority; gate must stay valid: true
```

**Structure Decision**: the single-package layout is fixed by the 2026-09-02 owner ruling
and is not revisited. The structural change is that `ingest/` rises from `rdam/rst/` to
`rdam/`, making the dependency direction machine → ingest and provider → ingest, so the
machine can no longer reach into a technique sub-package. No `rdam/rst/ingest.py` shim
remains. `projection.py`, `speakers.py`, and
`composition.py` are the new implementation modules; everything else is a move, a rename
without an alias, or an addition to an existing contract. The owner approved separating
assembly from orchestration on 2026-09-04. The concrete composition imports providers;
generic orchestration does not. `rdam.production_machine` directly exports the composition
factory; `rdam.machine` contains no forwarding factory. `AnalysisPlan.capacity` uses the
same name in Python and JSON. Historical baseline evidence is not rewritten; the comparison
reports this approved rename separately and still rejects any changed capacity value.

## Phase 2 outline (for `/speckit-tasks`, not created here)

Ordered so each step is independently verifiable and the tree stays green throughout.

1. **Relocate.** Move the package; remove the re-export; update production, tool, script,
   and test imports. *Gate*: full suite green, boundary `valid: true`,
   `rst-baseline compare` zero analytical differences.
2. **Rename what lies about its scope.** `PreparedRstDocument` → `PreparedDocument`,
   `ParserCapacity` → `AnalysisCapacity`, no aliases; `capacity` in Python and JSON.
   *Gate*: repository callers pass, old names are absent, baseline still zero analytical differences.
3. **Requirement and projection contracts.** Add `ContentRequirement` and
   `SourceProjection`; make projection a pure function of `(inventory, requirement)`.
   *Gate*: identical requirements share one projection; every projection reconstructs its
   text exactly and carries contributing items and anchors.
4. **RST declares today's policy.** Its requirement reproduces `AUTHORED_PROSE_V1` exactly.
   *Gate*: baseline comparison zero analytical differences — this is the step that proves
   the projection model is behaviour-preserving before anything else moves onto it.
5. **Speaker identity.** Add the contract, resolution, and coverage accounting. *Gate*:
   every turn resolved or explicitly unresolved; zero invented speakers on a deliberately
   unattributable fixture.
6. **Table linearisation.** Add the transformation parameter kind; admit tables to the
   requirements that declare them. *Gate*: Toulmin grounds anchor to table cells; RST still
   does not admit tables; every admitted unit names its transformation.
7. **Entry points and inventory-once.** `for_source` / `for_bytes`; inventory once per
   aggregate; receipt on the aggregate. *Gate*: all six forms reachable; inventory count
   exactly one for technique counts one to seven.
8. **Migrate the six providers.** Each declares its requirement and consumes its
   projection. *Gate*: each provider's own suite green; native contracts unchanged.
9. **Per-requirement planning.** Plan against each requirement's capacity and unit.
   *Gate*: two providers with different capacity units each receive a valid plan.
10. **Cache.** Lift the analytical identity into a key; reuse the cache discipline. *Gate*:
    hit performs zero model requests; one miss demonstrated per identity element; corrupt
    entry re-analyses.
11. **Concurrency — audit what already ships.** Concurrency, per-provider locking, and a
    result cache are already implemented. This step measures rather than builds: run the
    parser-concurrency stress test on CPU and MPS, replace the blanket lock with declared
    parallel safety, close the lock-registry retention path, and state the
    bug-versus-typed-failure rule explicitly. *Gate*: identical semantic digests concurrent
    vs sequential; wall-clock materially below the serial sum; no provider serialised
    without a declaration.
12. **Alignment.** Demonstrate two techniques' findings reported over one source span.
    *Gate*: SC-015.
13. **Documentation.** README, CLAUDE.md, `.claude/rules/architecture.md`, and the 29
    referencing documents. *Gate*: `mdlint` clean.

Full gates before completion: `lint`, `typecheck`, `test`, `mdlint`,
`-e default production-boundary`, `ontology-validate`, plus `test-all` and `smoke` because
steps 1 and 11 touch the predictor stack.

**Re-measure before implementing.** Every count above is a dated measurement, and the tree
moved substantially while this plan was written — concurrency, a result cache, an execution
policy and a provenance helper all landed. Task T001 re-takes these numbers; nothing here is
carried forward on trust.
