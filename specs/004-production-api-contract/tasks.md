---

description: "Dependency-ordered implementation tasks for the isanlp_rst 5.0.0 production API contract"
---

# Tasks: World-Class Production API Contract

**Input**: Design documents from `/specs/004-production-api-contract/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, and `quickstart.md`

**Tests**: Required by FR-036-FR-041, FR-047-FR-073, and every user story's
independent test.
Test tasks precede the implementation they specify and must fail for the
intended reason before implementation begins.

**Organization**: Tasks retain the specification's US1-US6 labels. Execution
order follows real technical dependency: retained source evidence enables
preparation; preparation enables analysis and completed-stage failures;
capability discovery and every functional story must exist before the immutable
5.0.0 distribution can be certified.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Safe to execute in parallel because the task touches different files
  and has no dependency on another incomplete `[P]` task in the same group.
- **[Story]**: Maps the task to the corresponding user story in `spec.md`.
- Every task names the exact target path and relevant requirements or success
  criteria.

## Phase 1: Setup and Contract Currency

**Purpose**: Establish the verified dependency, source-specification, version,
typing, and test-fixture baseline required by all stories.

- [X] T001 Verify current Docling and DocLang package/specification/fixture currency and record versions, accepted forms, optional extras, and any required same-pass remediation in `specs/004-production-api-contract/evidence/source-spec-currency.md` before touching `isanlp_rst/ingest/prepare.py`, `isanlp_rst/doclang/`, or format fixtures (FR-025, FR-028)
- [X] T002 Update the Python 3.14 production contract dependencies to Pydantic 2.13.x and PyPA build 1.6.x using Pixi, then commit the solved dependency state in `pyproject.toml` and `pixi.lock` without manual lock edits (FR-019, FR-043)
- [X] T003 Set the source distribution version to 5.0.0, declare `Import-Name: isanlp_rst`, include contract resources, and retain format packages exclusively in the `formats` extra in `pyproject.toml` (FR-022, FR-031, FR-042)
- [X] T004 [P] Add the PEP 561 marker at `isanlp_rst/py.typed` and its packaging assertion in `tests/production_boundary/test_release_metadata.py` (FR-002, FR-035)
- [X] T005 [P] Add deterministic Feature 004 source, parser, model-identity, cache, and private-marker fixture builders in `tests/ingest/production_ingest/conftest.py` (FR-037, FR-038)

**Checkpoint**: Dependency and source-contract assumptions are current,
versioned, and reproducible before production contracts are changed.

---

## Phase 2: Foundational Contract and Persistence Infrastructure

**Purpose**: Create the strict contract foundation that blocks every user story.

**CRITICAL**: No user-story implementation begins until this phase passes its
focused tests.

### Foundational tests

- [X] T006 [P] Add failing tests for recursive strictness, frozen nested values, forbidden extras, finite numbers, exact coverage, semantic versions, and SHA-256 identities in `tests/ingest/production_ingest/test_contract_base.py` (FR-011, FR-012, FR-019)
- [X] T007 [P] Add failing tests for RFC 8785 canonical bytes, duplicate-key rejection, semantic/execution separation, unsupported-version rejection, and serialize-load-serialize equality in `tests/ingest/production_ingest/test_serialization_v2.py` (FR-019-FR-021, SC-008)
- [X] T008 [P] Add failing tests that reconcile public manifest membership with `__all__`, imports, signatures, enums, discriminators, schemas, and documentation anchors in `tests/ingest/production_ingest/test_public_surface.py` (FR-002, FR-032, FR-039, SC-006)

### Foundational implementation

- [X] T009 Convert `isanlp_rst/ingest/contracts.py` into the cohesive `isanlp_rst/ingest/contracts/__init__.py`, `base.py`, `source.py`, `preparation.py`, `analysis.py`, `inference.py`, `failure.py`, and `capabilities.py` package while preserving existing internal imports until their owning migration task (FR-001, FR-003)
- [X] T010 Implement the shared strict base model, `SemanticVersion`, `Sha256Identity`, exact quantity types, contract-family constants, and 2.0.0 write/read registry types in `isanlp_rst/ingest/contracts/base.py` (FR-011, FR-019-FR-022)
- [X] T011 Implement the migrated `SourceArtifact`, `SourceSummary`, `SourceContractIdentity`, source anchors, origins, relationships, and closed representation/disposition type foundations in `isanlp_rst/ingest/contracts/source.py` (FR-003-FR-006)
- [X] T012 Implement preparation policy, planning policy, prepared segment/document, analysis unit/plan, transformation, coverage, semantic/execution evidence, and `PreparationOutcome` foundations in `isanlp_rst/ingest/contracts/preparation.py` (FR-007-FR-008, FR-020, FR-026)
- [X] T013 Implement model identity states, analysis status, anchor, semantic/execution evidence, `AnalysedOutcome`, `EmptyPrimaryAnalysisOutcome`, and the discriminated `ProductionAnalysisOutcome` in `isanlp_rst/ingest/contracts/analysis.py` (FR-009, FR-013-FR-014, FR-020)
- [X] T014 Implement lifecycle stages, retryability, safe contexts/causes, completed-evidence variants, safe redaction variants, diagnostic policy, failure records, and `ProductionIngestError` foundations in `isanlp_rst/ingest/contracts/failure.py` (FR-015-FR-017, FR-019)
- [X] T015 Implement source-form, operation, optional-extra, persistence, parser-identity, and cache-eligibility capability contract foundations in `isanlp_rst/ingest/contracts/capabilities.py` (FR-023-FR-024, FR-031)
- [X] T016 Implement strict UTF-8/I-JSON parsing, tagged version dispatch, RFC 8785 serialization, semantic projection, SHA-256 verification, and public load/serialize functions in `isanlp_rst/ingest/serialization.py` (FR-011, FR-019-FR-021)
- [X] T017 Implement the versioned public symbol, resource, console-command, and loopback-endpoint membership/classification authority in `isanlp_rst/ingest/public-surface.json` and its strict loader/reconciler in `isanlp_rst/ingest/public_surface.py` (FR-002, FR-032, FR-039, FR-072-FR-073)
- [X] T018 Implement deterministic serialization-mode Draft 2020-12 schema generation and committed byte-parity projections in `isanlp_rst/ingest/schemas/` with the generator in `tools/production_boundary/schemas.py` (FR-019, FR-021, FR-039)
- [X] T019 Migrate production imports and re-exports to the contract package in `isanlp_rst/ingest/__init__.py`, `prepare.py`, `policy.py`, `subdivision.py`, `identity.py`, `cache.py`, and `service.py`, then make T006-T008 pass without compatibility aliases for removed format APIs (FR-001-FR-003, FR-033)

**Checkpoint**: Strict v2 models, canonical persistence, schemas, and public
classification are coherent before lifecycle behaviour is changed.

---

## Phase 3: User Story 6 - Retain Valid Non-Primary Material (Priority: P2, Enabling)

**Goal**: Preserve every valid source item as primary or accessible retained
content with meaningful structure, anchors, relationships, and disposition.

**Independent Test**: Ingest the mixed-content fixtures and prove that every
valid item has one final disposition; table, hierarchy, list, note, caption,
metadata, media, and cross-reference structure round-trip; duplicates resolve
to one canonical item.

### Tests for User Story 6

- [X] T020 [P] [US6] Add mixed text, EDU, GFM, Docling JSON, DocLang XML, and DocLang archive fixtures with primary, retained, duplicate, and structured content under `tests/fixtures/production_api/retained_content/` (FR-003, FR-027-FR-028, SC-001)
- [X] T021 [P] [US6] Add failing representation and round-trip tests for text, table, list, metadata, annotation, media-reference, structure, and cross-reference variants in `tests/ingest/production_ingest/test_retained_representations.py` (FR-005-FR-006, FR-019, FR-028)
- [X] T022 [P] [US6] Add failing tests for hierarchy, table-cell spans/headers, list nesting, captions, notes, metadata, anchors, and relationship preservation in `tests/ingest/production_ingest/test_retained_structure.py` (FR-005, FR-028)
- [X] T023 [P] [US6] Add failing duplicate precedence, canonical-target, acyclicity, and one-disposition-per-item tests in `tests/ingest/production_ingest/test_inventory_dispositions.py` (FR-004-FR-005, FR-027, SC-001)

### Implementation for User Story 6

- [X] T024 [US6] Complete the closed `ContentRepresentation`, `ContentInventoryItem`, `Disposition`, origin, anchor, and relationship variants in `isanlp_rst/ingest/contracts/source.py` without adding downstream-specific fields (FR-005-FR-006, FR-028, FR-034)
- [X] T025 [US6] Preserve existing Docling item, table, page/bounding-box, caption, metadata, hierarchy, and cross-reference semantics during inventory construction in `isanlp_rst/ingest/prepare.py` (FR-025, FR-027-FR-028)
- [X] T026 [P] [US6] Preserve current DocLang layer, element-head, table/list, note/caption, metadata, archive-member, and cross-reference semantics in `isanlp_rst/doclang/text_walker.py` and `isanlp_rst/doclang/loader.py` (FR-025, FR-027-FR-028)
- [X] T027 [P] [US6] Preserve GFM hierarchy, front matter, list/table, image/caption, HTML, and source-span semantics in `isanlp_rst/markdown/loader.py` and the Markdown inventory path in `isanlp_rst/ingest/prepare.py` (FR-025, FR-027-FR-028)
- [X] T028 [US6] Embed exactly one canonical final disposition and explicit duplicate/transformation links in each item in `isanlp_rst/ingest/policy.py` and `isanlp_rst/ingest/contracts/source.py` (FR-005, FR-027)
- [X] T029 [US6] Add inventory relationship, duplicate, retained-accessibility, and complete item-coverage validators in `isanlp_rst/ingest/validation.py` (FR-006, FR-012, FR-027-FR-028, SC-001)
- [X] T030 [US6] Make all US6 tests pass across `tests/ingest/production_ingest/test_retained_representations.py`, `test_retained_structure.py`, and `test_inventory_dispositions.py` without flattening or digest-only substitutes (SC-001, SC-004)

**Checkpoint**: Retained content is independently inspectable and structurally
faithful before preparation and analysis outcomes depend on it.

---

## Phase 4: User Story 2 - Inspect Preparation Before Analysis (Priority: P1)

**Goal**: Return a complete deterministic `PreparationOutcome`, with or without
parser capacity, without running model inference.

**Independent Test**: Prepare every source form with and without capacity;
verify source contract, full inventory, transformations, mappings, coverage,
warnings, empty-primary state, and complete deterministic subdivision plan.

### Tests for User Story 2

- [X] T031 [P] [US2] Add failing construction, invariant, and canonical round-trip tests for complete `PreparationOutcome` semantic/execution evidence in `tests/ingest/production_ingest/test_preparation_outcome.py` (FR-007, FR-019-FR-021)
- [X] T032 [P] [US2] Add failing no-plan, single-unit, subdivided, capacity-bound, recombination, and deterministic plan tests in `tests/ingest/production_ingest/test_analysis_plan.py` (FR-008, FR-026, FR-040)
- [X] T033 [P] [US2] Add failing empty, whitespace-only, and retained-only successful preparation tests in `tests/ingest/production_ingest/test_empty_primary_preparation.py` (FR-012-FR-014, SC-003)
- [X] T034 [P] [US2] Add failing source mapping, structural boundary, anchor reconstruction, transformation, and exact coverage tests in `tests/ingest/production_ingest/test_preparation_validation.py` (FR-007, FR-010-FR-012, SC-003)
- [X] T035 [P] [US2] Add failing semantic mutation tests for source identity, source contract, preparation policy, prepared discourse, planning policy, capacity, and plan in `tests/ingest/production_ingest/test_preparation_identity.py` (FR-011, FR-026, FR-040-FR-041)

### Implementation for User Story 2

- [X] T036 [US2] Complete explicit preparation and planning policy semantics, defaults, fingerprints, and stable warning identifiers in `isanlp_rst/ingest/contracts/preparation.py` and `isanlp_rst/ingest/policy.py` (FR-007, FR-026)
- [X] T037 [US2] Build complete transformation records, prepared segments/document, source mapping, structural boundaries, exact coverage, and semantic evidence from inventory in `isanlp_rst/ingest/prepare.py` (FR-004-FR-007, FR-010)
- [X] T038 [US2] Upgrade deterministic subdivision and recombination planning to return the public `AnalysisPlan` before inference in `isanlp_rst/ingest/subdivision.py` (FR-008, FR-026)
- [X] T039 [US2] Implement preparation cross-field, coverage, mapping, anchor, plan-unit, and semantic-identity validation in `isanlp_rst/ingest/validation.py` (FR-011-FR-012, SC-003)
- [X] T040 [US2] Change `ProductionIngestor.prepare()` to return the complete `PreparationOutcome`, select and expose resolved defaults, and accept optional declarative parser capacity in `isanlp_rst/ingest/service.py` (FR-001, FR-007-FR-008, FR-014)
- [X] T041 [US2] Implement preparation semantic projection and identity recomputation from exposed values in `isanlp_rst/ingest/identity.py` (FR-011, FR-040-FR-041)
- [X] T042 [US2] Export the complete preparation types and exact `prepare()` signature from `isanlp_rst/ingest/__init__.py` and reconcile them in `isanlp_rst/ingest/public-surface.json` (FR-002, FR-032, FR-035)
- [X] T043 [US2] Make every source-form, empty-primary, subdivision, mapping, round-trip, and mutation test pass in `tests/ingest/production_ingest/` without model loading (FR-003, FR-037-FR-038)
- [X] T044 [US2] Enforce the 100,000- and 1,000,000-character preparation thresholds over one warm-up plus five measured runs in `tests/ingest/production_ingest/test_performance.py` (SC-014)

**Checkpoint**: Preparation is a complete independently usable public stage and
the explicit intentional-non-analysis path.

---

## Phase 5: User Story 1 - Consume a Complete Analysis Result (Priority: P1, MVP)

**Goal**: Return one validated self-contained analysis outcome containing the
complete preparation account, exact analysed substrate, discourse graph,
decision-complete primary/eRST evidence, refinement provenance, both-endpoint
anchors, composite component identity, recombination and validation receipts,
execution evidence, cache provenance, and recomputable semantic identity.

**Independent Test**: Analyse one representative fixture per source form,
serialize and reload it, and explain every provider decision from the single
outcome using only installed public imports.

### Tests for User Story 1

- [X] T045 [P] [US1] Add failing analysed/empty-primary discriminated outcome, full nested preparation, model identity, execution, cache provenance, and round-trip tests in `tests/ingest/production_ingest/test_analysis_outcomes_v2.py` (FR-009-FR-014, FR-019-FR-020)
- [X] T046 [P] [US1] Add failing primary-tree connectedness, acyclicity, single-root, nuclearity, and relation tests plus eRST sufficient-signal, no-self-loop, existing-endpoint, and unique-directed-pair tests that explicitly accept cycles, crossings, overlap, and unrestricted degree in `tests/ingest/production_ingest/test_analysis_validation.py` (FR-012, FR-018, SC-002)
- [X] T047 [P] [US1] Add failing EDU/node/primary-edge/secondary-edge anchor completeness, bounds, uniqueness, and source-reconstruction tests in `tests/ingest/production_ingest/test_analysis_anchor_validation.py` (FR-009, FR-012, SC-002)
- [X] T048 [P] [US1] Add failing multi-unit completeness, deterministic recombination, no-partial-success, and no-partial-cache tests in `tests/ingest/production_ingest/test_multi_unit_atomicity.py` (FR-008, FR-018, FR-040)
- [X] T049 [P] [US1] Add failing request/result/cache identity mutation and execution-only negative-control tests in `tests/ingest/production_ingest/test_semantic_mutations.py` (FR-011, FR-040-FR-041, SC-008-SC-009)
- [X] T050 [P] [US1] Add a representative zero-private-import consumer adapter test in `tests/ingest/production_ingest/test_public_consumer_adapter.py` (FR-010, FR-035, SC-004, SC-011)
- [X] T051 [P] [US1] Add failing closed output-formalism, resolved analysis-policy, evidence-detail, loss-policy, and semantic identity mutation tests in `tests/ingest/production_ingest/test_analysis_policy.py` (FR-047-FR-051, SC-023)
- [X] T052 [P] [US1] Add failing exact token/EDU/sentence/paragraph mapping, source-anchor, fidelity, 512/8,192-token truncation, 128-EDU cap, tokenizer-offset alignment, unanalysed-suffix, and approximate-allocation tests in `tests/ingest/production_ingest/test_analysed_document.py` (FR-052-FR-053, FR-070, SC-017, SC-027)
- [X] T053 [P] [US1] Add failing segmentation, split, relation, nuclearity, confidence-kind, entropy, distribution, and decision-to-graph link tests in `tests/ingest/production_ingest/test_primary_inference_evidence.py` (FR-049-FR-055, SC-017-SC-018)
- [X] T054 [P] [US1] Add failing relation/nuclearity/concept/confidence before-and-after marker refinement tests in `tests/ingest/production_ingest/test_refinement_provenance.py` (FR-056, FR-063, SC-020)
- [X] T055 [P] [US1] Add failing eRST signal/candidate/edge/relation/joint-score/calibration/decoder-receipt and orphan-signal tests in `tests/ingest/production_ingest/test_erst_completion_evidence.py` (FR-057-FR-058, SC-019)
- [X] T056 [P] [US1] Add failing primary/segmenter/refiner/eRST/decoder/calibration/relation-inventory/ontology composite identity tests, including local-release versus loaded tokenizer/configuration/weight bytes and deliberate path/revision substitution, in `tests/ingest/production_ingest/test_composite_analysis_identity.py` (FR-059, FR-063, FR-069, SC-026)
- [X] T057 [P] [US1] Add failing local-result identity, complete local-to-global mapping, boundary/nuclear-spine input, warning, timing, and receipt-digest tests in `tests/ingest/production_ingest/test_recombination_receipt.py` (FR-061, SC-021)
- [X] T058 [P] [US1] Add failing validation policy/check/count/disposition/digest and required-check consistency tests in `tests/ingest/production_ingest/test_validation_receipt.py` (FR-060, SC-022)
- [X] T059 [P] [US1] Add deliberate decoded-span, score, boundary, refinement, signal-link, decoder-receipt, mapping, validation-check, fabricated-fallback, and graph-only-ingest substitution tests for the active ModernBERT backend and every handoff in `tests/ingest/production_ingest/test_backend_evidence_loss.py` (FR-064, FR-067-FR-070, SC-018, SC-025-SC-027)

### Implementation for User Story 1

- [X] T060 [US1] Implement `OutputFormalism`, `EvidenceDetailPolicy`, `AnalysisPolicy`, `AnalysisRequest`, public `ParserAnalysisResult`, `AnalysedDocument`, score/distribution, primary/eRST evidence, refinement, composite identity, recombination, and validation receipt contracts in `isanlp_rst/ingest/contracts/inference.py` (FR-047-FR-063, FR-068)
- [X] T061 [US1] Implement canonical `Parser.analyse_document()` and build the exact analysed token/EDU/boundary/mapping substrate from real tokenizer offsets; fail closed on unauthorized paragraph/parser truncation, EDU capping, dropped suffixes, missing alignment, fabricated midpoint/default decisions, sequential-offset fallback, or approximation in `isanlp_rst/parser.py`, `isanlp_rst/segmentation/transformer_segmenter.py`, `isanlp_rst/transformer_parser/predictor.py`, `isanlp_rst/model_loading/parser_input.py`, and `isanlp_rst/ingest/service.py` (FR-052-FR-053, FR-066, FR-068, FR-070)
- [X] T062 [US1] Preserve the already-complete decoded span depth plus segmentation boundary logits, selected splits, relation/nuclearity scores, entropy, and requested normalized distributions across the active ModernBERT path in `isanlp_rst/segmentation/transformer_segmenter.py`, `isanlp_rst/transformer_parser/`, and `isanlp_rst/parser.py` without changing inference mathematics (FR-049-FR-055, FR-064, FR-068)
- [X] T063 [US1] Preserve original and revised relation/nuclearity/concept/confidence plus marker/rule triggers in `isanlp_rst/relations/primer.py` and `isanlp_rst/english/relations/primer.py` as typed refinement records (FR-056, FR-063)
- [X] T064 [US1] Preserve detector signals, candidate identities, edge/relation probabilities, joint scores, calibration, accepted/rejected decisions, signal back-links, and the complete decoder receipt in `isanlp_rst/english/erst/completer.py`, `isanlp_rst/erst/candidates.py`, `isanlp_rst/erst/neural_scorer.py`, and `isanlp_rst/erst/decoder.py` (FR-057-FR-058)
- [X] T065 [US1] Load primary parser and segmenter tokenizer/configuration/weight bytes from the exact validated release, assemble every participating primary/segmenter/refiner/eRST/decoder/calibration/relation-inventory/ontology identity, and fail on identity-versus-runtime-byte contradiction in `isanlp_rst/parser.py`, `isanlp_rst/transformer_parser/predictor.py`, `isanlp_rst/model_loading/release.py`, `isanlp_rst/erst/checkpoint.py`, `isanlp_rst/ingest/service.py`, and `isanlp_rst/ontology/adapter.py` (FR-059, FR-063, FR-069, SC-026)
- [X] T066 [US1] Emit complete compact local-result identities, local-to-global maps, boundary/nuclear-spine inputs, decisions, warnings, and timings from `isanlp_rst/hierarchical/stitcher.py` and `isanlp_rst/ingest/service.py` as `RecombinationReceipt` (FR-061, SC-021)
- [X] T067 [US1] Implement stable check-by-check graph, anchor, evidence-link, component-identity, recombination, and cache validation receipts in `isanlp_rst/ingest/validation.py` (FR-060, SC-022)
- [X] T068 [US1] Construct both-endpoint primary/secondary relation anchors, supporting-signal anchors, and declared relation/confidence/calibration/ontology provenance in `isanlp_rst/ingest/service.py` and `isanlp_rst/ingest/validation.py` (FR-058, FR-062-FR-063)
- [X] T069 [US1] Resolve `AnalysisPolicy`, assemble `AnalysisRequest`, make production ingest consume and embed `ParserAnalysisResult` rather than reconstruct evidence from `RstAnalysis`, enforce output-formalism/evidence-level invariants, and include all semantic evidence in request/result/cache identity in `isanlp_rst/ingest/service.py`, `isanlp_rst/ingest/identity.py`, and `isanlp_rst/ingest/cache.py` (FR-047-FR-051, FR-066, FR-068)
- [X] T070 [US1] Export `ParserAnalysisResult` and the complete inference-evidence contract from `isanlp_rst.ingest`, expose the canonical parser operation from `isanlp_rst.Parser`, reconcile `isanlp_rst/ingest/public-surface.json`, and generate byte-identical schemas under `isanlp_rst/ingest/schemas/` (FR-002, FR-032, FR-039, FR-065, FR-068)
- [X] T071 [US1] Make T051-T059 pass and add negative public-surface assertions for tensors, embeddings, activations, unrestricted charts, training-only labels, workbench types, and archived DMRST/UniRST capabilities in `tests/ingest/production_ingest/test_backend_evidence_loss.py` and `test_public_surface.py` (FR-064-FR-071, SC-017-SC-027)
- [X] T072 [US1] Complete immutable, mutable, unidentified, and absent model identity mapping from the existing parser facade in `isanlp_rst/ingest/contracts/analysis.py` and `isanlp_rst/model_loading/release.py` without changing parser mathematics (FR-009, FR-024, FR-029)
- [X] T073 [US1] Assemble analysed and empty-primary semantic/execution evidence with the complete nested `PreparationOutcome` in `isanlp_rst/ingest/service.py` (FR-009-FR-010, FR-013-FR-014, FR-020)
- [X] T074 [US1] Implement primary RST-tree, eRST sufficient-signal/no-self-loop/existing-endpoint/unique-directed-pair, status, model/result identity, and multi-unit completeness validators in `isanlp_rst/ingest/validation.py` without rejecting formally permitted secondary-edge cycles, crossings, overlap, or unrestricted degree (FR-012-FR-013, FR-018, SC-002)
- [X] T075 [US1] Implement complete analysis-anchor construction and reconstructability validation in `isanlp_rst/ingest/service.py` and `isanlp_rst/ingest/validation.py` (FR-009, FR-012, SC-002)
- [X] T076 [US1] Implement analysis request/result semantic projections and identity relationships in `isanlp_rst/ingest/identity.py` (FR-011, FR-040-FR-041)
- [X] T077 [US1] Update `isanlp_rst/ingest/cache.py` to persist only fully validated canonical v2 outcomes and to bind request, result, and cache-entry identities atomically (FR-018-FR-021, FR-040)
- [X] T078 [US1] Rework multi-unit orchestration in `isanlp_rst/ingest/service.py` so internal partial unit outputs cannot escape or enter the success cache (FR-018, SC-008)
- [X] T079 [US1] Export the exact `AnalysisParser`, `ParserAnalysisResult`, outcome variants, identities, anchors, load/serialize functions, and canonical parser/ingest `analyse()` signatures from `isanlp_rst/ingest/__init__.py` and reconcile `isanlp_rst/ingest/public-surface.json` (FR-002, FR-032, FR-035, FR-068)
- [X] T080 [US1] Make all six source-form analysed/empty-primary and canonical round-trip fixtures pass in `tests/ingest/production_ingest/test_conformance_matrix.py` (FR-003, FR-013, FR-037-FR-038, SC-007)
- [X] T081 [US1] Make cached and uncached immutable requests produce byte-identical semantic payloads and digests in `tests/ingest/production_ingest/test_determinism.py` and `test_cache.py` (FR-040-FR-041, SC-008-SC-009)
- [X] T082 [US1] Make the installed-public-import consumer answer received/retained/transformed/analysed/excluded/model/cache questions solely from one result in `tests/ingest/production_ingest/test_public_consumer_adapter.py` (FR-010, FR-035, SC-004, SC-011)

**Checkpoint**: The core API product is independently usable and self-contained.

---

## Phase 6: User Story 3 - Diagnose Failures with Completed Evidence (Priority: P1)

**Goal**: Raise typed safe production failures that retain all and only genuine
completed-stage evidence and never disclose raw private text by default.

**Independent Test**: Induce acquisition, classification, preparation,
planning, inference, validation, assembly, persistence, and cache-retrieval
failures; verify stable category, retryability, cause, safe context, monotonic
evidence, rendering, canonical serialization, and reload.

### Tests for User Story 3

- [X] T083 [P] [US3] Add failing all-nine-stage failure taxonomy, stable-code, retryability, and causal-chain tests in `tests/ingest/production_ingest/test_failure_stages.py` (FR-015, FR-037, SC-005)
- [X] T084 [P] [US3] Add failing monotonic completed-evidence tests for no evidence, acquisition, inventory, preparation, inference, validation, and assembly variants in `tests/ingest/production_ingest/test_completed_evidence.py` (FR-015-FR-016, SC-005)
- [X] T085 [P] [US3] Add failing default `str`/`repr`, nested evidence redaction, private-marker exclusion, and explicit diagnostic opt-in tests in `tests/ingest/production_ingest/test_failure_privacy.py` (FR-017, SC-005)
- [X] T086 [P] [US3] Add failing safe and diagnostic failure canonical serialization, schema, digest, and reload tests in `tests/ingest/production_ingest/test_failure_serialization.py` (FR-017, FR-019-FR-021)
- [X] T087 [P] [US3] Add failing no-parser, missing-format-extra, unavailable-release, malformed-source, corrupt-cache, and persistence-failure tests in `tests/ingest/production_ingest/test_provider_unavailability.py` (FR-014-FR-015, FR-031, FR-037)

### Implementation for User Story 3

- [X] T088 [US3] Complete stage-specific `ProductionFailure`, stable category/code, retryability, safe context/cause, and monotonic completed-evidence validation in `isanlp_rst/ingest/contracts/failure.py` (FR-015-FR-016)
- [X] T089 [US3] Implement typed safe redaction of nested completed evidence and separately discriminated diagnostic failure records in `isanlp_rst/ingest/contracts/failure.py` (FR-017, FR-019)
- [X] T090 [US3] Implement safe default and explicit diagnostic failure projection in `isanlp_rst/ingest/serialization.py` without serializing traceback frames, locals, arbitrary exception strings, environment values, or private paths (FR-017, FR-019-FR-020)
- [X] T091 [US3] Translate acquisition, classification, preparation, planning, inference, validation, and assembly exceptions with explicit `raise ... from ...` chaining in `isanlp_rst/ingest/service.py` (FR-014-FR-016)
- [X] T092 [US3] Translate missing optional format distributions into typed provider-unavailable failures in `isanlp_rst/ingest/prepare.py` without exposing `ModuleNotFoundError` (FR-014-FR-015, FR-031)
- [X] T093 [US3] Translate cache retrieval, corruption, and persistence errors while preserving request/outcome evidence permitted by stage in `isanlp_rst/ingest/cache.py` (FR-015-FR-018)
- [X] T094 [US3] Make `ProductionIngestError.__str__`, `repr`, attributes, and exception chaining safe and inspectable in `isanlp_rst/ingest/contracts/failure.py` (FR-015, FR-017)
- [X] T095 [US3] Export failure, diagnostic-policy, retryability, stage, and safe persisted record types from `isanlp_rst/ingest/__init__.py` and reconcile them in `isanlp_rst/ingest/public-surface.json` (FR-002, FR-032)
- [X] T096 [US3] Make every induced failure retain all and only completed evidence in `tests/ingest/production_ingest/test_failure_stages.py` and `test_completed_evidence.py` (FR-016, SC-005)
- [X] T097 [US3] Make default failure rendering and serialized bytes exclude every private-marker fixture while explicit diagnostic records remain unambiguous in `tests/ingest/production_ingest/test_failure_privacy.py` and `test_failure_serialization.py` (FR-017, SC-005)

**Checkpoint**: Failure handling is as complete and contract-governed as success.

---

## Phase 7: User Story 5 - Discover Capabilities Before Expensive Work (Priority: P2)

**Goal**: Describe source forms, operations, contract versions, extras, parser
identity, constraints, persistence, and cache eligibility offline without
loading adapters, models, weights, research code, or a network.

**Independent Test**: Query capabilities in a core-only offline process for no
parser, immutable release, mutable parser, unidentified parser, and missing
format extras; compare predictions with representative accepted/rejected calls.

### Tests for User Story 5

- [X] T098 [P] [US5] Add failing offline/no-network/no-model/no-adapter-import capability tests in `tests/ingest/production_ingest/test_capabilities_offline.py` (FR-023, FR-030-FR-031, SC-010)
- [X] T099 [P] [US5] Add failing all-source-form availability, required-extra, missing-distribution, media-type, and operation prediction tests in `tests/ingest/production_ingest/test_source_form_capabilities.py` (FR-023, FR-031)
- [X] T100 [P] [US5] Add failing immutable, mutable, unidentified, and not-configured parser identity/cache-eligibility plus output-formalism/evidence-capability tests that reject archived DMRST/UniRST claims and any advertised path lacking canonical `ParserAnalysisResult` support in `tests/ingest/production_ingest/test_parser_capabilities.py` (FR-023-FR-024, FR-047, FR-059, FR-066, FR-068-FR-071)
- [X] T101 [P] [US5] Add failing capability canonical serialization, schema, compatibility, and reload tests in `tests/ingest/production_ingest/test_capability_serialization.py` (FR-019-FR-024)

### Implementation for User Story 5

- [X] T102 [US5] Implement declarative installed-distribution and optional-extra probes that do not import adapters in `isanlp_rst/ingest/capabilities.py` (FR-023, FR-030-FR-031)
- [X] T103 [US5] Implement model-free `describe_capabilities(parser=None)` including package/write/read versions, lifecycle kinds, source forms, guarantees, parser state, only executable active ModernBERT formalisms/evidence levels, evidence availability reasons, exact-runtime-identity support, and cache eligibility in `isanlp_rst/ingest/capabilities.py` (FR-023-FR-024, FR-047, FR-066, FR-068-FR-071)
- [X] T104 [US5] Implement `ProductionIngestor.capabilities()` using the configured parser descriptor without inference or model resolution in `isanlp_rst/ingest/service.py` (FR-023-FR-024)
- [X] T105 [US5] Export capability contracts and operations from `isanlp_rst/ingest/__init__.py` and reconcile exact symbols/statuses in `isanlp_rst/ingest/public-surface.json` (FR-002, FR-023, FR-032)
- [X] T106 [US5] Make core import and capability discovery pass with Docling, DocLang, and Markdown distributions absent in `tests/ingest/production_ingest/test_capabilities_offline.py` (FR-031, SC-010)
- [X] T107 [US5] Make capability predictions agree with representative prepare/analyse acceptance and typed rejection in `tests/ingest/production_ingest/test_source_form_capabilities.py` and `test_parser_capabilities.py` (FR-023-FR-024)
- [X] T108 [US5] Make capability records serialize/reload canonically without changing semantic identity in `tests/ingest/production_ingest/test_capability_serialization.py` (FR-019-FR-021)

**Checkpoint**: Consumers can decide whether and how to call the provider before
expensive work.

---

## Phase 8: Polish and Cross-Cutting Release Readiness

**Purpose**: Reconcile documentation, conformance, performance, scope, and
quality before immutable source bytes are selected for US4 certification.

- [X] T109 [P] Generate and reconcile the exact 5.0.0 public symbol, canonical parser-result/signature, CLI/local-HTTP projection, enum, status, error, schema, analysis-policy/evidence, active capability, and compatibility tables in `docs/production-api-contract.md` from `isanlp_rst/ingest/public-surface.json` and runtime inspection (FR-002, FR-032, FR-039, FR-047-FR-073, SC-006, SC-025-SC-028)
- [X] T110 [P] Update the complete preparation, analysed-substrate, primary/eRST evidence, refinement, recombination, validation, retained-content, capability, failure, cache, and canonical persistence workflows in `docs/production-source-ingest.md` using exact runtime exports (FR-032, FR-047-FR-066, SC-004, SC-017-SC-024)
- [X] T111 [P] Update core/formats optional boundaries, model-free discovery, immutable/mutable model identity, production/offline exclusions, and installed provenance in `docs/production-offline-boundary.md` (FR-023-FR-025, FR-030-FR-031)
- [X] T112 Update Feature 004 Pixi tasks and version-derived artifact paths in `pyproject.toml` so `production-api-contract`, determinism, performance, build, artifact validation, and clean-install commands execute the real implementation (FR-036-FR-039)
- [X] T113 [P] Add failing CLI/local-HTTP conformance tests for all-six-source-form routing, one-inference execution, canonical semantic-byte parity with Python, presentation-projection labelling, typed capability/health output, and safe failure serialization in `tests/ingest/production_ingest/test_cli_contract.py` and `tests/ingest/production_ingest/test_local_http_contract.py` (FR-072-FR-073, SC-028)
- [X] T114 Route `isanlp-rst parse` and any retained loopback-only `serve` endpoint through `SourceArtifact`, explicit source identity, immutable model-store/release selection, closed analysis-policy arguments, `ProductionIngestor`, `ParserAnalysisResult`, `describe_capabilities()`, and canonical success/failure serialization in `isanlp_rst/cli.py`; remove duplicate inference, ignored structured-input detection, independent JSON schema, non-loopback binding, count-only result claims, and raw exception strings, then make T113 pass (FR-001, FR-003, FR-017, FR-030, FR-032, FR-068, FR-072-FR-073, SC-028)
- [X] T115 Execute every source-valid API example, direct `ParserAnalysisResult` assertion, graph-projection equivalence assertion, loaded-component receipt assertion, and installed-public-import assertion from `specs/004-production-api-contract/quickstart.md`, record the artifact-, receipt-, and promotion-dependent sections as deferred until T141, and correct only authoritative runtime/docs drift before source selection (FR-032, FR-035, FR-068-FR-073)

**Checkpoint**: Runtime documentation and source-valid consumer examples are
reconciled. Final scope/SOTA and canonical source-quality evidence are generated
in US4 only after release tooling and evidence contracts exist and before the
source release commit.

---

## Phase 9: User Story 4 - Stable Contract and Durable Distribution (Priority: P1, Final Certification)

**Goal**: Produce and certify immutable 5.0.0 wheel/sdist bytes, tracked under
`dist/5.0.0/`, with a canonical receipt that connects contract, source,
environment, artifacts, verification, and second-machine proof.

**Independent Test**: On the second supported development machine, first verify
the exact candidate-artifact bytes without rebuilding; after certification,
fetch the release tag, verify the final receipt and every named digest, install
the same wheel, and run complete installed conformance and quickstart acceptance.

### Tests for User Story 4

- [X] T116 [P] [US4] Add failing package/runtime/filename/metadata/contract-version and immutable-version tests in `tests/production_boundary/test_release_metadata.py` (FR-021-FR-022, SC-013)
- [X] T117 [P] [US4] Add failing strict release-receipt and release-evidence lifecycle tests covering schema/version fields, allowed creation states, source/build/artifact/verification fields, canonical bytes, detached digest, and rejection of future/self commit identities in `tests/production_boundary/test_release_receipt.py` (FR-043-FR-044, SC-016)
- [X] T118 [P] [US4] Add failing exact-commit archive, deterministic provenance injection, via-sdist double-build, and byte-identical artifact tests in `tests/production_boundary/test_reproducible_build.py` (FR-042-FR-044)
- [X] T119 [P] [US4] Add failing wheel `RECORD`, package-content, console-entry-point/public-surface, forbidden-content, artifact-hash, receipt, and source-revision tests in `tests/production_boundary/test_artifact_validation_v2.py` (FR-039, FR-042-FR-044, FR-072-FR-073, SC-016, SC-028)
- [X] T120 [P] [US4] Add failing isolated core/formats environment, `python -I`, checkout-exclusion, offline acceptance, complete installed parser/ingest/CLI/local-HTTP analysis-evidence surface, exact loaded-component identity, active-capability truth, forbidden-internal negative surface, `pip check`, and retained `pip inspect` tests in `tests/production_boundary/test_clean_install_v2.py` (FR-031, FR-035-FR-036, FR-047-FR-073, SC-010, SC-017-SC-028)

### Implementation and certification for User Story 4

- [X] T121 [US4] Remove the blanket `dist/` ignore while keeping temporary build roots outside the repository in `.gitignore` and `tools/production_boundary/build.py` (FR-042)
- [X] T122 [US4] Make `importlib.metadata.version("isanlp_rst")` the runtime package-version authority and remove the duplicate hard-coded version in `isanlp_rst/_version.py` and `isanlp_rst/__init__.py` (FR-022)
- [X] T123 [P] [US4] Implement strict versioned canonical contracts for `isanlp_rst.release_receipt` 1.0.0 and every JSON record governed by the release evidence lifecycle in `tools/production_boundary/contracts.py` (FR-043-FR-044)
- [X] T124 [P] [US4] Implement deterministic build-provenance generation/injection without artifact self-reference in `tools/production_boundary/build.py` and runtime resource loading in `isanlp_rst/_provenance.py` (FR-043-FR-044)
- [X] T125 [US4] Implement clean-status/source-commit/tree/archive checks, commit-derived `SOURCE_DATE_EPOCH`, PyPA build reports, via-sdist wheel builds, and two-build hash equality in `tools/production_boundary/build.py` (FR-042-FR-044)
- [X] T126 [US4] Implement wheel/sdist contents, `RECORD`, metadata/version, packaged provenance, source/archive, receipt, verification, and forbidden-offline-content validation in `tools/production_boundary/artifacts.py` and `tools/production_boundary/__main__.py` (FR-036, FR-042-FR-044)
- [X] T127 [P] [US4] Implement genuine isolated core and formats installs with exact-wheel paths, `python -I`, temporary working directories, checkout exclusion, network-disabled acceptance, `pip check`, and retained `pip inspect` evidence in `tools/production_boundary/clean_install.py` and `tools/production_boundary/installed_acceptance.py` (FR-031, FR-035-FR-036)
- [X] T128 [US4] Make T116-T120 pass with deterministic test fixtures and local build roots, without claiming validation of the not-yet-selected release artifacts, in `tests/production_boundary/` (FR-036-FR-044)
- [X] T129 [US4] Run the Feature 004 focused tests plus Ruff and Pyright through Pixi and write canonical results through the T123 evidence contract to `specs/004-production-api-contract/evidence/pre-release-quality.json` (FR-036-FR-038)
- [X] T130 [US4] Run the one-warm-up/five-run preparation performance gate and write canonical per-run results through the T123 evidence contract to `specs/004-production-api-contract/evidence/performance.json` (SC-014)
- [X] T131 [US4] Audit the final source diff, including T121-T127, for consumer-specific fields, restored format-specific APIs, research/offline leakage, forbidden scientific internals, model architecture changes, inference-mathematics changes, unexplained backend evidence loss, fabricated decisions, runtime-identity contradictions, archived capability claims, and independent CLI/local-HTTP semantics, then revalidate that the dated comparison in `specs/004-production-api-contract/research.md` covers every FR-045 practice with zero unclassified gaps; record both dispositions in `specs/004-production-api-contract/evidence/scope-audit.md` (FR-025, FR-029-FR-030, FR-033-FR-034, FR-045-FR-046, FR-064-FR-073, SC-015, SC-018, SC-024-SC-028)
- [X] T132 [US4] Run the complete source-only lint, Pyright, Markdown, pytest, Feature 004 conformance, canonical parser-result, component-byte identity, capability truth, CLI/local-HTTP parity, decision-evidence loss, determinism, and performance gates, reconcile T129-T131, and persist canonical aggregate results and evidence digests in `specs/004-production-api-contract/evidence/source-release-gates.json`, containing no artifact or clean-install claims (FR-036-FR-041, FR-047-FR-073, SC-006-SC-009, SC-014, SC-017-SC-028)
- [ ] T133 [US4] Create the clean source release commit containing the final `isanlp_rst/`, `tools/`, `tests/`, `docs/`, `pyproject.toml`, `pixi.lock`, and `specs/004-production-api-contract/` source candidate after T132 passes (FR-043-FR-044)
- [ ] T134 [US4] Generate canonical `specs/004-production-api-contract/evidence/source-release.json` after T133 exists, recording the exact source commit, tree, archive, and commit-derived `SOURCE_DATE_EPOCH` identities without claiming its own future commit identity (FR-043-FR-044)
- [ ] T135 [US4] Build wheel and sdist twice from the named T133 source commit and select only byte-identical `dist/5.0.0/isanlp_rst-5.0.0-py3-none-any.whl` and `dist/5.0.0/isanlp_rst-5.0.0.tar.gz` artifacts (FR-042-FR-044)
- [ ] T136 [US4] Run artifact validation, isolated core/formats installs, installed conformance, and both production-boundary gates against the exact T135 bytes, then persist canonical local results in `specs/004-production-api-contract/evidence/artifact-verification.json` (FR-031, FR-035-FR-044, SC-010, SC-013, SC-016)
- [ ] T137 [US4] Commit the T135 wheel and sdist under `dist/5.0.0/` plus `specs/004-production-api-contract/evidence/source-release.json` and `specs/004-production-api-contract/evidence/artifact-verification.json` as one untagged candidate-artifact commit, without creating any record that claims the candidate commit identity before it exists (FR-042-FR-044)
- [ ] T138 [US4] On the second supported development machine, check out the T137 candidate-artifact commit, verify and install the exact committed wheel without rebuilding, run installed conformance, and return canonical `specs/004-production-api-contract/evidence/second-machine-candidate-verification.json` identifying that already-existing commit and artifact bytes (FR-036, FR-042-FR-044)
- [ ] T139 [US4] Generate canonical `dist/5.0.0/release-receipt.json` and `dist/5.0.0/release-receipt.sha256` from the T133 source, T135 artifacts, T136 local evidence, and T138 candidate-verification evidence, then require zero receipt, artifact, or evidence-digest mismatch (FR-043-FR-044, SC-016)
- [ ] T140 [US4] Commit `specs/004-production-api-contract/evidence/second-machine-candidate-verification.json`, `dist/5.0.0/release-receipt.json`, and `dist/5.0.0/release-receipt.sha256` as the certification commit, push it, tag that unchanged-artifact commit for 5.0.0, push the tag, and verify local/remote commit, tag, and artifact-hash parity without writing self-referential certification data (FR-022, FR-042-FR-044, SC-013, SC-016)
- [ ] T141 [US4] On the second supported development machine, fetch and check out the T140 release tag, verify the detached receipt and every named artifact/evidence digest, install the exact tagged wheel, run installed conformance and every deferred `specs/004-production-api-contract/quickstart.md` assertion without rebuilding, and return canonical `specs/004-production-api-contract/evidence/release-certification.json` identifying the existing source, candidate, certification, tag, and remote state (FR-032, FR-035-FR-036, FR-042-FR-044, SC-012, SC-016)
- [ ] T142 [US4] Commit and push T141 as a post-certification evidence-only commit, then prove the 5.0.0 tag still resolves to T140, `git ls-files dist/5.0.0` lists exactly four promoted files, all four hashes are unchanged, and local/remote branch and tag identities agree (FR-022, FR-042-FR-044, SC-012-SC-013, SC-016)

**Checkpoint**: The repository contains one immutable, receipt-governed 5.0.0
wheel/sdist release whose candidate bytes and final tagged receipt another
machine has independently verified without rebuilding; its post-certification
evidence does not move the release tag or change certified bytes.

---

## Dependencies and Execution Order

### Phase dependencies

- **Phase 1** has no implementation dependency.
- **Phase 2** depends on Phase 1 and blocks every user story.
- **US6 (Phase 3)** depends on Phase 2 because retained content uses the shared
  contract envelope; it enables complete US2 evidence.
- **US2 (Phase 4)** depends on US6 because every preparation outcome must
  account for retained material.
- **US1 (Phase 5)** depends on US2 because analysis embeds the complete
  preparation outcome.
- **US3 (Phase 6)** depends on US2 and US1 because failures preserve evidence
  from completed preparation, inference, validation, and assembly stages.
- **US5 (Phase 7)** depends only on Phase 2 for its contracts, but completes
  before release because core clean-install acceptance exercises discovery.
- **Phase 8** depends on US1, US2, US3, US5, and US6.
- **US4 (Phase 9)** depends on every preceding phase because it certifies their
  exact combined bytes. T138 and T141 require access to the second supported
  development machine; T140 and T142 require the configured Git remote.

### User-story dependency graph

```text
Foundation
├── US6 retained evidence -> US2 preparation -> US1 analysis -> US3 failures
└── US5 capability discovery

US1 + US2 + US3 + US5 + US6 -> release readiness -> US4 distribution
```

### Within each user story

- Fixtures and tests are written first and observed failing for the intended
  missing behaviour.
- Contract types precede lifecycle services.
- Lifecycle services precede cross-field validation completion.
- Validation must pass before success cache writes.
- Public exports, schemas, manifest, and docs reconcile before installed tests.
- No artifact is built until the exact source candidate passes all gates.
- No final receipt or tag is created until the committed candidate bytes pass
  second-machine verification.
- No release is complete until the second machine verifies the tagged receipt
  and the post-certification evidence commit proves the tag and certified bytes
  remained unchanged.

## Parallel Opportunities

### User Story 6

After T020 fixtures exist, T021-T023 may run in parallel. T026 and T027 may run
in parallel after T024; T028-T030 then reconcile the shared inventory.

### User Story 2

T031-T035 may run in parallel against the agreed contract. Implementation is
mostly sequential because `prepare.py`, `validation.py`, and `service.py` build
one evidence pipeline.

### User Story 1

T045-T059 may run in parallel. T060 establishes the evidence contract;
T061-T068 then preserve independent producer and receipt paths before T069-T082
assemble, validate, persist, export, and exercise the complete outcome.

### User Story 3

T083-T087 may run in parallel. T088-T090 establish the failure value and
serialization path before service/cache translation in T091-T094.

### User Story 5

T098-T101 may run in parallel. T102-T104 are ordered; T105-T108 validate the
public installed boundary.

### User Story 4

T116-T120 may run in parallel. T123, T124, and T127 touch different components
after their tests exist; source selection, artifact construction, certification,
and post-certification proof T132-T142 are strictly sequential.

## Parallel Execution Examples

```text
US6: T021 representation tests | T022 structure tests | T023 disposition tests
US2: T031 outcome tests | T032 planning tests | T033 empty tests | T034 validation tests | T035 identity tests
US1: T045-T050 outcome/graph/anchor/atomicity/identity/consumer tests | T051-T059 policy/substrate/decision/refinement/eRST/component/recombination/validation/loss tests
US3: T083 stage tests | T084 evidence tests | T085 privacy tests | T086 serialization tests | T087 unavailability tests
US5: T098 offline tests | T099 source-form tests | T100 parser tests | T101 serialization tests
US4: T116 metadata tests | T117 receipt tests | T118 build tests | T119 artifact tests | T120 install tests
```

## Implementation Strategy

### Suggested MVP

The smallest honest MVP is **Phase 1 + Phase 2 + US6 + US2 + US1**. US1 cannot
be self-contained if retained evidence or preparation remains incomplete.
Validate the resulting complete analysis outcome independently before adding
failure, capability, and distribution certification.

### Incremental delivery

1. Complete setup and shared contract/persistence foundations.
2. Deliver rich retained evidence (US6).
3. Deliver complete preparation-only use (US2).
4. Deliver complete validated analysis (US1/MVP).
5. Deliver typed completed-stage failure evidence (US3).
6. Deliver offline capability discovery (US5).
7. Reconcile docs, gates, and scope.
8. Certify the immutable cross-machine distribution (US4).

### Solo-local execution

This is one-person local work. `[P]` marks only technically independent tasks
that may be interleaved or delegated by an explicitly requested agent workflow;
it does not introduce team process, CI infrastructure, or enterprise controls.

## Notes

- All commands run through the repository's locked Pixi environments.
- Every touched Python file must leave strict Pyright, Ruff, and tests truthful;
  no suppression or weakened assertion is permitted.
- If T001 finds Docling/DocLang drift, remediate it before T025-T027 and update
  fixtures/docs in the same pass.
- Runtime models own fields and types; `public-surface.json` owns membership and
  support classification; schemas and documentation are checked projections.
- `dist/5.0.0/` contains promoted immutable release content only; temporary
  build roots remain outside the repository.
- Check off a task only after its named evidence has been observed.
