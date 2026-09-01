# Tasks: ModernBERT Pure Transformer Discourse Parser Release & Operational Certification

**Input**: Design documents from `specs/005-modernbert-production-release/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Spec Kit structure tracking

- [x] T001 Initialize Spec Kit feature package in `specs/005-modernbert-production-release/`
- [x] T002 Update `.specify/feature.json` to track active feature `005-modernbert-production-release`
- [x] T003 [P] Add ModernBERT parser training to offline command suite in `workbench/smoke.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data authority and treebank parsing infrastructure that MUST be complete before ANY user story can proceed

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement recursive `.dis` LISP binary tree parser in `workbench/training/modern/gum_dataset.py`
- [x] T005 [P] Implement 32-to-15 coarse relation taxonomy and nuclearity mapping in `workbench/training/modern/gum_dataset.py`
- [x] T006 [P] Implement subword token alignment with `AutoTokenizer.from_pretrained("answerdotai/ModernBERT-base")` in `workbench/training/modern/gum_dataset.py`
- [x] T007 Ingest all 301 documents across `workbench/corpora/gum-v12.1.0/splits.md` (`train: 211`, `dev: 32`, `test: 32`, `test2: 26`)
- [x] T008 [P] Write unit tests in `tests/unit/test_gum_dataset.py` verifying tree parsing, mapping, and target matrices

**Checkpoint**: Foundation ready - GUM 12.1.0 corpus authority verified with 6/6 tests passing.

---

## Phase 3: User Story 1 - Document-Level Multi-Task Training on GUM 12.1.0 (Priority: P1) 🎯 MVP

**Goal**: Train `PureTransformerParsingNet` with mathematically finite loss ($\mathcal{L} > 0.0$) and non-NaN gradients across 211 GUM training documents

**Independent Test**: Run `pytest tests/unit/test_parsing_net_stability.py` and verify loss $> 0.0$ and finite parameter gradients

### Tests for User Story 1

- [x] T009 [P] [US1] Unit test for non-NaN loss and finite gradients in `tests/unit/test_parsing_net_stability.py`

### Implementation for User Story 1

- [x] T010 [P] [US1] Fix gradient stability in `TransformerSpanAttentionPooling` in `isanlp_rst/transformer_parser/span_encoder.py`
- [x] T011 [P] [US1] Implement robust multi-task loss ($\text{BCE} + \text{CE}_{\text{nuc}} + 1.2 \cdot \text{CE}_{\text{rel}}$) in `isanlp_rst/transformer_parser/model.py`
- [x] T012 [US1] Implement `ModernTreeParserTrainer` with AdamW and gradient accumulation ($K=16$) in `workbench/training/modern/train_tree_parser.py`
- [x] T013 [US1] Execute full multi-task training across 211 GUM training documents via `scripts/train_modernbert_treebank.py`

**Checkpoint**: At this point, User Story 1 is fully functional and produces trained weights in `models/modernbert_v1/model.safetensors`.

---

## Phase 4: User Story 2 - Dynamic CKY Evaluation & Parseval Scoring (Priority: P2)

**Goal**: Dynamically evaluate model performance on Dev (32 docs), Test (32 docs), and GENTLE Test2 (26 docs) partitions using projective CKY decoding and standard Parseval conventions

**Independent Test**: Run `scripts/benchmark_modernbert.py` against held-out GUM test gold trees

### Implementation for User Story 2

- [x] T014 [P] [US2] Implement CKY dynamic tree decoding and micro-averaged Parseval scoring via `StandardParsevalScorer` in `workbench/training/modern/train_tree_parser.py`
- [x] T015 [US2] Record dynamic validation metrics on Dev (32 docs), Test (32 docs), and GENTLE Test2 (26 docs) into `models/modernbert_v1/training_receipt.json`
- [x] T016 [US2] Modernize `scripts/benchmark_modernbert.py` to evaluate held-out gold trees via `Parser.from_model_release()`

**Checkpoint**: User Story 2 dynamically validates parser accuracy against independent held-out partitions.

---

## Phase 5: User Story 3 - Immutable Scientific Provenance Ledger (Priority: P3)

**Goal**: Record the complete execution provenance of every training and evaluation session into an append-only ledger

**Independent Test**: Verify that `workbench/experiments/central_ledger.jsonl` contains immutable records with matching Git SHA and lockfile hash

### Implementation for User Story 3

- [x] T017 [US3] Implement append-only JSONL ledger writing in `workbench/training/modern/train_tree_parser.py`
- [x] T018 [US3] Verify ledger entry generation during training and benchmark execution in `workbench/experiments/central_ledger.jsonl`

**Checkpoint**: User Story 3 captures full execution provenance for all experimental runs.

---

## Phase 6: User Story 4 - Atomic Release Packaging & Manifest Promotion (Priority: P4)

**Goal**: Package candidate model files and cryptographic manifest into dual storage release targets

**Independent Test**: Run `python -m workbench.promotion.modernbert --candidate-dir models/modernbert_v1` and verify `release-manifest.json` SHA-256 validation

### Implementation for User Story 4

- [x] T019 [P] [US4] Implement `workbench/promotion/modernbert.py` with runtime role validation (`encoder_config`, `parser_state`, `relation_inventory`, `tokenizer`)
- [x] T020 [US4] Generate canonical `release-manifest.json` with cryptographic SHA-256 byte digests
- [x] T021 [US4] Promote release candidate to dual storage targets: in-tree `models/model-releases/` and local cache `~/.cache/isanlp_rst/model-releases/`

**Checkpoint**: Release candidate is packaged, validated, and immutable in model stores.

---

## Phase 7: User Story 5 - Clean-Room Boundary Certification (Priority: P5)

**Goal**: Certify `isanlp_rst 5.0.0` clean-room installation and inference with external network access disabled across all source formats

**Independent Test**: Run `clean_install.py --full --model-store models/model-releases --release-id <promoted_id>` in isolated `production` environment

### Implementation for User Story 5

- [x] T022 [US5] Run `clean_install.py --full --model-store models/model-releases --release-id <promoted_id>` in isolated `production` Pixi environment
- [x] T023 [US5] Verify zero network access (`ISANLP_RST_NETWORK_DISABLED=1`) with genuine ModernBERT inference on raw text, Docling ASTs, DocLang XML ASTs, and Markdown emitting `{"valid": true}`

**Checkpoint**: Release boundary certified for isolated production deployment.

---

## Phase 8: User Story 6 - Baseline Comparison & Benchmark Reporting (Priority: P6)

**Goal**: Scientifically quantify ModernBERT performance against historical DMRST and UniRST baselines

**Independent Test**: Run `scripts/benchmark_modernbert.py` and review comparative metric tables

### Implementation for User Story 6

- [x] T024 [US6] Execute `scripts/benchmark_modernbert.py --release-id <promoted_id>` on held-out GUM Test and Test2
- [x] T025 [US6] Generate comparative Parseval matrix contrasting ModernBERT against published DMRST and UniRST results

**Checkpoint**: Baseline comparison complete with empirical superiority demonstrated.

---

## Phase 9: Polish & Cross-Cutting Quality

**Purpose**: Cross-cutting code quality and zero-stub elimination

- [x] T026 [P] Replace active `drawTree()` pass and file mapping stubs in `workbench/corpus/dmrst/data.py` and `workbench/corpus/unirst/data.py`
- [x] T027 [P] Modernize `scripts/bench.py`, `scripts/docling_rst_quality_check.py`, and `scripts/docling_long_input_determinism.py`
- [x] T028 Run `quickstart.md` validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Complete (No dependencies)
- **Foundational (Phase 2)**: Complete (GUM 12.1.0 data authority established)
- **User Story 1 (Phase 3)**: Active training in progress (T013)
- **User Story 2 (Phase 4)**: Depends on US1 (evaluates trained weights)
- **User Story 3 (Phase 5)**: Integrates with US1 and US2 (ledger tracking)
- **User Story 4 (Phase 6)**: Depends on US2 (packages verified checkpoint)
- **User Story 5 (Phase 7)**: Depends on US4 (certifies promoted release in clean-room)
- **User Story 6 (Phase 8)**: Depends on US4 promotion
- **Polish (Phase 9)**: Cross-cutting verification and validation

### User Story Dependencies

- **US1 (P1)**: Foundation for model weights; no dependency on other stories.
- **US2 (P2)**: Consumes trained weights from US1.
- **US3 (P3)**: Records ledger entries from US1/US2/US6.
- **US4 (P4)**: Consumes evaluated checkpoint from US2.
- **US5 (P5)**: Consumes promoted release from US4.
- **US6 (P6)**: Consumes promoted release from US4.

### Parallel Opportunities

- Foundational tasks marked [P] executed in parallel.
- Unit tests and span encoder stability fixes in US1 run in parallel.
- Promotion script implementation (T019) and benchmark modernization (T016) run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (GUM 12.1.0 data authority)
3. Complete Phase 3: User Story 1 (Train model with finite loss)
4. **STOP and VALIDATE**: Verify loss and gradients independently

### Incremental Delivery

1. Foundation verified (6/6 tests passing)
2. US1: Model weights trained
3. US2: Dynamic CKY evaluation passes Parseval quality gates
4. US3: Provenance ledger updated
5. US4: Release promoted and cryptographically validated
6. US5: Clean-room boundary certified in `production` environment with network disabled
7. US6: Baseline comparative benchmarks generated
