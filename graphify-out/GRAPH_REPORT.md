# Graph Report - isanlp_rst  (2026-08-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 3315 nodes · 7410 edges · 149 communities (128 shown, 21 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 524 edges (avg confidence: 0.52)
- Token cost: 10,932 input · 1,791 output

## Graph Freshness
- Built from commit: `4ae828d4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- RST Tree Conversion
- Discourse Relation Models
- Analysis Data Structures
- DocLang XML Parsing
- JQuery Library
- Document Tokenization Models
- DocLang Text Harvesting
- Parser Entry Points
- RS3 Tree Utilities
- Structural Boundary Detection
- DocLang API Schema
- Markdown Harvester Tests
- Base Predictor Logic
- Markdown Boundary Mapping
- RST Document Representation
- DocLang Boundary Detection
- EDU Segmentation Dataset
- Boundary Detection Tests
- Harvest Span Mapping
- RST Tree Visualization
- RST Tree Rendering
- Model Integration Tests
- RST Database Operations
- GUM Corpus Validation
- Generic Tree Flattening
- RS3 Node Utilities
- DMRST Corpus Management
- DocLang Source Provenance
- CRF Segmenter Implementation
- DMRST Tree Processing
- Universal Parser Corpus
- Thiago Tree Binarization
- DocLang Thread Mapping
- Compute Device Selection
- Repository Shell Utilities
- Markdown Parsing Tests
- RST Parsing Interface
- Markdown Boundary Tests
- RST Web UI
- Pickle Security Tests
- Pydantic Tree Serialization
- Predictor Configuration Utilities
- DMRST Predictor Implementation
- Markdown Loader Logic
- DMRST Data Manager
- Docling Text Harvesting
- Model Training Manager
- Sentence Span Management
- Parser Public API
- Tree Binarization Logic
- DMRST Neural Modules
- Parser Smoke Tests
- Markdown Content Harvesting
- Tree Propagation Logic
- Parser Cache Tests
- DMRST Parser Metrics
- Neural Segmenter Models
- Universal Parser Labels
- Universal Parser Discriminator
- Docling Quality Checks
- Parser Family Resolution
- RS3 Viewer Database
- Markdown Entry Tests
- Universal Parser Modules
- Parsing Network Implementation
- Docling Entry Tests
- HTML Viewer Helpers
- RST Ontology Adapter
- Model Family Detection
- Parse Result Helpers
- DPLP Tree Utilities
- Parsing Network Logic
- Docling Parsing Tests
- DMRST Binary Trees
- Training Metric Utilities
- Docling Table Harvesting
- Universal Binary Trees
- Bottom-Up Transition Parser
- Schema Compatibility Tests
- BiMPM Neural Module
- Contract Isolation Tests
- DMRST Encoder RNN
- Analysis Integration Tests
- Universal Parser Metrics
- Parser Input Models
- Docling Error Handling
- RST Quality Diagnostics
- DMRST Experiment Runner
- CRF Sequence Decoding
- MIME Type Registration
- Relation Inventory I/O
- Universal Encoder RNN
- Binary Tree Attachment
- Adversarial Learning Discriminator
- Docling Metadata Harvesting
- Markdown Error Handling
- Sentence Parsing Helpers
- Universal Experiment Runner
- RST Analytical Helpers
- Repository Cleanup Utility
- Markdown Integration Tests
- Dtype Normalization
- Cleanup Script Tests
- GUM Corpus Metrics
- Discourse Unit Mocking
- Project Workflow Tasks
- File Access Linter
- EDU File Utilities
- RST XML Processing
- Label Ordering Logic
- Docling JSON Fixtures
- DMRST Config Reader
- Universal Parser Config
- Performance Benchmarking
- Token Offset Mapping
- CUDA Verification Script
- Docling Smoke Tests
- Table Harvest Invariants
- RST Planning Strategies
- Orchestration Stub Nodes
- CUDA Device Validation
- DocLang Specification
- Docling Core Integration
- Long Input Partitioning
- Custom Tokenization
- Parser Test Fixtures
- Node Interface Mocking
- Assumption Check Script
- Development Standards
- Cleanup Shell Script
- System Architecture
- DocLang 0.7 Specification
- Docling Core API
- RST Platform Roadmap
- Elena Chistova
- English RST Diagrams
- Russian RST Diagrams
- CI Workflow
- Nightly Integration
- isanlp_rst Library
- Steve Allison
- Markdown Error Handling

## God Nodes (most connected - your core abstractions)
1. `Parser` - 108 edges
2. `RstAnalysis` - 85 edges
3. `parse_doclang()` - 56 edges
4. `parse_markdown()` - 55 edges
5. `parse_docling()` - 55 edges
6. `BasePredictor` - 50 edges
7. `RstNode` - 47 edges
8. `RstDocument` - 42 edges
9. `harvest_doclang_text()` - 41 edges
10. `PrimaryRelationEdge` - 40 edges

## Surprising Connections (you probably didn't know these)
- `_Predictor` --uses--> `BasePredictor`  [INFERRED]
  tests/test_base_predictor.py → isanlp_rst/base_predictor.py
- `GumGoldValidator` --uses--> `RS4Document`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/erst/rs4.py
- `GumGoldValidator` --uses--> `RS4Reader`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/erst/rs4.py
- `GumGoldValidator` --uses--> `ErstScorer`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/eval/erst_scorer.py
- `GumGoldValidator` --uses--> `SecondaryEdgeMetrics`  [INFERRED]
  tests/gum_validator.py → isanlp_rst/eval/erst_scorer.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **DocLang Verification Context** — claude_memory_verified_doclang_fixtures_md, claude_memory_verified_doclang_spec_md, doclang_package [EXTRACTED 1.00]
- **Docling Verification Context** — claude_memory_verified_docling_core_api_md, claude_memory_verified_docling_schema_md, docling_core_doclingdocument [EXTRACTED 1.00]
- **Native RST Entry Points** — docs_plans_2026_05_15_doclang_native_rst, docs_plans_2026_05_15_docling_native_rst, docs_plans_2026_06_12_markdown_native_rst [EXTRACTED 1.00]
- **Spec-Kit SDD Loop** — cursor_skills_speckit_specify_skill, cursor_skills_speckit_plan_skill, cursor_skills_speckit_tasks_skill, cursor_skills_speckit_implement_skill, cursor_skills_speckit_converge_skill [EXTRACTED 1.00]

## Communities (149 total, 21 thin omitted)

### Community 0 - "RST Tree Conversion"
Cohesion: 0.04
Nodes (90): DiGraph, Find the root node if present., A node in a discourse tree or graph., RstNode, analysis_to_rs4(), Conversion utilities between RS4 DOM, DiscourseUnit, and typed contracts., Convert an RstDocument and RstAnalysis back into an RS4Document., Convert an RS4Document into an RstDocument and an RstAnalysis. (+82 more)

### Community 1 - "Discourse Relation Models"
Cohesion: 0.04
Nodes (75): Look up a node by its ID., A directed secondary rhetorical relation edge without nuclearity., Complete discourse analysis result., RstAnalysis, SecondaryRelationEdge, NuclearityPatternEnum, Nuclearity pattern for primary relation edges., CalibrationBin (+67 more)

### Community 2 - "Analysis Data Structures"
Cohesion: 0.07
Nodes (55): DiscourseSignal, Discourse analysis result models and graph structures., An anchored or unanchored discourse signal., Execution timing profile in milliseconds., TimingRecord, Character offset span in the original text., TextSpan, AnnotationStatusEnum (+47 more)

### Community 3 - "DocLang XML Parsing"
Cohesion: 0.06
Nodes (62): parse_doclang(), Path, Parse a DocLang XML file and return its RST analysis. Args: path: filesystem…, Validate ``path`` against the DocLang schema via the ``doclang`` package. When…, _validate_xml(), DoclangRstError, EmptyDoclangError, EmptyHarvestError (+54 more)

### Community 4 - "JQuery Library"
Cohesion: 0.06
Nodes (42): ba(), Ea(), Fa(), fb(), ga(), ha(), b(), hb() (+34 more)

### Community 5 - "Document Tokenization Models"
Cohesion: 0.07
Nodes (48): FormatRstAnalysis, Composite analysis for structured documents (Docling, DocLang, Markdown)., DocumentToken, Edu, ProvenanceRecord, Document input models and coordinate representation., Create an RstDocument from pre-segmented EDU strings. Note: Character offsets…, A single token aligned with character coordinates. (+40 more)

### Community 6 - "DocLang Text Harvesting"
Cohesion: 0.06
Nodes (59): harvest_doclang_text(), _ElementTree, HarvestResult, Produce the main document harvest with per-span xpath mapping. Args: tree: a…, _ElementTree, parametrize, Unit tests for the doclang harvesters (main text + per-table)., ``ok_table_rectangular`` is table-only — the main harvest must be empty; the… (+51 more)

### Community 7 - "Parser Entry Points"
Cohesion: 0.08
Nodes (49): ``parse_doclang`` entry point — load → harvest → boundaries → parse → flatten.…, ``parse_docling`` entry point — load → harvest → boundaries → parse → flatten.…, ``parse_markdown`` entry point — load → harvest → boundaries → parse → flatten.…, _coerce(), dataclass_from_dict(), load_cached(), Any, Path (+41 more)

### Community 8 - "RS3 Tree Utilities"
Cohesion: 0.08
Nodes (55): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+47 more)

### Community 9 - "Structural Boundary Detection"
Cohesion: 0.08
Nodes (55): ContentLayer, _content_layers(), detect_boundaries(), _detect_pptx_slide_boundaries(), _detect_section_boundaries(), _detect_table_boundaries(), _detect_vtt_turn_boundaries(), _iter_body_self_refs() (+47 more)

### Community 10 - "DocLang API Schema"
Cohesion: 0.06
Nodes (43): DocLang-native RST parsing for isanlp_rst. Public API: - ``parse_doclang(path,…, Map an RST tree's character-offset spans to DocLang xpaths. Thin format binding…, DoclangRstResult, HarvestResult, Any, Schema types for the DocLang-native RST output. All types are frozen-slots…, One internal node of an RST tree., One leaf of an RST tree (Elementary Discourse Unit). (+35 more)

### Community 11 - "Markdown Harvester Tests"
Cohesion: 0.06
Nodes (53): _harvest(), Unit tests for ``isanlp_rst.markdown.harvester``. Tests focus on inline-…, Three bullet items → three list_item spans, not one., Nested bullets join their parent item's text rather than emit separate spans —…, Paragraphs inside `>` become blockquote_paragraph, not paragraph., Negative-space: a plain para must not be classified as blockquote., A heading inside `>` is quoted content — it must not carry the plain `heading`…, The knob gates the whole quoted region: paragraphs, headings, lists, code… (+45 more)

### Community 12 - "Base Predictor Logic"
Cohesion: 0.06
Nodes (41): AbstractContextManager, BasePredictor, Any, Path, T, Mixin-style base with shared tokenization, batching and offset utils. Not…, Yield chunks of size `n` from `_list` (handles empty lists)., Build offset converter from word tokens and optional (start, end) pairs. If… (+33 more)

### Community 13 - "Markdown Boundary Mapping"
Cohesion: 0.08
Nodes (46): Detect structural boundaries in a markdown harvest. Boundaries are derived from…, Markdown-native RST parsing for isanlp_rst. Public API: -…, compute_overlap_refs(), flatten_tree(), _make_edu(), Any, Boundary, HarvestSpan (+38 more)

### Community 14 - "RST Document Representation"
Cohesion: 0.07
Nodes (36): PrimaryRelationEdge, A directed primary rhetorical relation edge with nuclearity., Create an RstDocument from raw text without pre-segmented EDUs., Lossless document representation for discourse parsing., RstDocument, CompleterConfig, ErstCompleter, Any (+28 more)

### Community 15 - "DocLang Boundary Detection"
Cohesion: 0.10
Nodes (46): _detect_document_fallback(), _detect_field_region_boundaries(), _detect_group_boundaries(), _detect_heading_boundaries(), _detect_page_boundaries(), _detect_table_boundaries(), _harvest_eligible_xpaths(), Boundary (+38 more)

### Community 16 - "EDU Segmentation Dataset"
Cohesion: 0.07
Nodes (38): inference_mode, EduSegmentationDataset, parse_disrpt_tok_file(), parse_rs4_to_sentences(), Any, Dataset, Path, Tensor (+30 more)

### Community 17 - "Boundary Detection Tests"
Cohesion: 0.08
Nodes (47): detect_boundaries(), _ElementTree, Detect every structural boundary in ``tree``. Always emits ``table-N`` and…, _ElementTree, parametrize, Path, Unit tests for ``isanlp_rst.doclang.boundaries.detect_boundaries``., ``ok_comprehensive.dclg.xml`` has top-level groups. (+39 more)

### Community 18 - "Harvest Span Mapping"
Cohesion: 0.13
Nodes (46): HarvestSpan, One unit of text harvested from a DocLang document. ``xpath`` is the source…, compute_overlap_refs(), flatten_tree(), Any, Boundary, HarvestSpan, RstRelation (+38 more)

### Community 19 - "RST Tree Visualization"
Cohesion: 0.08
Nodes (40): _rs3tohtml_with_db(), get_depth(), get_left_right(), NODE, NodeMap, RST tree node types and parent-chain attribute walks., EDU used by the segmenter, not by the structurer., Set graphical nesting depth of ``orig_node`` from the parent chain. RST… (+32 more)

### Community 20 - "RST Tree Rendering"
Cohesion: 0.06
Nodes (52): AsyncBrowser, AsyncPage, AsyncPlaywright, Browser, CaptureFixture, IO, T, Render an RST tree and, optionally, display it inline. This is a light-weight… (+44 more)

### Community 21 - "Model Integration Tests"
Cohesion: 0.09
Nodes (45): skipif, _assert_aligned(), _collect_leaf_units(), _collect_leaves(), dmrst_gumrrg_cpu(), dmrst_rstdt_cpu(), dmrst_rstreebank_cpu(), fixture (+37 more)

### Community 22 - "RST Database Operations"
Cohesion: 0.15
Nodes (42): add_node(), add_seg(), count_children(), count_multinuc_children(), count_span_children(), delete_node(), generic_query(), get_children() (+34 more)

### Community 23 - "GUM Corpus Validation"
Cohesion: 0.08
Nodes (32): GumGoldValidator, GumValidationReport, DiscourseUnit, Path, Validator that verifies model predictions or processed files against GUM gold…, Validate an RstAnalysis against a GUM gold fixture., Validate a legacy DiscourseUnit tree against a GUM gold fixture., Validate a processed JSON or RS4 file against a GUM gold fixture. (+24 more)

### Community 24 - "Generic Tree Flattening"
Cohesion: 0.07
Nodes (35): E, flatten_tree(), Any, Generic, iterative DiscourseUnit-tree flattening. One implementation shared by…, Flatten a binary ``DiscourseUnit`` tree into ``(relations, edus)``. Ids are…, compute_overlap_refs(), Protocol, Generic overlap computation for harvest spans of any format. ``SpanIndex`` is… (+27 more)

### Community 25 - "RS3 Node Utilities"
Cohesion: 0.12
Nodes (38): areAdjacent(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree(), findNode() (+30 more)

### Community 26 - "DMRST Corpus Management"
Cohesion: 0.08
Nodes (16): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Write the bracketed tree into a file Remove the original extension, keep only…, Draw RST tree into a file (+8 more)

### Community 27 - "DocLang Source Provenance"
Cohesion: 0.06
Nodes (40): Any, Capture lightweight provenance from the parsed tree. Reports: declared…, _source_origin(), The document uses a DocLang construct this parser does not support yet., UnsupportedDoclangError, parse_doclang_xml(), _ElementTree, Path (+32 more)

### Community 28 - "CRF Segmenter Implementation"
Cohesion: 0.08
Nodes (13): CRF, LinearSegmenter, PointerSegmenter, device, Tensor, Conditional random field. modified from https://github.com/kmkurn/pytorch-…, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions… (+5 more)

### Community 29 - "DMRST Tree Processing"
Cohesion: 0.09
Nodes (37): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), __getforminfo(), getLabelMapping(), getParse() (+29 more)

### Community 30 - "Universal Parser Corpus"
Cohesion: 0.09
Nodes (15): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Write the bracketed tree into a file Remove the original extension, keep only…, Draw RST tree into a file (+7 more)

### Community 31 - "Thiago Tree Binarization"
Cohesion: 0.12
Nodes (36): binarizeTreeRightThiago(), bTree(), buildTree(), buildTreeThiago(), checkcontent(), cleanChildren(), convert_parens_in_rst_tree_str(), correctThiago() (+28 more)

### Community 32 - "DocLang Thread Mapping"
Cohesion: 0.13
Nodes (35): compute_overlap_refs(), flatten_tree(), Any, Boundary, HarvestSpan, RstEdu, RstRelation, Return ``(xpaths, note)`` for the half-open range ``[start, end)``. DocLang-… (+27 more)

### Community 33 - "Compute Device Selection"
Cohesion: 0.13
Nodes (33): _device_from_legacy_int(), _device_from_spec(), DeviceProbe, _mps_available(), device, Reproduce the historical ``cuda_device: int`` selection exactly. ``-1`` -> CPU.…, Resolve the compute device from the string API (or the deprecated int).…, Immutable snapshot of which accelerators the host exposes. Production code uses… (+25 more)

### Community 34 - "Repository Shell Utilities"
Cohesion: 0.08
Nodes (17): check-prerequisites.sh script, check_dir(), check_file(), get_feature_paths(), get_repo_root(), has_jq(), _persist_feature_json(), resolve_specify_init_dir() (+9 more)

### Community 35 - "Markdown Parsing Tests"
Cohesion: 0.11
Nodes (34): parse_markdown(), Path, Parse a markdown file and return its RST analysis. Args: path: filesystem path…, Path, A table-only document must NOT raise: the main tree is empty and the table…, Two-level invariant: the document tree knows nothing of cells., A different knob set must produce a different key, not a stale hit., Same stub object (no identity attrs) but different ``hf_model_name`` kwarg must… (+26 more)

### Community 36 - "RST Parsing Interface"
Cohesion: 0.09
Nodes (20): Data, Takes word-level tokenized data and converts it to transformer subword inputs., Splits a batch into multiple smaller batches of the given size. Note:…, Parse text into an RST tree. Args: text: Original document text. tokens:…, Parse text using predefined EDU boundaries., DUConverter, Parses the tree predictions given in a string format. Args: description: Tree…, Takes the model outputs and converts them into isanlp binary trees. Returns:… (+12 more)

### Community 37 - "Markdown Boundary Tests"
Cohesion: 0.09
Nodes (32): detect_boundaries(), Boundary, HarvestSpan, TableHarvest, Detect all boundaries in the main ``spans`` + ``table_harvests``., _boundaries(), Unit tests for ``isanlp_rst.markdown.boundaries``. Tests focus on boundary…, Two-level analysis: cells are not part of the document tree, so they live only… (+24 more)

### Community 38 - "RST Web UI"
Cohesion: 0.18
Nodes (30): act(), add_node(), count_children(), count_multinuc_children(), count_span_children(), create_node_div(), crel(), delete_node() (+22 more)

### Community 39 - "Pickle Security Tests"
Cohesion: 0.12
Nodes (29): dump_relation_inventory(), Unpickler that only reconstructs inventory leaf types + containers.…, RestrictedUnpickler, _EvilReduce, _local_shell(), parametrize, Path, Adversarial / inventory-load tests for UniRST pickle handling. No HF downloads,… (+21 more)

### Community 40 - "Pydantic Tree Serialization"
Cohesion: 0.12
Nodes (26): BaseModel, Any, DiscourseUnit, DiscourseUnit, PydanticDiscourseUnit, Typed Pydantic model for RST trees — optional, requires the ``pydantic`` extra.…, Validated, JSON-serialisable representation of one DiscourseUnit RST tree node.…, Build a ``PydanticDiscourseUnit`` from a ``DiscourseUnit`` tree (recursive). (+18 more)

### Community 41 - "Predictor Configuration Utilities"
Cohesion: 0.12
Nodes (14): Robust string-to-bool conversion used in configs., str2bool(), parse_corpora_config(), ``config['data']['corpora']`` is sometimes a Python-literal string., relation_table_from_txt(), PredictorUniRST, device, dtype (+6 more)

### Community 42 - "DMRST Predictor Implementation"
Cohesion: 0.11
Nodes (17): PredictorDMRST, Any, Data, device, dtype, Path, Takes data with word level tokenization, run current transformer tokenizer and…, Splits a batch into multiple smaller with given size. (+9 more)

### Community 43 - "Markdown Loader Logic"
Cohesion: 0.10
Nodes (28): build_parser(), load_markdown(), LoadResult, Tokenise a markdown source string into a ``markdown-it-py`` token stream. The…, The output of ``load_markdown``. ``tokens`` is the body token stream (front-…, Construct a configured ``MarkdownIt`` instance. The ``front_matter`` plugin is…, Tokenise ``source_text`` and split out the YAML front-matter., MarkdownIt (+20 more)

### Community 44 - "DMRST Data Manager"
Cohesion: 0.12
Nodes (11): DataManager, Data, Path, One-way import of a published HF pickle → relation labels only., :param number: int - fold number :param lang: str - (main) language :param…, :param lang: str - (main) language :param mixed: int - percentage for other…, Makes self.mixed_train_* versions with 100% train files from first language and…, :param corpus: str - from {'GUM', 'RST-DT', 'RuRSTB', 'RST-DT-tr',} :param… (+3 more)

### Community 45 - "Docling Text Harvesting"
Cohesion: 0.11
Nodes (29): harvest_docling_text(), DoclingDocument, HarvestResult, Produce the main document harvest with per-span self_ref mapping. Args: doc: a…, DoclingDocument, Span ``kind`` mirrors the Docling item label so consumers can distinguish…, All 5 PPTX pictures with meta.description.text appear in the harvest., PDF fixture: 48 pictures, 0 with meta.description.text — none in harvest. (+21 more)

### Community 46 - "Model Training Manager"
Cohesion: 0.12
Nodes (18): Any, Data, Module, no_grad, Path, Tensor, Default DMRST method for linear learning rate adjustment (deprecated)., Trains the model. Returns: dict: best_metrics (+10 more)

### Community 47 - "Sentence Span Management"
Cohesion: 0.13
Nodes (9): DataManager, Node, Path, One-way import of a published HF pickle → relation labels only., Makes self.mixed_train_* versions with 100% train files from first language and…, :param corpus: str - from {'GUM', 'RST-DT', 'RuRSTB'} :param cross_validation:…, Take all rs3 documents and save them in the same directory as *.edus and *.lisp…, Scatter examples on folds divided into train/val/test. Preserve subclasses… (+1 more)

### Community 48 - "Parser Public API"
Cohesion: 0.09
Nodes (16): Parser, Public façade for the DMRST and UniRST parser families. The family is resolved…, Parse a document using predefined EDUs., parser_cpu(), fixture, Real DMRST end-to-end model parsing into a typed RstAnalysis contract., Real UniRST end-to-end multilingual model parse into RstAnalysis., Edge cases on real model: unicode punctuation, multi-paragraph, and empty fails. (+8 more)

### Community 49 - "Tree Binarization Logic"
Cohesion: 0.17
Nodes (26): binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), cleanChildren(), correctThiago(), find_missing_eduspan(), find_missing_eduspan_backup(), findChild() (+18 more)

### Community 50 - "DMRST Neural Modules"
Cohesion: 0.11
Nodes (12): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param input_size: int - input size :param hidden_size: int - hidden size of…, Default classifier takes as input averaged DU representations, BiMPM computes… (+4 more)

### Community 51 - "Parser Smoke Tests"
Cohesion: 0.15
Nodes (24): _assert_tree_aligned(), _check(), _check_from_edus(), _check_parse_rst(), _collect_leaves(), _expect_raises(), main(), Path (+16 more)

### Community 52 - "Markdown Content Harvesting"
Cohesion: 0.12
Nodes (23): harvest_markdown_tables(), harvest_markdown_text(), _inline_text(), _line_range(), HarvestResult, TableHarvest, Harvest text from a markdown token stream for RST parsing. Two harvesters: -…, Produce one ``TableHarvest`` per table, in document order. Tables inside… (+15 more)

### Community 53 - "Tree Propagation Logic"
Cohesion: 0.14
Nodes (21): backprop(), BFTbin(), __getforminfo(), getParse(), getParseNobin(), __getrelationinfo(), __getspaninfo(), parse() (+13 more)

### Community 54 - "Parser Cache Tests"
Cohesion: 0.18
Nodes (22): Path, Two paragraphs so the stub emits a relation tree., Path and str inputs reach the same guard., Hand-written prose-only Docling: empty ``table_analyses``, and main relations…, Tiny hand-written Docling JSON with one text paragraph., Deterministic Parser stand-in — no model load., StubParser, test_cache_misses_when_device_changes() (+14 more)

### Community 55 - "DMRST Parser Metrics"
Cohesion: 0.13
Nodes (20): Data, nucs_and_rels(), One batched parser example. Field order matches the historical constructor., calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics() (+12 more)

### Community 56 - "Neural Segmenter Models"
Cohesion: 0.14
Nodes (5): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter

### Community 57 - "Universal Parser Labels"
Cohesion: 0.14
Nodes (21): addLabels(), checkTree(), countLabels(), getLabelMapping(), getRelation(), __gettextinfo(), mapLabels(), performMapping() (+13 more)

### Community 58 - "Universal Parser Discriminator"
Cohesion: 0.11
Nodes (13): Data, getLabelOrdered(), nucs_and_rels(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…, One batched parser example. Field order matches the historical constructor., Discriminator (+5 more)

### Community 59 - "Docling Quality Checks"
Cohesion: 0.16
Nodes (20): main(), Any, Phase 0 steps 6 and 7 — long-input smoke and determinism check. Step 6: parse a…, Build a structural signature of a tree for equality comparison. Captures…, tree_signature(), collect_leaves(), collect_relations(), extract_picture_description() (+12 more)

### Community 60 - "Parser Family Resolution"
Cohesion: 0.15
Nodes (6): Any, device, dtype, When both family and version are set, version must belong to family., Explicit family must match detectable signatures when present., TestResolveFamily

### Community 61 - "RS3 Viewer Database"
Cohesion: 0.19
Nodes (20): rs3tohtml(), delete_document(), get_rst_doc(), import_document(), Path, Parse and import an RS3 file into the local rstWeb SQLite database., Return database representation of the given RS3 file., Create a private SQLite file for one render; unlink in ``finally``. (+12 more)

### Community 62 - "Markdown Entry Tests"
Cohesion: 0.12
Nodes (15): Any, Build the ``source_origin`` block for the result., _source_origin(), parser(), fixture, Unit + integration tests for ``isanlp_rst.markdown.parse_markdown``. Fast unit…, ``@cache`` invariant: identical object across calls., Pin the wire-format identifier — downstream consumers branch on it. (+7 more)

### Community 63 - "Universal Parser Modules"
Cohesion: 0.13
Nodes (9): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+1 more)

### Community 64 - "Parsing Network Implementation"
Cohesion: 0.17
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 65 - "Docling Entry Tests"
Cohesion: 0.12
Nodes (13): Any, Serialise ``doc.origin`` (a Pydantic model) to a JSON-safe dict. Returns ``{}``…, _serialise_source_origin(), _Node, parser(), fixture, Unit + integration tests for ``isanlp_rst.docling.parse_docling``. Fast unit…, Two calls return the identical object — caching is the contract. (+5 more)

### Community 66 - "HTML Viewer Helpers"
Cohesion: 0.29
Nodes (7): PathLike, Convert an ``.rs3`` file into HTML. Parameters ---------- rs3_path: Path to the…, to_html(), Path, Unit tests for viewer convenience helpers in ``isanlp_rst``., When ``html_path`` is set, ``to_html`` must write the file AND return the HTML…, test_to_html_returns_string_and_writes_file()

### Community 67 - "RST Ontology Adapter"
Cohesion: 0.16
Nodes (15): OntologyAdapter, Adapts and resolves model outputs and corpus labels against the pinned ontology., Strip embedded (-e) and nuclearity (-s/-n) suffixes from RST-DT labels., Resolve a raw corpus label to its canonical label and coarse concept., load_ontology_lock(), Path, Load and parse the ontology lockfile, caching the immutable structure., Unit tests for ontology lock loader and adapter. (+7 more)

### Community 68 - "Model Family Detection"
Cohesion: 0.18
Nodes (5): Path, Inspect a local checkpoint directory and infer the parser family. Returns…, Read ``path`` as JSON. Returns ``None`` if the file is missing, unreadable, or…, If both signatures are present, UniRST wins (more specific)., TestDetectFamilyFromModelDir

### Community 69 - "Parse Result Helpers"
Cohesion: 0.19
Nodes (16): DiscourseUnit, Parse text and return a typed RST root instead of the legacy mapping payload.…, extract_root_tree(), ParseFailedError, Any, Helpers for unpacking ``Parser`` / predictor call results., Return ``result['rst'][0]``, or raise :class:`ParseFailedError`. Preferred over…, Raised when a parse result has no usable RST root tree. (+8 more)

### Community 70 - "DPLP Tree Utilities"
Cohesion: 0.13
Nodes (19): buildTree(), buildTreeThiago(), checkcontent(), convert_parens_in_rst_tree_str(), createnode(), createnodeThiago(), createtext(), processtext() (+11 more)

### Community 71 - "Parsing Network Logic"
Cohesion: 0.19
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 72 - "Docling Parsing Tests"
Cohesion: 0.17
Nodes (18): parse_docling(), Path, Parse a Docling JSON file and return its RST analysis. Args: path: filesystem…, slow, Two-level invariant: cells live in table_analyses, the synthetic marker lives…, The PPTX fixture has 20 tables — analyses exist for those with non-empty cells,…, Every relation ref points to a self_ref that exists in the source., Two calls with the same injected parser return consistent results. (+10 more)

### Community 73 - "DMRST Binary Trees"
Cohesion: 0.20
Nodes (8): collect(), BinaryTree, Node, Path, :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 74 - "Training Metric Utilities"
Cohesion: 0.22
Nodes (6): _metrics_as_floats(), Any, Data, no_grad, Path, TrainingManager

### Community 75 - "Docling Table Harvesting"
Cohesion: 0.18
Nodes (15): harvest_docling_tables(), TableHarvest, Produce one ``TableHarvest`` per ``TableItem``, in ``doc.tables`` order. Cell…, markdown_doc(), pdf_doc(), pptx_doc(), fixture, Unit tests for the docling harvesters (main text + per-table). (+7 more)

### Community 76 - "Universal Binary Trees"
Cohesion: 0.20
Nodes (8): collect(), BinaryTree, Node, Path, :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 77 - "Bottom-Up Transition Parser"
Cohesion: 0.22
Nodes (8): _Node, ParsingNetBottomUp, Any, Tensor, Bottom-up transition-based parser. This module reuses the encoder, segmenters…, Reconstructs the gold tree from pre-order traversal., Return gold transition sequence in postorder., ParsingNet

### Community 78 - "Schema Compatibility Tests"
Cohesion: 0.17
Nodes (15): parametrize, Path, Compatibility guard: do we still read CURRENT Docling / DocLang output? The…, Return the XML namespace declared on a fixture's root element (or '')., Guard against the guard silently no-opping if fixtures are moved/renamed — an…, Each fixture's declared Docling schema version must equal the installed…, The installed docling-core must validate-load each fixture AND our harvester…, Our ``DOCLANG_NS`` constant must match the namespace the installed doclang… (+7 more)

### Community 79 - "BiMPM Neural Module"
Cohesion: 0.29
Nodes (6): BiMPM, device, Tensor, :param v1: (batch, seq_len, hidden_size) :param v2: (batch, seq_len,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, Inputs can be of infinite length, hence BiMPM matching can cause OOM. This is a…

### Community 80 - "Contract Isolation Tests"
Cohesion: 0.16
Nodes (12): _CapturingParser, _Node, MonkeyPatch, parametrize, Path, Wave 4 — construct-path kwargs + formats-extra isolation., Core ``isanlp_rst.parser`` must not require the formats extra., Stand-in for ``Parser`` that records constructor kwargs. (+4 more)

### Community 81 - "DMRST Encoder RNN"
Cohesion: 0.20
Nodes (7): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts., :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…

### Community 82 - "Analysis Integration Tests"
Cohesion: 0.22
Nodes (10): du_to_analysis(), Any, Convert an isanlp.annotation_rst.DiscourseUnit tree into a typed RstAnalysis., DummyPredictor, DiscourseUnit, MonkeyPatch, Unit tests for Parser.parse_document integration., test_du_to_analysis_nuclearity_and_relations() (+2 more)

### Community 83 - "Universal Parser Metrics"
Cohesion: 0.32
Nodes (12): calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement(), get_micro_metrics(), get_seg_measure() (+4 more)

### Community 84 - "Parser Input Models"
Cohesion: 0.21
Nodes (6): ParserInput, Any, Data, Mutable per-document parser example. Extra attributes stay settable., :param number: int - fold number :param lang: str - (main) language :param…, :param lang: str - (main) language :param mixed: int - percentage for other…

### Community 85 - "Docling Error Handling"
Cohesion: 0.24
Nodes (11): DoclingRstError, EmptyDoclingError, EmptyHarvestError, InputTooLargeError, Exception, Custom exceptions for Docling-native RST parsing., The harvest produced no text (e.g. a tables-only document)., Harvested text exceeds the configured length threshold. (+3 more)

### Community 86 - "RST Quality Diagnostics"
Cohesion: 0.29
Nodes (12): _discover(), DocMetrics, _format_of(), main(), _metrics(), _parse(), _print_table(), Any (+4 more)

### Community 87 - "DMRST Experiment Runner"
Cohesion: 0.23
Nodes (5): MultipleRunnerGeneral, Script for multiple runs of experiments. For monolingual experiments run: #…, Running training with second language injection of ``mixed`` %, :param corpus: (str) - 'GUM' or 'RST-DT' :param lang: (str) - 'en' or 'ru'…, range

### Community 88 - "CRF Sequence Decoding"
Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from https://github.com/kmkurn/pytorch-…, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 89 - "MIME Type Registration"
Cohesion: 0.21
Nodes (9): ensure_docling_mimetypes(), Platform MIME registrations required by Docling JSON validation. ``docling-…, Idempotently register MIME types Docling ImageRef may require., Pytest session fixtures / env bootstrap for the isanlp_rst suite. Registers…, _clear_webp_mapping(), Production MIME registration for Docling ImageRef validation., Remove ``.webp`` from the stdlib MIME map; return prior value if any., Production registration — not conftest — must make WebP fixtures load. Forces… (+1 more)

### Community 90 - "Relation Inventory I/O"
Cohesion: 0.23
Nodes (10): _ensure_parent_module(), ensure_unirst_module_aliases(), import_relation_table_from_legacy_pickle(), load_relation_inventory_json(), Path, Relation-inventory I/O for UniRST. Native format is JSON (or a plain…, One-way import: published HF pickles → ``relation_table`` labels only., Register Elena-era module paths so legacy pickles can unpickle ParserInput. (+2 more)

### Community 91 - "Universal Encoder RNN"
Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 92 - "Binary Tree Attachment"
Cohesion: 0.22
Nodes (9): RST tree node (from DPLP, by Yangfeng Ji), SpanNode, binarizeTreeRight(), Convert a general RST tree to a binary RST tree (from DPLP, by Yangfeng Ji)…, binarizeTreeGeneral(), leftAttach(), Convert a general RST tree to a binary RST tree < DPLP but modified: no more…, rightAttach() (+1 more)

### Community 93 - "Adversarial Learning Discriminator"
Cohesion: 0.20
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 * 19 * 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 94 - "Docling Metadata Harvesting"
Cohesion: 0.18
Nodes (10): _label_value(), _picture_description(), PictureItem, Harvest text from a DoclingDocument for RST parsing. Two harvesters: -…, Return the string value of a Docling enum label, or str(thing)., Return ``picture.meta.description.text`` when present and non-empty., HarvestResult, Concatenated harvest produced from a DoclingDocument. ``full_text`` is the… (+2 more)

### Community 95 - "Markdown Error Handling"
Cohesion: 0.24
Nodes (10): EmptyHarvestError, EmptyMarkdownError, InputTooLargeError, MarkdownRstError, Exception, Custom exceptions for Markdown-native RST parsing., The harvest produced no text (e.g. all knobs gated their content out)., Harvested text exceeds the configured length threshold. (+2 more)

### Community 96 - "Sentence Parsing Helpers"
Cohesion: 0.31
Nodes (4): ParserInput, Any, Node, Mutable per-document parser example. Extra attributes (legacy pickle…

### Community 97 - "Universal Experiment Runner"
Cohesion: 0.25
Nodes (4): MultipleRunnerGeneral, Script for multiple runs of experiments. For monolingual experiments run: #…, Running training with second language injection of ``mixed`` %, :param corpora: corpus names, e.g. ['GUM'] or ['RST-DT'] :param lang: 'en' or…

### Community 98 - "RST Analytical Helpers"
Cohesion: 0.27
Nodes (10): find_cdu(), _is_leaf(), Any, Analytical helpers for parsed RST trees. These functions operate on…, Classify an RST relation label as subject-matter or presentational. Follows…, Compute structural diagnostics for an RST tree. Returned dict keys: ``depth``…, Locate the Central Discourse Unit (CDU) of an RST tree. Descends from the root…, relation_category() (+2 more)

### Community 99 - "Repository Cleanup Utility"
Cohesion: 0.31
Nodes (10): collect_junk(), _display(), is_junk_dir(), is_junk_file(), main(), Path, Remove regenerable junk from the repo: bytecode, tool caches, temp files. Does…, Delete ``paths``. Returns the number of paths acted on. (+2 more)

### Community 100 - "Markdown Integration Tests"
Cohesion: 0.18
Nodes (11): slow, End-to-end smoke: verify the result carries the pinned wire-format identifiers…, Shared id namespace invariant — every left/right ref points to a known relation…, gfm-rich has one table → one analysis whose refs resolve against the table…, Round-trip closure: every relation ref must be a HarvestSpan block_ref., Idempotence: same input + same parser → identical relation shape., test_parse_markdown_emits_expected_metadata(), test_parse_markdown_ids_resolve_left_right() (+3 more)

### Community 101 - "Dtype Normalization"
Cohesion: 0.22
Nodes (9): dtype, Normalise a dtype spec to a ``torch.dtype``. Accepts: * ``None`` -> ``float32``…, parametrize, Default is fp32 on every device — measured fp32 wins on MPS for typical inputs;…, test_resolve_dtype_default_is_float32(), test_resolve_dtype_passthrough(), test_resolve_dtype_string_parsing(), test_resolve_dtype_unknown_string_raises() (+1 more)

### Community 102 - "Cleanup Script Tests"
Cohesion: 0.29
Nodes (8): fixture, Path, Unit tests for ``scripts/cleanup.py`` (stdlib-only project cleaner)., test_collects_bytecode_caches_and_temp_not_source(), test_dry_run_does_not_delete(), test_remove_deletes_junk_keeps_source_and_protected(), test_skips_git_and_pixi_trees(), tree()

### Community 104 - "Discourse Unit Mocking"
Cohesion: 0.28
Nodes (8): _FakeNode, _Predictor, Stand-in for isanlp.DiscourseUnit with the attributes used by remap., Minimal concrete subclass (BasePredictor is ABC)., Unary node = DUConverter bug; surface it rather than patch it., test_remap_tree_offsets_binary(), test_remap_tree_offsets_leaf(), test_remap_tree_offsets_unary_raises()

### Community 105 - "Project Workflow Tasks"
Cohesion: 0.39
Nodes (8): speckit-converge, speckit-implement, speckit-plan, speckit-specify, speckit-tasks, speckit-taskstoissues, isanlp_rst Constitution, Full SDD Cycle Workflow

### Community 106 - "File Access Linter"
Cohesion: 0.43
Nodes (6): is_content_free(), looks_like_path(), main(), offending_tool(), Return (tool, path) for the first file-reading invocation, else None.…, True when this invocation cannot print a line of file content. Every argument…

### Community 107 - "EDU File Utilities"
Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 108 - "RST XML Processing"
Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element, _ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 109 - "Label Ordering Logic"
Cohesion: 0.50
Nodes (4): getLabelOrdered(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…

### Community 110 - "Docling JSON Fixtures"
Cohesion: 0.29
Nodes (7): _minimal_docling_json(), Body contains only a one-cell table — no prose harvest., Table-only + ``include_table_cells=False`` → nothing to parse., Minimal DoclingDocument JSON for tmp_path fixtures., test_empty_docling_error(), test_empty_harvest_error_when_tables_disabled_on_table_only_doc(), _write_table_only_docling()

### Community 111 - "DMRST Config Reader"
Cohesion: 0.33
Nodes (3): ConfigReader, Any, Path

### Community 112 - "Universal Parser Config"
Cohesion: 0.33
Nodes (3): ConfigReader, Any, Path

### Community 113 - "Performance Benchmarking"
Cohesion: 0.47
Nodes (5): main(), Performance benchmark for isanlp_rst across devices and dtypes. Usage: pixi run…, Run parser n times after a warm-up. Return median seconds and tree shape., _shape(), _time_parse()

### Community 114 - "Token Offset Mapping"
Cohesion: 0.40
Nodes (4): _OffsetToken, Protocol, Minimal razdel-token surface used by offset remapping., Build offset converter from a list of `razdel.Token` objects.

### Community 115 - "CUDA Verification Script"
Cohesion: 0.60
Nodes (4): _assert_aligned(), _collect_leaves(), main(), CUDA verification script — to be run on a real NVIDIA host. Usage: pixi run…

### Community 116 - "Docling Smoke Tests"
Cohesion: 0.50
Nodes (4): main(), Path, Smoke-iterate Docling JSON fixtures via docling-core's canonical walker. Phase…, smoke_iterate()

### Community 117 - "Table Harvest Invariants"
Cohesion: 0.50
Nodes (5): FixtureRequest, parametrize, Two-level invariant: tables live in their own harvests; the main document…, test_main_harvest_never_contains_table_refs(), test_offsets_match_full_text()

### Community 118 - "RST Planning Strategies"
Cohesion: 0.50
Nodes (4): Ontology Lock, DocLang-native RST Plan, Docling-native RST Plan, Markdown-native RST Plan

### Community 121 - "DocLang Specification"
Cohesion: 0.67
Nodes (3): Verified DocLang Fixtures, Verified DocLang Spec, doclang PyPI Package

### Community 122 - "Docling Core Integration"
Cohesion: 0.67
Nodes (3): Verified Docling Core API, Verified Docling Schema, docling_core.DoclingDocument

### Community 125 - "Parser Test Fixtures"
Cohesion: 0.67
Nodes (3): parser(), fixture, Construct gumrrg parser once for the slow tests.

## Knowledge Gaps
- **24 isolated node(s):** `no-assumptions-check.sh script`, `cleanup.sh script`, `isanlp_rst`, `common.sh script`, `DocLang 0.7 Spec` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Parser` connect `Parser Public API` to `RST Tree Conversion`, `Analysis Data Structures`, `Model Family Detection`, `Parse Result Helpers`, `RST Document Representation`, `EDU Segmentation Dataset`, `Parser Family Resolution`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Why does `parse_markdown()` connect `Markdown Parsing Tests` to `Markdown Boundary Tests`, `Parse Result Helpers`, `Parser Entry Points`, `DocLang API Schema`, `Markdown Loader Logic`, `Markdown Boundary Mapping`, `Parser Public API`, `Markdown Content Harvesting`, `Markdown Entry Tests`, `Markdown Error Handling`?**
  _High betweenness centrality (0.003) - this node is a cross-community bridge._
- **Why does `PredictorDMRST` connect `DMRST Predictor Implementation` to `Base Predictor Logic`, `RST Parsing Interface`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `Parser` (e.g. with `ErstCompleter` and `DiscourseMarkerPrimer`) actually correct?**
  _`Parser` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `RstAnalysis` (e.g. with `ProvenanceRecord` and `FailureCodeEnum`) actually correct?**
  _`RstAnalysis` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `parse_doclang()` (e.g. with `EmptyDoclangError` and `EmptyHarvestError`) actually correct?**
  _`parse_doclang()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `parse_markdown()` (e.g. with `EmptyHarvestError` and `EmptyMarkdownError`) actually correct?**
  _`parse_markdown()` has 7 INFERRED edges - model-reasoned connections that need verification._