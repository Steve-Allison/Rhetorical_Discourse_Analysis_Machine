# Feature Specification: World-Class Production Source Ingest

**Feature Branch**: `codex/spec-kit-adoption`

**Created**: 2026-08-25

**Status**: Draft

**Input**: User request to make ingest of real-world source materials used for RST analysis world-class and state of the art, explicitly excluding training content and training/evaluation preparation.

## Scope Authority

This feature governs only production source material submitted for immediate RST/eRST analysis. Its input boundary is the set of source forms currently accepted by the product: plain text, pre-segmented EDUs, Markdown, DoclingDocument JSON, and DocLang documents. When Docling material represents an original PDF, presentation, word-processing document, image, audio transcript, or other upstream source, the ingest must retain the available original-source and conversion provenance.

This feature does **not** acquire or prepare training corpora, create gold labels, generate training examples or candidates, train or select models, run research experiments, or redesign evaluation harnesses. It also does not perform the separately specified production-codeline split. Existing released model behavior and inference mathematics remain unchanged unless a later, explicit feature authorizes a model change.

The feature is complete only when real-world documents reach analysis with relevant authored discourse, operative document structure, exact source traceability, no silent loss or duplication, deterministic evidence, and measured local-machine performance.

## World-Class and State-of-the-Art Standard

For this small-volume local product, **world-class is the acceptance floor**. It means each source is handled with exceptional fidelity, relevance judgment, structural integrity, traceability, and downstream RST quality. It does not mean enterprise scale, concurrent throughput, distributed processing, service infrastructure, or automation for its own sake.

“State of the art” applies specifically to **production source preparation for RST/eRST analysis**, not to a claim that the unchanged parser model is the best available RST model. The ingest qualifies only when a concise, dated comparison with current published and normative practice finds no material unaddressed gap in source-contract compliance, authored-content selection, structure-aware long-document preparation, provenance, loss accounting, determinism, and production evaluation.

Correctness and analytical quality take precedence over speed. Promotion gates MUST be evaluated in this order: source validity, content relevance, complete coverage, reversible provenance, downstream RST quality, determinism, and only then efficiency. A later gate cannot compensate for failure of an earlier gate.

## User Scenarios & Testing

### User Story 1 - Analyse relevant authored discourse without manual cleaning (Priority: P1)

As a local RST user, I want to submit a supported real-world source and receive an analysis of its authored discourse without first deleting code, furniture, repeated notes, machine descriptions, raw markup, or other irrelevant material.

**Why this priority**: The quality of every downstream RST relation depends on what text is admitted to the discourse stream. Irrelevant or duplicated material can create relations that do not exist in the source.

**Independent Test**: Submit a conformance set containing prose, headings, lists, transcript turns, code, raw HTML, tables, slide notes, picture descriptions, furniture, formulas, and repeated blocks; prove that the default policy includes only the declared primary discourse and receipts every other item without losing its source identity.

**Acceptance Scenarios**:

1. **Given** a document containing authored prose and non-prose material, **When** it is analysed with the default policy, **Then** only eligible authored discourse enters the primary RST stream and every excluded item remains accounted for with its exclusion reason.
2. **Given** an exact block repeated within a source, **When** ingest prepares the document, **Then** the repetition is detected and the declared policy is applied without silently changing the source record.
3. **Given** a user who intentionally wants notes, picture descriptions, code, raw markup, or table content included, **When** a named policy explicitly permits that class, **Then** the receipt identifies the class, origin, transformation, and resulting analysis scope.
4. **Given** a supported conforming source, **When** the user requests analysis, **Then** no manual source cleaning or format-specific preprocessing is required.

---

### User Story 2 - Preserve exact source fidelity and provenance (Priority: P1)

As a user reviewing an RST result, I want every analysed EDU and relation to trace back to the exact source material that produced it so that I can verify the analysis rather than trusting an opaque flattened string.

**Why this priority**: An analysis without exact source identity, coordinates, and transformation evidence cannot support trustworthy review, comparison, caching, or downstream use.

**Independent Test**: Analyse representative sources in every supported form, serialize and reload the results, and prove complete model-input coverage, reversible source anchors, exact source identity, explicit synthetic separators, and zero unreceipted transformation.

**Acceptance Scenarios**:

1. **Given** an analysed EDU or relation, **When** its provenance is inspected, **Then** it identifies the source artifact, the originating source element or range, and the exact prepared-text range used by analysis.
2. **Given** content separated or normalized during preparation, **When** the preparation receipt is inspected, **Then** every synthetic separator and normalization is distinguishable from authored source text.
3. **Given** equal content under different source identities, **When** both sources are analysed, **Then** neither result inherits the other's filename, location, conversion provenance, or cache identity.
4. **Given** a persisted analysis, **When** it is reloaded, **Then** its source anchors, content policy, model identity, preparation evidence, and analysis meaning are unchanged.

---

### User Story 3 - Use document structure as analysis material (Priority: P1)

As a user analysing a structured or long document, I want headings, sections, pages, slides, groups, lists, and speaker turns to constrain preparation and analysis so that the result reflects the document rather than an arbitrary concatenation of blocks.

**Why this priority**: Structure is part of the authored discourse. Detecting it only after parsing cannot prevent implausible cross-boundary EDUs or relations and does not support complete long-document analysis.

**Independent Test**: Analyse multi-section, multi-slide, multi-page, and multi-speaker sources—including a source larger than the existing single-pass limit—and prove complete eligible-content coverage, structure-aligned local analysis, a coherent document-level result, and stable source anchors.

**Acceptance Scenarios**:

1. **Given** a source with meaningful structural boundaries, **When** it is analysed, **Then** those boundaries influence segmentation and discourse construction rather than appearing only as annotations on a pre-existing flat parse.
2. **Given** a long conforming source, **When** it exceeds the safe single-analysis size, **Then** all eligible content is analysed through structure-aware subdivision and returned as one coherent document result without silent truncation.
3. **Given** a transcript with multiple turns or a presentation with multiple slides, **When** analysis completes, **Then** local and cross-boundary relations remain distinguishable and traceable to their structural context.
4. **Given** a source with no usable structure, **When** analysis completes, **Then** a deterministic fallback policy covers the entire eligible source and the receipt identifies that fallback.

---

### User Story 4 - Prove ingest quality on real production sources (Priority: P1)

As the product owner, I want the candidate ingest compared with the current production path on a small, deeply verified set of representative real sources so that “world-class” and “state of the art” are evidence-backed release claims.

**Why this priority**: Source fidelity alone is insufficient if changed preparation makes the resulting RST analysis worse. A small excellence project needs deep evidence on every promotion source, not broad throughput statistics.

**Independent Test**: Freeze a compact production benchmark before candidate evaluation, run the current and candidate ingest with the same released model, score content selection, coverage, source anchors, structural-boundary behavior, EDU segmentation, and RST relations, then inspect every persisted result and receipt.

**Acceptance Scenarios**:

1. **Given** the frozen production benchmark, **When** baseline and candidate analyses run with the same released model, **Then** every source uses identical model identity and its preparation and RST differences are attributable to ingest.
2. **Given** a structured source whose current flat preparation causes boundary errors, **When** the candidate is evaluated, **Then** structural-boundary errors are materially reduced without a protected RST metric regression.
3. **Given** aggregate improvement with a per-format or per-source regression, **When** promotion is assessed, **Then** the regression remains visible and blocks promotion unless the specification already declares that outcome acceptable.
4. **Given** a promotion candidate, **When** final acceptance runs, **Then** every benchmark source, prepared document, receipt, and analysis result is inspected rather than inferred from aggregate test status.

---

### User Story 5 - Retain complex non-prose material without contaminating RST (Priority: P2)

As a user submitting documents with tables, nested tables, code, formulas, images, or raw HTML, I want those elements preserved faithfully even when they are not suitable for primary RST analysis.

**Why this priority**: Fidelity does not require treating every source element as prose. Destructive flattening loses meaning, while silent inclusion degrades discourse quality.

**Independent Test**: Submit current-valid nested tables, rich tables, code, formulas, raw HTML containing scripts/styles/navigation, and picture descriptions; prove structural retention, safe eligibility decisions, explicit analysis status, and no unintended primary-discourse text.

**Acceptance Scenarios**:

1. **Given** a table or nested table, **When** it is ingested under the default policy, **Then** its row, column, header, cell, nesting, and source ancestry remain available without being converted into primary prose.
2. **Given** raw HTML, **When** it is ingested, **Then** scripts, styles, navigation, and markup artifacts cannot silently become authored discourse.
3. **Given** machine-authored picture descriptions or OCR-derived content, **When** they are retained, **Then** their origin and confidence status remain distinct from human-authored prose.
4. **Given** an unsupported analysis treatment for a valid source element, **When** ingest encounters it, **Then** the element is preserved and marked as not analysed rather than rejected or destructively flattened.

---

### User Story 6 - Receive deterministic, actionable production evidence (Priority: P2)

As the local operator, I want repeated analyses to be deterministic, cache-safe, efficient, and explicit about failures so that I can trust results and diagnose problems without inspecting internal files.

**Why this priority**: Production ingest must be dependable on one local machine. Fast but stale, partial, or unexplained results are not world-class.

**Independent Test**: Repeat analyses with unchanged and deliberately changed sources, policies, schemas, validators, and models; inject malformed and oversized inputs; then verify deterministic outputs, correct cache behavior, complete receipts, bounded resource use, and fail-closed errors.

**Acceptance Scenarios**:

1. **Given** identical source bytes, source identity, policy, format contract, and released model, **When** analysis is repeated, **Then** the persisted result and preparation receipt are semantically identical.
2. **Given** a change to any input that can alter analytical meaning, **When** analysis is requested, **Then** a prior cached analysis is not returned as current.
3. **Given** malformed, unsafe, unsupported, or incomplete source material, **When** ingest cannot produce a trustworthy complete result, **Then** it fails with an actionable reason and does not return an apparently successful partial analysis.
4. **Given** a valid cache entry, **When** it is used, **Then** current source validation and analytical identity requirements still hold.

### Edge Cases

- Empty, whitespace-only, and one-EDU inputs.
- Unicode normalization, combining characters, bidirectional text, unusual punctuation, non-breaking spaces, and mixed line endings.
- Sources with duplicate identifiers, equal bytes under different names, renamed sources, and changed conversion provenance.
- Extremely deep heading/list/table nesting and valid recursive DocLang tables.
- Documents consisting mainly of OCR text, tables, notes, code, formulas, furniture, or picture descriptions.
- Identical repeated blocks, near-duplicate blocks, and intentionally repeated authored refrains.
- Missing, overlapping, discontinuous, contradictory, or out-of-range source coordinates.
- Sources with a valid structure but no eligible primary prose, and sources with eligible prose but no usable structure.
- Very long paragraphs, slides, cells, turns, and documents whose individual structural units exceed a safe analysis window.
- Corrupt cache entries, results created under an older analytical contract, and changes to source validators or inclusion policy.
- Current-valid upstream constructs not represented in the local fixture collection.
- Partial upstream conversion evidence, including missing original-source identity or uncertain machine-generated content origin.

## Requirements

### Functional Requirements

- **FR-001**: The production ingest feature MUST accept plain text, pre-segmented EDUs, Markdown, DoclingDocument JSON, and DocLang documents as distinct supported source forms.
- **FR-002**: The feature MUST begin at the production analysis boundary and MUST NOT acquire or prepare training corpora, generate training labels/examples/candidates, train or select models, or execute research/evaluation workflows.
- **FR-003**: Each ingest request MUST establish an immutable source identity covering the supplied bytes or text, source name, source form, available original-source identity, conversion provenance, and upstream document-contract version.
- **FR-004**: Every structured source MUST be validated against the current accepted source contract before its content or any cached analysis is trusted.
- **FR-005**: Ingest MUST create a complete content inventory before analysis, classifying each source element by authored role and content class without discarding elements merely because they are not eligible for primary RST.
- **FR-006**: The default production policy MUST admit authored prose, headings, meaningful list text, and authored transcript turns to the primary discourse stream.
- **FR-007**: Code, formulas, raw markup artifacts, scripts, styles, navigation, furniture, background content, machine-authored picture descriptions, slide notes, and table structures MUST NOT enter primary discourse by default.
- **FR-008**: Any inclusion of a normally excluded content class MUST require an explicit named policy and MUST remain distinguishable in both the prepared material and receipt.
- **FR-009**: Every included, excluded, deduplicated, retained-as-side-channel, or transformed source element MUST have a recorded disposition and reason.
- **FR-010**: Exact duplicate detection MUST report repeated blocks before analysis; deduplication MUST be policy-controlled, reversible in evidence, and MUST NOT silently erase intentional authored repetition.
- **FR-011**: HTML-derived material MUST be processed as structured content; executable, styling, navigation, and markup artifacts MUST NOT be converted into prose through generic tag removal.
- **FR-012**: Tables, including current-valid recursive/nested tables, MUST retain their structural hierarchy and source ancestry. Default ingest MUST NOT imply prose semantics by concatenating cells without an explicit validated table-analysis policy.
- **FR-013**: Valid source elements that cannot be analysed under the selected policy MUST be preserved with an explicit analysis status rather than rejected or destructively flattened.
- **FR-014**: Preparation MUST retain meaningful document boundaries—including available sections, headings, pages, slides, groups, lists, tables, and speaker turns—before analysis begins.
- **FR-015**: Meaningful source boundaries MUST influence segmentation or discourse construction; they MUST NOT be used solely as post-analysis overlap labels.
- **FR-016**: Long sources MUST be processed through deterministic, structure-aware subdivision that covers all eligible content and produces one coherent document-level result.
- **FR-017**: No eligible source character, source element, structural unit, or prepared-text region may be silently omitted, duplicated, or left beyond the analysable range.
- **FR-018**: When a structural unit itself exceeds the safe analysis range, ingest MUST subdivide it using a deterministic fallback and record the original boundary, derived subdivisions, overlaps, and coverage.
- **FR-019**: Every prepared text range MUST map either to exact source content or to an explicitly identified synthetic separator or normalization.
- **FR-020**: Every analysed EDU and relation MUST retain reversible anchors to the prepared material and to the originating source elements or coordinates available in that source form.
- **FR-021**: Format-specific provenance MUST survive projection into the shared analysis result and persistence/reload without fabricated source text, positions, or structural memberships.
- **FR-022**: The user MUST receive a preparation receipt containing source identity, source-contract identity, selected policy, model-release identity, content-class counts, every disposition, transformation counts, duplicate findings, structural/subdivision evidence, coverage totals, cache identity, timing, and all warnings or failures.
- **FR-023**: Receipt totals MUST reconcile: the complete source inventory equals the sum of included, excluded, side-channel, transformed, and rejected dispositions, with transformations linked to their source elements.
- **FR-024**: A successful result MUST prove complete eligible-content coverage and zero unreported truncation. If that proof cannot be produced, ingest MUST fail rather than return an apparently complete analysis.
- **FR-025**: Analysis and receipt identity MUST change whenever source bytes/identity, upstream source contract, validation semantics, selected policy, preparation behavior, model release, or result contract can change analytical meaning.
- **FR-026**: Cache lookup MUST NOT bypass current source validation, and corrupt, stale, incompatible, or identity-mismatched cache entries MUST never be returned as successful analyses.
- **FR-027**: Equal analytical inputs MUST produce semantically identical prepared material, receipts, and results regardless of prior cache state.
- **FR-028**: Malformed, unsafe, unsupported, internally contradictory, or incomplete source material MUST produce a precise actionable failure identifying the affected source element and violated expectation.
- **FR-029**: Partial success MUST be disabled by default. If a future named policy permits partial analysis, every omission and its effect on completeness MUST be prominent in the result and receipt.
- **FR-030**: Current upstream Docling and DocLang normative behavior MUST be verified at implementation time; package pins, locks, local fixtures, and prior reports MUST NOT be treated as proof of current source-contract compliance.
- **FR-031**: Production ingest conformance MUST be demonstrated with unmodified normative specimens plus representative real-world sources covering text, Markdown, rich/nested structured documents, long documents, OCR-heavy documents, presentations with repeated notes, and multi-speaker transcripts.
- **FR-032**: The feature MUST preserve existing released parser mathematics and MUST assess improvements using the same released model identity unless an independently approved model feature changes it.
- **FR-033**: Production source ingest MUST remain usable on one local machine without requiring training corpora, training tools, research artifacts, network services, or multi-user infrastructure.
- **FR-034**: This feature MUST NOT move packages, split environments, or restructure the production and development codelines; those changes belong exclusively to the separate codeline-separation feature.
- **FR-035**: Before implementation planning closes, the feature MUST record a concise, dated comparison against current normative and published practice for source-contract compliance, content relevance, structure-aware long-document preparation, source provenance, loss accounting, determinism, and production RST evaluation.
- **FR-036**: Promotion MUST use one compact, immutable Production Ingest Gold Set containing representative real-world sources from every supported source form and every material risk class named in this specification.
- **FR-037**: The Gold Set MUST contain at least 20 deeply verified sources, including at least two examples each of long structured prose, presentations with notes, OCR-heavy material, multi-speaker discourse, code/raw-markup-rich Markdown, rich or nested tables, repeated content, and Unicode/coordinate stress. One source may satisfy multiple risk classes.
- **FR-038**: Every Gold Set source MUST have immutable source identity plus human-verified expectations for source inventory, content-class disposition, meaningful structure, eligible-content coverage, duplicate handling, and source anchors. At least 12 representative sources MUST additionally have adjudicated EDU boundaries and primary RST structure sufficient to score downstream analysis quality.
- **FR-039**: Gold Set expectations MUST be frozen before candidate evaluation. Promotion evidence MUST distinguish untouched real sources, unmodified normative specimens, and synthetic edge cases; synthetic or implementation-shaped mocks MUST NOT substitute for real or normative promotion evidence.
- **FR-040**: Candidate evaluation MUST compare the current production ingest and candidate ingest using the identical released model, source set, scoring rules, and machine. This feature MUST NOT retrain, tune, or select a model to improve ingest results.
- **FR-041**: Promotion MUST report results for every source and source form as well as aggregates. An aggregate gain MUST NOT hide a regression in content selection, coverage, anchoring, structural-boundary behavior, EDU segmentation, or RST quality.
- **FR-042**: The candidate MUST NOT contain per-document exceptions, benchmark-specific allowlists, manual source cleanup, destructive upstream flattening, reduced difficult-fixture coverage, validation bypasses, silent fallbacks, or cache reuse that can make promotion evidence easier to pass.
- **FR-043**: Promotion MUST fail immediately on any earlier quality gate before efficiency is considered. Performance targets MUST NOT justify content loss, weaker validation, reduced provenance, coarser structure, or lower downstream RST quality.
- **FR-044**: Final promotion MUST include direct inspection of every Gold Set prepared document, preparation receipt, and persisted RST result, with all anomalies resolved or explicitly recorded as failed gates.
- **FR-045**: SOTA status MUST be bounded and dated. The release evidence MUST state that it covers production source ingest for RST/eRST, name the practices and systems compared, identify the evidence date, and avoid claiming model-level SOTA unless separately proven.
- **FR-046**: Concurrency, multi-user operation, distributed execution, service uptime, queueing, horizontal scale, and mass-throughput optimization MUST remain outside this feature unless required to correct a measured single-machine quality defect.

### Key Entities

- **Source Artifact**: The immutable production input and its identity, source form, name, available original-source provenance, conversion provenance, and source-contract version.
- **Content Inventory Item**: One source element with its authored role, content class, source coordinates/identity, structural ancestry, origin, and eligibility evidence.
- **Preparation Policy**: A named, versioned selection of inclusion, exclusion, side-channel, duplicate, table, HTML, and partial-result rules.
- **Prepared RST Document**: The exact discourse material supplied for analysis, its meaningful hierarchy and boundaries, and complete mappings back to source inventory items.
- **Source Anchor**: A reversible relationship between prepared text or an analysis unit and its originating source element, coordinates, and structural context.
- **Side Channel**: Faithfully retained source material that is not part of primary RST discourse under the selected policy.
- **Preparation Receipt**: Reconciled evidence of source identity, policy, dispositions, transformations, coverage, structure, analytical identity, timing, cache status, warnings, and failures.
- **Production Analysis Result**: The persisted RST/eRST analysis linked to its prepared document, source anchors, preparation receipt, and released model identity.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Across the production conformance suite, 100% of source inventory items have exactly one reconciled disposition and zero items disappear without evidence.
- **SC-002**: Across all default-policy fixtures, 100% of expected authored-discourse elements enter primary RST and 100% of declared non-discourse elements remain outside it.
- **SC-003**: Every analysed EDU and relation in every supported source form maps to valid prepared-text and source anchors; round-trip inspection finds zero fabricated, out-of-range, or wrong-source coordinates.
- **SC-004**: Ten repeated uncached and cached runs of each conformance source produce semantically identical prepared documents, receipts, and analysis results.
- **SC-005**: Every tested change to source identity, source bytes, source-contract semantics, preparation policy, preparation behavior, model release, or result contract causes a cache miss or a separately valid analytical identity; zero stale results are accepted.
- **SC-006**: Current normative Docling and DocLang specimens accepted by their authorities ingest without destructive upstream flattening; unsupported analysis treatments preserve the valid element and report its status.
- **SC-007**: The promotion suite includes at least one source with 1,000,000 or more characters and proves 100% eligible-content coverage, zero silent truncation, stable anchors, and one coherent document result.
- **SC-008**: On the designated local reference machine, preparation excluding model inference completes within 2 seconds for 100,000-character conforming sources and within 15 seconds for the 1,000,000-character promotion source, with peak memory and timings recorded.
- **SC-009**: Malformed, unsafe, contradictory, stale-cache, and unsupported test cases produce zero apparently successful partial analyses and identify the failed source element or contract in every case.
- **SC-010**: Representative presentations, OCR-heavy documents, nested tables, raw HTML, code-rich Markdown, and multi-speaker transcripts require no manual cleaning before a trustworthy default-policy result or an explicit no-primary-discourse outcome is produced.
- **SC-011**: Source-to-analysis receipts can answer, for every successful result, which source and model were used, what entered analysis, what did not, what changed, whether anything was subdivided or deduplicated, and whether complete coverage was achieved.
- **SC-012**: Production ingest and its acceptance suite run without access to training corpora, training/evaluation commands, experiment caches, or network services.
- **SC-013**: The frozen Gold Set contains at least 20 sources, covers every supported source form and required risk class, and has 100% reconciled source identity and expected-outcome evidence; at least 12 sources carry adjudicated EDU and primary-RST gold.
- **SC-014**: On the Gold Set, the candidate achieves 100% precision and 100% recall for required primary-discourse inclusion/exclusion decisions, 100% eligible-content coverage, and zero unreceipted duplication or loss.
- **SC-015**: With the identical released model, candidate EDU, Span, Nuclearity, Relation, and Full scores are no lower than the current production baseline for any supported source form, and the candidate introduces zero new source-anchor or structural-boundary violations.
- **SC-016**: On Gold Set sources with adjudicated errors caused by flat preparation, the candidate reduces structural-boundary violations by at least 50% while still passing the protected-metric no-regression gate.
- **SC-017**: Every Gold Set source has an individually inspectable baseline/candidate comparison; zero per-source regressions are hidden by aggregate reporting, and every persisted candidate result and receipt is directly inspected.
- **SC-018**: A dated current-practice comparison identifies zero material production-ingest capability gaps left unaddressed or unmeasured by the specification. Any unresolved gap blocks the SOTA claim and promotion.
- **SC-019**: Promotion evidence contains zero modified normative specimens, manual source-cleaning steps, benchmark-specific behavior, silent fallbacks, validation bypasses, or quality-gate waivers.
- **SC-020**: The complete production promotion run executes locally as a bounded batch over the small Gold Set; no enterprise, distributed, concurrency, or mass-throughput infrastructure is introduced.

## Assumptions

- The product is for one local user on one machine; no multi-user, service-availability, or enterprise infrastructure requirements apply.
- The production input boundary begins with plain text, pre-segmented EDUs, Markdown, DoclingDocument JSON, or DocLang. Conversion of original binary/media files into Docling or DocLang is upstream, but available original-source and conversion provenance remains in scope.
- Authored prose is the default RST subject. Non-prose and machine-generated material remains valuable source evidence but requires an explicit policy before joining primary discourse.
- The existing released parser variants remain available and retain their trained architecture and inference mathematics.
- Exact source coordinates vary by source form; every source must retain the strongest native anchor it supplies, plus prepared-text coordinates.
- A document may legitimately contain no primary RST discourse after policy application; that is an explicit, successful preparation outcome without a fabricated parse.
- The production conformance corpus may contain redistributable fixtures and locally held real-world sources; private or licensed source content does not need to be committed to the repository, but its evidence must be reproducible locally.
- Codeline/package/environment separation is a separate feature and may be implemented before this feature; this specification remains authoritative for production ingest behavior regardless of physical package location.
- A small deeply verified Gold Set is more valuable for this product than a large shallow benchmark; breadth is required only where it covers a distinct source form or material failure mode.
- Human verification may be performed by the solo project owner using a documented rubric and a deliberate second-pass review; a team annotation workflow is not required.
- Existing production outputs provide the ingest baseline. They are comparison evidence, not authority for what the improved behavior should be.
