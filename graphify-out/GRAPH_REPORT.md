# Graph Report - isanlp_rst  (2026-08-25)

## Corpus Check

- cluster-only mode — file stats not available

## Summary

- 4103 nodes · 9827 edges · 202 communities (154 shown, 48 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1074 edges (avg confidence: 0.56)
- Token cost: 12,807 input · 2,476 output

## Graph Freshness

- Built from commit: `bf953a73`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)

- RST Analysis Models
- RST Enumerations
- Discourse Tree Structures
- Markdown Entry Points
- Frontend Assets
- DocLang XML Parsing
- Docling JSON Parsing
- RST Tree Rendering
- EDU Segmentation Dataset
- DocLang Boundary Detection
- Markdown Boundary Mapping
- Content Layer Detection
- DocLang Text Harvesting
- Analysis Data Contracts
- RS4 Format Converters
- Markdown Harvester Tests
- Base Predictor Logic
- RSTWeb SQL Operations
- Model Validation Logic
- DocLang Boundary Tests
- Universal Parser Utils
- Corpus Loading Contracts
- Docling Span Mapping
- Thiago Parser Utils
- RST Viewer Classes
- DMRST RS3 Utils
- Model Integration Tests
- Structural Data Protocols
- Secondary Relation Completion
- eRST Checkpoint State
- DocLang Eligibility Policy
- Universal Parser Common
- Parser Evaluation Metrics
- Research Authority Models
- GUM Corpus Authority
- Data Management Logic
- Research Promotion Logic
- Data Management Logic
- DMRST Corpus Data
- Universal Parser Data
- Environment Compatibility Probes
- Model Identity Helpers
- Compute Device Resolution
- DMRST Common Utils
- DocLang Tree Projection
- DocLang Span Mapping
- Inventory Serialization Security
- Markdown Boundary Detection
- Shell Utility Scripts
- Secondary Edge Candidates
- UniRST Predictor Logic
- DocLang Table Harvesting
- Docling Text Harvesting
- DMRST Tree Utils
- Docling Error Handling
- Parser Batch Data
- Discourse Signal Models
- RST Structure UI
- Public Parser API
- Pydantic Tree Serialization
- DMRST Predictor Logic
- Markdown Loader Logic
- Checkpoint Metadata Evidence
- Neural Secondary Scorer
- Format Analysis Schema
- BiMPM Classifier Modules
- End-to-End Smoke Tests
- Result Caching Logic
- Tree String Converter
- DMRST Training Runner
- Relation Inventory IO
- Source Identity Validation
- EDU Segmenter Models
- Markdown Text Harvester
- EDU Segmenter Models
- GUM Gold Validation
- Format Projection Tests
- Parser Family Resolution
- Secondary Scorer Training
- Parse Result Helpers
- GUM Gold Validator
- DocLang Source Provenance
- Checkpoint Family Detection
- Parsing Network Logic
- Parsing Network Logic
- BiMPM Attention Module
- Result Cache Identity
- Candidate Selection Logic
- Baseline Association Serialization
- DMRST Binary Tree
- Universal Binary Tree
- Bottom-Up Transition Parser
- Schema Compatibility Tests
- Decoder RNN Modules
- Markdown Error Handling
- Runtime Provenance Helpers
- Wave 4 Integration
- Tree Flattening Utils
- Parser Integration Tests
- Viewer Security Hardening
- BiMPM Encoder Module
- eRST Checkpoint Management
- RST Tree Construction
- RST Quality Diagnostics
- DocLang Fixture Verification
- DMRST Label Ordering
- RNN Sequence Encoder
- CRF Sequence Labeling
- Adversarial Discriminator
- RNN Sequence Encoder
- CRF Sequence Labeling
- Torch Dtype Normalization
- Multi-Run Experiment Runner
- Default Label Classifier
- Repository Cleanup Script
- Docling Table Harvesting
- Cleanup Unit Tests
- RS3 Annotation Parsing
- Discourse Tree Flattening
- Docling Smoke Tests
- RS3 Annotation Parsing
- GUM Validation Metrics
- Discourse Unit Mocking
- DocLang Parity Tests
- Checkpoint Verification Receipt
- Docling Text Harvester
- HTML Viewer Export
- File Access Linter
- Speckit Workflow Stages
- EDU File Utilities
- Markdown RST Output
- Parser Protocol Interface
- Markdown Manifest Verification
- Schema Verification Status
- DMRST Config Reader
- Universal Parser Config
- Performance Benchmarking
- Token Offset Conversion
- Source Origin Serialization
- Span Character Offsets
- CUDA Verification Script
- Table Harvest Invariants
- LSTM Dropout Tests
- Speckit Task Management
- CUDA Device Validation
- RST Build Planning
- Custom Tokenizer
- Custom Tokenizer
- GUMRRG Parser Fixture
- GUMRRG Parser Fixture
- Agent Instructions
- Assumptions Check Script
- Design Decisions
- Document Memory Policy
- Parser Policy Knobs
- DocLang Specification Status
- Speckit Planning
- Cleanup Shell Script
- Forensic Remediation Report
- Parser Documentation
- Speckit Clarification
- Docling Integration Decision
- Project Status
- Upstream Issue Tracking
- Architecture Overview
- Code Standards
- Command Reference
- No Assumptions Rule
- Speckit Clarification
- Speckit Constitution
- Speckit Task Automation
- Speckit Constitution
- Speckit Checklist
- DocLang Versioning
- Docling Core Versioning
- Markdown Walkthrough
- RST Output Plan
- Long-Input Parsing Plan
- Markdown Output Plan
- Capability Platform Plan
- English Tree Visualization
- Russian Tree Visualization
- Render Code Example
- Assumptions Rule Feedback
- Remediation Data Model
- Experiment Protocol
- GUM Corpus
- GUM Corpus Version
- IsaNLP DocLang Module
- IsaNLP Docling Module
- IsaNLP RST Package
- Remediation Implementation Plan
- Research Authority Ledger
- Task to Issue Conversion

## God Nodes (most connected - your core abstractions)

1. `Parser` - 112 edges
2. `RstAnalysis` - 103 edges
3. `SpanNode` - 68 edges
4. `parse_doclang()` - 61 edges
5. `parse_markdown()` - 60 edges
6. `parse_docling()` - 60 edges
7. `RstDocument` - 58 edges
8. `RstNode` - 56 edges
9. `harvest_doclang_text()` - 51 edges
10. `BasePredictor` - 50 edges

## Surprising Connections (you probably didn't know these)

- `_Predictor` --uses--> `BasePredictor`  [INFERRED]
  tests/test_base_predictor.py → isanlp_rst/base_predictor.py
- `_BundleInputs` --uses--> `NeuralSecondaryEdgeScorer`  [INFERRED]
  tests/test_erst_checkpoint.py → isanlp_rst/erst/neural_scorer.py
- `_BundleInputs` --uses--> `RuleBasedSignalDetector`  [INFERRED]
  tests/test_erst_checkpoint.py → isanlp_rst/erst/signals.py
- `TestResolveFamily` --uses--> `Parser`  [INFERRED]
  tests/test_parser_facade.py → isanlp_rst/parser.py
- `GumGoldValidator` --uses--> `RS4Document`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/erst/rs4.py

## Import Cycles

- None detected.

## Hyperedges (group relationships)

- **Native Document Format Support** — doclang_native_plan, docling_native_plan, docs_examples_markdown_native_walkthrough [EXTRACTED 0.90]
- **DocLang Integration Design** — claude_memory_verified_doclang_fixtures, claude_memory_verified_doclang_spec [EXTRACTED 1.00]
- **Docling-Native RST Design** — claude_memory_open_output_schema_specifics, claude_memory_open_parse_per_boundary, claude_memory_open_parser_facade_unverified, claude_memory_open_rst_real_world_quality, claude_memory_open_schema_detail_verifications, claude_memory_open_v1_policy_knobs, claude_memory_verified_docling_core_api, claude_memory_verified_docling_schema [EXTRACTED 1.00]
- **Spec-Kit SDD Lifecycle** — specify_skill, plan_skill, tasks_skill, implement_skill, clarify_skill, converge_skill [EXTRACTED 1.00]
- **Spec Kit Core Workflow** — claude_skills_speckit_specify_skill, claude_skills_speckit_plan_skill, claude_skills_speckit_tasks_skill, claude_skills_speckit_implement_skill, claude_skills_speckit_converge_skill [EXTRACTED 1.00]
- **Spec Kit Core Workflow** — claude_skills_speckit_specify_skill, claude_skills_speckit_clarify_skill, claude_skills_speckit_plan_skill, claude_skills_speckit_tasks_skill, claude_skills_speckit_implement_skill, claude_skills_speckit_converge_skill [EXTRACTED]

## Communities (202 total, 48 thin omitted)

### Community 0 - "RST Analysis Models"

Cohesion: 0.04
Nodes (71): Counter, DirectedSpanKey, Complete discourse analysis result., Find the root node if present., Look up a node by its ID., RstAnalysis, NodeKindEnum, Discourse tree or graph node kind. (+63 more)

### Community 1 - "RST Enumerations"

Cohesion: 0.04
Nodes (71): AnnotationStatusEnum, CapabilityStatusEnum, ConfidenceKindEnum, DeviceEnum, EdgeKindEnum, InputModeEnum, MappingKindEnum, NuclearityPatternEnum (+63 more)

### Community 2 - "Discourse Tree Structures"

Cohesion: 0.06
Nodes (65): PrimaryRelationEdge, Execution timing profile in milliseconds., A node in a discourse tree or graph., A directed primary rhetorical relation edge with nuclearity., RstNode, TimingRecord, DocumentToken, Edu (+57 more)

### Community 3 - "Markdown Entry Points"

Cohesion: 0.06
Nodes (61): parse_markdown(), Any, Path, Build the ``source_origin`` block for the result., Parse a markdown file and return its RST analysis. Args: path: filesystem path…,_source_origin(),_Node, Path (+53 more)

### Community 4 - "Frontend Assets"

Cohesion: 0.06
Nodes (42): ba(), Ea(), Fa(), fb(), ga(), ha(), b(), hb() (+34 more)

### Community 5 - "DocLang XML Parsing"

Cohesion: 0.06
Nodes (53): parse_doclang(), Parse a DocLang XML file and return its RST analysis. Args: path: filesystem…, EmptyDoclangError, EmptyHarvestError, The harvest produced no text (e.g. a tables-only document)., The loaded DocLang document has no harvestable body content., MonkeyPatch, Path (+45 more)

### Community 6 - "Docling JSON Parsing"

Cohesion: 0.08
Nodes (52): parse_docling(), Path, Parse a Docling JSON file and return its RST analysis. Args: path: filesystem…,_minimal_docling_json(), _Node, Path, slow, Unit + integration tests for ``isanlp_rst.docling.parse_docling``. Fast unit… (+44 more)

### Community 7 - "RST Tree Rendering"

Cohesion: 0.06
Nodes (53): AsyncBrowser, AsyncPage, AsyncPlaywright, Browser, IO, T, Render an RST tree and, optionally, display it inline. This is a light-weight…, Render an ``.rs3`` file to PNG (works in both sync and async environments). (+45 more)

### Community 8 - "EDU Segmentation Dataset"

Cohesion: 0.06
Nodes (46): inference_mode, EduSegmentationDataset, parse_disrpt_tok_file(), parse_rs4_to_sentences(), Any, Dataset, Path, Tensor (+38 more)

### Community 9 - "DocLang Boundary Detection"

Cohesion: 0.07
Nodes (55): _detect_document_fallback(),_detect_field_region_boundaries(),_detect_group_boundaries(), _detect_heading_boundaries(),_detect_page_boundaries(), _detect_table_boundaries(),_harvest_eligible_xpaths(), _is_within() (+47 more)

### Community 10 - "Markdown Boundary Mapping"

Cohesion: 0.08
Nodes (53): Detect structural boundaries in a markdown harvest. Boundaries are derived from…, Markdown-native RST parsing for isanlp_rst. Public API: -…, compute_overlap_refs(), flatten_tree(), _make_edu(), Any, Boundary, HarvestSpan (+45 more)

### Community 11 - "Content Layer Detection"

Cohesion: 0.08
Nodes (55): ContentLayer, _content_layers(), detect_boundaries(),_detect_pptx_slide_boundaries(),_detect_section_boundaries(), _detect_table_boundaries(),_detect_vtt_turn_boundaries(),_iter_body_self_refs() (+47 more)

### Community 12 - "DocLang Text Harvesting"

Cohesion: 0.07
Nodes (56): harvest_doclang_text(), HarvestResult, Produce the main document harvest with per-span xpath mapping. Args: tree: a…, _ElementTree, parametrize, Unit tests for the doclang harvesters (main text + per-table)., ``ok_table_rectangular`` is table-only — the main harvest must be empty; the…, The fixture has 3 tables; harvests must match boundary numbering (document… (+48 more)

### Community 13 - "Analysis Data Contracts"

Cohesion: 0.09
Nodes (46): Discourse analysis result models and graph structures., ProvenanceRecord, Document input models and coordinate representation., Provenance pointer to the source document., Provenance and derivation record., SourceReference, FailureCodeEnum, InputFidelityEnum (+38 more)

### Community 14 - "RS4 Format Converters"

Cohesion: 0.09
Nodes (42): analysis_to_rs4(), Conversion utilities between RS4 DOM, DiscourseUnit, and typed contracts., Convert an RstDocument and RstAnalysis back into an RS4Document., Convert an RS4Document into an RstDocument and an RstAnalysis., rs4_to_document_and_analysis(), RS4 XML processing, eRST data structures, and converters., Any, Path (+34 more)

### Community 15 - "Markdown Harvester Tests"

Cohesion: 0.06
Nodes (53): _harvest(), Unit tests for ``isanlp_rst.markdown.harvester``. Tests focus on inline-…, h1..h6 must yield level 1..6 respectively., Three bullet items → three list_item spans, not one., Nested bullets join their parent item's text rather than emit separate spans —…, Paragraphs inside `>` become blockquote_paragraph, not paragraph., Negative-space: a plain para must not be classified as blockquote., A heading inside `>` is quoted content — it must not carry the plain `heading`… (+45 more)

### Community 16 - "Base Predictor Logic"

Cohesion: 0.06
Nodes (41): AbstractContextManager, BasePredictor, Any, Path, T, Mixin-style base with shared tokenization, batching and offset utils. Not…, Yield chunks of size `n` from `_list` (handles empty lists)., Build offset converter from word tokens and optional (start, end) pairs. If… (+33 more)

### Community 17 - "RSTWeb SQL Operations"

Cohesion: 0.13
Nodes (49): add_node(), add_seg(), count_children(), count_multinuc_children(), count_span_children(), delete_document(), delete_node(), generic_query() (+41 more)

### Community 18 - "Model Validation Logic"

Cohesion: 0.07
Nodes (13): field_validator, Require valid half-open anchors while retaining overlap and order., Require non-empty, unique raw relation labels., Require unique non-negative token identifiers without reordering.,_canonical_model_hash(), model_validator,_canonical_hash(), field_validator (+5 more)

### Community 19 - "DocLang Boundary Tests"

Cohesion: 0.07
Nodes (50): detect_boundaries(),_ElementTree, HarvestResult, Detect all structures using the exact policy and harvested membership., _ElementTree, parametrize, Path, Unit tests for ``isanlp_rst.doclang.boundaries.detect_boundaries``. (+42 more)

### Community 20 - "Universal Parser Utils"

Cohesion: 0.11
Nodes (47): RST tree node used by the universal parser corpus readers., SpanNode, areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU() (+39 more)

### Community 21 - "Corpus Loading Contracts"

Cohesion: 0.08
Nodes (44): CorpusAuthorityEntry, CorpusDocumentReceipt, CorpusLoadFailure, CorpusLoadReceipt, CorpusPartition, DecodeRejectionReason, ErstCheckpointFileRole, HardNegativeStrategy (+36 more)

### Community 22 - "Docling Span Mapping"

Cohesion: 0.14
Nodes (47): HarvestSpan, One eligible DocLang text span with parser-input coordinates., compute_overlap_refs(), Map an RST tree's character-offset spans to Docling self_refs. Thin format…, Return ``(refs, note)`` for the half-open range ``[start, end)``. Docling-…, HarvestSpan, One harvested Docling span with offsets into its parser input., FakeUnit (+39 more)

### Community 23 - "Thiago Parser Utils"

Cohesion: 0.09
Nodes (48): _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), buildTree(), buildTreeThiago(), checkcontent(), cleanChildren() (+40 more)

### Community 24 - "RST Viewer Classes"

Cohesion: 0.09
Nodes (39): Document, get_depth(), get_left_right(), NODE, NodeMap, RST tree node types and parent-chain attribute walks., EDU used by the segmenter, not by the structurer., Set graphical nesting depth of ``orig_node`` from the parent chain. RST… (+31 more)

### Community 25 - "DMRST RS3 Utils"

Cohesion: 0.10
Nodes (44): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+36 more)

### Community 26 - "Model Integration Tests"

Cohesion: 0.09
Nodes (45): _assert_aligned(), _collect_leaf_units(),_collect_leaves(), dmrst_gumrrg_cpu(), dmrst_rstdt_cpu(), dmrst_rstreebank_cpu(), fixture, parametrize (+37 more)

### Community 27 - "Structural Data Protocols"

Cohesion: 0.07
Nodes (35): ProjectedEduLike, ProjectedRelationLike, Protocol, Structural contract shared by all format-native EDU wire objects., Structural contract shared by all format-native relation wire objects., find_cdu(),_is_leaf(), Any (+27 more)

### Community 28 - "Secondary Relation Completion"

Cohesion: 0.09
Nodes (35): A directed secondary rhetorical relation edge without nuclearity., SecondaryRelationEdge, ErstDecoderConfig, ErstDecodeReceipt, Immutable threshold and raw-relation inventory for eRST decoding., Reconciled proof of threshold selection and formal eRST constraints., Any, Complete a classical primary tree into an eRST graph with signals and secondary… (+27 more)

### Community 29 - "eRST Checkpoint State"

Cohesion: 0.12
Nodes (42): ErstCalibrationState, ErstCheckpointBuildSpec, ErstCheckpointManifest, ErstCheckpointTestVector, ErstGraphComponentConfig, ErstScorerConfig, Dev-fitted edge calibration and decision threshold., Architecture fields required to reconstruct a scorer without network access. (+34 more)

### Community 30 - "DocLang Eligibility Policy"

Cohesion: 0.08
Nodes (30): DoclangEligibility, Single immutable eligibility policy for DocLang harvest and boundaries., All switches that determine text harvest and boundary membership., Return the DocLang layers admitted by this policy., Return whether ``layer`` contributes harvestable content., Return whether a semantic kind contributes to the main harvest., Path, ``parse_doclang`` entry point — load → harvest → boundaries → parse → flatten.… (+22 more)

### Community 31 - "Universal Parser Common"

Cohesion: 0.08
Nodes (41): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), Document, __getforminfo(), getLabelMapping() (+33 more)

### Community 32 - "Parser Evaluation Metrics"

Cohesion: 0.09
Nodes (29): calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement(), get_micro_metrics(), get_seg_measure() (+21 more)

### Community 33 - "Research Authority Models"

Cohesion: 0.11
Nodes (38): date, datetime, CorpusLicenseClass, Conservative release-safety class for underlying document text., AuthoritySearchEvidence, BaselineAuthorityBlocker, BaselineCorpusSource, ErstBaselineAuthorityReceipt (+30 more)

### Community 34 - "GUM Corpus Authority"

Cohesion: 0.11
Nodes (38): CorpusFailureType, GumCorpusAuthority, HardNegativeSamplingConfig, Hashed interpretation of pinned GUM split and licence authorities., Return the upstream authority entry for one exact document ID., Deterministic training-only hard-negative selection configuration., Stable machine-readable corpus failure categories., CorpusLoadError (+30 more)

### Community 35 - "Data Management Logic"

Cohesion: 0.10
Nodes (15): DataManager, ParserInput, Any, Data, Node, Path, Mutable per-document parser example. Extra attributes (legacy pickle…, One-way import of a published HF pickle → relation labels only. (+7 more)

### Community 36 - "Research Promotion Logic"

Cohesion: 0.09
Nodes (36): BaselineEvaluationSetting, BaselineReproductionDiagnosis, MandatoryResearchSystem, MandatorySystemDisposition, PromotionDecision, PromotionGateName, PromotionOutcome, StrEnum (+28 more)

### Community 37 - "Data Management Logic"

Cohesion: 0.09
Nodes (15): DataManager, ParserInput, Any, Data, Node, Path, Mutable per-document parser example. Extra attributes stay settable., One-way import of a published HF pickle → relation labels only. (+7 more)

### Community 38 - "DMRST Corpus Data"

Cohesion: 0.08
Nodes (15): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Write the bracketed tree into a file Remove the original extension, keep only…, Draw RST tree into a file (+7 more)

### Community 39 - "Universal Parser Data"

Cohesion: 0.08
Nodes (15): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Write the bracketed tree into a file Remove the original extension, keep only…, Draw RST tree into a file (+7 more)

### Community 40 - "Environment Compatibility Probes"

Cohesion: 0.10
Nodes (36): One pinned tokenizer's fast/parity/MPS compatibility evidence., Hashed Python/Transformers/MPS compatibility receipt for mandatory tokenizers., TokenizerCompatibilityReceipt, TokenizerProbeResult, HfTokenSource, load_repository_environment(), _nonempty_environment_value(), BaseModel (+28 more)

### Community 41 - "Model Identity Helpers"

Cohesion: 0.10
Nodes (36): model_identity_knobs(), Model-identity helpers for format-native result metadata and caching. An…, Return cache-key parts that identify the producing model., Return ``(model_version, inventory)`` for a result payload. Prefer attributes…, resolve_result_model_meta(), Pick the inventory string for result metadata. Explicit ``relinventory`` wins;…, resolve_inventory(), _InjectedParser (+28 more)

### Community 42 - "Compute Device Resolution"

Cohesion: 0.12
Nodes (34): _device_from_legacy_int(), _device_from_spec(), DeviceProbe,_mps_available(), device, Reproduce the historical ``cuda_device: int`` selection exactly. ``-1`` -> CPU.…, Resolve the compute device from the string API (or the deprecated int).…, Immutable snapshot of which accelerators the host exposes. Production code uses… (+26 more)

### Community 43 - "DMRST Common Utils"

Cohesion: 0.09
Nodes (37): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), __getforminfo(), getLabelMapping(), getParse() (+29 more)

### Community 44 - "DocLang Tree Projection"

Cohesion: 0.09
Nodes (28): Map an RST tree's character-offset spans to DocLang xpaths. Thin format binding…, AuthoritativeProjection, flatten_tree(), project_tree(), ProjectedTreeNode, Any, E, R (+20 more)

### Community 45 - "DocLang Span Mapping"

Cohesion: 0.14
Nodes (35): compute_overlap_refs(), Return ``(xpaths, note)`` for the half-open range ``[start, end)``. DocLang-…, One self-contained internal RST node., One self-contained Elementary Discourse Unit., RstEdu, RstRelation, FakeUnit, flatten_tree() (+27 more)

### Community 46 - "Inventory Serialization Security"

Cohesion: 0.11
Nodes (32): dump_relation_inventory(), import_relation_table_from_legacy_pickle(), Path, One-way import: published HF pickles → ``relation_table`` labels only., Unpickler that only reconstructs inventory leaf types + containers.…, RestrictedUnpickler,_EvilReduce, _local_shell() (+24 more)

### Community 47 - "Markdown Boundary Detection"

Cohesion: 0.08
Nodes (35): detect_boundaries(), Boundary, HarvestSpan, TableHarvest, Detect all boundaries in the main ``spans`` + ``table_harvests``., harvest_markdown_tables(), TableHarvest, Produce one ``TableHarvest`` per table, in document order. Tables inside… (+27 more)

### Community 48 - "Shell Utility Scripts"

Cohesion: 0.08
Nodes (17): check-prerequisites.sh script, check_dir(), check_file(), get_feature_paths(), get_repo_root(), has_jq(),_persist_feature_json(), resolve_specify_init_dir() (+9 more)

### Community 49 - "Secondary Edge Candidates"

Cohesion: 0.13
Nodes (33): DiGraph, CandidateMode, compute_structural_features(), generate_secondary_edge_candidates(), iter_candidate_batches(), iter_secondary_edge_candidates(), _node_heads(), _overlaps() (+25 more)

### Community 50 - "UniRST Predictor Logic"

Cohesion: 0.10
Nodes (15): Robust string-to-bool conversion used in configs., str2bool(), PredictorUniRST, Data, device, dtype, txt (published) → JSON (native) → legacy pickle (labels only)., Load ``relation_table_<variant>.txt`` using corpus aliases. (+7 more)

### Community 51 - "DocLang Table Harvesting"

Cohesion: 0.08
Nodes (34): _element_layer(), harvest_doclang_tables(), _list_items(), _Element,_ElementTree, TableHarvest, Yield ``(marker, item_text)`` for each ``<ldiv/>`` in a ``<list>`` body. Item…, Yield ``(marker, kind, text, row, col)`` per non-empty cell in a ``<table>``.… (+26 more)

### Community 52 - "Docling Text Harvesting"

Cohesion: 0.12
Nodes (34): harvest_docling_text(), HarvestResult, Produce the main document harvest with per-span self_ref mapping. Args: doc: a…, markdown_doc(), pdf_doc(), pptx_doc(), DoclingDocument, fixture (+26 more)

### Community 53 - "DMRST Tree Utils"

Cohesion: 0.16
Nodes (30): RST tree node used by the DMRST corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), cleanChildren(), correctThiago() (+22 more)

### Community 54 - "Docling Error Handling"

Cohesion: 0.09
Nodes (24): ``parse_docling`` entry point — load → harvest → boundaries → parse → flatten.…, DoclingRstError, EmptyDoclingError, EmptyHarvestError, InputTooLargeError, Exception, Custom exceptions for Docling-native RST parsing., The harvest produced no text (e.g. a tables-only document). (+16 more)

### Community 55 - "Parser Batch Data"

Cohesion: 0.11
Nodes (20): Data, One batched parser example. Field order matches the historical constructor., calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement() (+12 more)

### Community 56 - "Discourse Signal Models"

Cohesion: 0.12
Nodes (26): DiscourseSignal, BaseModel, Immutable identity of the detector or source that produced a signal., Typed, anchored discourse signal; overlaps are explicitly permitted., SignalDetectorProvenance, How a discourse signal entered the analysis., SignalDetectionMethod, eRST graph completer: secondary-edge candidate generation and signal anchoring. (+18 more)

### Community 57 - "RST Structure UI"

Cohesion: 0.18
Nodes (30): act(), add_node(), count_children(), count_multinuc_children(), count_span_children(), create_node_div(), crel(), delete_node() (+22 more)

### Community 58 - "Public Parser API"

Cohesion: 0.08
Nodes (19): Parser, Public façade for the DMRST and UniRST parser families. The family is resolved…, Parse a document using predefined EDUs., parser(), fixture, Construct gumrrg parser once for the slow tests., parser_cpu(), fixture (+11 more)

### Community 59 - "Pydantic Tree Serialization"

Cohesion: 0.12
Nodes (26): Any, DiscourseUnit, BaseModel, DiscourseUnit, PydanticDiscourseUnit, Typed Pydantic model for RST trees — optional, requires the ``pydantic`` extra.…, Validated, JSON-serialisable representation of one DiscourseUnit RST tree node.…, Build a ``PydanticDiscourseUnit`` from a ``DiscourseUnit`` tree (recursive). (+18 more)

### Community 60 - "DMRST Predictor Logic"

Cohesion: 0.11
Nodes (16): PredictorDMRST, Any, Data, device, dtype, Path, Takes data with word level tokenization, run current transformer tokenizer and…, Splits a batch into multiple smaller with given size. (+8 more)

### Community 61 - "Markdown Loader Logic"

Cohesion: 0.10
Nodes (28): build_parser(), load_markdown(), LoadResult, Tokenise a markdown source string into a ``markdown-it-py`` token stream. The…, The output of ``load_markdown``. ``tokens`` is the body token stream (front-…, Construct a configured ``MarkdownIt`` instance. The ``front_matter`` plugin is…, Tokenise ``source_text`` and split out the YAML front-matter., MarkdownIt (+20 more)

### Community 62 - "Checkpoint Metadata Evidence"

Cohesion: 0.13
Nodes (28): ErstCheckpointLicenses, ErstCheckpointMetrics, ErstCheckpointResearchEvidence, ErstFeatureSchema, Content identities for every feature and decoding contract., Immutable research authorities used to construct a checkpoint., Official secondary, calibration, runtime, and parity evidence., Licence and release-policy evidence carried by every bundle. (+20 more)

### Community 63 - "Neural Secondary Scorer"

Cohesion: 0.10
Nodes (19): AttentionPooling, BoundaryAwareSpanEncoder, NeuralSecondaryEdgeScorer, device, dtype, Tensor, Neural Secondary Edge Scorer with boundary-aware span pooling and asymmetric…, Learned attention pooling over sequence representations. (+11 more)

### Community 64 - "Format Analysis Schema"

Cohesion: 0.12
Nodes (20): FormatRstAnalysis, Composite analysis for structured documents (Docling, DocLang, Markdown)., DoclangRstResult, Any, Top-level output of ``parse_doclang``., Return JSON-shaped plain data., Serialize deterministically without non-JSON dataclass values., Project through the single shared ``RstAnalysis`` conversion. (+12 more)

### Community 65 - "BiMPM Classifier Modules"

Cohesion: 0.12
Nodes (13): DefaultPlusBiMPMClassifier, PointerAtten, Default classifier takes as input averaged DU representations, BiMPM computes…, DecoderRNN, DefaultPlusBiMPMClassifier, PointerAtten, Tensor, Default classifier takes as input averaged DU representations, BiMPM computes… (+5 more)

### Community 66 - "End-to-End Smoke Tests"

Cohesion: 0.15
Nodes (24): _assert_tree_aligned(),_check(), _check_from_edus(),_check_parse_rst(), _collect_leaves(), _expect_raises(), main(), Path (+16 more)

### Community 67 - "Result Caching Logic"

Cohesion: 0.14
Nodes (23): _coerce(), dataclass_from_dict(), load_cached(), normalize_source_basename(), Any, Path, T, Optional on-disk result cache for the format-native entry points. Keyed on the… (+15 more)

### Community 68 - "Tree String Converter"

Cohesion: 0.13
Nodes (15): DUConverter, Parses the tree predictions given in a string format. Args: description: Tree…, Takes the model outputs and converts them into isanlp binary trees. Returns:…, Selects the discourse unit description for given constituent. Args: start: DU…, Constructs the DiscourseUnit binary tree. Args: root: Index of the root…, Produces EDUs in isanlp format from the model predictions. Args: tokens: List…, Unit tests for ``isanlp_rst.utils.du_converter.DUConverter``. Focuses on the…, When the first gold token already covers the whitespace-stripped predicted… (+7 more)

### Community 69 - "DMRST Training Runner"

Cohesion: 0.10
Nodes (11): MultipleRunnerGeneral, Script for multiple runs of experiments. For monolingual experiments run: #…, Running training with second language injection of ``mixed`` %, :param corpus: (str) - 'GUM' or 'RST-DT' :param lang: (str) - 'en' or 'ru'…, Discriminator, device, Module, Tensor (+3 more)

### Community 70 - "Relation Inventory IO"

Cohesion: 0.13
Nodes (17): _ensure_parent_module(), ensure_unirst_module_aliases(), load_relation_inventory_json(), parse_corpora_config(), Relation-inventory I/O for UniRST. Native format is JSON (or a plain…, Register Elena-era module paths so legacy pickles can unpickle ParserInput., ``config['data']['corpora']`` is sometimes a Python-literal string., relation_table_from_json_obj() (+9 more)

### Community 71 - "Source Identity Validation"

Cohesion: 0.11
Nodes (12): CandidateIdentityProbe, CorpusSourceIdentity, field_validator, Text-free identity for one source in a private corpus checkout., Determinism evidence for one private document without candidate text.,_validate_relative_source_path(), main(), Path (+4 more)

### Community 72 - "EDU Segmenter Models"

Cohesion: 0.14
Nodes (5): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter

### Community 73 - "Markdown Text Harvester"

Cohesion: 0.12
Nodes (19): harvest_markdown_text(), _inline_text(), _InlineToken,_line_range(), HarvestResult, Protocol, Harvest text from a markdown token stream for RST parsing. Two harvesters: -…, Produce the main document harvest with per-span ``block_ref`` mapping. Args:… (+11 more)

### Community 74 - "EDU Segmenter Models"

Cohesion: 0.14
Nodes (5): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter

### Community 75 - "GUM Gold Validation"

Cohesion: 0.13
Nodes (21): gold_edus(),_gold_path(), gumrrg_cpu(), fixture, parametrize, Path, slow, GUM gold RST fixtures — real documents with human trees to compare against. The… (+13 more)

### Community 76 - "Format Projection Tests"

Cohesion: 0.18
Nodes (18): DoclingRstResult, Any, Return JSON-shaped plain data., Serialize deterministically without non-JSON dataclass values., Top-level output of ``parse_docling``., _doclang_projection(), _docling_projection(), _format_analyses() (+10 more)

### Community 77 - "Parser Family Resolution"

Cohesion: 0.15
Nodes (6): Any, device, dtype, When both family and version are set, version must belong to family., Explicit family must match detectable signatures when present., TestResolveFamily

### Community 78 - "Secondary Scorer Training"

Cohesion: 0.15
Nodes (19): compute_edge_metrics(), epoch_improves(), Any, Path, Training script for fine-tuning NeuralSecondaryEdgeScorer on GUM eRST treebanks., Reject zero-step runs before a scheduler or success receipt can exist., Treat the first finite metric as the baseline, including an exact zero., Reject absent, empty, pickle-capable, or unreadable training state. (+11 more)

### Community 79 - "Parse Result Helpers"

Cohesion: 0.18
Nodes (17): DiscourseUnit, Parse text and return a typed RST root instead of the legacy mapping payload.…, extract_root_tree(), ParseFailedError, Any, RuntimeError, Helpers for unpacking ``Parser`` / predictor call results., Return ``result['rst'][0]``, or raise :class:`ParseFailedError`. Preferred over… (+9 more)

### Community 80 - "GUM Gold Validator"

Cohesion: 0.16
Nodes (11): GumGoldValidator, GumValidationReport, DiscourseUnit, Path, Validator that verifies model predictions or processed files against GUM gold…, Validate an RstAnalysis against a GUM gold fixture., Validate a legacy DiscourseUnit tree against a GUM gold fixture., Validate a processed JSON or RS4 file against a GUM gold fixture. (+3 more)

### Community 81 - "DocLang Source Provenance"

Cohesion: 0.13
Nodes (19): Any, Capture lightweight provenance from the parsed tree. Reports: declared…, _source_origin(), parse_doclang_xml(), _ElementTree, Path, Parse the ``.dclg`` file at ``path`` and return the ElementTree. Uses a…, ``ok_comprehensive.dclg`` has ``<head>`` with several children (title, author,… (+11 more)

### Community 82 - "Checkpoint Family Detection"

Cohesion: 0.18
Nodes (5): Path, Inspect a local checkpoint directory and infer the parser family. Returns…, Read ``path`` as JSON. Returns ``None`` if the file is missing, unreadable, or…, If both signatures are present, UniRST wins (more specific)., TestDetectFamilyFromModelDir

### Community 83 - "Parsing Network Logic"

Cohesion: 0.19
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 84 - "Parsing Network Logic"

Cohesion: 0.18
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 85 - "BiMPM Attention Module"

Cohesion: 0.25
Nodes (7): BiMPM, device, Tensor, :param v1: (batch, seq_len, hidden_size) :param v2: (batch, seq_len,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, Inputs can be of infinite length, hence BiMPM matching can cause OOM. This is a…, LSTM

### Community 86 - "Result Cache Identity"

Cohesion: 0.18
Nodes (14): Compute a stable hex key from source bytes + sorted knob parts. Values are…, result_cache_key(), _Node, parametrize, Path, Result-cache identity and persisted provenance regressions.,_StubParser, test_behavior_option_change_forces_cache_miss() (+6 more)

### Community 87 - "Candidate Selection Logic"

Cohesion: 0.20
Nodes (14): CandidateDocumentSelection, CandidateSelectionReceipt, Complete-versus-selected counts for one already-partitioned document., Hashed evidence that only train candidates were sampled., _candidate_identity(), candidate_identity_sha256(), _document_selection(), _hardness_key() (+6 more)

### Community 88 - "Baseline Association Serialization"

Cohesion: 0.28
Nodes (14): BaselineDirection, BaselineSignalLocation, PublishedBaselineExample, One exact association-classifier input before deterministic serialization., Direction token used by the released association serialization., Span containing the signal targeted by one association example., _marked_text(), Deterministic serialization for the published eRST association baseline. (+6 more)

### Community 89 - "DMRST Binary Tree"

Cohesion: 0.20
Nodes (8): collect(), BinaryTree, Node, Path, :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 90 - "Universal Binary Tree"

Cohesion: 0.20
Nodes (8): collect(), BinaryTree, Node, Path, :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 91 - "Bottom-Up Transition Parser"

Cohesion: 0.23
Nodes (8): _Node, ParsingNetBottomUp, Any, Tensor, Bottom-up transition-based parser. This module reuses the encoder, segmenters…, Reconstructs the gold tree from pre-order traversal., Return gold transition sequence in postorder., ParsingNet

### Community 92 - "Schema Compatibility Tests"

Cohesion: 0.17
Nodes (15): parametrize, Path, Compatibility guard: do we still read CURRENT Docling / DocLang output? The…, Return the XML namespace declared on a fixture's root element (or '')., Guard against the guard silently no-opping if fixtures are moved/renamed — an…, Each fixture's declared Docling schema version must equal the installed…, The installed docling-core must validate-load each fixture AND our harvester…, Our ``DOCLANG_NS`` constant must match the namespace the installed doclang… (+7 more)

### Community 93 - "Decoder RNN Modules"

Cohesion: 0.15
Nodes (6): DecoderRNN, DefaultLabelClassifier, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of…

### Community 94 - "Markdown Error Handling"

Cohesion: 0.19
Nodes (13): ``parse_markdown`` entry point — load → harvest → boundaries → parse → flatten.…, EmptyHarvestError, EmptyMarkdownError, InputTooLargeError, MarkdownRstError, Exception, Custom exceptions for Markdown-native RST parsing., The harvest produced no text (e.g. all knobs gated their content out). (+5 more)

### Community 95 - "Runtime Provenance Helpers"

Cohesion: 0.16
Nodes (13): Shared runtime helpers for the format-native entry points. One home for the…, Backward-compatible name for installed semantic package version., Return the checkout commit, with dirty state, independently of SemVer., resolve_source_revision(), resolve_tool_version(), _clear_runtime_caches(), fixture, MonkeyPatch (+5 more)

### Community 96 - "Wave 4 Integration"

Cohesion: 0.16
Nodes (12): _CapturingParser,_Node, MonkeyPatch, parametrize, Path, Wave 4 — construct-path kwargs + formats-extra isolation., Core ``isanlp_rst.parser`` must not require the formats extra., Stand-in for ``Parser`` that records constructor kwargs. (+4 more)

### Community 97 - "Tree Flattening Utils"

Cohesion: 0.16
Nodes (14): flatten_tree(),_make_edu(), Any, Boundary, HarvestSpan, RstEdu, RstRelation, Flatten a DiscourseUnit tree into ``(relations, edus)`` tuples. Ids are… (+6 more)

### Community 98 - "Parser Integration Tests"

Cohesion: 0.22
Nodes (10): du_to_analysis(), Any, Convert an isanlp.annotation_rst.DiscourseUnit tree into a typed RstAnalysis., DummyPredictor, DiscourseUnit, MonkeyPatch, Unit tests for Parser.parse_document integration., test_du_to_analysis_nuclearity_and_relations() (+2 more)

### Community 99 - "Viewer Security Hardening"

Cohesion: 0.32
Nodes (13): rs3tohtml(), Create a private SQLite file for one render; unlink in ``finally``., _resolve_dbpath(), setup_db(), temporary_db(), Path, Viewer hardening: XXE posture, HTML escape, per-render SQLite., test_rs3tohtml_escapes_basename_in_header() (+5 more)

### Community 100 - "BiMPM Encoder Module"

Cohesion: 0.15
Nodes (11): _DistinctBiMpmEncoder, Any, Module, parametrize, Tensor, The MPS-safe elementwise reduction remains mathematically equivalent to GEMV., Capture the representations passed by the combined classifier., The right DU must use right BiMPM features and its own length. (+3 more)

### Community 101 - "eRST Checkpoint Management"

Cohesion: 0.15
Nodes (11): ErstCheckpointComponent, ErstCheckpointFile, ErstCheckpointProvenance, BaseModel, One declared, content-addressed file in an eRST completion bundle., Reload contract for one explicit eRST completion component., Producer and immutable source identity for one bundle construction., Train-derived raw eRST labels with explicit ontology projections. (+3 more)

### Community 102 - "RST Tree Construction"

Cohesion: 0.21
Nodes (13): buildTree(), buildTreeThiago(), checkcontent(), convert_parens_in_rst_tree_str(), createtext(), processtext(), Preprocessing token list for filtering '(' and ')' in text (from DPLP, by…, Create text from a list of tokens (from DPLP, by Yangfeng Ji) :type lst: list… (+5 more)

### Community 103 - "RST Quality Diagnostics"

Cohesion: 0.29
Nodes (12): _discover(), DocMetrics,_format_of(), main(),_metrics(), _parse(),_print_table(), Any (+4 more)

### Community 104 - "DocLang Fixture Verification"

Cohesion: 0.22
Nodes (12): FixtureParityError, FixtureParityReceipt, _GithubEntry,_Manifest, BaseModel, RuntimeError, Verify local DocLang fixtures against an immutable upstream GitHub commit., Raised when local, manifest, and upstream fixture authority diverge. (+4 more)

### Community 105 - "DMRST Label Ordering"

Cohesion: 0.21
Nodes (10): getLabelOrdered(), nucs_and_rels(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…, parametrize, DMRST ``nucs_and_rels`` must match UniRST ``rpartition`` semantics., test_dmrst_ns_satellite_on_right() (+2 more)

### Community 106 - "RNN Sequence Encoder"

Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 107 - "CRF Sequence Labeling"

Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from <https://github.com/kmkurn/pytorch-…>, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 108 - "Adversarial Discriminator"

Cohesion: 0.18
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 *19* 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 109 - "RNN Sequence Encoder"

Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 110 - "CRF Sequence Labeling"

Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from <https://github.com/kmkurn/pytorch-…>, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 111 - "Torch Dtype Normalization"

Cohesion: 0.20
Nodes (10): dtype, Normalise a dtype spec to a ``torch.dtype``. Accepts: * ``None`` -> ``float32``…, parametrize, Default is fp32 on every device — measured fp32 wins on MPS for typical inputs;…, test_resolve_dtype_default_is_float32(), test_resolve_dtype_passthrough(), test_resolve_dtype_string_parsing(), test_resolve_dtype_unknown_string_raises() (+2 more)

### Community 112 - "Multi-Run Experiment Runner"

Cohesion: 0.25
Nodes (4): MultipleRunnerGeneral, Script for multiple runs of experiments. For monolingual experiments run: #…, Running training with second language injection of ``mixed`` %, :param corpora: corpus names, e.g. ['GUM'] or ['RST-DT'] :param lang: 'en' or…

### Community 113 - "Default Label Classifier"

Cohesion: 0.22
Nodes (4): DefaultLabelClassifier, device, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of…

### Community 114 - "Repository Cleanup Script"

Cohesion: 0.31
Nodes (10): collect_junk(),_display(), is_junk_dir(), is_junk_file(), main(), Path, Remove regenerable junk from the repo: bytecode, tool caches, temp files. Does…, Delete ``paths``. Returns the number of paths acted on. (+2 more)

### Community 115 - "Docling Table Harvesting"

Cohesion: 0.20
Nodes (10): harvest_docling_tables(), DoclingDocument, TableHarvest, Produce one ``TableHarvest`` per ``TableItem``, in ``doc.tables`` order. Cell…, Each cell span must carry kind + row/col from TableCell., Cell refs must resolve mechanically against the Docling JSON — the path…, test_table_harvest_carries_grid_metadata(), test_table_harvest_offsets_tile_full_text() (+2 more)

### Community 116 - "Cleanup Unit Tests"

Cohesion: 0.29
Nodes (8): fixture, Path, Unit tests for ``scripts/cleanup.py`` (stdlib-only project cleaner)., test_collects_bytecode_caches_and_temp_not_source(), test_dry_run_does_not_delete(), test_remove_deletes_junk_keeps_source_and_protected(), test_skips_git_and_pixi_trees(), tree()

### Community 117 - "RS3 Annotation Parsing"

Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element,_ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 118 - "Discourse Tree Flattening"

Cohesion: 0.22
Nodes (9): flatten_tree(), Any, Boundary, HarvestSpan, RstEdu, RstRelation, Return the deduplicated thread ids carried by the named spans. Order is the…, Flatten a DiscourseUnit tree into ``(relations, edus)`` tuples. Ids are… (+1 more)

### Community 119 - "Docling Smoke Tests"

Cohesion: 0.25
Nodes (7): _picture_description(), PictureItem, Return ``picture.meta.description.text`` when present and non-empty., main(), Path, Smoke-iterate Docling JSON fixtures via docling-core's canonical walker. Phase…, smoke_iterate()

### Community 120 - "RS3 Annotation Parsing"

Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element,_ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 122 - "Discourse Unit Mocking"

Cohesion: 0.28
Nodes (8): _FakeNode,_Predictor, Stand-in for isanlp.DiscourseUnit with the attributes used by remap., Minimal concrete subclass (BasePredictor is ABC)., Unary node = DUConverter bug; surface it rather than patch it., test_remap_tree_offsets_binary(), test_remap_tree_offsets_leaf(), test_remap_tree_offsets_unary_raises()

### Community 123 - "DocLang Parity Tests"

Cohesion: 0.22
Nodes (6): BaseModel, parametrize, Path, Pinned upstream parity and locked-validator tests for DocLang fixtures., test_locked_doclang_validator_accepts_every_upstream_fixture(),_UpstreamManifest

### Community 124 - "Checkpoint Verification Receipt"

Cohesion: 0.32
Nodes (7): ErstCheckpointVerificationReceipt, Machine-readable proof that a bundle reloaded and passed its graph vector., main(), Path, Fail-closed clean-process verifier for an eRST completion bundle., Strict-reload a bundle, run its test vector, and emit a typed receipt., verify_checkpoint()

### Community 125 - "Docling Text Harvester"

Cohesion: 0.25
Nodes (7): _label_value(), Harvest text from a DoclingDocument for RST parsing. Two harvesters: -…, Return the string value of a Docling enum label, or str(thing)., HarvestResult, Concatenated document harvest and its source-address spans., One table-cell harvest with coordinates local to ``full_text``., TableHarvest

### Community 126 - "HTML Viewer Export"

Cohesion: 0.29
Nodes (7): PathLike, Convert an ``.rs3`` file into HTML. Parameters ---------- rs3_path: Path to the…, to_html(), Path, Unit tests for viewer convenience helpers in ``isanlp_rst``., When ``html_path`` is set, ``to_html`` must write the file AND return the HTML…, test_to_html_returns_string_and_writes_file()

### Community 127 - "File Access Linter"

Cohesion: 0.43
Nodes (6): is_content_free(), looks_like_path(), main(), offending_tool(), Return (tool, path) for the first file-reading invocation, else None.…, True when this invocation cannot print a line of file content. Every argument…

### Community 128 - "Speckit Workflow Stages"

Cohesion: 0.29
Nodes (7): speckit-converge, CI Workflow, speckit-implement, speckit-plan, isanlp_rst Constitution, speckit-specify, speckit-tasks

### Community 129 - "EDU File Utilities"

Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 130 - "Markdown RST Output"

Cohesion: 0.33
Nodes (5): MarkdownRstResult, Any, Top-level output of ``parse_markdown``., Return JSON-shaped plain data., Serialize deterministically without non-JSON dataclass values.

### Community 131 - "Parser Protocol Interface"

Cohesion: 0.29
Nodes (5): Protocol, Structural contract for injectable RST parsers., Return a parser result containing an RST tree., Callable boundary used by format-native parsing entry points., RstParser

### Community 132 - "Markdown Manifest Verification"

Cohesion: 0.48
Nodes (6): _is_approved_exclusion(), main(),_manifest_paths(), Verify and lint the complete repository Markdown manifest.,_repository_markdown(), verify_manifest()

### Community 133 - "Schema Verification Status"

Cohesion: 0.47
Nodes (6): Open Output Schema Specifics, Open Parse Per Boundary, Open RST Real World Quality, Open Schema Detail Verifications, Verified Docling Core API, Verified Docling Schema

### Community 134 - "DMRST Config Reader"

Cohesion: 0.33
Nodes (3): ConfigReader, Any, Path

### Community 135 - "Universal Parser Config"

Cohesion: 0.33
Nodes (3): ConfigReader, Any, Path

### Community 136 - "Performance Benchmarking"

Cohesion: 0.47
Nodes (5): main(), Performance benchmark for isanlp_rst across devices and dtypes. Usage: pixi run…, Run parser n times after a warm-up. Return median seconds and tree shape.,_shape(), _time_parse()

### Community 137 - "Token Offset Conversion"

Cohesion: 0.40
Nodes (4): _OffsetToken, Protocol, Minimal razdel-token surface used by offset remapping., Build offset converter from a list of `razdel.Token` objects.

### Community 138 - "Source Origin Serialization"

Cohesion: 0.40
Nodes (5): Any, Serialise ``doc.origin`` (a Pydantic model) to a JSON-safe dict. Returns ``{}``…, _serialise_source_origin(), test_serialise_source_origin_none_returns_empty_dict(), test_serialise_source_origin_real_fixture_has_mimetype_and_hash()

### Community 139 - "Span Character Offsets"

Cohesion: 0.40
Nodes (3): Protocol, Any harvest span with half-open ``[start, end)`` character offsets., SpanLike

### Community 140 - "CUDA Verification Script"

Cohesion: 0.60
Nodes (4): _assert_aligned(), _collect_leaves(), main(), CUDA verification script — to be run on a real NVIDIA host. Usage: pixi run…

### Community 141 - "Table Harvest Invariants"

Cohesion: 0.50
Nodes (5): FixtureRequest, parametrize, Two-level invariant: tables live in their own harvests; the main document…, test_main_harvest_never_contains_table_refs(), test_offsets_match_full_text()

### Community 142 - "LSTM Dropout Tests"

Cohesion: 0.50
Nodes (4): parametrize, PyTorch RNN dropout is inter-layer only. A 1-layer LSTM with non-zero dropout…, test_tony_one_layer_lstm_does_not_warn(), test_tony_stacked_lstm_keeps_dropout()

### Community 143 - "Speckit Task Management"

Cohesion: 0.50
Nodes (4): speckit-converge, speckit-implement, speckit-tasks, speckit-analyze

### Community 145 - "RST Build Planning"

Cohesion: 0.67
Nodes (3): Central Ontology Lock, DocLang-native RST Plan, Docling-native RST Build Plan

### Community 148 - "GUMRRG Parser Fixture"

Cohesion: 0.67
Nodes (3): parser(), fixture, Construct gumrrg parser once for the slow tests.

### Community 149 - "GUMRRG Parser Fixture"

Cohesion: 0.67
Nodes (3): parser(), fixture, Construct gumrrg parser once for the slow tests.

## Knowledge Gaps

- **56 isolated node(s):** `no-assumptions-check.sh script`, `cleanup.sh script`, `isanlp_rst`, `common.sh script`, `Docling-native RST output plan` (+51 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **48 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions

*Questions this graph is uniquely positioned to answer:*

- **Why does `Parser` connect `Public Parser API` to `RST Enumerations`, `Discourse Tree Structures`, `EDU Segmentation Dataset`, `Parser Family Resolution`, `Parse Result Helpers`, `Checkpoint Family Detection`?**
  *High betweenness centrality (0.006) - this node is a cross-community bridge.*
- **Why does `HierarchicalSectionStitcher` connect `Discourse Tree Structures` to `RST Analysis Models`, `Analysis Data Contracts`, `Discourse Signal Models`, `Public Parser API`, `Secondary Relation Completion`?**
  *High betweenness centrality (0.003) - this node is a cross-community bridge.*
- **Why does `parse_docling()` connect `Docling JSON Parsing` to `Tree Flattening Utils`, `Result Caching Logic`, `Parser Protocol Interface`, `Markdown Text Harvester`, `Source Origin Serialization`, `Content Layer Detection`, `Format Projection Tests`, `Model Identity Helpers`, `Parse Result Helpers`, `Docling Table Harvesting`, `Docling Text Harvesting`, `Docling Error Handling`, `Result Cache Identity`, `Public Parser API`, `Runtime Provenance Helpers`?**
  *High betweenness centrality (0.002) - this node is a cross-community bridge.*
- **Are the 6 inferred relationships involving `Parser` (e.g. with `CompleterConfig` and `ErstCompleter`) actually correct?**
  *`Parser` has 6 INFERRED edges - model-reasoned connections that need verification.*
- **Are the 4 inferred relationships involving `RstAnalysis` (e.g. with `ProvenanceRecord` and `FailureCodeEnum`) actually correct?**
  *`RstAnalysis` has 4 INFERRED edges - model-reasoned connections that need verification.*
- **Are the 8 inferred relationships involving `parse_doclang()` (e.g. with `DoclangEligibility` and `EmptyDoclangError`) actually correct?**
  *`parse_doclang()` has 8 INFERRED edges - model-reasoned connections that need verification.*
- **What connects `no-assumptions-check.sh script`, `cleanup.sh script`, `isanlp_rst` to the rest of the system?**
  *56 weakly-connected nodes found - possible documentation gaps or missing edges.*
