---

description: "Dependency-ordered implementation tasks for world-class production source ingest"
---

# Tasks: World-Class Production Source Ingest

**Input**: Design documents from `specs/002-production-source-ingest/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. The specification makes contract, conformance, determinism, provenance, quality, and real-source promotion evidence part of acceptance. Test tasks precede the implementation they govern and must be observed failing for the intended causal reason before implementation begins.

**Organization**: Tasks are grouped by user story. Production runtime work is confined to `isanlp_rst/`; repository-only Gold Set, scoring, inspection, and release evidence remain under `tools/`, `tests/`, `offline_workbench/`, and `specs/002-production-source-ingest/evidence/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Logically parallelizable because it touches different files and has no dependency on another incomplete task in the same work packet.
- **[Story]**: User story from `spec.md`.
- Every task names the exact files it creates or changes and an observable completion condition.

## Phase 1: Setup and Frozen Authorities

**Purpose**: Create the minimal feature structure and freeze current external and project authorities before candidate behavior exists.

- [X] T001 Create the canonical package/test/tool directories and minimal package markers in `isanlp_rst/ingest/__init__.py`, `tests/production_ingest/__init__.py`, and `tools/production_ingest/__init__.py`, without exporting incomplete runtime behavior.
- [X] T002 Add focused Feature 002 Pixi commands for contract, conformance, determinism, performance, canonical-public-surface, clean-install, freeze, candidate, and assessment workflows in `pyproject.toml`, using existing locked dependencies unless a demonstrated requirement forces a lock change.
- [X] T003 [P] Record the implementation-start Docling PyPI/repository/schema/API evidence and exact local pin/lock comparison in `specs/002-production-source-ingest/evidence/docling-contract-baseline.json`, including raw fixture declarations and current loader acceptance results.
- [X] T004 [P] Record the implementation-start DocLang PyPI/repository/spec/toolkit/valid-fixture evidence and exact local pin/lock comparison in `specs/002-production-source-ingest/evidence/doclang-contract-baseline.json`, including `.dclg`, empty-namespace, nested-table, and `.dclx` contract facts.
- [X] T005 [P] Define the text-free evidence directory policy, protected-content exclusions, evidence schemas, and direct-inspection record format in `specs/002-production-source-ingest/evidence/README.md` and `specs/002-production-source-ingest/evidence/evidence-schema.json`.

**Checkpoint**: Current upstream facts and evidence-handling rules are frozen before implementation choices can influence them.

---

## Phase 2: Foundational Production Contracts and Pre-Candidate Freeze

**Purpose**: Establish the strict shared contracts, identities, released-model capability authority, and immutable baseline that block every user story.

**CRITICAL**: No source-format or service implementation begins until this phase and the baseline freeze are complete.

- [X] T006 [P] Write failing strict-model and invariant tests for every production entity and enumeration in `tests/production_ingest/test_contracts.py`, covering unknown-field rejection, immutability, absence semantics, ranges, source payload exclusivity, and empty-discourse status.
- [X] T007 Implement the complete strict Pydantic contract family and typed failure hierarchy in `isanlp_rst/ingest/contracts.py` so T006 passes without suppressions or fabricated defaults.
- [X] T008 [P] Write failing canonicalization and identity tests in `tests/production_ingest/test_identity.py`, proving source name/form/original identity/conversion provenance/upstream declaration, validator semantics, policy, preparation, model files, and result contract all affect semantic identity while execution observations do not.
- [X] T009 Implement RFC-8785-compatible canonical semantic serialization and digest composition in `isanlp_rst/ingest/identity.py` so T008 passes across key ordering, Unicode, numeric, absent, and changed-input cases.
- [X] T010 [P] Write failing released-model identity and parser-capacity tests in `tests/production_ingest/test_model_identity.py`, using real manifest/file digests and proving an injected parser without immutable identity cannot enable durable caching.
- [X] T011 Implement immutable released-model identity and actual limiting-unit capacity exposure in `isanlp_rst/model_loading/release.py`, `isanlp_rst/model_loading/parser_input.py`, and `isanlp_rst/parser.py` without changing inference mathematics.
- [X] T012 [P] Write failing source-constructor tests in `tests/production_ingest/test_source_artifact.py` for text, exact EDU arrays, strict UTF-8 bytes, one-read paths, unambiguous extensions, ambiguous JSON/XML/text rejection, and complete source identity.
- [X] T013 Implement `SourceArtifact.from_text()`, `from_edus()`, `from_bytes()`, and `from_path()` in `isanlp_rst/ingest/contracts.py`, with deterministic identification separated from current-contract validation.
- [X] T014 [P] Write failing semantic/result serialization and payload-integrity tests in `tests/production_ingest/test_result_serialization.py`, including persistence/reload, schema incompatibility, digest mismatch, and execution-receipt exclusion from semantic equality.
- [X] T015 Extend deterministic serialization in `isanlp_rst/contracts/serialization.py` and implement the `isanlp_rst_ingest` v1 envelope round trip in `isanlp_rst/ingest/contracts.py` so T014 passes.
- [X] T016 [P] Write failing diagnostic-failure tests in `tests/production_ingest/test_failures.py` for every stage/code family, completed-stage evidence, private-text-safe messages, no success envelope, and no reusable cache entry.
- [X] T017 Implement stable stage-specific production ingest errors and diagnostic evidence assembly in `isanlp_rst/ingest/contracts.py` and export only complete public contracts from `isanlp_rst/ingest/__init__.py`.
- [X] T018 [P] Implement and test repository-only Gold Set/freeze schemas in `tools/production_ingest/contracts.py` and `tests/production_ingest/test_gold_contracts.py`, with no import from `isanlp_rst` back into `tools` and no protected source text in repository evidence.
- [X] T019 Assemble and adjudicate the immutable 20-or-more-source manifest and expectations in `specs/002-production-source-ingest/evidence/gold-manifest.json` and the private `--gold-root`, covering every source form, at least two of each mandated risk class, and at least 12 EDU/RST-gold sources without committing protected content.
- [X] T020 Implement the pre-candidate freeze command in `tools/production_ingest/freeze.py` and `tools/production_ingest/__main__.py`, recording Git state, current wheel, released-model files, lock, source/expectation hashes, machine, scorer configuration, and current baseline outputs before candidate runtime files change.
- [X] T021 Execute the freeze against the current production path and persist the text-free immutable authority record in `specs/002-production-source-ingest/evidence/baseline-freeze.json`; verify every manifest item resolves and abort implementation if any source, gold expectation, model, or baseline result is incomplete.

**Checkpoint**: Shared contracts and baseline evidence are immutable; user-story implementation may begin.

---

## Phase 3: User Story 1 — Analyse Relevant Authored Discourse Without Manual Cleaning (Priority: P1) MVP

**Goal**: Every supported source is completely inventoried before one named policy admits only relevant authored discourse and receipts everything else.

**Independent Test**: Submit the mixed-content conformance set from the specification and prove 100% expected primary inclusion, 100% expected exclusion, exactly one disposition per item, duplicate reporting, no manual cleanup, and an explicit empty-primary result where appropriate.

### Tests for User Story 1

- [X] T022 [P] [US1] Write failing default/named-policy and duplicate tests in `tests/production_ingest/test_policy.py`, covering all included/excluded classes, intentional repetition retention, provenance-backed reversible deduplication, and prohibition of mutable per-document exceptions.
- [X] T023 [P] [US1] Write failing plain-text and presegmented-EDU inventory/preparation tests in `tests/production_ingest/test_plain_ingest.py`, covering exact characters, paragraph structure, indivisible supplied EDU boundaries, synthetic separators, empty inputs, and no fabricated discourse.
- [X] T024 [P] [US1] Write failing complete Markdown inventory/relevance tests in `tests/production_ingest/test_markdown_ingest.py` using `tests/fixtures/markdown/`, covering headings, prose, lists, code, tables, raw HTML, repeated content, and source spans.
- [X] T025 [P] [US1] Write failing complete Docling inventory/relevance tests in `tests/production_ingest/test_docling_ingest.py` using all fixtures under `tests/fixtures/docling/`, covering every layer, group, top-level collection, notes, picture descriptions, tables, captions, and unresolved references.
- [X] T026 [P] [US1] Write failing complete DocLang XML inventory/relevance tests in `tests/production_ingest/test_doclang_ingest.py` using the full normative fixture manifest, covering full validation, accepted empty namespace, head metadata, layers, semantic/structural items, and explicit unsupported status.

### Implementation for User Story 1

- [X] T027 [US1] Implement immutable named policies, `AUTHORED_PROSE_V1`, complete content-class rules, and exact duplicate findings/actions in `isanlp_rst/ingest/policy.py` so T022 passes.
- [X] T028 [US1] Implement plain-text and presegmented-EDU complete inventory and canonical preparation dispatch in `isanlp_rst/ingest/prepare.py` so T023 passes without changing supplied EDU boundaries.
- [X] T029 [US1] Implement complete Markdown token/source-span inventory in `isanlp_rst/markdown/loader.py` and the private Markdown adapter in `isanlp_rst/ingest/prepare.py`, leaving relevance decisions to the canonical policy.
- [X] T030 [US1] Implement raw Docling declaration capture, current loader validation, all-layer/group/picture traversal, and top-level reconciliation directly in the private Docling adapter in `isanlp_rst/ingest/prepare.py`.
- [X] T031 [US1] Implement current full-validation and complete recursive DocLang XML/archive inventory in `isanlp_rst/doclang/loader.py`, `isanlp_rst/doclang/text_walker.py`, and the private DocLang adapter in `isanlp_rst/ingest/prepare.py`.
- [X] T032 [US1] Implement canonical inventory reconciliation, policy application, duplicate reporting, side-channel retention, disposition totals, and empty-primary handling in `isanlp_rst/ingest/prepare.py`, failing on every gap, duplicate identity, or contradictory disposition.
- [X] T033 [US1] Implement `ProductionIngestor.prepare()` orchestration in `isanlp_rst/ingest/service.py` and public exports in `isanlp_rst/ingest/__init__.py`, ensuring all five forms use the same validation-inventory-policy-preparation path.
- [X] T034 [US1] Delete the obsolete `parse_markdown`, `parse_docling`, and `parse_doclang` entry points, result envelopes, format-specific caches, and public package exports; retain only private helpers required by `ProductionIngestor`, with no independent preparation/cache path.
- [X] T035 [US1] Run and retain the US1 mixed-content evidence from `tests/production_ingest/test_policy.py`, `test_plain_ingest.py`, `test_markdown_ingest.py`, `test_docling_ingest.py`, and `test_doclang_ingest.py` in `specs/002-production-source-ingest/evidence/us1-conformance.json`.

**Checkpoint**: User Story 1 is independently usable for trustworthy primary-discourse selection and is the MVP.

---

## Phase 4: User Story 2 — Preserve Exact Source Fidelity and Provenance (Priority: P1)

**Goal**: Every prepared character, EDU, relation, and persisted result reversibly identifies its exact source or explicit synthetic origin.

**Independent Test**: Prepare, analyse, serialize, and reload every source form; prove 100% inventory, primary-source, prepared-text, and analysis-anchor coverage with zero fabricated, overlapping, duplicated, or wrong-source mappings.

### Tests for User Story 2

- [X] T036 [P] [US2] Write failing property/invariant tests for source-derived and synthetic segment mappings, Unicode, line endings, quote selectors, ranges, and total reverse maps in `tests/production_ingest/test_prepared_mapping.py`.
- [X] T037 [P] [US2] Write failing format-native anchor tests in `tests/production_ingest/test_native_anchors.py` for Markdown line/range/DOM, Docling ref/page/bounding-box/table, DocLang XML/item/location/table, plain-text range, and EDU identity anchors.
- [X] T038 [P] [US2] Write failing persisted analysis-anchor and receipt reconciliation tests in `tests/production_ingest/test_provenance_roundtrip.py`, covering every EDU/relation/node, local versus macro origin, changed source identity, and schema reload.

### Implementation for User Story 2

- [X] T039 [P] [US2] Project exact Markdown source spans, structural ancestry, quote selectors, and parsed HTML node addresses in the private Markdown adapter in `isanlp_rst/ingest/prepare.py`.
- [X] T040 [P] [US2] Project exact Docling refs, page/bounding-box/table coordinates, content layers, conversion provenance, and raw/accepted contract identity in the private Docling adapter in `isanlp_rst/ingest/prepare.py`.
- [X] T041 [P] [US2] Project exact DocLang XML paths, semantic IDs, locations, layers/threads, nested-table ancestry, and archive asset identity in the private DocLang adapter in `isanlp_rst/ingest/prepare.py`.
- [X] T042 [US2] Implement ordered prepared segments, explicit synthetic separators, reversible transformations, complete range maps, and all four fail-closed coverage proofs in `isanlp_rst/ingest/prepare.py` so T036 and T037 pass.
- [X] T043 [US2] Implement EDU/relation/tree-node source projection and local/macro provenance construction in `isanlp_rst/ingest/service.py`, using descendant unions rather than fabricated relation coordinates.
- [X] T044 [US2] Implement deterministic `PreparationReceipt`, truthful separate `ExecutionReceipt`, persistence integrity, and reload verification in `isanlp_rst/ingest/contracts.py`, `isanlp_rst/ingest/service.py`, and `isanlp_rst/contracts/serialization.py`.
- [X] T045 [US2] Run the every-format persistence/round-trip suite and directly inspect representative mappings, recording text-free results in `specs/002-production-source-ingest/evidence/us2-provenance.json`.

**Checkpoint**: User Story 2 independently proves exact, persistent source-to-analysis traceability.

---

## Phase 5: User Story 3 — Use Document Structure as Analysis Material (Priority: P1)

**Goal**: Source structure constrains segmentation and recursive analysis before inference, including complete coherent results for oversized documents.

**Independent Test**: Analyse multi-section, slide, page, group, list, and speaker-turn sources plus a one-million-character source; prove structure-aligned units, complete non-duplicated EDUs, distinguishable local/macro relations, stable anchors, and one coherent tree.

### Tests for User Story 3

- [X] T046 [P] [US3] Write failing deterministic subdivision-plan tests in `tests/production_ingest/test_subdivision.py` for structural precedence, actual parser capacity, oversized units, context-only overlap, deterministic fallbacks, and complete non-overlapping output ranges.
- [X] T047 [P] [US3] Write failing hierarchical tree/stitching tests in `tests/production_ingest/test_structural_analysis.py` for local analyses, anchored nuclear-spine macro representations, recursive parents, one coherent tree, and exact local/macro origin.
- [X] T048 [P] [US3] Write failing long-source and indivisible-EDU tests in `tests/production_ingest/test_long_source.py`, deterministically generating at least one one-million-character structured source without storing a huge fixture in Git.

### Implementation for User Story 3

- [X] T049 [US3] Implement the deterministic structure-first `AnalysisUnit` tree, parser-capacity partitioning, context/output separation, and fully receipted fallback algorithm in `isanlp_rst/ingest/subdivision.py`.
- [X] T050 [P] [US3] Make Markdown inventory structure express operative heading/section/list/turn hierarchy before parsing in `isanlp_rst/ingest/prepare.py`.
- [X] T051 [P] [US3] Make Docling inventory structure express operative groups/headings/pages/slides/lists/turns/tables before parsing in `isanlp_rst/ingest/prepare.py`.
- [X] T052 [P] [US3] Make DocLang inventory structure express operative semantic/group/list/page/turn/table hierarchy before parsing in `isanlp_rst/ingest/prepare.py`.
- [X] T053 [US3] Replace fixed-prefix macro summaries with deterministic anchored nuclear-spine representations and complete recursive stitching in `isanlp_rst/hierarchical/stitcher.py`, preserving every output EDU exactly once.
- [X] T054 [US3] Integrate subdivision, unchanged local parser inference, recursive macro analysis, final tree validation, and native-anchor projection in `isanlp_rst/ingest/service.py` and `isanlp_rst/parser.py`.
- [X] T055 [US3] Run real released-model CPU and available Apple MPS structural-analysis tests and retain model/tree/coverage evidence in `specs/002-production-source-ingest/evidence/us3-structural-analysis.json`.
- [X] T056 [US3] Run the one-million-character preparation and end-to-end coherence scenario, recording complete coverage, unit counts, anchors, preparation time, peak RSS, and final tree identity in `specs/002-production-source-ingest/evidence/us3-million-character.json`.

**Checkpoint**: User Story 3 independently produces structure-aware, complete long-document analyses with unchanged model mathematics.

---

## Phase 6: User Story 4 — Prove Ingest Quality on Real Production Sources (Priority: P1)

**Goal**: Provide immutable, per-source baseline/candidate comparison and direct inspection infrastructure. Final promotion execution waits for User Stories 5 and 6 so the complete candidate—not a reduced P1 subset—is assessed.

**Independent Test**: Against frozen pilot copies of every output type, prove that the repository-only assessor enforces ordered per-source gates, identical model/source/scorer identity, protected metrics, inspection completeness, and a no-waiver decision without any reverse production import.

### Tests for User Story 4

- [X] T057 [P] [US4] Write failing promotion-contract and freeze-integrity tests in `tests/production_ingest/test_promotion_contracts.py`, including changed Gold/source/model/scorer/machine identity, protected-text leakage, and post-freeze mutation.
- [X] T058 [P] [US4] Write failing isolated-wheel baseline/candidate runner tests in `tests/production_ingest/test_candidate_runner.py`, proving repository removal from `sys.path`, no network, identical released-model bytes, complete per-source outputs, and no evaluation dependency in the production environment.
- [X] T059 [P] [US4] Write failing per-source assessor/inspection tests in `tests/production_ingest/test_promotion_assessor.py`, covering gate order, 100% relevance/coverage/anchors, per-form EDU/Parseval non-regression, 50% structural improvement, zero hidden regression, and no waiver field.

### Implementation for User Story 4

- [X] T060 [US4] Complete immutable freeze verification and candidate identity checks in `tools/production_ingest/freeze.py` and `tools/production_ingest/contracts.py` so T057 passes.
- [X] T061 [US4] Implement clean temporary-environment baseline/candidate wheel execution and serialized-output collection in `tools/production_ingest/runner.py` and `tools/production_ingest/__main__.py` so T058 passes.
- [X] T062 [US4] Implement repository-only content-selection, coverage, anchor, structural-boundary, EDU, and canonical offline Parseval assessment in `tools/production_ingest/assessor.py`, importing `offline_workbench.evaluation.rst` only from the assessor side.
- [X] T063 [US4] Implement mandatory per-source prepared-document/receipt/result inspection records and fail-closed anomaly reconciliation in `tools/production_ingest/inspection.py` and `tools/production_ingest/contracts.py`.
- [X] T064 [US4] Implement ordered gate evaluation, per-source/per-form reporting, protected-metric enforcement, and a no-waiver promotion decision in `tools/production_ingest/report.py` and `tools/production_ingest/__main__.py`.
- [X] T065 [US4] Update the dated primary-source comparison with implementation-measurable evidence slots and bounded claim language in `specs/002-production-source-ingest/evidence/current-practice-comparison.md`.
- [X] T066 [US4] Run the promotion framework against frozen pilot outputs, prove all assessor failure paths causally, and store text-free framework evidence in `specs/002-production-source-ingest/evidence/us4-promotion-framework.json`; do not issue the final candidate decision yet.

**Checkpoint**: User Story 4's promotion machinery is independently proven; its final decision remains blocked on the complete US1–US6 candidate.

---

## Phase 7: User Story 5 — Retain Complex Non-Prose Material Without Contaminating RST (Priority: P2)

**Goal**: Preserve tables, recursive tables, code, formulas, pictures/assets, raw HTML, and machine/OCR material faithfully as structured side channels without contaminating default RST.

**Independent Test**: Submit current-valid nested DocLang tables, rich Docling content, code/formula/table-heavy Markdown, and hostile raw HTML/archives; prove structural retention, safe origin-aware dispositions, explicit `not_analysed`, and zero unintended primary text.

### Tests for User Story 5

- [X] T067 [P] [US5] Add failing current-valid recursive/nested-table and `.dclx` conformance/security tests in `tests/production_ingest/test_doclang_complex.py`, including empty namespace, archive traversal/symlink/duplicate/encrypted/ratio/size/relationship cases.
- [X] T068 [P] [US5] Add failing structural raw-HTML and complex Markdown tests in `tests/production_ingest/test_markdown_complex.py`, proving script/style/template/navigation/markup never become prose and authored DOM text retains exact anchors.
- [X] T069 [P] [US5] Add failing complex Docling side-channel tests in `tests/production_ingest/test_docling_complex.py` for recursive tables, captions, pictures/descriptions, notes, OCR provenance/confidence, all content layers, and unknown current-valid items.

### Implementation for User Story 5

- [X] T070 [US5] Implement secure bounded stdlib-ZIP `.dclx` loading, `document.xml` relationship/asset identity, and full current validation in `isanlp_rst/doclang/loader.py` and `isanlp_rst/doclang/errors.py` without extraction to an uncontrolled path.
- [X] T071 [US5] Preserve recursive DocLang table/list/group/field/asset hierarchy and explicit unsupported analysis status in `isanlp_rst/doclang/text_walker.py` and the private DocLang adapter in `isanlp_rst/ingest/prepare.py`.
- [X] T072 [US5] Replace regex HTML removal with hardened structural lxml inventory and authored-node selection in `isanlp_rst/markdown/loader.py` and the private Markdown adapter in `isanlp_rst/ingest/prepare.py`, with no execution or resource fetching.
- [X] T073 [US5] Preserve complete complex Docling structure, machine/OCR authorship/confidence, and side-channel anchors in the private Docling adapter in `isanlp_rst/ingest/prepare.py` without flattening table cells into default prose.
- [X] T074 [US5] Run the complete complex-content suite and directly inspect all retained side channels, recording zero-contamination and structural-retention evidence in `specs/002-production-source-ingest/evidence/us5-complex-content.json`.

**Checkpoint**: User Story 5 independently preserves valid complex content without implying RST prose semantics.

---

## Phase 8: User Story 6 — Receive Deterministic, Actionable Production Evidence (Priority: P2)

**Goal**: Equal analytical inputs are semantically deterministic, cache-safe, efficient on one machine, and fail closed with actionable evidence.

**Independent Test**: Repeat cached/uncached analyses ten times; mutate every analytical identity dimension; inject corruption, malformed/unsafe sources, and parser identity gaps; prove deterministic semantic outputs, correct hits/misses/failures, truthful execution receipts, and bounded local performance.

### Tests for User Story 6

- [X] T075 [P] [US6] Write failing cache identity/integrity/atomicity tests in `tests/production_ingest/test_cache.py` for every fingerprint dimension, verified hits, normal changed-identity misses, corruption/contradiction failures, interrupted writes, and parser-without-release-identity disablement.
- [X] T076 [P] [US6] Write failing ten-run cached/uncached semantic determinism tests in `tests/production_ingest/test_determinism.py`, allowing truthful execution timestamp/timing/RSS/cache differences only.
- [X] T077 [P] [US6] Expand failing malformed/unsafe/contradictory/incomplete/no-primary tests in `tests/production_ingest/test_fail_closed.py`, requiring exact artifact/item/stage/code evidence and zero apparently successful partial results.
- [X] T078 [P] [US6] Write preparation/cache/one-million-character benchmark tests with fixed reference-machine metadata and correctness-first assertions in `tests/production_ingest/test_performance.py`.

### Implementation for User Story 6

- [X] T079 [US6] Implement post-validation/prepared-identity cache lookup, canonical keys, verified payloads, corruption distinction, and same-filesystem atomic writes in `isanlp_rst/ingest/cache.py`.
- [X] T080 [US6] Integrate cache sequencing, durable-cache disablement, truthful stage timings/peak RSS, and semantic-versus-execution receipts in `isanlp_rst/ingest/service.py`.
- [X] T081 [US6] Complete fail-closed error projection across the private format adapters, `isanlp_rst/doclang/errors.py`, and `isanlp_rst/ingest/contracts.py`, preserving all completed-stage evidence without private-text leakage.
- [X] T082 [US6] Make every persisted semantic collection and traversal order deterministic in `isanlp_rst/ingest/prepare.py`, `isanlp_rst/ingest/subdivision.py`, and `isanlp_rst/contracts/serialization.py` so T076 passes across cache state.
- [X] T083 [US6] Run ten-run determinism, complete invalidation, cache corruption, fail-closed, and local performance suites; retain actual timings/RSS/cache evidence in `specs/002-production-source-ingest/evidence/us6-production-evidence.json`.

**Checkpoint**: User Story 6 independently proves dependable local production operation without stale, partial, or unexplained results.

---

## Phase 9: Cross-Cutting Convergence and Final Promotion

**Purpose**: Prove the exact complete candidate from its built wheel, execute the frozen Gold Set, directly inspect every result, and reconcile every requirement before claiming completion.

- [X] T084 [P] Add exact production wheel payload/import/dependency and clean-install ingest scenarios to `tests/test_production_boundary.py` and `tools/production_boundary/installed_acceptance.py`, covering every source form with the repository absent and training/evaluation/Gold modules unavailable.
- [X] T085 [P] Add canonical public-surface tests in `tests/production_ingest/test_public_api.py`, proving `isanlp_rst.ingest` is the only source-ingest API and obsolete format entry points, envelopes, and caches are absent from both source and built wheel.
- [X] T086 [P] Add current normative Docling/DocLang unmodified-specimen, fixture-inventory parity, and `.dclx` archive conformance to `tests/production_ingest/test_upstream_conformance.py` and `scripts/verify_doclang_fixtures.py`.
- [X] T087 Update the public production-ingest API, default policy, provenance, empty-discourse, single-public-surface, and offline-boundary documentation in `README.md`, `docs/production-source-ingest.md`, and `docs/raw-material-ingest-forensic-analysis.md` without describing target commands as already proven.
- [X] T088 Run focused Feature 002 tests, the applicable complete production/offline suites, Ruff, Pyright, Markdown lint, packaging checks, and `pixi run -e production production-boundary`; record the exact commands/results and resolve every failure in `specs/002-production-source-ingest/evidence/verification-record.json`.
- [X] T089 Build the immutable candidate wheel/sdist once, verify artifact contents/digests, install outside the repository, and run all source-form, persistence, cache, CPU, and available MPS acceptance paths; record proof in `specs/002-production-source-ingest/evidence/candidate-artifact.json`.
- [X] T090 Re-verify current upstream Docling/DocLang releases, specifications, source APIs, normative specimen inventories, and local pin/lock currency immediately before promotion; update `specs/002-production-source-ingest/evidence/docling-contract-final.json` and `specs/002-production-source-ingest/evidence/doclang-contract-final.json`, and rebuild/retest if the accepted contract changed.
- [X] T091 Execute the frozen Gold Set baseline/candidate comparison with identical model/source/scorer/machine identities and store every text-free per-source/per-form gate result in `specs/002-production-source-ingest/evidence/promotion-report.json`.
- [X] T092 Directly inspect every Gold Set prepared document, receipt, persisted RST result, source anchor, and anomaly; record all source-level decisions in `specs/002-production-source-ingest/evidence/inspection-record.json`, with any unresolved anomaly failing promotion.
- [X] T093 Complete the dated current-practice matrix with measured candidate evidence and issue the bounded no-waiver decision in `specs/002-production-source-ingest/evidence/current-practice-comparison.md` and `specs/002-production-source-ingest/evidence/promotion-decision.json` only if every ordered gate passes.
- [X] T094 Run `$speckit-analyze` and `$speckit-converge`, implement any appended work, re-run the affected and final gates, and leave `specs/002-production-source-ingest/tasks.md` with every genuinely completed task checked and no unresolved traceability finding.
- [X] T095 Record the immutable delivery commit, clean working-tree status, built artifact digests, branch/publication state, and exact final verification evidence in `specs/002-production-source-ingest/evidence/release-record.json`, then publish through the repository's approved Git workflow.

**Checkpoint**: Feature 002 is complete only if every task, per-source gate, direct inspection, current-spec check, clean-wheel boundary check, and bounded promotion decision is actually green.

---

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1 — Setup**: Starts immediately.
- **Phase 2 — Foundation/freeze**: Depends on Phase 1 and blocks candidate implementation. T021 must freeze the current baseline before T022.
- **US1**: Depends on Phase 2 and is the MVP.
- **US2**: Depends on the canonical prepared-document path from US1; its tests/contracts can be prepared after Phase 2 in separate files.
- **US3**: Depends on US1 preparation and US2 provenance mappings.
- **US4 framework**: Depends on the frozen Phase 2 authority and serialized outputs from US1–US3. Final promotion execution is intentionally deferred to Phase 9.
- **US5**: Depends on US1 inventory/policy contracts; it can proceed independently of US2/US3 after that checkpoint.
- **US6**: Depends on US1 and foundational identity contracts. Cache tests can proceed alongside US2/US5; final determinism evidence follows US3 integration.
- **Phase 9 — Final promotion**: Depends on US1–US6 completion and the immutable baseline freeze.

### User-story dependency graph

```text
Setup -> Foundation + baseline freeze -> US1 (MVP)
                                      ├-> US2 -> US3 ─┐
                                      ├-> US5 ────────┼-> final US4 promotion -> convergence/release
                                      └-> US6 ────────┘
                         US1 + US2 + US3 -> US4 promotion framework
```

### Within each story

1. Write the specified tests and observe the intended failure.
2. Implement contracts/models before orchestration.
3. Implement format-specific inventory/mapping before the canonical service consumes it.
4. Make focused tests pass without weakening assertions or suppressing diagnostics.
5. Run the independent scenario and inspect persisted evidence before crossing the checkpoint.

## Parallel Opportunities

Parallel markers identify independent files/work packets, not a team or enterprise execution model. On this solo-local project they may simply be completed in either order.

- T003–T005 can be researched independently after T001.
- T006/T008/T010/T012/T014/T016/T018 are independent failing-test work packets before their paired implementation tasks.
- US1 format tests T023–T026 and format implementations T029–T031 touch separate adapters.
- US2 native mapper tasks T039–T041 are independent after their shared contracts exist.
- US3 boundary tasks T050–T052 are independent after the subdivision contract is frozen.
- US4 test tasks T057–T059 exercise distinct freeze, runner, and assessor boundaries.
- US5 test tasks T067–T069 exercise distinct source families.
- US6 test tasks T075–T078 exercise distinct cache, determinism, failure, and performance properties.
- Final boundary, canonical-public-surface, and upstream-conformance tests T084–T086 touch separate files.

## Parallel Examples

### User Story 1

```text
T023 plain/EDU inventory tests
T024 Markdown inventory tests
T025 Docling inventory tests
T026 DocLang inventory tests
```

### User Story 2

```text
T039 Markdown native-anchor projection
T040 Docling native-anchor projection
T041 DocLang native-anchor projection
```

### User Story 3

```text
T050 Markdown operative boundaries
T051 Docling operative boundaries
T052 DocLang operative boundaries
```

### User Story 4

```text
T057 freeze-integrity tests
T058 isolated-wheel runner tests
T059 assessor and inspection tests
```

### User Story 5

```text
T067 DocLang complex/archive tests
T068 Markdown/HTML complex tests
T069 Docling complex-content tests
```

### User Story 6

```text
T075 cache correctness tests
T076 determinism tests
T077 fail-closed tests
T078 performance tests
```

## Implementation Strategy

### MVP first

1. Freeze current authorities and baseline in Phases 1–2.
2. Implement US1 only.
3. Stop and validate the complete mixed-content independent test.
4. The MVP is usable authored-discourse preparation, but it is not Feature 002 completion or SOTA evidence.

### Excellence sequence

1. Add exact provenance (US2) and structural long-document analysis (US3).
2. Build the promotion framework (US4) against frozen outputs without issuing a premature claim.
3. Complete complex-content fidelity (US5) and deterministic/cache-safe operation (US6).
4. Build one immutable candidate and run Phase 9 exactly once per candidate identity.
5. Any failure produces a new candidate after correction; it never alters the frozen benchmark or waives a gate.

### Scope discipline

- Do not retrain, tune, select, or alter model mathematics.
- Do not move packages or redesign the production/offline split in Feature 002.
- Do not introduce services, queues, concurrency frameworks, databases, or enterprise controls.
- Do not duplicate Parseval or source-format authorities.
- Do not commit private Gold source content or expose it in evidence.
- Fix any discovered Feature 003 boundary defect as an explicitly identified boundary repair while keeping production dependencies one-way.

## Notes

- `[P]` means file/dependency independence, not permission to skip sequential verification.
- Every task must leave touched Python at the repository's Python 3.14 quality bar.
- A checker passes only by making its assertion true; suppressions and weakened fixtures are prohibited.
- Upstream currency is verified both before implementation and immediately before promotion.
- Current tests and fixtures are baseline evidence, never automatic proof of the new contract.
- Commit after coherent verified work packets; never publish an unverified moving candidate as final evidence.

## Phase 10: Convergence

- [X] T096 Implement and causally test policy-controlled reversible deduplication of non-authored conversion artifacts in `isanlp_rst/ingest/policy.py`, `isanlp_rst/ingest/prepare.py`, and `tests/production_ingest/test_policy.py`, while retaining intentional authored repetition, per FR-010 and plan step 4 (contradicts).
- [X] T097 Prove that a caller-supplied named policy can explicitly admit a normally excluded content class and that the resulting disposition and preparation evidence remain truthful in `tests/production_ingest/test_policy.py` and `tests/production_ingest/test_plain_ingest.py`, per FR-008 and US1/AC3 (partial).
- [X] T098 Execute ten exact-wheel cached/uncached semantic runs for every real Gold Set source and record zero stale or nondeterministic results in `specs/002-production-source-ingest/evidence/us6-production-evidence.json`, per SC-004 and SC-005 (partial).
- [X] T099 Record real-model end-to-end coherence, coverage, subdivision, timing, memory, and final-tree identity for the 1,848,302-character Gold source in `specs/002-production-source-ingest/evidence/us3-million-character.json`, per SC-007 and SC-008 (partial).
- [X] T100 Reconcile the implemented feature's active branch and status metadata in `specs/002-production-source-ingest/spec.md` and `specs/002-production-source-ingest/plan.md` before release, without changing scope or intent (partial).
