# Research: Universal Source Pipeline

**Feature**: 017 | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

Every finding was established by reading the contracts in full and inspecting the working
tree on 2026-09-03. Where a question could not be settled by reading, it is carried as an
open risk with the experiment that settles it — not as a guess.

## R1 — What does the existing ingest actually model?

**Finding**: far more than a prose extractor, and the design must build on it rather than
around it. Established by reading `contracts/source.py` and `contracts/preparation.py` in
full.

| Capability | Evidence |
|---|---|
| 23 typed content classes | `ContentClass` — includes `TURN`, `TABLE`, `TABLE_CELL`, `CAPTION`, `FORMULA` |
| Nine discriminated representations | `TableRepresentation` with per-cell `row`/`column`/`row_span`/`column_span`/`header`/`linked_item_ids`; `ListRepresentation` with nesting; `CrossReferenceRepresentation` with `target_identity` + `relation`; `StructureRepresentation` with `child_ids` |
| Eight anchor kinds | text span, page, page box, **coordinate box with per-coordinate resolution**, JSON-pointer/XML-path, item, **table coordinate (row, column)**, archive member |
| Full document tree | `parent_id` / `child_ids` / `ItemRelationship` on every item |
| Exhaustive accounting | `ExactCoverage` over inventory, primary, retained, and mapping |
| Nothing discarded | `apply_policy` docstring: "one fully dispositioned inventory without discarding valid content" |
| Strong prepared-text invariant | `PreparedRstDocument` validates that segments are contiguous, correctly ordered, and reconstruct the text **exactly** |
| Segment traceability | `PreparedSegment` carries both `contributing_item_ids` and `source_anchors` |

**Decision**: the inventory is the right primitive and is not re-designed. It becomes the
machine's shared input rather than an RST intermediate.

## R2 — Then what is actually wrong?

**Finding**: exactly one projection of the inventory is ever produced, and it is tuned to
one technique.

1. `DEFAULT_PREPARATION_POLICY.primary_classes` is a single global tuple —
   `TITLE, HEADING, PARAGRAPH, LIST_ITEM, TURN`. `TABLE`, `TABLE_CELL`, `CAPTION`, `CODE`,
   `FORMULA` are `RETAINED`.
2. `PreparationPolicy` validates `primary_classes` and `retained_classes` are **disjoint**
   — so the policy is structurally a single partition, not a per-consumer view.
3. `AnalysisPlan.parser_capacity` is singular; `BoundaryPreference` terminates at `EDU`.
4. `DispositionDecision.TRANSFORMED` and `DispositionReason.NORMALIZED_FOR_ANALYSIS` are
   defined and never produced. `TransformationParameters` has four kinds — preserve, NFC,
   line endings, separator insertion — **none capable of projecting a table into text**.
5. No contract field anywhere carries a speaker.

**Consequence, stated concretely**: Toulmin's contract requires at least one ground. Its
projection excludes tables. A document whose evidence is tabular therefore reaches the
model with the claim present and the evidence absent, and the predictable result is a
confabulated ground — the one output this machine must never produce.

**Decision**: **one inventory, many declared projections.** Inventory once; each provider
declares a requirement; a projection is a deterministic function of `(inventory,
requirement)`. Identical requirements share one computed projection.

**Rationale**: it implements the owner ruling exactly — the shared source input is the
inventory — while letting each technique see what its formalism can analyse. It also
preserves every existing invariant, because a projection is the same shape of object the
current preparation already produces.

**Alternatives considered**: widen the single global primary set to admit tables —
rejected, it would corrupt RST, whose formalism is the rhetorical structure of prose, and
it would break SC-010. Per-technique preparation from source — rejected, it is the
divergence the owner ruled out and it would destroy cross-technique comparability. Leave
the projection alone and let providers post-filter — rejected, content excluded from the
prepared text is not recoverable downstream, and it would put policy in seven places.

## R3 — Speaker identity

**Finding**: there is **no first-class speaker anywhere** in the ingest contracts.
`ContentClass.TURN` and `AuthorshipRole.TRANSCRIBED` exist; `StructureKind.TURN` exists.
Attribution could only be smuggled through `SourceOrigin.producer`,
`TextRepresentation.attributes`, or `ContentInventoryItem.provider_attributes` — all
untyped, none required, none validated.

**Why it matters now, not later**: SDRT is built and reports `available`. Multi-party
dialogue is SDRT's native object; an SDRS whose units have no participants is a degraded
analysis presented as a complete one. Walton's `expert_opinion` scheme needs a `source`
premise role for the same reason.

**Decision**: add a validated `SpeakerIdentity` carried by turn items, with resolution
accounted in the receipt, and never invented. A provider declares whether it requires it;
where it cannot be supplied, the provider is told explicitly.

**Alternatives considered**: convention in `provider_attributes` — rejected, an unvalidated
string map is exactly how this kind of requirement rots. Infer speakers with the model —
rejected outright: fabricating participants is fabricating analysis.

## R4 — Table projection

**Finding**: the mechanism exists and is unused. `TransformationRecord` already maps
`input_item_ids → output_segment_ids` with a discriminated `parameters` union and a
semantic digest; `TableRepresentation` already carries full cell geometry; the
`TableCoordinateAnchor` already exists.

**Decision**: add one transformation parameter kind for table linearisation. The source
table is never rewritten; a projection of it becomes analysable text, recorded as a
transformation, with each produced segment anchored to the cells it came from.

**Rationale**: reuses three existing mechanisms rather than adding a fourth, and satisfies
FR-015 — nothing appears in a projection without a traceable derivation.

**Alternatives considered**: pass tables as raw markup — rejected, it puts format parsing
into every provider's prompt. Emit tables as a separate side input — rejected, it breaks
the contiguous-text invariant that makes anchoring work.

## R5 — Capacity and planning

**Finding**: `CapacityUnit` **already** offers `EDU_COUNT`, `TOKEN_COUNT`, and
`SEGMENT_COUNT`, and `ParserCapacity` already names its `estimation_algorithm` and
`estimation_version`. The limitation is not the unit — it is that `AnalysisPlan` carries
one capacity, and the type is named for the parser.

**Decision**: plan per requirement against that requirement's declared capacity. Rename the
capacity type to what it models, keeping the existing name as an alias (FR-006).

**Rationale**: the estimator identity is already in the contract, so a plan stays
reproducible and a change of estimator stays visible. Multiple plans from one inventory
cost nothing — planning is deterministic and cheap relative to inventory construction.

## R6 — Where preparation happens

**Decision**: `AggregateRequest` stays **declarative data** — it carries the source
artifact, never a prepared result. `Machine.analyse()` inventories once and projects per
requirement.

**Rationale**: capability reporting must stay side-effect-free, so building a request in
order to ask what is available must not do work. `AggregateRequest` is a frozen,
digest-bearing record; putting derived artifacts inside it would fold computation output
into the request's identity, conflating what was asked with what was computed.

## R7 — Concurrency mechanism

**Decision**: a bounded `ThreadPoolExecutor` inside `Machine.analyse()`.

**Rationale**: the `Provider` protocol is synchronous and `StructuredAnalyst.extract()`
calls Pydantic AI's `run_sync`, so threads let all seven providers stay exactly as they
are. Four of seven are network-bound, which is where the entire latency sits and where the
GIL is released. It matches the idiom the repository already uses to prove thread safety.
It is in-process, satisfying FR-039.

**Alternatives considered**: convert the protocol to async — rejected, it breaks all seven
providers and the public contract for a win threads already deliver. Multiprocessing —
rejected, it would require pickling model state and buys nothing for network-bound work.

**Ordering**: outcomes are keyed by technique and the aggregate validator already forbids
duplicates, so completion order cannot leak into the result. FR-034 makes that a checked
property rather than an argument.

## R8 — Is the RST parser safe to run concurrently?

**Status**: **partially established; one real gap remains.**

`tests/stress/test_concurrency_stress.py` already proves:

| Proven | How | Limit of the evidence |
|---|---|---|
| `ProductionIngestor.prepare()` is thread-safe | 30 sources, 16 workers, digests and segment counts verified | constructed with `parser=None` — proves **preparation**, not parsing |
| `NeuralSecondaryEdgeScorer` forward pass is thread-safe | 16 tasks, 8 workers, `torch.inference_mode()` | **CPU only**, `float32`, and it is the eRST scorer, not the tree parser |
| BLAKE3 / SHA-256 / RFC 8785 digests are thread-safe | 100 payloads at 32 workers | — |

**The gap**: nothing exercises `PredictorDMRST` or `PredictorUniRST` under concurrency, and
nothing exercises **MPS** concurrently at all. MPS is the default device here and the
parser holds loaded model state across calls.

**Decision**: treat it as unproven and settle it by experiment before relying on it (FR-035).
If it does not hold, the RST provider is serialised behind a lock while the four
network-bound providers still run concurrently — which retains nearly all the benefit,
since RST is the only local-compute provider.

**That preparation is already proven thread-safe is what makes the inventory-once,
project-per-requirement shape safe regardless of how this resolves.**

## R9 — Cache design

**Decision**: mirror `ProductionIngestCache` — content-addressed path, atomic write,
integrity validation on load, opt-in by cache directory, corrupt entry treated as a miss.

**Key composition**, the full analytical identity:

| Element | Why it must be in the key |
|---|---|
| source identity | a different document |
| **projection identity** | same document, different admitted content or segmentation — this is what makes the key correct under the projection model |
| provider id, contract version | the provider's own output contract changed |
| model identity | `gpt-5.6-sol` and `claude-opus-5` do not produce interchangeable analyses |
| instructions identity | prompts are generated from the formalism; a scheme-table change changes the analysis |

The Toulmin and Walton providers already emit an `instructions_digest`, so that element
exists today and only needs lifting into the key.

**Alternatives considered**: key on the prompt alone — rejected, it collides across
providers sending similar text and misses the contract version. A time-to-live — rejected,
the key is content-addressed so a stale hit is impossible by construction; a TTL would be a
knob with no failure mode behind it.

## R10 — Relocation mechanics

**Decision**: move the directory, then re-export. `rdam/rst/ingest/` → `rdam/ingest/`, with
`rdam/rst/ingest` re-exporting the public surface unchanged.

**Scale**: 25 modules, 10,477 lines; 109 code files and 29 documents reference
`rst.ingest`. Within production the importers are five files: `rdam/rst/cli.py`,
`rdam/rst/parser.py`, `rdam/rst/provider.py`, `rdam/rst/doclang/__init__.py`,
`rdam/rst/markdown/__init__.py`.

**Safety net**: `pixi run rst-baseline compare` classifies every serialized field
difference as execution, package identity, package source identity, derived digest, or
analytical. Acceptable only at **zero analytical differences** — the bar the 6.0.0 rename
was held to.

**Constraint**: persisted identifiers do not move with the package —
`isanlp_rst.production` 2.0.0, the schema `$id`s, and the runtime contract names are
unchanged (FR-004). They name stored contracts, not module paths.

**Naming**: `PreparedRstDocument` and `ParserCapacity` model general concepts under
technique-specific names. They are renamed with aliases retained (FR-006), so no consumer
breaks and the contract stops lying about its own scope.

## Open risks carried into implementation

| Risk | Resolution |
|---|---|
| **R8** parser concurrency on MPS unproven | settle by stress test before enabling; serialise if it fails |
| Table linearisation fidelity for merged cells and headerless tables | fixture-driven; the transformation records exactly what it did, so a poor projection is visible rather than silent |
| Speaker resolution varies by source form | resolution coverage is reported per source; unresolved is a first-class state, never filled in |
| Six providers migrate from raw text | native contracts expected unaffected — only input changes; each re-verified against its own suite |
| 109 code references to `rst.ingest` | the re-export means most need no change; the boundary gate and baseline comparison catch what does |
