# Graph Report - isanlp_rst  (2026-08-24)

## Corpus Check

- cluster-only mode — file stats not available

## Summary

- 4620 nodes · 10352 edges · 227 communities (197 shown, 30 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1075 edges (avg confidence: 0.56)
- Token cost: 15,790 input · 2,665 output

## Graph Freshness

- Built from commit: `693aa316`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)

- Calibration Metrics
- RST Analysis Models
- RST Node Harvesting
- Document Token Alignment
- eRST Checkpoint Configuration
- DocLang XML Parsing
- Docling Text Harvesting
- Markdown Parsing Tests
- Minified JavaScript Assets
- Docling Entry Tests
- DocLang Eligibility Policy
- Data Validation Logic
- EDU Segmentation Dataset
- Corpus Loading Receipts
- Markdown Mapper Tests
- Docling Boundary Detection
- eRST Graph Completion
- DocLang Text Harvester
- RST Tree Rendering
- Scorer Training Script
- DocLang Boundary Tests
- Structural Data Protocols
- Markdown Harvester Tests
- eRST Secondary Decoder
- RS4 XML Serialization
- Universal Parser Nodes
- Training Candidate Selection
- Universal Parser Common
- RS3 Corpus Utilities
- DMRST RS3 Utilities
- RSTWeb SQL Database
- Parser Integration Tests
- Body Text Extraction
- Result Caching System
- Parser Evaluation Metrics
- DMRST Data Management
- DMRST Corpus Data
- UniRST Data Management
- CRF Segmentation Model
- DMRST Common Corpus
- DocLang Boundary Detection
- Universal Parser Data
- DMRST Parsing Network
- Core Domain Enums
- Research Authority Baseline
- UniRST Predictor
- Parser Neural Modules
- Shell Environment Prerequisites
- RST Tree Mapping
- Segmenter Architectures
- Task Implementation Templates
- Markdown Boundary Tests
- DMRST Parser Nodes
- RSTWeb UI Logic
- Relation Inventory Import
- Training Manager
- Parser Public API
- Pydantic Tree Serialization
- Markdown Loader
- Base Predictor Logic
- DMRST Predictor
- Neural Decoder Modules
- Compute Device Selection
- Baseline Serialization
- Research Promotion Logic
- Markdown Boundary Detection
- End-to-End Smoke Tests
- Speckit Analyze Skill
- RST Tree Visualization
- RST Parsing Logic
- Environment Configuration
- Neural Span Encoding
- Speckit Analyze Skill
- Parser Family Resolution
- Markdown Result Serialization
- Parse Result Helpers
- HTML Viewer Hardening
- Checkpoint Validation
- Model Signature Detection
- BiMPM Matching Logic
- UniRST Parsing Network
- Docling Entry Point
- Universal Data Manager
- RST Tree Preprocessing
- Result Cache Keys
- DMRST Data Manager
- RST Analysis Projections
- Bottom-Up Transition Parser
- Razdel Offset Converter
- Tokenizer Compatibility Probing
- Runtime Provenance Helpers
- UniRST Inventory IO
- Parser Contract Tests
- DMRST Data Loading
- RST Quality Diagnostics
- Fixture Parity Verification
- RS3 Document Rendering
- Speckit Analyze Skill
- Multi-Run Experiment Runner
- RNN Sequence Encoder
- MIME Type Registration
- RNN Sequence Encoder
- Torch Dtype Normalization
- Baseline Reproduction Gates
- Adversarial Discriminator Module
- RS3 to HTML Conversion
- Multi-Run Experiment Runner
- Repository Cleanup Script
- Parser Integration Tests
- SDLC Workflow Skills
- Cleanup Script Tests
- Checkpoint Verification Tool
- RS3 Annotation Parsing
- RS3 Annotation Parsing
- GUM Corpus Metrics
- Discourse Unit Mocks
- Fixture Parity Tests
- File Access Linter
- GUM Corpus Identity
- System Disposition Validation
- EDU File Reader
- Project Data Model
- Markdown Manifest Linter
- DMRST Config Reader
- DiscourseSignal
- Universal Parser Config
- Parser Performance Benchmark
- GUM Gold Validation
- CUDA Smoke Test
- Architecture Decision Records
- DocLang Source Provenance
- Corpus Loading Models
- Custom Tokenizer Class
- GUM Parser Fixture
- Project Roadmap
- Assumption Check Script
- Docling Parsing Tests
- DocLang Specification Docs
- Cleanup Shell Script
- Ontology Locking
- Device-Aware Initialization
- Speckit Converge Skill
- Code Standards
- Command Definitions
- Design Assumptions
- Project Constitution
- Task Issue Integration
- Doclang Specification
- Docling Core Library
- Speckit Converge Skill
- Long-Input Parsing Plan
- Markdown Parsing Guide
- English RST Platform
- Contributor Elena Chistova
- English RST Diagrams
- Russian RST Diagrams
- Inline RST Rendering
- ISANLP RST Parser
- Implementation Planning
- Contributor Steve Allison
- Table Harvesting
- RST Tree Mapping
- Schema Compatibility Tests
- RST Parser Metrics
- Batch Parsing Documentation
- Feature Specification Template
- CRF Layer Implementation
- Adversarial Discriminator Module
- Experiment Protocol Documentation
- Token Offset Alignment
- Planning Skill Definition
- Specification Skill Definition
- Task Generation Skill
- Boundary Design Decisions
- Claude Planning Skill
- Claude Specification Skill
- Claude Task Skill
- Docling Harvester Implementation
- Project Constitution Template
- Research and Authority Ledger
- Docling Fixture Documentation
- RST Output Walkthrough
- Source Origin Serialization
- Project Design Records
- Output Schema Specifics
- Implementation Plan Template
- Rich Markdown Elements
- Checklist Skill Definition
- Claude Checklist Skill
- Cursor Checklist Skill
- Verification Quickstart Guide
- Clarification Skill Definition
- Implementation Skill Definition
- Claude Clarification Skill
- Claude Implementation Skill
- RST Result Serialization
- EDU File Reader
- Constitution Skill Definition
- Claude Constitution Skill
- Multi-Level Markdown Structure
- Markdown Fixture Index
- Task to Issue Skill
- Claude Task to Issue
- JSON Serialization Helpers
- Checklist Template
- Table Invariant Tests
- Custom Tokenizer Class
- Evidence Matrix Documentation
- Discourse Unit Stand-in
- Checkpoint Bundle Contract
- Corpus Experiment Contract
- Format Projection Contract
- DocLang Fixture Documentation
- GUM RST Fixtures
- Minimal Documentation
- Tool Version Caching

## God Nodes (most connected - your core abstractions)

1. `Parser` - 112 edges
2. `RstAnalysis` - 103 edges
3. `SpanNode` - 68 edges
4. `parse_doclang()` - 61 edges
5. `parse_docling()` - 60 edges
6. `parse_markdown()` - 60 edges
7. `RstDocument` - 58 edges
8. `RstNode` - 56 edges
9. `harvest_doclang_text()` - 51 edges
10. `BasePredictor` - 50 edges

## Surprising Connections (you probably didn't know these)

- `GumGoldValidator` --uses--> `RS4Document`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/erst/rs4.py
- `GumGoldValidator` --uses--> `RS4Reader`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/erst/rs4.py
- `GumGoldValidator` --uses--> `OntologyAdapter`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/ontology/adapter.py
- `GumGoldValidator` --uses--> `Parser`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/parser.py
- `_Predictor` --uses--> `BasePredictor`  [INFERRED]
  tests/test_base_predictor.py → isanlp_rst/base_predictor.py

## Import Cycles

- None detected.

## Hyperedges (group relationships)

- **Steve's Quality Standards** — agents_md, claude_md, gemini_md [EXTRACTED 0.90]
- **DocLang Integration Flow** — claude_memory_verified_doclang_fixtures, claude_memory_verified_doclang_spec [EXTRACTED 1.00]
- **Docling Integration Flow** — claude_memory_open_rst_real_world_quality, claude_memory_open_schema_detail_verifications, claude_memory_verified_docling_core_api, claude_memory_verified_docling_schema [EXTRACTED 1.00]
- **Spec-Kit Core SDD Loop** — cursor_skills_speckit_specify_skill, cursor_skills_speckit_plan_skill, cursor_skills_speckit_tasks_skill, cursor_skills_speckit_implement_skill [EXTRACTED 1.00]
- **Extended RST (eRST) Subsystem** — isanlp_rst_erst, forensic_code_review_report_md, readme_md [INFERRED 0.85]
- **Native RST Parsing Strategy** — doclang_native_rst_plan, docling_native_rst_build_plan, central_ontology [INFERRED 0.85]
- **Project Governance and Standards** — claude_memory_project_status, claude_rules_code_standards, claude_rules_no_assumptions [INFERRED 0.90]

## Communities (227 total, 30 thin omitted)

### Community 0 - "Calibration Metrics"

Cohesion: 0.04
Nodes (75): Counter, DirectedSpanKey, A directed secondary rhetorical relation edge without nuclearity., SecondaryRelationEdge, CalibrationBin, CalibrationSummary, compute_calibration_error(), Confidence calibration metrics and error estimators. (+67 more)

### Community 1 - "RST Analysis Models"

Cohesion: 0.05
Nodes (79): PrimaryRelationEdge, Discourse analysis result models and graph structures., Execution timing profile in milliseconds., Complete discourse analysis result., Find the root node if present., Look up a node by its ID., A node in a discourse tree or graph., A directed primary rhetorical relation edge with nuclearity. (+71 more)

### Community 2 - "RST Node Harvesting"

Cohesion: 0.07
Nodes (84): compute_overlap_refs(), HarvestSpan, Return ``(xpaths, note)`` for the half-open range ``[start, end)``. DocLang-…, Return the deduplicated thread ids carried by the named spans. Order is the…, _thread_ids_for_xpaths(), HarvestSpan, One eligible DocLang text span with parser-input coordinates., One self-contained internal RST node. (+76 more)

### Community 3 - "Document Token Alignment"

Cohesion: 0.08
Nodes (47): FormatRstAnalysis, Composite analysis for structured documents (Docling, DocLang, Markdown)., DocumentToken, Edu, ProvenanceRecord, Document input models and coordinate representation., Create an RstDocument from pre-segmented EDU strings. Note: Character offsets…, A single token aligned with character coordinates. (+39 more)

### Community 4 - "eRST Checkpoint Configuration"

Cohesion: 0.07
Nodes (70): ErstCalibrationState, ErstCheckpointManifest, ErstCheckpointMetrics, ErstCheckpointResearchEvidence, ErstCheckpointTestVector, ErstFeatureSchema, ErstGraphComponentConfig, Content identities for every feature and decoding contract. (+62 more)

### Community 5 - "DocLang XML Parsing"

Cohesion: 0.05
Nodes (61): parse_doclang(), Path, Parse a DocLang XML file and return its RST analysis. Args: path: filesystem…, Validate ``path`` against the DocLang schema via the ``doclang`` package. When…,_validate_xml(), EmptyDoclangError, EmptyHarvestError, InvalidDoclangError (+53 more)

### Community 6 - "Docling Text Harvesting"

Cohesion: 0.11
Nodes (29): harvest_docling_text(), DoclingDocument, HarvestResult, Produce the main document harvest with per-span self_ref mapping. Args: doc: a…, DoclingDocument, Span ``kind`` mirrors the Docling item label so consumers can distinguish…, All 5 PPTX pictures with meta.description.text appear in the harvest., PDF fixture: 48 pictures, 0 with meta.description.text — none in harvest. (+21 more)

### Community 7 - "Markdown Parsing Tests"

Cohesion: 0.06
Nodes (64): parse_markdown(), Any, Path, Build the ``source_origin`` block for the result., Parse a markdown file and return its RST analysis. Args: path: filesystem path…,_source_origin(),_Node, parser() (+56 more)

### Community 8 - "Minified JavaScript Assets"

Cohesion: 0.06
Nodes (42): ba(), Ea(), Fa(), fb(), ga(), ha(), b(), hb() (+34 more)

### Community 9 - "Docling Entry Tests"

Cohesion: 0.13
Nodes (30): _minimal_docling_json(), Path, Unit + integration tests for ``isanlp_rst.docling.parse_docling``. Fast unit…, Two paragraphs so the stub emits a relation tree., Path and str inputs reach the same guard., Hand-written prose-only Docling: empty ``table_analyses``, and main relations…, Tiny hand-written Docling JSON with one text paragraph., Body contains only a one-cell table — no prose harvest. (+22 more)

### Community 10 - "DocLang Eligibility Policy"

Cohesion: 0.06
Nodes (48): DoclangEligibility, Single immutable eligibility policy for DocLang harvest and boundaries., All switches that determine text harvest and boundary membership., Return the DocLang layers admitted by this policy., Return whether ``layer`` contributes harvestable content., Return whether a semantic kind contributes to the main harvest., ``parse_doclang`` entry point — load → harvest → boundaries → parse → flatten.…, DoclangRstError (+40 more)

### Community 11 - "Data Validation Logic"

Cohesion: 0.08
Nodes (12): field_validator, Require valid half-open anchors while retaining overlap and order., Require non-empty, unique raw relation labels., Require unique non-negative token identifiers without reordering.,_canonical_model_hash(), ErstCheckpointBuildSpec, model_validator, Authoritative inputs used to construct an eRST completion bundle. (+4 more)

### Community 12 - "EDU Segmentation Dataset"

Cohesion: 0.06
Nodes (47): inference_mode, EduSegmentationDataset, parse_disrpt_tok_file(), parse_rs4_to_sentences(), Any, Dataset, Path, Tensor (+39 more)

### Community 13 - "Corpus Loading Receipts"

Cohesion: 0.08
Nodes (44): CorpusAuthorityEntry, CorpusLoadReceipt, GumCorpusAuthority, One document assignment derived from immutable upstream authority., Hashed interpretation of pinned GUM split and licence authorities., Return the upstream authority entry for one exact document ID., Reconciled receipt for a complete or explicitly partial corpus load., CorpusLoadError (+36 more)

### Community 14 - "Markdown Mapper Tests"

Cohesion: 0.14
Nodes (30): compute_overlap_refs(), HarvestSpan, Return ``(block_refs, note)`` for the half-open range ``[start, end)``.…, FakeUnit, flatten_tree(),_materialize_source(), Boundary, HarvestSpan (+22 more)

### Community 15 - "Docling Boundary Detection"

Cohesion: 0.08
Nodes (57): ContentLayer, _content_layers(), detect_boundaries(),_detect_pptx_slide_boundaries(),_detect_section_boundaries(), _detect_table_boundaries(),_detect_vtt_turn_boundaries(),_iter_body_self_refs() (+49 more)

### Community 16 - "eRST Graph Completion"

Cohesion: 0.07
Nodes (55): DiGraph, Any, eRST graph completer: secondary-edge candidate generation and signal anchoring., Delegate every runtime mode to the canonical complete generator., Complete a classical primary tree into an eRST graph with signals and secondary…, CandidateMode, compute_structural_features(), generate_secondary_edge_candidates() (+47 more)

### Community 17 - "DocLang Text Harvester"

Cohesion: 0.06
Nodes (59): harvest_doclang_text(), _ElementTree, HarvestResult, Produce the main document harvest with per-span xpath mapping. Args: tree: a…,_ElementTree, parametrize, Unit tests for the doclang harvesters (main text + per-table)., ``ok_table_rectangular`` is table-only — the main harvest must be empty; the… (+51 more)

### Community 18 - "RST Tree Rendering"

Cohesion: 0.11
Nodes (29): IO, Render an RST tree and, optionally, display it inline. This is a light-weight…, render(), cli(), _html_to_fragment(),_new_root_id(), IO, Path (+21 more)

### Community 19 - "Scorer Training Script"

Cohesion: 0.13
Nodes (20): Immutable upstream model revisions selected by the v4 research protocol., compute_edge_metrics(), epoch_improves(), Any, Path, Training script for fine-tuning NeuralSecondaryEdgeScorer on GUM eRST treebanks., Reject zero-step runs before a scheduler or success receipt can exist., Treat the first finite metric as the baseline, including an exact zero. (+12 more)

### Community 20 - "DocLang Boundary Tests"

Cohesion: 0.07
Nodes (50): detect_boundaries(),_ElementTree, HarvestResult, Detect all structures using the exact policy and harvested membership., _ElementTree, parametrize, Path, Unit tests for ``isanlp_rst.doclang.boundaries.detect_boundaries``. (+42 more)

### Community 21 - "Structural Data Protocols"

Cohesion: 0.06
Nodes (39): ProjectedEduLike, ProjectedRelationLike, Protocol, Structural contract shared by all format-native EDU wire objects., Structural contract shared by all format-native relation wire objects., find_cdu(),_is_leaf(), Any (+31 more)

### Community 22 - "Markdown Harvester Tests"

Cohesion: 0.05
Nodes (56): _harvest(), Unit tests for ``isanlp_rst.markdown.harvester``. Tests focus on inline-…, h1..h6 must yield level 1..6 respectively., Three bullet items → three list_item spans, not one., Nested bullets join their parent item's text rather than emit separate spans —…, Paragraphs inside `>` become blockquote_paragraph, not paragraph., Negative-space: a plain para must not be classified as blockquote., A heading inside `>` is quoted content — it must not carry the plain `heading`… (+48 more)

### Community 23 - "eRST Secondary Decoder"

Cohesion: 0.14
Nodes (24): DecodeRejectionReason, ErstDecoderConfig, ErstDecodeReceipt, Immutable threshold and raw-relation inventory for eRST decoding., Reconciled proof of threshold selection and formal eRST constraints., The only formal reasons an above-threshold eRST edge may be rejected., DecodedErstEdges, ErstSecondaryEdgeDecoder (+16 more)

### Community 24 - "RS4 XML Serialization"

Cohesion: 0.09
Nodes (38): isanlp_rst.erst, analysis_to_rs4(), Convert an RstDocument and RstAnalysis back into an RS4Document., Any, Path, Faithful RS4 XML reader and writer for GUM eRST and classical RST., Parse an RS4 XML file into an RS4Document., Writes RS4Document objects to well-formed RS4 XML. (+30 more)

### Community 25 - "Universal Parser Nodes"

Cohesion: 0.11
Nodes (43): RST tree node used by the universal parser corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), buildTree(), buildTreeThiago() (+35 more)

### Community 26 - "Training Candidate Selection"

Cohesion: 0.14
Nodes (31): CandidateDocumentSelection, CandidateSelectionReceipt, CorpusFailureType, HardNegativeSamplingConfig, Deterministic training-only hard-negative selection configuration., Complete-versus-selected counts for one already-partitioned document., Hashed evidence that only train candidates were sampled., Stable machine-readable corpus failure categories. (+23 more)

### Community 27 - "Universal Parser Common"

Cohesion: 0.08
Nodes (42): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), Document, __getforminfo(), getLabelMapping() (+34 more)

### Community 28 - "RS3 Corpus Utilities"

Cohesion: 0.10
Nodes (47): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+39 more)

### Community 29 - "DMRST RS3 Utilities"

Cohesion: 0.10
Nodes (44): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+36 more)

### Community 30 - "RSTWeb SQL Database"

Cohesion: 0.14
Nodes (47): add_node(), add_seg(), count_children(), count_multinuc_children(), count_span_children(), delete_document(), delete_node(), generic_query() (+39 more)

### Community 31 - "Parser Integration Tests"

Cohesion: 0.09
Nodes (45): _assert_aligned(), _collect_leaf_units(),_collect_leaves(), dmrst_gumrrg_cpu(), dmrst_rstdt_cpu(), dmrst_rstreebank_cpu(), fixture, parametrize (+37 more)

### Community 32 - "Body Text Extraction"

Cohesion: 0.21
Nodes (13): body_text(), iter_body_text(),_Element, Yield eligible text beneath ``element`` without its outer tail. The root is an…, Return normalized eligible body text for an explicitly selected root., _ElementTree, Regression tests for exactly-once DocLang text traversal., test_nested_formatting_text_and_tails_appear_once() (+5 more)

### Community 33 - "Result Caching System"

Cohesion: 0.06
Nodes (59): _coerce(), dataclass_from_dict(), load_cached(), normalize_source_basename(), Any, Path, T, Optional on-disk result cache for the format-native entry points. Keyed on the… (+51 more)

### Community 34 - "Parser Evaluation Metrics"

Cohesion: 0.09
Nodes (29): calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement(), get_micro_metrics(), get_seg_measure() (+21 more)

### Community 35 - "DMRST Data Management"

Cohesion: 0.09
Nodes (15): DataManager, ParserInput, Any, Data, Node, Path, Mutable per-document parser example. Extra attributes stay settable., One-way import of a published HF pickle → relation labels only. (+7 more)

### Community 36 - "DMRST Corpus Data"

Cohesion: 0.08
Nodes (15): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Write the bracketed tree into a file Remove the original extension, keep only…, Draw RST tree into a file (+7 more)

### Community 37 - "UniRST Data Management"

Cohesion: 0.10
Nodes (15): DataManager, ParserInput, Any, Data, Node, Path, Mutable per-document parser example. Extra attributes (legacy pickle…, One-way import of a published HF pickle → relation labels only. (+7 more)

### Community 38 - "CRF Segmentation Model"

Cohesion: 0.09
Nodes (9): CRF, LinearSegmenter, PointerSegmenter, device, Tensor, Conditional random field. modified from <https://github.com/kmkurn/pytorch-…>, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions… (+1 more)

### Community 39 - "DMRST Common Corpus"

Cohesion: 0.09
Nodes (38): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), __getforminfo(), getLabelMapping(), getParse() (+30 more)

### Community 40 - "DocLang Boundary Detection"

Cohesion: 0.07
Nodes (52): _detect_document_fallback(),_detect_field_region_boundaries(),_detect_group_boundaries(), _detect_heading_boundaries(),_detect_page_boundaries(), _detect_table_boundaries(),_harvest_eligible_xpaths(), _is_within() (+44 more)

### Community 41 - "Universal Parser Data"

Cohesion: 0.08
Nodes (15): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Write the bracketed tree into a file Remove the original extension, keep only…, Draw RST tree into a file (+7 more)

### Community 42 - "DMRST Parsing Network"

Cohesion: 0.19
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 43 - "Core Domain Enums"

Cohesion: 0.07
Nodes (54): CapabilityStatusEnum, ConfidenceKindEnum, DeviceEnum, EdgeKindEnum, FailureCodeEnum, InputFidelityEnum, InputModeEnum, MappingKindEnum (+46 more)

### Community 44 - "Research Authority Baseline"

Cohesion: 0.14
Nodes (27): date, AuthoritySearchEvidence, BaselineAuthorityBlocker, ModelRevisionAuthority, Immutable model-hub identity used by the published baseline., One completely inspected public surface and its scorer-resolution result., Reasons the published eRST baseline cannot yet authorize experiments., Immutable identity for one public research artifact. (+19 more)

### Community 45 - "UniRST Predictor"

Cohesion: 0.14
Nodes (10): Robust string-to-bool conversion used in configs., str2bool(), PredictorUniRST, device, dtype, txt (published) → JSON (native) → legacy pickle (labels only)., Load ``relation_table_<variant>.txt`` using corpus aliases., Count distinct ``label_classifiers.<N>.*`` indices in a state dict. Returns… (+2 more)

### Community 46 - "Parser Neural Modules"

Cohesion: 0.07
Nodes (21): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+13 more)

### Community 47 - "Shell Environment Prerequisites"

Cohesion: 0.08
Nodes (17): check-prerequisites.sh script, check_dir(), check_file(), get_feature_paths(), get_repo_root(), has_jq(),_persist_feature_json(), resolve_specify_init_dir() (+9 more)

### Community 48 - "RST Tree Mapping"

Cohesion: 0.06
Nodes (42): flatten_tree(), Any, Boundary, RstEdu, RstRelation, Map an RST tree's character-offset spans to DocLang xpaths. Thin format binding…, Flatten a DiscourseUnit tree into ``(relations, edus)`` tuples. Ids are…, AuthoritativeProjection (+34 more)

### Community 49 - "Segmenter Architectures"

Cohesion: 0.14
Nodes (5): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter

### Community 50 - "Task Implementation Templates"

Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 51 - "Markdown Boundary Tests"

Cohesion: 0.09
Nodes (32): detect_boundaries(), Boundary, HarvestSpan, TableHarvest, Detect all boundaries in the main ``spans`` + ``table_harvests``.,_boundaries(), Unit tests for ``isanlp_rst.markdown.boundaries``. Tests focus on boundary…, Two-level analysis: cells are not part of the document tree, so they live only… (+24 more)

### Community 52 - "DMRST Parser Nodes"

Cohesion: 0.16
Nodes (30): RST tree node used by the DMRST corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), cleanChildren(), correctThiago() (+22 more)

### Community 53 - "RSTWeb UI Logic"

Cohesion: 0.18
Nodes (30): act(), add_node(), count_children(), count_multinuc_children(), count_span_children(), create_node_div(), crel(), delete_node() (+22 more)

### Community 54 - "Relation Inventory Import"

Cohesion: 0.11
Nodes (32): dump_relation_inventory(), import_relation_table_from_legacy_pickle(), Path, One-way import: published HF pickles → ``relation_table`` labels only., Unpickler that only reconstructs inventory leaf types + containers.…, RestrictedUnpickler,_EvilReduce, _local_shell() (+24 more)

### Community 55 - "Training Manager"

Cohesion: 0.22
Nodes (6): _metrics_as_floats(), Any, Data, no_grad, Path, TrainingManager

### Community 56 - "Parser Public API"

Cohesion: 0.09
Nodes (16): Parser, Public façade for the DMRST and UniRST parser families. The family is resolved…, Parse a document using predefined EDUs., parser_cpu(), fixture, Real DMRST end-to-end model parsing into a typed RstAnalysis contract., Real UniRST end-to-end multilingual model parse into RstAnalysis., Edge cases on real model: unicode punctuation, multi-paragraph, and empty fails. (+8 more)

### Community 57 - "Pydantic Tree Serialization"

Cohesion: 0.12
Nodes (26): Any, DiscourseUnit, BaseModel, DiscourseUnit, PydanticDiscourseUnit, Typed Pydantic model for RST trees — optional, requires the ``pydantic`` extra.…, Validated, JSON-serialisable representation of one DiscourseUnit RST tree node.…, Build a ``PydanticDiscourseUnit`` from a ``DiscourseUnit`` tree (recursive). (+18 more)

### Community 58 - "Markdown Loader"

Cohesion: 0.09
Nodes (30): build_parser(), load_markdown(), LoadResult, Tokenise a markdown source string into a ``markdown-it-py`` token stream. The…, The output of ``load_markdown``. ``tokens`` is the body token stream (front-…, Construct a configured ``MarkdownIt`` instance. The ``front_matter`` plugin is…, Tokenise ``source_text`` and split out the YAML front-matter., MarkdownIt (+22 more)

### Community 59 - "Base Predictor Logic"

Cohesion: 0.07
Nodes (31): AbstractContextManager, BasePredictor, Any, Path, T, Mixin-style base with shared tokenization, batching and offset utils. Not…, Yield chunks of size `n` from `_list` (handles empty lists)., Recursively remap ``.start``/``.end`` of leaf/internal nodes from the tokenized… (+23 more)

### Community 60 - "DMRST Predictor"

Cohesion: 0.09
Nodes (18): PredictorDMRST, Any, Data, device, dtype, Path, Takes data with word level tokenization, run current transformer tokenizer and…, Splits a batch into multiple smaller with given size. (+10 more)

### Community 61 - "Neural Decoder Modules"

Cohesion: 0.12
Nodes (9): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+1 more)

### Community 62 - "Compute Device Selection"

Cohesion: 0.12
Nodes (34): _device_from_legacy_int(), _device_from_spec(), DeviceProbe,_mps_available(), device, Reproduce the historical ``cuda_device: int`` selection exactly. ``-1`` -> CPU.…, Resolve the compute device from the string API (or the deprecated int).…, Immutable snapshot of which accelerators the host exposes. Production code uses… (+26 more)

### Community 63 - "Baseline Serialization"

Cohesion: 0.28
Nodes (14): BaselineDirection, BaselineSignalLocation, PublishedBaselineExample, One exact association-classifier input before deterministic serialization., Direction token used by the released association serialization., Span containing the signal targeted by one association example., _marked_text(), Deterministic serialization for the published eRST association baseline. (+6 more)

### Community 64 - "Research Promotion Logic"

Cohesion: 0.14
Nodes (25): BaselineEvaluationSetting, MandatoryResearchSystem, PromotionDecision, PromotionGateName, PromotionOutcome, StrEnum, Fail-closed research-authority contracts for eRST benchmark reproduction., Hashed proof that all mandatory systems were retained and none was run. (+17 more)

### Community 65 - "Markdown Boundary Detection"

Cohesion: 0.06
Nodes (53): Detect structural boundaries in a markdown harvest. Boundaries are derived from…, ``parse_markdown`` entry point — load → harvest → boundaries → parse → flatten.…, EmptyHarvestError, EmptyMarkdownError, InputTooLargeError, MarkdownRstError, Exception, Custom exceptions for Markdown-native RST parsing. (+45 more)

### Community 66 - "End-to-End Smoke Tests"

Cohesion: 0.15
Nodes (24): _assert_tree_aligned(),_check(), _check_from_edus(),_check_parse_rst(), _collect_leaves(), _expect_raises(), main(), Path (+16 more)

### Community 67 - "Speckit Analyze Skill"

Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 68 - "RST Tree Visualization"

Cohesion: 0.09
Nodes (39): Document, get_depth(), get_left_right(), NODE, NodeMap, RST tree node types and parent-chain attribute walks., EDU used by the segmenter, not by the structurer., Set graphical nesting depth of ``orig_node`` from the parent chain. RST… (+31 more)

### Community 69 - "RST Parsing Logic"

Cohesion: 0.09
Nodes (20): Data, Takes word-level tokenized data and converts it to transformer subword inputs., Splits a batch into multiple smaller batches of the given size. Note:…, Parse text into an RST tree. Args: text: Original document text. tokens:…, Parse text using predefined EDU boundaries., DUConverter, Parses the tree predictions given in a string format. Args: description: Tree…, Takes the model outputs and converts them into isanlp binary trees. Returns:… (+12 more)

### Community 70 - "Environment Configuration"

Cohesion: 0.19
Nodes (21): HfTokenSource, load_repository_environment(), _nonempty_environment_value(), BaseModel, Path, StrEnum, Explicit, non-logging repository environment loading for eRST operations., Supported Hugging Face token environment variables in precedence order. (+13 more)

### Community 71 - "Neural Span Encoding"

Cohesion: 0.11
Nodes (15): AttentionPooling, BoundaryAwareSpanEncoder, device, dtype, Tensor, Learned attention pooling over sequence representations., Move the complete scorer while keeping its runtime contract synchronized., Compute existence logit, relation logits, and multi-task loss. (+7 more)

### Community 72 - "Speckit Analyze Skill"

Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 73 - "Parser Family Resolution"

Cohesion: 0.15
Nodes (6): Any, device, dtype, When both family and version are set, version must belong to family., Explicit family must match detectable signatures when present., TestResolveFamily

### Community 74 - "Markdown Result Serialization"

Cohesion: 0.18
Nodes (18): MarkdownRstResult, Any, Top-level output of ``parse_markdown``., Return JSON-shaped plain data., Serialize deterministically without non-JSON dataclass values., _doclang_projection(), _docling_projection(), _format_analyses() (+10 more)

### Community 75 - "Parse Result Helpers"

Cohesion: 0.18
Nodes (17): DiscourseUnit, Parse text and return a typed RST root instead of the legacy mapping payload.…, extract_root_tree(), ParseFailedError, Any, RuntimeError, Helpers for unpacking ``Parser`` / predictor call results., Return ``result['rst'][0]``, or raise :class:`ParseFailedError`. Preferred over… (+9 more)

### Community 76 - "HTML Viewer Hardening"

Cohesion: 0.32
Nodes (13): rs3tohtml(), Create a private SQLite file for one render; unlink in ``finally``., _resolve_dbpath(), setup_db(), temporary_db(), Path, Viewer hardening: XXE posture, HTML escape, per-render SQLite., test_rs3tohtml_escapes_basename_in_header() (+5 more)

### Community 77 - "Checkpoint Validation"

Cohesion: 0.08
Nodes (27): datetime, CandidateIdentityProbe, CorpusSourceIdentity, ErstCheckpointComponent, ErstCheckpointFile, ErstCheckpointLicenses, ErstCheckpointProvenance, ErstScorerConfig (+19 more)

### Community 78 - "Model Signature Detection"

Cohesion: 0.18
Nodes (5): Path, Inspect a local checkpoint directory and infer the parser family. Returns…, Read ``path`` as JSON. Returns ``None`` if the file is missing, unreadable, or…, If both signatures are present, UniRST wins (more specific)., TestDetectFamilyFromModelDir

### Community 79 - "BiMPM Matching Logic"

Cohesion: 0.22
Nodes (8): BiMPM, device, Tensor, :param v1: (batch, seq_len, hidden_size) :param v2: (batch, seq_len,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, Inputs can be of infinite length, hence BiMPM matching can cause OOM. This is a…, LSTM

### Community 80 - "UniRST Parsing Network"

Cohesion: 0.18
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 81 - "Docling Entry Point"

Cohesion: 0.14
Nodes (15): ``parse_docling`` entry point — load → harvest → boundaries → parse → flatten.…, DoclingRstError, EmptyDoclingError, EmptyHarvestError, InputTooLargeError, Exception, Custom exceptions for Docling-native RST parsing., The harvest produced no text (e.g. a tables-only document). (+7 more)

### Community 82 - "Universal Data Manager"

Cohesion: 0.20
Nodes (8): collect(), BinaryTree, Node, Path, :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 83 - "RST Tree Preprocessing"

Cohesion: 0.21
Nodes (13): buildTree(), buildTreeThiago(), checkcontent(), convert_parens_in_rst_tree_str(), createtext(), processtext(), Preprocessing token list for filtering '(' and ')' in text (from DPLP, by…, Create text from a list of tokens (from DPLP, by Yangfeng Ji) :type lst: list… (+5 more)

### Community 84 - "Result Cache Keys"

Cohesion: 0.18
Nodes (14): Compute a stable hex key from source bytes + sorted knob parts. Values are…, result_cache_key(), _Node, parametrize, Path, Result-cache identity and persisted provenance regressions.,_StubParser, test_behavior_option_change_forces_cache_miss() (+6 more)

### Community 85 - "DMRST Data Manager"

Cohesion: 0.20
Nodes (8): collect(), BinaryTree, Node, Path, :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 86 - "RST Analysis Projections"

Cohesion: 0.21
Nodes (11): Project through the single shared ``RstAnalysis`` conversion., Project through the single shared ``RstAnalysis`` conversion., Project through the single shared ``RstAnalysis`` conversion., projection_to_format_analysis(), projection_to_rst_analysis(), ProjectionTree, E, R (+3 more)

### Community 87 - "Bottom-Up Transition Parser"

Cohesion: 0.23
Nodes (8): _Node, ParsingNetBottomUp, Any, Tensor, Bottom-up transition-based parser. This module reuses the encoder, segmenters…, Reconstructs the gold tree from pre-order traversal., Return gold transition sequence in postorder., ParsingNet

### Community 88 - "Razdel Offset Converter"

Cohesion: 0.40
Nodes (4): _OffsetToken, Protocol, Minimal razdel-token surface used by offset remapping., Build offset converter from a list of `razdel.Token` objects.

### Community 89 - "Tokenizer Compatibility Probing"

Cohesion: 0.19
Nodes (15): One pinned tokenizer's fast/parity/MPS compatibility evidence., Hashed Python/Transformers/MPS compatibility receipt for mandatory tokenizers., TokenizerCompatibilityReceipt, TokenizerProbeResult, _encoding_payload(), main(), _payload_hash(), probe_mandatory_tokenizers() (+7 more)

### Community 90 - "Runtime Provenance Helpers"

Cohesion: 0.16
Nodes (13): Shared runtime helpers for the format-native entry points. One home for the…, Backward-compatible name for installed semantic package version., Return the checkout commit, with dirty state, independently of SemVer., resolve_source_revision(), resolve_tool_version(), _clear_runtime_caches(), fixture, MonkeyPatch (+5 more)

### Community 91 - "UniRST Inventory IO"

Cohesion: 0.13
Nodes (17): _ensure_parent_module(), ensure_unirst_module_aliases(), load_relation_inventory_json(), parse_corpora_config(), Relation-inventory I/O for UniRST. Native format is JSON (or a plain…, Register Elena-era module paths so legacy pickles can unpickle ParserInput., ``config['data']['corpora']`` is sometimes a Python-literal string., relation_table_from_json_obj() (+9 more)

### Community 92 - "Parser Contract Tests"

Cohesion: 0.16
Nodes (12): _CapturingParser,_Node, MonkeyPatch, parametrize, Path, Wave 4 — construct-path kwargs + formats-extra isolation., Core ``isanlp_rst.parser`` must not require the formats extra., Stand-in for ``Parser`` that records constructor kwargs. (+4 more)

### Community 93 - "DMRST Data Loading"

Cohesion: 0.18
Nodes (12): Data, getLabelOrdered(), nucs_and_rels(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…, One batched parser example. Field order matches the historical constructor., parametrize (+4 more)

### Community 94 - "RST Quality Diagnostics"

Cohesion: 0.29
Nodes (12): _discover(), DocMetrics,_format_of(), main(),_metrics(), _parse(),_print_table(), Any (+4 more)

### Community 95 - "Fixture Parity Verification"

Cohesion: 0.22
Nodes (12): FixtureParityError, FixtureParityReceipt, _GithubEntry,_Manifest, BaseModel, RuntimeError, Verify local DocLang fixtures against an immutable upstream GitHub commit., Raised when local, manifest, and upstream fixture authority diverge. (+4 more)

### Community 96 - "RS3 Document Rendering"

Cohesion: 0.10
Nodes (27): AsyncBrowser, AsyncPage, AsyncPlaywright, Browser, PathLike, T, Render an ``.rs3`` file to PNG (works in both sync and async environments)., Render an ``.rs3`` file to PDF. The viewer exposes only an asynchronous PDF… (+19 more)

### Community 97 - "Speckit Analyze Skill"

Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 98 - "Multi-Run Experiment Runner"

Cohesion: 0.23
Nodes (5): MultipleRunnerGeneral, Script for multiple runs of experiments. For monolingual experiments run: #…, Running training with second language injection of ``mixed`` %, :param corpus: (str) - 'GUM' or 'RST-DT' :param lang: (str) - 'en' or 'ru'…, range

### Community 99 - "RNN Sequence Encoder"

Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 100 - "MIME Type Registration"

Cohesion: 0.21
Nodes (9): ensure_docling_mimetypes(), Platform MIME registrations required by Docling JSON validation. ``docling-…, Idempotently register MIME types Docling ImageRef may require., Pytest session fixtures / env bootstrap for the isanlp_rst suite. Registers…, _clear_webp_mapping(), Production MIME registration for Docling ImageRef validation., Remove``.webp`` from the stdlib MIME map; return prior value if any., Production registration — not conftest — must make WebP fixtures load. Forces… (+1 more)

### Community 101 - "RNN Sequence Encoder"

Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 102 - "Torch Dtype Normalization"

Cohesion: 0.20
Nodes (10): dtype, Normalise a dtype spec to a ``torch.dtype``. Accepts: * ``None`` -> ``float32``…, parametrize, Default is fp32 on every device — measured fp32 wins on MPS for typical inputs;…, test_resolve_dtype_default_is_float32(), test_resolve_dtype_passthrough(), test_resolve_dtype_string_parsing(), test_resolve_dtype_unknown_string_raises() (+2 more)

### Community 103 - "Baseline Reproduction Gates"

Cohesion: 0.22
Nodes (12): BaselineReproductionDiagnosis, ErstBaselineAuthorityReceipt, Hashed authority and blocker evidence for the published eRST baseline., Hashed evidence that no baseline or architecture run was permitted., diagnose_reproduction_gate(), main(), Path, Fail-closed entry point for the published eRST baseline reproduction gate. (+4 more)

### Community 104 - "Adversarial Discriminator Module"

Cohesion: 0.20
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 *19* 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 105 - "RS3 to HTML Conversion"

Cohesion: 0.33
Nodes (6): Convert an ``.rs3`` file into HTML. Parameters ---------- rs3_path: Path to the…, to_html(), Path, Unit tests for viewer convenience helpers in ``isanlp_rst``., When ``html_path`` is set, ``to_html`` must write the file AND return the HTML…, test_to_html_returns_string_and_writes_file()

### Community 106 - "Multi-Run Experiment Runner"

Cohesion: 0.25
Nodes (4): MultipleRunnerGeneral, Script for multiple runs of experiments. For monolingual experiments run: #…, Running training with second language injection of ``mixed`` %, :param corpora: corpus names, e.g. ['GUM'] or ['RST-DT'] :param lang: 'en' or…

### Community 107 - "Repository Cleanup Script"

Cohesion: 0.31
Nodes (10): collect_junk(),_display(), is_junk_dir(), is_junk_file(), main(), Path, Remove regenerable junk from the repo: bytecode, tool caches, temp files. Does…, Delete ``paths``. Returns the number of paths acted on. (+2 more)

### Community 108 - "Parser Integration Tests"

Cohesion: 0.23
Nodes (9): ErstCapabilityError, A requested eRST completion capability has no validated bundle., DummyPredictor, DiscourseUnit, MonkeyPatch, Unit tests for Parser.parse_document integration., test_du_to_analysis_nuclearity_and_relations(), test_parse_document_from_edus_requires_validated_erst_bundle() (+1 more)

### Community 109 - "SDLC Workflow Skills"

Cohesion: 0.24
Nodes (10): speckit-clarify, speckit-converge, speckit-implement, speckit-plan, speckit-specify, speckit-tasks, DocLang-native RST Plan, Docling-native RST Build Plan (+2 more)

### Community 110 - "Cleanup Script Tests"

Cohesion: 0.29
Nodes (8): fixture, Path, Unit tests for ``scripts/cleanup.py`` (stdlib-only project cleaner)., test_collects_bytecode_caches_and_temp_not_source(), test_dry_run_does_not_delete(), test_remove_deletes_junk_keeps_source_and_protected(), test_skips_git_and_pixi_trees(), tree()

### Community 111 - "Checkpoint Verification Tool"

Cohesion: 0.32
Nodes (7): ErstCheckpointVerificationReceipt, Machine-readable proof that a bundle reloaded and passed its graph vector., main(), Path, Fail-closed clean-process verifier for an eRST completion bundle., Strict-reload a bundle, run its test vector, and emit a typed receipt., verify_checkpoint()

### Community 112 - "RS3 Annotation Parsing"

Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element,_ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 113 - "RS3 Annotation Parsing"

Cohesion: 0.29
Nodes (7): getRelationsType(), parseXML(), _Element,_ElementTree, Path, Write files similar to the .edus files in the RST DT for the other RST…, writeEdus()

### Community 115 - "Discourse Unit Mocks"

Cohesion: 0.28
Nodes (8): _FakeNode,_Predictor, Stand-in for isanlp.DiscourseUnit with the attributes used by remap., Minimal concrete subclass (BasePredictor is ABC)., Unary node = DUConverter bug; surface it rather than patch it., test_remap_tree_offsets_binary(), test_remap_tree_offsets_leaf(), test_remap_tree_offsets_unary_raises()

### Community 116 - "Fixture Parity Tests"

Cohesion: 0.22
Nodes (6): BaseModel, parametrize, Path, Pinned upstream parity and locked-validator tests for DocLang fixtures., test_locked_doclang_validator_accepts_every_upstream_fixture(),_UpstreamManifest

### Community 117 - "File Access Linter"

Cohesion: 0.43
Nodes (6): is_content_free(), looks_like_path(), main(), offending_tool(), Return (tool, path) for the first file-reading invocation, else None.…, True when this invocation cannot print a line of file content. Every argument…

### Community 118 - "GUM Corpus Identity"

Cohesion: 0.33
Nodes (3): BaselineCorpusSource, field_validator, Text-free identity for one exact GUM V9.2.0 comparison document.

### Community 119 - "System Disposition Validation"

Cohesion: 0.21
Nodes (7): _canonical_hash(), MandatorySystemDisposition, PromotionGateResult, BaseModel, model_validator, No-run status for one system that remains mandatory in the frozen protocol., One promotion threshold and the evidence that determined it.

### Community 120 - "EDU File Reader"

Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 121 - "Project Data Model"

Cohesion: 0.08
Nodes (24): ChampionManifest, Checkpoint boundary, Corpus boundaries, CorpusDocumentReceipt, CorpusLoadFailure, CorpusLoadReceipt, Data Model, DiscourseSignal (+16 more)

### Community 122 - "Markdown Manifest Linter"

Cohesion: 0.48
Nodes (6): _is_approved_exclusion(), main(),_manifest_paths(), Verify and lint the complete repository Markdown manifest.,_repository_markdown(), verify_manifest()

### Community 123 - "DMRST Config Reader"

Cohesion: 0.33
Nodes (3): ConfigReader, Any, Path

### Community 124 - "DiscourseSignal"

Cohesion: 0.12
Nodes (29): DiscourseSignal, BaseModel, Immutable identity of the detector or source that produced a signal., Typed, anchored discourse signal; overlaps are explicitly permitted., SignalDetectorProvenance, AnnotationStatusEnum, How a discourse signal entered the analysis., Status or origin of an annotation. (+21 more)

### Community 125 - "Universal Parser Config"

Cohesion: 0.33
Nodes (3): ConfigReader, Any, Path

### Community 126 - "Parser Performance Benchmark"

Cohesion: 0.47
Nodes (5): main(), Performance benchmark for isanlp_rst across devices and dtypes. Usage: pixi run…, Run parser n times after a warm-up. Return median seconds and tree shape.,_shape(), _time_parse()

### Community 127 - "GUM Gold Validation"

Cohesion: 0.13
Nodes (21): gold_edus(),_gold_path(), gumrrg_cpu(), fixture, parametrize, Path, slow, GUM gold RST fixtures — real documents with human trees to compare against. The… (+13 more)

### Community 128 - "CUDA Smoke Test"

Cohesion: 0.60
Nodes (4): _assert_aligned(), _collect_leaves(), main(), CUDA verification script — to be run on a real NVIDIA host. Usage: pixi run…

### Community 129 - "Architecture Decision Records"

Cohesion: 0.22
Nodes (8): Open RST Real World Quality, Open Schema Detail Verifications, Open V1 Policy Knobs, Project Status, Upstream Issue 14, Verified Docling Core API, Verified Docling Schema, Architecture

### Community 130 - "DocLang Source Provenance"

Cohesion: 0.13
Nodes (19): Any, Capture lightweight provenance from the parsed tree. Reports: declared…, _source_origin(), parse_doclang_xml(), _ElementTree, Path, Parse the ``.dclg`` file at ``path`` and return the ElementTree. Uses a…, ``ok_comprehensive.dclg`` has ``<head>`` with several children (title, author,… (+11 more)

### Community 131 - "Corpus Loading Models"

Cohesion: 0.14
Nodes (24): CorpusDocumentReceipt, CorpusLicenseClass, CorpusLoadFailure, CorpusPartition, ErstCheckpointFileRole, HardNegativeStrategy, StrEnum, Pydantic boundaries for private GUM/eRST corpus loading and partitioning. (+16 more)

### Community 133 - "GUM Parser Fixture"

Cohesion: 0.67
Nodes (3): parser(), fixture, Construct gumrrg parser once for the slow tests.

### Community 134 - "Project Roadmap"

Cohesion: 0.11
Nodes (18): Baseline gate, Corpus integrity and partitions, Dependencies and execution order, DocLang current-spec compliance, Formal decoder, labels, scorer, Implementation strategy, Mandatory research systems, Phase 1: Governed baseline and dependency authority (+10 more)

### Community 138 - "Docling Parsing Tests"

Cohesion: 0.17
Nodes (18): parse_docling(), Path, Parse a Docling JSON file and return its RST analysis. Args: path: filesystem…, slow, Two-level invariant: cells live in table_analyses, the synthetic marker lives…, The PPTX fixture has 20 tables — analyses exist for those with non-empty cells,…, Every relation ref points to a self_ref that exists in the source., Two calls with the same injected parser return consistent results. (+10 more)

### Community 139 - "DocLang Specification Docs"

Cohesion: 0.50
Nodes (3): Verified DocLang Fixtures, Verified DocLang Spec, Docling-native RST output Plan

### Community 143 - "Device-Aware Initialization"

Cohesion: 0.19
Nodes (8): orthogonal_(), Tensor, Device-aware orthogonal weight initialisation for Apple Silicon MPS. PyTorch's…, Drop-in replacement for ``torch.nn.init.orthogonal_`` that is safe on Apple…, parametrize, PyTorch RNN dropout is inter-layer only. A 1-layer LSTM with non-zero dropout…, test_tony_one_layer_lstm_does_not_warn(), test_tony_stacked_lstm_keeps_dropout()

### Community 144 - "Speckit Converge Skill"

Cohesion: 0.12
Nodes (15): 1. Initialize Convergence Context, 2. Load Artifacts (Progressive Disclosure), 3. Build the Intent Inventory, 4. Assess the Codebase and Classify Findings, 5. Assign Severity, 6. Present the In-Session Findings Summary, 7. Append Convergence Tasks (or report converged), 8. Provide Next Actions (Handoff) (+7 more)

### Community 152 - "Speckit Converge Skill"

Cohesion: 0.12
Nodes (15): 1. Initialize Convergence Context, 2. Load Artifacts (Progressive Disclosure), 3. Build the Intent Inventory, 4. Assess the Codebase and Classify Findings, 5. Assign Severity, 6. Present the In-Session Findings Summary, 7. Append Convergence Tasks (or report converged), 8. Provide Next Actions (Handoff) (+7 more)

### Community 154 - "Markdown Parsing Guide"

Cohesion: 0.15
Nodes (12): Addressing scheme, Batch parsing — inject one Parser, add a cache, Errors to expect, Front-matter, Group relations by boundary, Markdown-native RST output — walkthrough, Quick start, Reconstruct the tree (+4 more)

### Community 168 - "Implementation Planning"

Cohesion: 0.08
Nodes (22): Content Quality, Readiness, Requirement Completeness, Specification Quality Checklist: isanlp-rst 4.0.0 Forensic Remediation, Complexity Tracking, Constitution Check, Dependency-ordered implementation, Documentation for this feature (+14 more)

### Community 171 - "Table Harvesting"

Cohesion: 0.18
Nodes (15): harvest_docling_tables(), TableHarvest, Produce one ``TableHarvest`` per ``TableItem``, in ``doc.tables`` order. Cell…, markdown_doc(), pdf_doc(), pptx_doc(), fixture, Unit tests for the docling harvesters (main text + per-table). (+7 more)

### Community 172 - "RST Tree Mapping"

Cohesion: 0.18
Nodes (14): flatten_tree(),_make_edu(), Any, Boundary, HarvestSpan, RstEdu, RstRelation, Map an RST tree's character-offset spans to Docling self_refs. Thin format… (+6 more)

### Community 173 - "Schema Compatibility Tests"

Cohesion: 0.17
Nodes (15): parametrize, Path, Compatibility guard: do we still read CURRENT Docling / DocLang output? The…, Return the XML namespace declared on a fixture's root element (or '')., Guard against the guard silently no-opping if fixtures are moved/renamed — an…, Each fixture's declared Docling schema version must equal the installed…, The installed docling-core must validate-load each fixture AND our harvester…, Our ``DOCLANG_NS`` constant must match the namespace the installed doclang… (+7 more)

### Community 174 - "RST Parser Metrics"

Cohesion: 0.25
Nodes (12): calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement(), get_micro_metrics(), get_seg_measure() (+4 more)

### Community 175 - "Batch Parsing Documentation"

Cohesion: 0.14
Nodes (14): Batch parsing — inject one Parser, Boundary kinds, DocLang-native RST output — walkthrough, Errors to expect, Filter for within-boundary relations only, Group relations by boundary, How addresses work — local-name canonical XPath, Quick start (+6 more)

### Community 176 - "Feature Specification Template"

Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 177 - "CRF Layer Implementation"

Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from <https://github.com/kmkurn/pytorch-…>, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 178 - "Adversarial Discriminator Module"

Cohesion: 0.18
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 *19* 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 179 - "Experiment Protocol Documentation"

Cohesion: 0.17
Nodes (11): Authorities and isolation, Calibration and decoding, Frozen eRST Experiment Protocol, Mandatory systems, Promotion decision, Reproduced baseline gate, Required ablations, Resource measurement (+3 more)

### Community 180 - "Token Offset Alignment"

Cohesion: 0.17
Nodes (10): Build offset converter from word tokens and optional (start, end) pairs. If…, Best-effort alignment of already-tokenized `tokens` to raw `text`. Used when…, The fix: a missing token must raise rather than silently fall back., Token at the very end should match cleanly., test_guess_token_offsets_at_text_boundary(), test_guess_token_offsets_raises_on_miss(), test_guess_token_offsets_simple(), test_guess_token_offsets_token_longer_than_text() (+2 more)

### Community 181 - "Planning Skill Definition"

Cohesion: 0.18
Nodes (10): Completion Report, Done When, Key rules, Mandatory Post-Execution Hooks, Outline, Phase 0: Outline & Research, Phase 1: Design & Contracts, Phases (+2 more)

### Community 182 - "Specification Skill Definition"

Cohesion: 0.18
Nodes (10): Completion Report, Done When, For AI Generation, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, Quick Guidelines, Section Requirements (+2 more)

### Community 183 - "Task Generation Skill"

Cohesion: 0.18
Nodes (10): Checklist Format (REQUIRED), Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Phase Structure, Pre-Execution Checks, Task Generation Rules (+2 more)

### Community 184 - "Boundary Design Decisions"

Cohesion: 0.18
Nodes (10): `boundary_memberships` semantics, `coalesce_speaker_turns=False`, Degenerate cases, Empty boundary, How to apply, Page boundaries, Picture-caption vs OCR-text disambiguation, Section nesting (parent_boundary_id) (+2 more)

### Community 185 - "Claude Planning Skill"

Cohesion: 0.18
Nodes (10): Completion Report, Done When, Key rules, Mandatory Post-Execution Hooks, Outline, Phase 0: Outline & Research, Phase 1: Design & Contracts, Phases (+2 more)

### Community 186 - "Claude Specification Skill"

Cohesion: 0.18
Nodes (10): Completion Report, Done When, For AI Generation, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, Quick Guidelines, Section Requirements (+2 more)

### Community 187 - "Claude Task Skill"

Cohesion: 0.18
Nodes (10): Checklist Format (REQUIRED), Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Phase Structure, Pre-Execution Checks, Task Generation Rules (+2 more)

### Community 188 - "Docling Harvester Implementation"

Cohesion: 0.18
Nodes (10): _label_value(), _picture_description(), PictureItem, Harvest text from a DoclingDocument for RST parsing. Two harvesters: -…, Return the string value of a Docling enum label, or str(thing)., Return ``picture.meta.description.text`` when present and non-empty., HarvestResult, Concatenated document harvest and its source-address spans. (+2 more)

### Community 189 - "Project Constitution Template"

Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 190 - "Research and Authority Ledger"

Cohesion: 0.18
Nodes (10): DocLang contract decision, Docling contract decision, Environment and credential boundary, eRST formal and benchmark authority, GUM corpus and licence decision, Model and literature scan, Rejected approaches, Release dependency decisions (+2 more)

### Community 191 - "Docling Fixture Documentation"

Cohesion: 0.18
Nodes (10): Cross-fixture claims (sample-scoped, not universal), Docling JSON fixtures, File-by-file verified facts, How facts were verified, `markdown.docling.json` — 24 KB, `pdf.docling.json` — 965 KB, `pptx.docling.json` — 333 KB, Provenance (+2 more)

### Community 192 - "RST Output Walkthrough"

Cohesion: 0.20
Nodes (10): Batch parsing — inject one Parser, Docling-native RST output — walkthrough, Errors to expect, Filter for within-boundary relations only, Group relations by boundary, Quick start, Reconstruct the tree, Table analyses (two-level) (+2 more)

### Community 193 - "Source Origin Serialization"

Cohesion: 0.40
Nodes (5): Any, Serialise ``doc.origin`` (a Pydantic model) to a JSON-safe dict. Returns ``{}``…, _serialise_source_origin(), test_serialise_source_origin_none_returns_empty_dict(), test_serialise_source_origin_real_fixture_has_mimetype_and_hash()

### Community 194 - "Project Design Records"

Cohesion: 0.22
Nodes (9): Design decisions (Docling work), Feedback (HARD-RULE enforcement), MEMORY.md — isanlp_rst, Open design questions, Project framing, Resolved questions (kept as historical record), Upstream tracking, Verified facts (DocLang work) (+1 more)

### Community 195 - "Output Schema Specifics"

Cohesion: 0.22
Nodes (8): `edus[]` order, Empty / minimal cases, How to apply, Id space, JSON serialisation specifics, `relations[]` order, `source` field format, `tool_version` format

### Community 196 - "Implementation Plan Template"

Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 197 - "Rich Markdown Elements"

Cohesion: 0.22
Nodes (8): Blockquote, Closing, Code, Image, List, Overview, Raw HTML, Table

### Community 198 - "Checklist Skill Definition"

Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 199 - "Claude Checklist Skill"

Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 200 - "Cursor Checklist Skill"

Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 201 - "Verification Quickstart Guide"

Cohesion: 0.25
Nodes (7): Architecture screening and final evaluation, Corpus and baseline, Environment, Exact release candidate, Focused contract validation, Publication close, Verification Quickstart

### Community 202 - "Clarification Skill Definition"

Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 203 - "Implementation Skill Definition"

Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 204 - "Claude Clarification Skill"

Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 205 - "Claude Implementation Skill"

Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 206 - "RST Result Serialization"

Cohesion: 0.33
Nodes (5): DoclingRstResult, Any, Return JSON-shaped plain data., Serialize deterministically without non-JSON dataclass values., Top-level output of ``parse_docling``.

### Community 207 - "EDU File Reader"

Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 208 - "Constitution Skill Definition"

Cohesion: 0.33
Nodes (5): Outline, Post-Execution Checks, Pre-Execution Checks, Scope Guard, User Input

### Community 209 - "Claude Constitution Skill"

Cohesion: 0.33
Nodes (5): Outline, Post-Execution Checks, Pre-Execution Checks, Scope Guard, User Input

### Community 210 - "Multi-Level Markdown Structure"

Cohesion: 0.33
Nodes (5): A third-level heading, First subsection, Second chapter, Second subsection, Top-level chapter

### Community 211 - "Markdown Fixture Index"

Cohesion: 0.33
Nodes (5): `gfm-rich.md`, `golden_two_para.rst.json`, Markdown fixtures, `minimal.md`, `multi-level.md`

### Community 212 - "Task to Issue Skill"

Cohesion: 0.40
Nodes (4): Outline, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 213 - "Claude Task to Issue"

Cohesion: 0.40
Nodes (4): Outline, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 214 - "JSON Serialization Helpers"

Cohesion: 0.40
Nodes (3): Any, Return JSON-shaped plain data., Serialize deterministically without non-JSON dataclass values.

### Community 215 - "Checklist Template"

Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

### Community 216 - "Table Invariant Tests"

Cohesion: 0.50
Nodes (5): FixtureRequest, parametrize, Two-level invariant: tables live in their own harvests; the main document…, test_main_harvest_never_contains_table_refs(), test_offsets_match_full_text()

## Knowledge Gaps

- **432 isolated node(s):** `ChampionManifest`, `CorpusDocumentReceipt`, `CorpusLoadFailure`, `CorpusLoadReceipt`, `DiscourseSignal` (+427 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions

*Questions this graph is uniquely positioned to answer:*

- **Why does `Parser` connect `Parser Public API` to `RST Analysis Models`, `Parser Family Resolution`, `Parse Result Helpers`, `Parser Integration Tests`, `EDU Segmentation Dataset`, `Model Signature Detection`?**
  *High betweenness centrality (0.004) - this node is a cross-community bridge.*
- **Why does `PredictorDMRST` connect `DMRST Predictor` to `Base Predictor Logic`, `RST Parsing Logic`?**
  *High betweenness centrality (0.001) - this node is a cross-community bridge.*
- **Why does `parse_doclang()` connect `DocLang XML Parsing` to `Result Caching System`, `DocLang Source Provenance`, `DocLang Boundary Detection`, `DocLang Eligibility Policy`, `Parse Result Helpers`, `RST Tree Mapping`, `DocLang Text Harvester`, `DocLang Boundary Tests`, `Result Cache Keys`, `Parser Public API`, `Runtime Provenance Helpers`?**
  *High betweenness centrality (0.001) - this node is a cross-community bridge.*
- **Are the 6 inferred relationships involving `Parser` (e.g. with `CompleterConfig` and `ErstCompleter`) actually correct?**
  *`Parser` has 6 INFERRED edges - model-reasoned connections that need verification.*
- **Are the 4 inferred relationships involving `RstAnalysis` (e.g. with `ProvenanceRecord` and `FailureCodeEnum`) actually correct?**
  *`RstAnalysis` has 4 INFERRED edges - model-reasoned connections that need verification.*
- **Are the 8 inferred relationships involving `parse_doclang()` (e.g. with `DoclangEligibility` and `EmptyDoclangError`) actually correct?**
  *`parse_doclang()` has 8 INFERRED edges - model-reasoned connections that need verification.*
- **What connects `ChampionManifest`, `CorpusDocumentReceipt`, `CorpusLoadFailure` to the rest of the system?**
  *432 weakly-connected nodes found - possible documentation gaps or missing edges.*
