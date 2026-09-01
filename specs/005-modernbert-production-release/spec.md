# Feature Specification: ModernBERT Pure Transformer Discourse Parser Release & Operational Certification

**Feature Branch**: `005-modernbert-production-release`  
**Created**: 2026-08-30  
**Status**: In Review  
**Input**: User description: "ModernBERT Pure Transformer Discourse Parser Release & Operational Certification"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Document-Level Multi-Task Training on GUM 12.1.0 (Priority: P1)

As a machine learning engineer, I train `PureTransformerParsingNet` on the 211 authoritative GUM training documents so that the model learns joint neural representations for constituent span boundaries, nuclearity, and coarse relations across document context up to 8,192 subwords.

**Why this priority**: Core foundation of the modern parser. Without stable multi-task training on authoritative data, no downstream evaluation, packaging, or release is possible.

**Independent Test**: Can be trained independently and tested via `tests/unit/test_parsing_net_stability.py` and `tests/unit/test_gum_dataset.py`, verifying finite loss ($\mathcal{L} > 0.0$), non-NaN parameter gradients, and clean subword token alignment.

**Acceptance Scenarios**:

1. **Given** 211 authoritative GUM training `.dis` files in `workbench/corpora/gum-v12.1.0/`, **When** `GUMTreebankDataset` parses the trees and aligns EDUs using the ModernBERT fast tokenizer, **Then** all 211 documents parse without unmapped relations or token alignment failures.
2. **Given** `PureTransformerParsingNet` with `answerdotai/ModernBERT-base` encoder, **When** forward and backward optimization executes with multi-task loss $\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{split}} + \mathcal{L}_{\text{nuc}} + 1.2 \cdot \mathcal{L}_{\text{rel}}$, **Then** loss remains strictly positive and finite ($> 0.0$) and parameter gradients contain zero NaN or infinite values across all training steps.
3. **Given** long documents up to 8,192 subwords, **When** Rotary Position Embeddings (RoPE) and masked attention pooling encode EDU spans, **Then** span representations are generated without division-by-zero or gradient overflow.

---

### User Story 2 - Dynamic CKY Evaluation & Parseval Scoring (Priority: P2)

As an evaluation engineer, I evaluate parser accuracy across development (32 docs), held-out in-domain test (32 docs), and out-of-domain GENTLE test2 (26 docs) partitions using projective CKY chart decoding and standard Parseval conventions.

**Why this priority**: Validates parser quality against independent ground truth using standard discourse parsing metrics without circular self-benchmarking or hardcoded scores.

**Independent Test**: Can be evaluated on development and test splits via `workbench/training/modern/train_tree_parser.py` and `scripts/benchmark_modernbert.py`, computing micro-averaged Parseval scores from decoded trees.

**Acceptance Scenarios**:

1. **Given** a trained model checkpoint and 32 development documents, **When** CKY chart parsing decodes optimal projective binary discourse trees, **Then** `StandardParsevalScorer` calculates exact micro-averaged Precision, Recall, and F1 across Span, Nuclearity, Relation, and Full tree criteria from scratch.
2. **Given** quantitative release gates, **When** evaluation completes on the development partition, **Then** the parser meets or exceeds the target thresholds: Span F1 $\ge 82.0\%$, Nuclearity F1 $\ge 68.0\%$, Relation F1 $\ge 55.0\%$, and Full F1 $\ge 52.0\%$.
3. **Given** in-domain test (32 docs) and out-of-domain GENTLE test2 (26 docs), **When** held-out benchmarking runs, **Then** genre-specific and out-of-domain Parseval metrics and per-relation F1 scores across all 15 coarse relations are recorded.

---

### User Story 3 - Immutable Scientific Provenance Ledger (Priority: P3)

As a research engineer, I record the complete execution provenance of every training, validation, and benchmarking run into an append-only ledger so that all scientific results are 100% reproducible and auditable.

**Why this priority**: Ensures scientific rigor, traceability, and reproducibility across experiments and release candidates.

**Independent Test**: Run a training or benchmark session and verify that `workbench/experiments/central_ledger.jsonl` contains an immutable record with matching Git commit SHA, `pixi.lock` hash, hardware descriptor, hyperparameters, and evaluation metrics.

**Acceptance Scenarios**:

1. **Given** a completed training or evaluation run, **When** provenance recording triggers, **Then** an immutable JSONL line is appended to `workbench/experiments/central_ledger.jsonl`.
2. **Given** a ledger entry, **When** inspected, **Then** it contains Git commit SHA, `pixi.lock` hash, hardware device string (MPS/CUDA/CPU), PyTorch version, hyperparameters, random seeds, and micro/macro Parseval scores.
3. **Given** a run directory under `workbench/experiments/runs/<run_id>/`, **When** inspected, **Then** it contains immutable training receipts, configuration JSON, and evaluation metrics.

---

### User Story 4 - Atomic Release Packaging & Manifest Promotion (Priority: P4)

As a release manager, I package trained weights, transformer configuration, relation inventory, and fast tokenizers into immutable model release stores with cryptographic SHA-256 provenance.

**Why this priority**: Guarantees artifact integrity, immutability, and reproducible runtime loading for production deployment.

**Independent Test**: Run `python -m workbench.promotion.modernbert --candidate-dir models/modernbert_v1` and verify that `release-manifest.json` is generated, all file hashes match, and `validate_model_release()` passes with zero errors.

**Acceptance Scenarios**:

1. **Given** candidate training artifacts in `models/modernbert_v1/`, **When** the promotion utility executes, **Then** `model.safetensors`, `config.json`, `relation_inventory.json`, `tokenizer.json`, `tokenizer_config.json`, and `special_tokens_map.json` are packaged.
2. **Given** packaged release files, **When** `release-manifest.json` is created, **Then** it declares runtime contract `"isanlp_rst.parser/modernbert-v1"` and contains exact SHA-256 digests and byte counts for every file.
3. **Given** the promotion workflow, **When** promotion completes, **Then** the release is mirrored to dual storage locations: in-tree `models/model-releases/` and runtime cache `~/.cache/isanlp_rst/model-releases/`.

---

### User Story 5 - Clean-Room Release Boundary Certification (Priority: P5)

As a QA engineer, I certify that `isanlp_rst 5.0.0` installs into an isolated clean-room environment, loads the promoted ModernBERT model with external network access disabled, and performs end-to-end discourse parsing across all supported source formats.

**Why this priority**: Ensures the distribution wheel is self-contained, contains zero dev/offline dependencies, and operates reliably in air-gapped production environments.

**Independent Test**: Execute `clean_install.py --full --model-store models/model-releases --release-id <promoted_id>` in the isolated `production` Pixi environment and verify `"valid": true` output.

**Acceptance Scenarios**:

1. **Given** the built wheel `isanlp_rst-5.0.0-py3-none-any.whl`, **When** installed into the `production` environment, **Then** zero offline or dev dependencies (`pytest`, `nltk`, `peft`, `fire`, `jsonnet`, `blake3`) are present.
2. **Given** inference execution with `ISANLP_RST_NETWORK_DISABLED=1`, **When** `Parser.from_model_release()` loads the model, **Then** inference runs with zero external network requests.
3. **Given** diverse input formats, **When** the clean-room certification runner parses raw text, Docling ASTs (`*.docling.json`), DocLang XML ASTs (`*.dclg` / `*.xml`), and Markdown, **Then** valid discourse trees are returned for all formats and the certification runner emits `"valid": true`.

---

### User Story 6 - Baseline Comparison & Benchmark Reporting (Priority: P6)

As an author and researcher, I evaluate the promoted ModernBERT model against historical DMRST and UniRST baselines on held-out GUM data to scientifically quantify improvements in boundary detection, nuclearity assignment, and relation labeling.

**Why this priority**: Provides empirical validation of the architecture transition and proves superiority over legacy models.

**Independent Test**: Execute `scripts/benchmark_modernbert.py --release-id <promoted_id>` and verify that comparative Parseval tables and per-relation breakdown across all 15 coarse relations are output.

**Acceptance Scenarios**:

1. **Given** held-out GUM test gold trees, **When** `scripts/benchmark_modernbert.py` runs against the promoted release, **Then** micro-averaged Span, Nuclearity, Relation, and Full F1 scores are calculated without self-comparison shortcuts.
2. **Given** benchmark output, **When** formatted, **Then** a comparative matrix contrasting ModernBERT against published DMRST and UniRST baselines is generated.
3. **Given** 15 coarse discourse relations, **When** per-relation analysis runs, **Then** individual precision, recall, F1, and support counts are reported for every relation class.

---

### Edge Cases

- **Single-EDU Documents**: When a document consists of a single elementary discourse unit ($N=1$), CKY decoding must emit a trivial root DiscourseUnit without attempting split or nuclearity scoring.
- **Empty Relation Slices**: When a document batch contains candidate spans with no active relation labels (all targets are $-100$), loss computation must apply active-target boolean masking (`target != -100`) to avoid `CrossEntropyLoss` NaN/division-by-zero on empty tensors.
- **Maximum Context Saturation**: When document token length approaches 8,192 subwords, Rotary Position Embeddings and FlashAttention/SDPA must process the sequence without out-of-memory or position coordinate truncation.
- **Air-Gapped / Network-Disabled Execution**: When `ISANLP_RST_NETWORK_DISABLED=1` is set, all model loading must resolve from local model release directories without initiating socket connections or Hugging Face Hub queries.
- **Multi-Format Malformed AST Input**: When Docling or DocLang input contains unsegmented text or missing boundary attributes, parser fallbacks must handle errors gracefully without crashing the runtime.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ingestion system MUST parse all 301 authoritative GUM v12.1.0 `.dis` binary LISP trees across Train (211), Dev (32), Test (32), and GENTLE Test2 (26) partitions with zero syntax or mapping errors.
- **FR-002**: Tokenization pipeline MUST use `answerdotai/ModernBERT-base` fast BPE tokenizer with subword offset mapping that aligns EDU character boundaries without crossing-boundary errors.
- **FR-003**: Span representation layer MUST combine start token, end token, difference, product, and masked attention pooling vectors into normalized EDU embeddings with gradient-safe masking.
- **FR-004**: Multi-task scoring architecture MUST compute biaffine split scores $\mathbf{S} \in \mathbb{R}^{B \times N \times N}$, 3-class nuclearity scores $\mathbf{N} \in \mathbb{R}^{B \times N \times N \times 3}$, and 15-class coarse relation scores $\mathbf{R} \in \mathbb{R}^{B \times N \times N \times 15}$ over upper-triangular candidate spans ($0 \le i < j < N$).
- **FR-005**: Loss computation MUST calculate multi-task loss $\mathcal{L}_{\text{total}} = \text{BCEWithLogitsLoss}(S, Y_{\text{split}}) + \text{CrossEntropyLoss}(N, Y_{\text{nuc}}) + 1.2 \cdot \text{CrossEntropyLoss}(R, Y_{\text{rel}})$ using active-target masking to ensure finite, non-NaN values ($> 0.0$) at every optimization step.
- **FR-006**: Decoding pipeline MUST implement projective CKY chart parsing to construct valid binary discourse trees maximizing split, nuclearity, and relation scores.
- **FR-007**: Evaluation framework MUST compute standard micro-averaged Parseval scores (Span, Nuclearity, Relation, Full F1) dynamically against gold trees with zero hardcoded metrics.
- **FR-008**: Provenance system MUST record immutable JSONL receipts in `workbench/experiments/central_ledger.jsonl` capturing Git SHA, `pixi.lock` hash, hardware device, random seeds, and confusion matrices.
- **FR-009**: Promotion tool MUST package candidate model weights (`model.safetensors`), configuration (`config.json`), relation inventory (`relation_inventory.json`), and tokenizers into immutable release bundles.
- **FR-010**: Release manifest generator MUST emit `release-manifest.json` under runtime contract `"isanlp_rst.parser/modernbert-v1"` containing SHA-256 byte digests and size verifications for all packaged files.
- **FR-011**: Storage manager MUST support dual release storage: in-tree `models/model-releases/` and runtime cache `~/.cache/isanlp_rst/model-releases/`.
- **FR-012**: Runtime parser MUST load promoted releases via `Parser.from_model_release()` and execute air-gapped inference when `ISANLP_RST_NETWORK_DISABLED=1` is set.
- **FR-013**: Clean-room certification runner MUST verify wheel installation and end-to-end inference across plain text, Docling ASTs, DocLang XML ASTs, and Markdown in the isolated `production` Pixi environment.
- **FR-014**: Codebase MUST eliminate all active stubs, no-ops (`drawTree()`), and circular benchmarks across `workbench/corpus/` and scripts.

### Key Entities *(include if feature involves data)*

- **Elementary Discourse Unit (EDU)**: Minimal discourse segment defined by start and end character offsets in source text and corresponding subword token span $[s_u, e_u]$.
- **Discourse Tree (`DiscourseUnit`)**: Recursive binary tree node representing an EDU leaf or constituent span with nuclearity ($\text{NS}, \text{SN}, \text{NN}$) and coarse relation label ($0 \dots 14$).
- **Supervised Target Matrices**: Tensor representations for an $N$-EDU document: binary split matrix $(N \times N)$, nuclearity matrix $(N \times N \in \{0, 1, 2, -100\})$, and coarse relation matrix $(N \times N \in \{0 \dots 14, -100\})$.
- **Model Release Package**: Immutable bundle containing `model.safetensors`, `config.json`, `relation_inventory.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, and `release-manifest.json`.
- **Release Manifest (`release-manifest.json`)**: Cryptographically verified JSON document containing `schema_version`, `release_id`, `runtime_contract`, `compatibility_range`, and SHA-256 file hashes.
- **Ledger Record (`central_ledger.jsonl`)**: Immutable audit record linking run ID, Git commit SHA, `pixi.lock` hash, hardware configuration, hyperparameters, and Parseval evaluation results.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the 301 authoritative GUM v12.1.0 documents (211 train, 32 dev, 32 test, 26 test2) are ingested and parsed without unmapped relations or token alignment failures.
- **SC-002**: Parser achieves development partition Parseval quality targets: Span F1 $\ge 82.0\%$, Nuclearity F1 $\ge 68.0\%$, Relation F1 $\ge 55.0\%$, and Full F1 $\ge 52.0\%$.
- **SC-003**: Training throughput on Apple Silicon Metal (MPS) completes in $\le 15$ minutes per epoch across the 211 training documents with gradient accumulation ($K=16$).
- **SC-004**: Clean-room installation into an isolated `production` Pixi environment executes end-to-end inference across plain text, Docling AST, DocLang XML, and Markdown formats with 100% success (`"valid": true`) and zero network requests.
- **SC-005**: 100% of packaged release files match their cryptographic SHA-256 byte digests in `release-manifest.json` during validation.
- **SC-006**: 100% of training, validation, and benchmarking runs append verifiable provenance entries to `workbench/experiments/central_ledger.jsonl`.
- **SC-007**: 0 active stubs, no-op passes, or circular benchmark scripts remain in the repository.

---

## Assumptions

- **Target Hardware**: Training and evaluation support Apple Silicon Metal (MPS) as primary acceleration target, with autodispatch to NVIDIA CUDA and CPU fallback.
- **Runtime Environment**: Python `>=3.14` managed exclusively through locked Pixi environments (`default` for development/workbench and `production` for clean-room certification).
- **Model Architecture**: Base encoder is `answerdotai/ModernBERT-base` with 8,192 subword context window and Rotary Position Embeddings (RoPE).
- **Discourse Relation Taxonomy**: 15 standard coarse discourse relations mapped deterministically from GUM 12.1.0 fine-grained annotations per `data-model.md`.
- **Packaging Standard**: Model release weights are packaged as `.safetensors` files and distributed independently of the Python code wheel to preserve package lightness and cryptographic integrity.
- **Network Policy**: Runtime inference is fully self-contained and air-gapped when model releases are present in local or in-tree stores.
