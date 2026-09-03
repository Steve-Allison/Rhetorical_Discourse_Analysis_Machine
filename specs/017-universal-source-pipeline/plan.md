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

Around that: ingest moves to `rdam.ingest`, the machine accepts files and bytes so all six
source forms become reachable, results are cacheable on their full analytical identity, and
independent providers run concurrently.

The approach is conservative where it touches working code. Ingest is **moved and
re-exported**, not rewritten. RST's requirement reproduces today's policy exactly, so the
classified baseline comparison can hold at zero analytical differences. Concurrency is
threads around the unchanged synchronous `Provider` protocol, so no provider is rewritten
to gain it.

## Technical Context

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
the RST baseline comparison; persisted contract identifiers unchanged; nothing enters a
projection without a recorded derivation; no invented speakers; no checker suppressions;
in-process only.

**Scale/Scope**: relocation of 25 modules / 10,477 lines with 109 code and 29 document
references; new requirement and projection contracts; a speaker contract; one new
transformation parameter kind; changes to `rdam/contracts.py`, `rdam/machine.py`,
`rdam/_llm.py`, and six of the seven providers. Current baseline 1348 tests passing with all
seven techniques available.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Pre-design | Post-design |
|---|---|---|---|
| **I. Evidence Before Claims** | Claims grounded in evidence inspected now; sample scope retained; unverified hypotheses marked and dated | **PASS** — every Context row verified on 2026-09-03 by reading `contracts/source.py` and `contracts/preparation.py` in full, not by grep | **PASS** — R8 (parser concurrency on MPS) is carried as an open risk settled by experiment, not asserted |
| **II. One Production Quality Bar** | Modern Python 3.14, accurate types, no suppressions, no weakened tests; trained architecture and inference maths untouched | **PASS** — SC-017 forbids suppressions; FR-005 forbids analytical change | **PASS** — the relocation moves modules without touching inference maths; the baseline comparison enforces it |
| **III. Solo-Local Simplicity** | One person one machine; no multi-user, distributed, or hypothetical configurability; no silent scope reduction | **PASS** — FR-039 forbids distributed execution and queues | **PASS** — threads in one process; requirements are declared by providers from their formalism, not exposed as caller knobs, so no configurability is invented |
| **IV. Honest Verification** | Claims cite checks actually run; doubles only for genuinely external systems; verification proportional and dependency-aware | **PASS** — every SC names a runnable check | **PASS** — the model is the only mocked boundary; predictor-stack changes trigger `test-all` and `smoke` per the commands rule |
| **V. Canonical Contracts** | One canonical authority per governed fact; public contracts explicit and tested; upstream specs verified before format-native work | **PASS** — FR-001 gives ingest one owner; FR-026 keeps the capability report authoritative | **PASS** — re-export rather than duplicate; no second source-form list; renames keep aliases so no competing name appears |

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
├── spec.md              # FR-001..FR-039, SC-001..SC-017
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
├── machine.py                 inventories once, projects per requirement, runs providers
│                              concurrently
├── _llm.py                    cache lookup and store at the model boundary
├── ingest/                    ← MOVED from rdam/rst/ingest (25 modules)
│   ├── contracts/
│   │   ├── source.py          + SpeakerIdentity on turn items
│   │   ├── preparation.py     + ContentRequirement, SourceProjection;
│   │   │                      + table-linearisation transformation parameters;
│   │   │                      PreparedRstDocument → PreparedDocument (alias kept),
│   │   │                      ParserCapacity → AnalysisCapacity (alias kept)
│   │   └── analysis, capabilities, failure, inference, legacy
│   ├── policy.py              per-requirement projection, replacing one global partition
│   ├── projection.py          ← NEW: deterministic (inventory, requirement) → projection
│   ├── speakers.py            ← NEW: resolution and coverage accounting
│   ├── cache.py  service.py  prepare.py  subdivision.py  recombination.py
│   ├── validation.py  serialization.py  capabilities.py  enrichment.py
│   └── parser_result.py  public_surface.py  _harvest.py
├── rst/
│   ├── ingest.py              ← NEW re-export preserving the documented RST surface
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
machine can no longer reach into a technique sub-package. `rdam/rst/ingest.py` exists solely
to preserve the documented RST public surface. `projection.py` and `speakers.py` are the
only genuinely new modules; everything else is a move, a rename with an alias, or an
addition to an existing contract.

## Phase 2 outline (for `/speckit-tasks`, not created here)

Ordered so each step is independently verifiable and the tree stays green throughout.

1. **Relocate.** Move the package; add the re-export; update the five production import
   sites and the test imports. *Gate*: full suite green, boundary `valid: true`,
   `rst-baseline compare` zero analytical differences.
2. **Rename what lies about its scope.** `PreparedRstDocument` → `PreparedDocument`,
   `ParserCapacity` → `AnalysisCapacity`, aliases retained. *Gate*: no consumer breaks;
   baseline still zero.
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
11. **Concurrency — measure first.** Add the R8 stress test; enable concurrency; serialise
    the RST provider if and only if the measurement says to. *Gate*: identical semantic
    digests concurrent vs sequential; wall-clock materially below the serial sum.
12. **Alignment.** Demonstrate two techniques' findings reported over one source span.
    *Gate*: SC-015.
13. **Documentation.** README, CLAUDE.md, `.claude/rules/architecture.md`, and the 29
    referencing documents. *Gate*: `mdlint` clean.

Full gates before completion: `lint`, `typecheck`, `test`, `mdlint`,
`-e default production-boundary`, `ontology-validate`, plus `test-all` and `smoke` because
steps 1 and 11 touch the predictor stack.
