# Feature Specification: Universal Source Pipeline

**Feature Branch**: `017-universal-source-pipeline`

**Created**: 2026-09-03

**Status**: Draft

**Input**: Owner rulings 2026-09-02/03: "ingest and source content prep should be universal
and EVERYTHING gets the same source input"; "move it to `rdam.ingest`"; "write the 017
without a split — make sure it is truly world-class".

## Context

The machine runs seven techniques natively side by side. Its source preparation was built
for one of them. Verified against the working tree on 2026-09-03:

| Observation | Evidence |
|---|---|
| No machine-level ingest exists | `rdam/ingest` — no such directory |
| Ingest is owned by the RST sub-package | `rdam/rst/ingest/`, 25 modules, 10,477 lines |
| Only RST reaches it | of seven `provider.py` files, only `rdam/rst/provider.py` imports ingest; `sdrt`, `pdtb`, `toulmin`, `walton` read `request.text` directly |
| The machine cannot accept a file | `AggregateRequest` contains zero occurrences of `for_source` or `SourceArtifact` |
| Providers run one at a time | `rdam/machine.py:115` — `for technique in request.techniques:`; no concurrency primitives in the module |
| Model calls are never reused | `rdam/_llm.py` contains zero occurrences of `cache` |
| Reach of the change | 109 code files, 29 documents reference `rst.ingest` |

### What is already strong, and must be preserved

Reading the contracts in full, the inventory is not a prose extractor. It is a complete,
typed, anchored representation, and this feature builds on it rather than around it:

- **23 content classes** including `TURN`, `TABLE`, `TABLE_CELL`, `CAPTION`, `FORMULA`.
- **Nine discriminated representations** — `TableRepresentation` carries per-cell geometry
  (`row`, `column`, `row_span`, `column_span`, `header`, `linked_item_ids`);
  `ListRepresentation` carries nesting; `CrossReferenceRepresentation` carries
  `target_identity` and `relation`; `StructureRepresentation` carries the container tree.
- **Eight anchor kinds** — text span, page, page box, coordinate box with per-coordinate
  resolution, JSON-pointer / XML-path, item, **table coordinate (row, column)**, archive
  member.
- `apply_policy` returns "one fully dispositioned inventory **without discarding valid
  content**"; coverage is accounted exactly across inventory, primary, retained, and
  mapping.
- `PreparedSegment` carries `contributing_item_ids` **and** `source_anchors`, and the
  prepared document validates that segments are contiguous and reconstruct the prepared
  text exactly.

### What is RST-shaped, and is the actual defect

The inventory keeps everything. Exactly one projection of it is ever produced, and that
projection is tuned to one technique:

1. **One global admitted set.** `DEFAULT_PREPARATION_POLICY.primary_classes` is a single
   tuple — `TITLE, HEADING, PARAGRAPH, LIST_ITEM, TURN`. `TABLE`, `TABLE_CELL`, `CAPTION`,
   `CODE`, `FORMULA` are all `RETAINED`. Correct for RST. It means **Toulmin and Walton
   never see a table** — so an argument whose grounds are a table of costs or survey
   results reaches the model with its claim present and its evidence absent, against a
   contract that requires at least one ground. The predictable failure is a confabulated
   ground, which is the one thing this machine must never produce.
2. **No speaker identity.** `ContentClass.TURN` exists and `AuthorshipRole.TRANSCRIBED`
   exists, but no contract field carries *who spoke*. It can only be smuggled through
   `SourceOrigin.producer`, `TextRepresentation.attributes`, or `provider_attributes` —
   none required, none validated. **SDRT's native object is multi-party dialogue.** An
   SDRS over a meeting transcript with turns present and speakers absent is a degraded
   analysis presented as a real one.
3. **One capacity, named for the parser.** `AnalysisPlan.parser_capacity` is singular and
   `BoundaryPreference` terminates at `EDU`. `CapacityUnit` already offers `TOKEN_COUNT`
   and `SEGMENT_COUNT`, but a plan carries one capacity — so four model-backed providers
   with token windows cannot each be planned correctly.
4. **The transformation mechanism is unused.** `DispositionDecision.TRANSFORMED` and
   `DispositionReason.NORMALIZED_FOR_ANALYSIS` are defined and never produced;
   `TransformationParameters` has no kind capable of projecting a table into analysable
   text.

### The design this feature adopts

**One inventory, many declared projections.** The source is inventoried and dispositioned
exactly once. Each provider declares what it can analyse; a projection is a deterministic
function of `(inventory, requirement)`. Every technique receives the same source input —
the inventory — and the view it can actually analyse, anchored back to identical source
offsets. Two providers declaring identical requirements share one projection object.

That anchoring is the machine's unrealised payoff: seven analyses over one source, all
carrying anchors into the same inventory, and therefore comparable *on the source* without
ever being merged into a common formalism.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analyse a Real Document (Priority: P1)

I hand the machine a file I actually have — a Markdown report, a Docling JSON, a DocLang
archive — and every requested technique analyses it.

**Why this priority**: five of the six implemented source forms are unreachable through the
machine. Without this, the machine analyses only strings already pasted into memory.

**Independent Test**: analyse a Markdown file for two techniques; both return native
results carrying anchors into the same inventory.

**Acceptance Scenarios**:

1. **Given** a Markdown file, **When** an aggregate names it for RST and Toulmin, **Then**
   both return native results and the aggregate carries one preparation receipt.
2. **Given** the same file analysed twice, **When** the receipts are compared, **Then** they
   are identical — preparation is a pure function of source and policy.
3. **Given** a source form whose optional dependency is absent, **When** capabilities are
   reported, **Then** the ingest capability reports it unavailable and requesting it fails
   typed and staged, never partially.

---

### User Story 2 - Each Technique Sees What It Can Actually Analyse (Priority: P1)

Toulmin sees the table its grounds live in. RST does not, because a table is not rhetorical
prose. Neither decision is a preference — each follows from the technique's formalism.

**Why this priority**: equal first. Delivering the pipeline while every technique receives
the RST projection would ship confabulated Toulmin grounds and speaker-less SDRT, and each
would look like a working analysis. That is worse than the current gap, which at least
fails visibly.

**Independent Test**: analyse a document whose only quantitative evidence is in a table for
both RST and Toulmin; verify the table reaches Toulmin as analysable content anchored to
its cells, and does not reach RST.

**Acceptance Scenarios**:

1. **Given** a document whose argument's grounds are in a table, **When** Toulmin analyses
   it, **Then** the table's content is present in Toulmin's projection and each ground
   traces to a table-coordinate anchor.
2. **Given** the same document, **When** RST analyses it, **Then** the table is retained
   and not admitted to RST's projection, exactly as today.
3. **Given** two providers declaring identical requirements, **When** the aggregate is
   analysed, **Then** one projection is computed and shared, not two.
4. **Given** a projection admitting a table, **When** its segments are inspected, **Then**
   the linearisation is recorded as a transformation naming its input items and output
   segments, so nothing appears in a projection without a traceable derivation.
5. **Given** any projection, **When** its segments are concatenated, **Then** they
   reconstruct its prepared text exactly and every segment carries its contributing items
   and source anchors.

---

### User Story 3 - Dialogue Keeps Its Speakers (Priority: P2)

A meeting transcript analysed by SDRT knows who said what.

**Why this priority**: SDRT was built and reports `available`, so this is a live
correctness gap, not a future feature. Walton's expert-opinion scheme needs a `source`
premise role for the same reason.

**Independent Test**: analyse a multi-party transcript with SDRT; verify each discourse
unit resolves to a speaker, and that a source without recoverable speakers says so rather
than inventing them.

**Acceptance Scenarios**:

1. **Given** a transcript with speaker attribution, **When** it is inventoried, **Then**
   each turn carries a resolved speaker identity.
2. **Given** a provider that declares it requires speaker identity, **When** the source has
   turns whose speakers cannot be resolved, **Then** the receipt records the unresolved
   coverage and the provider is told, rather than silently receiving anonymous turns.
3. **Given** a source with no turns at all, **When** a speaker-requiring provider analyses
   it, **Then** the outcome is explicit about the absence rather than fabricating
   participants.

---

### User Story 4 - One Preparation, Not Seven (Priority: P2)

The cost and the meaning of preparing a source are paid once per request.

**Why this priority**: preparing a long document seven times risks seven subtly different
inventories, which would destroy cross-technique comparability.

**Independent Test**: instrument inventory construction; analyse seven techniques over one
source; verify it ran once.

**Acceptance Scenarios**:

1. **Given** an aggregate naming seven techniques, **When** it is analysed, **Then**
   inventory and disposition execute exactly once.
2. **Given** two techniques in one aggregate, **When** their results are inspected, **Then**
   their anchors refer to the same inventory items by identity.
3. **Given** a source requiring subdivision, **When** two providers declare different
   capacities, **Then** each is planned against its own capacity from the one inventory.

---

### User Story 5 - Do Not Pay Twice for the Same Question (Priority: P3)

Re-analysing an unchanged source with an unchanged configuration repeats no paid model
call.

**Why this priority**: four providers now call a commercial model on every `analyse()`.
This is the difference between the machine being usable daily and being rationed.

**Independent Test**: analyse twice with a cache configured; verify the second performs no
model request.

**Acceptance Scenarios**:

1. **Given** a completed analysis and a configured cache, **When** the identical request
   repeats, **Then** no model request is made and the result is semantically identical.
2. **Given** a cached analysis, **When** any element of the analytical identity changes,
   **Then** the cache does not answer.
3. **Given** no cache configured, **When** a source is analysed, **Then** nothing is
   written and behaviour is unchanged.

---

### User Story 6 - Independent Techniques Do Not Queue (Priority: P4)

Requesting several techniques takes about as long as the slowest, not the sum.

**Why this priority**: a latency refinement over work already isolated by contract. Real,
but last.

**Independent Test**: request four model-backed techniques; verify wall-clock is materially
below the serial sum with identical outcomes.

**Acceptance Scenarios**:

1. **Given** four model-backed techniques, **When** the aggregate is analysed, **Then**
   elapsed time is materially less than the sum of the four run individually.
2. **Given** one provider failing and another succeeding concurrently, **When** the
   aggregate is inspected, **Then** the success is unaffected and the failure is one
   explicit typed outcome.
3. **Given** the same request run concurrently and sequentially, **When** the aggregates are
   compared, **Then** their semantic digests are identical.

### Edge Cases

- A source form whose optional dependency is absent (`docling-core`, `doclang`).
- A source that inventories to no admissible content for one technique's requirement but
  does for another's — for example a page of nothing but tables.
- A table with merged cells, nested headers, or no header row.
- A turn whose speaker is present but unresolvable to a distinct participant, and a
  transcript where two speakers share a display name.
- A source large enough that one provider's capacity subdivides it and another's does not.
- A cache directory that is unwritable, full, or holds a corrupt or contract-stale entry.
- Two concurrent providers whose runtimes are not safe in parallel (the RST parser holds
  model state on MPS or CUDA).
- A provider raising a non-`ProviderError` bug while running concurrently.
- A structured-input technique (Dung, IBIS) in the same aggregate as text techniques.
- A cross-reference whose target is retained but not admitted to the requesting
  projection — the argument points at evidence the technique cannot see.

## Requirements *(mandatory)*

### Functional Requirements

#### Relocation and ownership

- **FR-001**: Canonical source ingest MUST become a machine-level authority at
  `rdam.ingest`, owned by the machine rather than by any technique.
- **FR-002**: `rdam.rst.ingest` MUST remain importable with the same public surface.
- **FR-003**: The dependency direction MUST be machine → ingest and provider → ingest. The
  machine layer MUST NOT import from any technique sub-package.
- **FR-004**: Persisted contract identifiers MUST NOT change: `isanlp_rst.production`
  2.0.0, the schema `$id`s, and the runtime contract names. Changing them is a separate
  owner ruling.
- **FR-005**: RST analytical behaviour MUST be preserved — the classified baseline
  comparison MUST report zero analytical differences.
- **FR-006**: Contracts named for one technique MUST be renamed to what they actually
  model, with the technique-named identifiers retained as aliases so no consumer breaks.

#### One inventory

- **FR-007**: An aggregate request MUST be constructible from a file path and from
  in-memory bytes, in addition to plain text.
- **FR-008**: Constructing a request MUST perform no preparation, load no model, and touch
  no network.
- **FR-009**: Source inventory and disposition MUST run exactly once per aggregate request,
  regardless of how many techniques are requested.
- **FR-010**: The inventory MUST remain complete — every source item classified,
  dispositioned, and anchored, with exact coverage accounting and no valid content
  discarded.
- **FR-011**: The aggregate MUST carry one preparation receipt covering the whole request.

#### Declared projections

- **FR-012**: Each provider MUST declare a content requirement stating the content classes
  it can analyse, how non-text representations are to be projected, its capacity unit and
  maximum, its boundary preferences, its normalization need, and whether it requires
  speaker identity.
- **FR-013**: A projection MUST be a deterministic function of the inventory and one
  requirement, identified by a digest of both. Identical requirements in one aggregate MUST
  share one computed projection.
- **FR-014**: Every projection MUST preserve the existing invariants: its segments
  reconstruct its prepared text exactly, and every segment carries its contributing item
  identities and its source anchors.
- **FR-015**: Content admitted to a projection by transforming a non-text representation
  MUST be recorded as a transformation naming its input items and output segments. Nothing
  may appear in a projection without a traceable derivation.
- **FR-016**: Table content admitted to a projection MUST retain cell-level traceability,
  so a result derived from a cell anchors to that cell's coordinate.
- **FR-017**: A provider MUST NOT receive content its requirement does not admit, and MUST
  NOT be denied content its requirement does admit.
- **FR-018**: Structured-input techniques (Dung, IBIS) MUST declare no projection and
  receive none; they analyse a supplied structure only.
- **FR-019**: Where a projection cannot supply something a requirement declares as
  required, that MUST be reported explicitly to the provider and recorded in the receipt.
  It MUST NOT be silently substituted, padded, or omitted.

#### Speaker identity

- **FR-020**: Turn content MUST carry a first-class speaker identity as a validated
  contract field, not as an untyped attribute.
- **FR-021**: Speaker resolution MUST be accounted in the receipt: how many turns resolved
  to a distinct participant, and how many did not.
- **FR-022**: A speaker identity MUST never be invented. An unresolvable speaker is
  recorded as unresolved.

#### Capacity and planning

- **FR-023**: Analysis planning MUST be per requirement, against that requirement's
  declared capacity and unit, rather than against a single parser capacity.
- **FR-024**: Capacity estimation MUST name its algorithm and version, so a plan is
  reproducible and a change of estimator is visible.
- **FR-025**: Subdivision MUST respect the requirement's boundary preferences, and
  recombination MUST remain lossless.

#### Format coverage

- **FR-026**: Every source form the ingest capability reports as available MUST be
  acceptable to the machine. That report MUST remain the single authority; no second list
  may exist.
- **FR-027**: A form whose optional dependency is absent MUST fail typed and staged, never
  partially and never by silent fallback.

#### Caching

- **FR-028**: Results MUST be cacheable on the complete analytical identity: source
  identity, projection identity, provider identity, provider contract version, and — for
  model-backed providers — model identity and instructions identity.
- **FR-029**: A cache MUST NOT answer when any element of that identity differs.
- **FR-030**: Caching MUST be opt-in, and MUST write nothing when not configured.
- **FR-031**: Cache writes MUST be atomic and integrity-checked; a corrupt or
  contract-stale entry MUST cause re-analysis, never an error and never a wrong answer.

#### Concurrency

- **FR-032**: Independent providers MUST be able to execute concurrently, in-process.
- **FR-033**: Concurrency MUST NOT change outcome semantics: one outcome per requested
  technique, no failure suppressing another's success, and no retrying.
- **FR-034**: Concurrent and sequential execution of one request MUST produce identical
  aggregate semantic digests.
- **FR-035**: A provider whose runtime is not safe in parallel MUST be identified by
  measurement and serialised, not run concurrently on assumption.
- **FR-036**: A non-`ProviderError` exception MUST still propagate as a bug rather than
  being relabelled as a provider failure.

#### Alignment and boundaries

- **FR-037**: Because every projection anchors into one inventory, results from different
  techniques over one source MUST be alignable on source anchors, without merging their
  formalisms.
- **FR-038**: The machine MUST NOT derive one technique's input from another technique's
  output. Cross-technique consumption stays caller-declared with recorded lineage.
- **FR-039**: The pipeline MUST remain single-process and local — no distributed execution,
  work queue, scheduler, or remote control plane.

### Key Entities

- **Content Inventory**: the complete typed anchored representation of one source, built
  once. Every item classified, dispositioned, and traceable. Unchanged in kind by this
  feature; it becomes the shared input rather than an RST intermediate.
- **Content Requirement**: what one provider declares it can analyse — admitted classes,
  representation projections, capacity, boundary preferences, normalization, and whether
  speaker identity is required. A property of the technique's formalism, not a preference.
- **Source Projection**: the deterministic view of one inventory through one requirement —
  prepared text, contiguous segments, structural boundaries, and an analysis plan.
  Identified by inventory identity plus requirement identity; shared by providers whose
  requirements are identical.
- **Speaker Identity**: who produced a turn — a validated field, resolved or explicitly
  unresolved, never invented.
- **Preparation Receipt**: every decision made — inventory coverage, per-class
  dispositions, transformations, speaker resolution coverage, and one entry per projection
  produced. Carried on the aggregate.
- **Analytical Identity**: the complete set of inputs determining a result, and therefore
  exactly what a cache key must cover.

## Success Criteria *(mandatory)*

- **SC-001**: Every source form the capability report declares available is analysable
  through the machine; today five of six are not.
- **SC-002**: Inventory and disposition execute exactly once per aggregate, for every
  technique count from one to seven.
- **SC-003**: Two providers with identical requirements in one aggregate share one computed
  projection.
- **SC-004**: A document whose argument's grounds are in a table yields Toulmin grounds that
  anchor to that table's cells, and an RST analysis that does not admit the table.
- **SC-005**: Every segment of every projection reconstructs its prepared text exactly and
  names its contributing items and anchors — verified across all six source forms.
- **SC-006**: Every unit of content admitted to a projection by transformation names the
  transformation that produced it; zero admitted content lacks a derivation.
- **SC-007**: For a multi-party transcript, every turn carries a resolved speaker or an
  explicit unresolved marker, and the receipt's speaker coverage accounts for all of them.
- **SC-008**: Zero invented speakers, verified by analysing a transcript with deliberately
  unattributable turns.
- **SC-009**: Two providers declaring different capacity units over one source each receive
  a plan valid for their own capacity.
- **SC-010**: The classified RST baseline comparison reports zero analytical differences.
- **SC-011**: A repeated identical analysis against a configured cache performs zero model
  requests and returns a semantically identical result.
- **SC-012**: Changing any single element of the analytical identity causes a miss,
  demonstrated once per element.
- **SC-013**: An aggregate over four model-backed techniques completes in materially less
  wall-clock time than the sum of the four run individually.
- **SC-014**: Concurrent and sequential execution of one request produce identical
  aggregate semantic digests.
- **SC-015**: Results from two techniques over one source can be aligned on source anchors,
  demonstrated by reporting both techniques' findings over one span.
- **SC-016**: All seven techniques still report `available`; the full suite passes with new
  tests covering every requirement above.
- **SC-017**: Zero checker suppressions introduced; lint, strict typing, markdown lint,
  ontology validation, and the production boundary gate all pass.

## Assumptions

- **"The same source input" means the same inventory.** Every technique is prepared from
  one inventory built once. What differs between techniques is which parts of it their
  formalism can analyse, which is a property of the technique rather than a configuration
  choice. This is the owner ruling implemented, not weakened.
- **Requirements are declared by providers, not configured by callers.** A technique's
  admissible content follows from its theory. Making it a caller knob would let a caller
  ask Toulmin to analyse navigation furniture.
- **The RST requirement reproduces today's policy exactly.** That is what makes SC-010
  achievable: RST's projection is the current `AUTHORED_PROSE_V1` primary set, unchanged.
- **Table linearisation is a transformation, not a rewrite.** It uses the existing
  `TRANSFORMED` disposition and transformation record, and adds one parameter kind. The
  source table is untouched; a projection of it becomes analysable text with cell anchors.
- **Speaker identity is recoverable only where the source carries it.** Docling and DocLang
  turn structures and transcript formats carry attribution; plain prose does not. Absence is
  reported, never filled in.
- **Caching is opt-in**, matching the existing ingest cache which takes a cache directory
  rather than defaulting one.
- **Concurrency is in-process** — threads around the existing synchronous provider
  protocol. The scale ruling forbids more.
- **The RST parser's parallel safety is unknown** and is established by measurement, not
  assumed. If unsafe it is serialised while network-bound providers still run concurrently.
- **Six providers were built against raw text** in features 013–016 and are migrated here.
  Their native result contracts are expected to be unaffected; only their input changes.
- **`rdam.rst.ingest` is retained indefinitely** as a re-export. Removing it is a separate
  owner ruling.
