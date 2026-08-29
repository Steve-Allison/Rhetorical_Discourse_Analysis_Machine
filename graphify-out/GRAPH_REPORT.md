# Graph Report - isanlp_rst  (2026-08-29)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 4498 nodes · 11614 edges · 191 communities (163 shown, 28 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 1194 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1ad15be5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- erst/runner.py
- erst/contracts.py
- gum_validator.py
- CorpusPartition
- gold.py
- test_production_boundary.py
- RstAnalysis
- contracts/__init__.py
- load_doclang_archive
- validate_model_release
- ProductionIngestor
- contracts/erst.py
- TrainingManager
- prepare.py
- SecondaryEdgeCandidate
- jquery-1.11.3.min.js
- isanlp_rst/erst/__init__.py
- SourceArtifact
- DiscourseSignal
- NuclearityPatternEnum
- rstweb_sql.py
- parser.py
- unirst/utils_rs3.py
- test_runner.py
- SpanNode
- main.py
- dmrst/utils_rs3.py
- read_rst
- test_integration.py
- technology.py
- unirst/common.py
- ProductionAnalysisResult
- Path
- candidates.py
- dmrst/common.py
- dmrst/data.py
- finalize_selection.py
- RstDocument
- compute_calibration_error
- dmrst/utils_dis_thiago.py
- DataManager
- common.sh
- DataManager
- test_erst_checkpoint.py
- ingest/contracts.py
- properties
- DiscourseUnit
- PredictorDMRST
- structure.js
- test_blake3_hashing.py
- load_repository_environment
- Parser
- ParserInput
- load_markdown
- protocol.py
- DocumentToken
- BasePredictor
- dmrst_parser/src/parser/parsing_net.py
- test_serialization.py
- test_base_predictor.py
- verify_gum_corpus_manifest.py
- test_erst_decoder.py
- semantic_sha256
- universal_parser/src/parser/segmenters.py
- FrozenEvaluationAdapter
- universal_parser/predictor.py
- test_unirst_pickle_security.py
- test_discourse_unit.py
- ._detect_family_from_model_dir
- smoke_test.py
- test_transformer_segmenter.py
- RS4Document
- PredictorUniRST
- DUConverter
- BoundaryAwareSpanEncoder
- docling_rst_quality_check.py
- ToNySegmenter
- rs4_to_document_and_analysis
- test_parser_attention.py
- ._graph_inputs
- to_html
- test_parse_result.py
- ParsingNet
- model_validator
- Parsing Network Logic
- PureTransformerParsingNet
- BiMPM
- ._resolve_family
- ParsingNetBottomUp
- .divide_chunks
- base_predictor.py
- probe_erst_tokenizers.py
- model_authority.py
- BinaryTree
- BinaryTree
- ._load_torch_weights
- Data
- RS4Reader
- rs3tohtml
- TemperatureCalibration
- CrossEncoderConfig
- str2bool
- installed_acceptance.py
- TransformerBoundarySpanEncoder
- DocLang Fixture Verification
- buildTree
- DeepBiaffineScorer
- ._guess_token_offsets
- EncoderRNN
- CRF
- .parse_rst
- EncoderRNN
- CRF
- MultipleRunnerGeneral
- test_transformer_parser.py
- Discriminator
- tree_stats
- cleanup.py
- _Predictor
- model_validator
- MultipleRunnerGeneral
- MpsMemorySampler
- test_cleanup.py
- parseXML
- _StructuralClassifier
- smoke.py
- ErstCheckpointVerificationReceipt
- train_segmenter
- verify_model_licensing.py
- test_doclang_fixture_parity.py
- GumCorpusValidationReport
- test_runtime_provenance.py
- parseXML
- EduSegmentationDataset
- SecondaryEdgeInferenceDataset
- offending_tool
- SignalPattern
- verify_markdown_manifest.py
- clean_install.py
- findFile
- findFile
- AblationPlan
- ConfigReader
- ConfigReader
- InvalidSegmenterCheckpointError
- bench.py
- test_public_api.py
- test_megadoc_stress.py
- _HierarchicalAdapterModel
- cuda_smoke.py
- smoke_iterate
- DummyPredictor
- TestCudaDeviceValidation
- test_release_versions.py
- test_wave4_contracts.py
- production_smoke.py
- CustomTokenizer
- no-assumptions-check.sh
- doclang/__init__.py
- markdown/__init__.py
- conftest.py
- ingest/production_ingest/__init__.py
- tools/__init__.py
- tools/production_ingest/__init__.py
- corpus/__init__.py
- evaluation/__init__.py
- workbench/__init__.py
- systems/__init__.py
- workbench/research/__init__.py
- training/__init__.py
- BaseModel
- DiGraph
- StrEnum
- Any
- device
- dtype
- PreTrainedTokenizerBase
- isanlp_rst
- CustomTokenizer

## God Nodes (most connected - your core abstractions)
1. `RstAnalysis` - 155 edges
2. `Parser` - 113 edges
3. `RstDocument` - 95 edges
4. `SourceArtifact` - 69 edges
5. `SpanNode` - 68 edges
6. `CorpusPartition` - 66 edges
7. `ProductionIngestor` - 64 edges
8. `DiscourseUnit` - 64 edges
9. `RstNode` - 61 edges
10. `PrimaryRelationEdge` - 55 edges

## Surprising Connections (you probably didn't know these)
- `test_range_is_non_empty_and_half_open()` --uses--> `PreparedRange`  [INFERRED]
  tests/ingest/production_ingest/test_contracts.py → isanlp_rst/ingest/contracts.py
- `test_ontology_adapter_handles_unusual_and_unknown_inputs()` --uses--> `OntologyAdapter`  [INFERRED]
  tests/unit/test_adversarial_stress.py → isanlp_rst/ontology/adapter.py
- `test_discourse_unit_internal_node()` --uses--> `DiscourseUnit`  [INFERRED]
  tests/unit/test_discourse_unit.py → isanlp_rst/annotation_rst.py
- `test_discourse_unit_leaf_creation()` --uses--> `DiscourseUnit`  [INFERRED]
  tests/unit/test_discourse_unit.py → isanlp_rst/annotation_rst.py
- `test_discourse_unit_textfields_manipulation()` --uses--> `DiscourseUnit`  [INFERRED]
  tests/unit/test_discourse_unit.py → isanlp_rst/annotation_rst.py

## Import Cycles
- 3-file cycle: `workbench/corpus/dmrst/__init__.py -> workbench/corpus/dmrst/data_manager.py -> workbench/corpus/dmrst/data.py -> workbench/corpus/dmrst/__init__.py`
- 3-file cycle: `workbench/corpus/unirst/__init__.py -> workbench/corpus/unirst/data_manager.py -> workbench/corpus/unirst/data.py -> workbench/corpus/unirst/__init__.py`

## Communities (191 total, 28 thin omitted)

### Community 0 - "erst/runner.py"
Cohesion: 0.05
Nodes (78): Exception, Explicit, non-logging repository environment loading for eRST operations., IncompatibleAdapter, Synthetic measured incompatibility proving durable unsuccessful evidence., Frozen, model-neutral ablation definitions and evidence boundaries., canonical_threshold_grid(), Frozen development threshold grid, including the neutral 0.5 point., GenerativeDecoderConfig (+70 more)

### Community 1 - "erst/contracts.py"
Cohesion: 0.04
Nodes (102): _protocol(), Regression tests for calibration, statistics, resources, and system constraints., _receipt(), _resource(), test_bootstrap_and_holm_are_reproducible_and_content_hashed(), test_screening_completeness_requires_every_system_seed_disposition(), _protocol(), Contract tests for executable eRST comparison evidence. (+94 more)

### Community 2 - "gum_validator.py"
Cohesion: 0.03
Nodes (74): Counter, DirectedSpanKey, K, GumGoldValidator, GumValidationReport, Path, GUM Gold Standard Validation Engine. Provides automated validation of processed…, Validator that verifies model predictions or processed files against GUM gold… (+66 more)

### Community 3 - "CorpusPartition"
Cohesion: 0.04
Nodes (70): CorpusPartition, PrivateCorpusVerificationReceipt, Official GUM document partitions., Full-source and sampled-candidate verification for the private corpus., main(), Derive the raw eRST relation inventory from the official GUM train partition., Persist a text-free train-derived raw relation inventory., _candidate() (+62 more)

### Community 4 - "gold.py"
Cohesion: 0.05
Nodes (78): Path, Stream a local regular file into a SHA-256 digest., sha256_file(), MonkeyPatch, parametrize, Isolated wheel runner fails closed before executing ambiguous candidates., test_baseline_runner_requires_full_immutable_commit(), test_candidate_runner_rejects_invalid_determinism_run_counts() (+70 more)

### Community 5 - "test_production_boundary.py"
Cohesion: 0.06
Nodes (69): Path, Causal tests for the production/offline boundary authority., test_ambiguous_relevant_path_fails_closed(), test_artifact_dependencies_are_read_from_metadata(), test_authority_classifies_each_surface(), test_commit_export_build_cannot_package_stale_build_tree(), test_direct_production_to_offline_import_reports_complete_path(), test_forbidden_sdist_member_is_named() (+61 more)

### Community 6 - "RstAnalysis"
Cohesion: 0.06
Nodes (66): PrimaryRelationEdge, Complete discourse analysis result., Find the root node if present., Look up a node by its ID., A node in a discourse tree or graph., A directed primary rhetorical relation edge with nuclearity., A directed secondary rhetorical relation edge without nuclearity., RstAnalysis (+58 more)

### Community 7 - "contracts/__init__.py"
Cohesion: 0.06
Nodes (72): Native Rhetorical Structure Theory (RST) tree annotations and RS3…, FormatRstAnalysis, Discourse analysis result models and graph structures., Execution timing profile in milliseconds., Composite analysis for structured documents (Docling, DocLang, Markdown)., TimingRecord, ProvenanceRecord, Document input models and coordinate representation. (+64 more)

### Community 8 - "load_doclang_archive"
Cohesion: 0.06
Nodes (71): DoclangIngestError, InvalidDoclangError, ValueError, Failures raised by the private DocLang source loader., A DocLang archive violates bounded local ZIP safety invariants., Base class for DocLang validation and archive-loading failures., The XML file is not a valid DocLang document., UnsafeDoclangArchiveError (+63 more)

### Community 9 - "validate_model_release"
Cohesion: 0.06
Nodes (62): Production-safe released-model contracts and loaders., canonical_json_bytes(), load_model_release(), ModelFile, ModelReleaseError, ModelReleaseIdentity, ModelReleaseManifest, PromotionReceipt (+54 more)

### Community 10 - "ProductionIngestor"
Cohesion: 0.07
Nodes (60): AnalysisUnit, PreparedRange, PreparedRstDocument, SegmentKind, StructureKind, prepare_source(), Prepare one source and return complete semantic evidence., _structure_kind() (+52 more)

### Community 11 - "contracts/erst.py"
Cohesion: 0.07
Nodes (68): CandidateIdentityProbe, CorpusAuthorityEntry, CorpusDocumentReceipt, CorpusFailureType, CorpusLicenseClass, CorpusLoadFailure, CorpusLoadReceipt, GumCorpusAuthority (+60 more)

### Community 12 - "TrainingManager"
Cohesion: 0.05
Nodes (48): calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement(), get_micro_metrics(), get_seg_measure() (+40 more)

### Community 13 - "prepare.py"
Cohesion: 0.10
Nodes (67): AnchorKind, AuthorshipRole, ContentClass, ContentInventoryItem, DispositionKind, NativeAnchor, PreparationPolicy, StrEnum (+59 more)

### Community 14 - "SecondaryEdgeCandidate"
Cohesion: 0.05
Nodes (58): CandidateDocumentSelection, CandidateSelectionReceipt, HardNegativeSamplingConfig, Deterministic training-only hard-negative selection configuration., Complete-versus-selected counts for one already-partitioned document., Hashed evidence that only train candidates were sampled., Complete evidence for one ordered primary-tree node pair., SecondaryEdgeCandidate (+50 more)

### Community 15 - "jquery-1.11.3.min.js"
Cohesion: 0.06
Nodes (42): ba(), Ea(), Fa(), fb(), ga(), ha(), b(), hb() (+34 more)

### Community 16 - "isanlp_rst/erst/__init__.py"
Cohesion: 0.08
Nodes (57): ErstCheckpointManifest, ErstCheckpointTestVector, ErstDecoderConfig, ErstGraphComponentConfig, ErstScorerConfig, Immutable threshold and raw-relation inventory for eRST decoding., Architecture fields required to reconstruct a scorer without network access., Explicit graph-component declaration, including the state-free case. (+49 more)

### Community 17 - "SourceArtifact"
Cohesion: 0.06
Nodes (46): _identify_path(), _media_type(), Path, SourceArtifact, SourceForm, _artifact(), _discover(), DocMetrics (+38 more)

### Community 18 - "DiscourseSignal"
Cohesion: 0.06
Nodes (40): DiscourseSignal, BaseModel, field_validator, Require valid half-open anchors while retaining overlap and order., Require non-empty, unique raw relation labels., Immutable identity of the detector or source that produced a signal., Typed, anchored discourse signal; overlaps are explicitly permitted., Require unique non-negative token identifiers without reordering. (+32 more)

### Community 19 - "NuclearityPatternEnum"
Cohesion: 0.06
Nodes (41): NuclearityPatternEnum, Nuclearity pattern for primary relation edges., Rhetorical relation annotation or model scheme., RelationSchemeEnum, Runtime projection of raw GUM eRST relations to ontology concepts., Project one raw GUM relation while preserving the caller's raw value., resolve_gum_relation_concept(), OntologyAdapter (+33 more)

### Community 20 - "rstweb_sql.py"
Cohesion: 0.13
Nodes (49): add_node(), add_seg(), count_children(), count_multinuc_children(), count_span_children(), delete_document(), delete_node(), generic_query() (+41 more)

### Community 21 - "parser.py"
Cohesion: 0.06
Nodes (41): Create an RstDocument from raw text without pre-segmented EDUs., analysis_from_json(), Deserialize an RstAnalysis from a JSON string., CompleterConfig, Configuration for eRST graph completion and candidate filtering., English eRST graph completion package., ErstCapabilityError, A requested eRST completion capability has no validated bundle. (+33 more)

### Community 22 - "unirst/utils_rs3.py"
Cohesion: 0.10
Nodes (48): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+40 more)

### Community 23 - "test_runner.py"
Cohesion: 0.07
Nodes (32): PayloadT, _data(), _protocol(), Path, Execution-path tests for the isolated eRST technology-comparison harness., Synthetic system proving the shared runner without private corpus access., _request(), SuccessfulAdapter (+24 more)

### Community 24 - "SpanNode"
Cohesion: 0.11
Nodes (44): RST tree node used by the universal parser corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), buildTree(), buildTreeThiago() (+36 more)

### Community 25 - "main.py"
Cohesion: 0.06
Nodes (53): AsyncBrowser, AsyncPage, AsyncPlaywright, Browser, IO, T, Render an RST tree and, optionally, display it inline. This is a light-weight…, Render an ``.rs3`` file to PNG (works in both sync and async environments). (+45 more)

### Community 26 - "dmrst/utils_rs3.py"
Cohesion: 0.10
Nodes (45): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+37 more)

### Community 27 - "read_rst"
Cohesion: 0.09
Nodes (39): Document, get_depth(), get_left_right(), NODE, NodeMap, RST tree node types and parent-chain attribute walks., EDU used by the segmenter, not by the structurer., Set graphical nesting depth of ``orig_node`` from the parent chain. RST… (+31 more)

### Community 28 - "test_integration.py"
Cohesion: 0.09
Nodes (45): _assert_aligned(), _collect_leaf_units(), _collect_leaves(), dmrst_gumrrg_cpu(), dmrst_rstdt_cpu(), dmrst_rstreebank_cpu(), fixture, parametrize (+37 more)

### Community 29 - "technology.py"
Cohesion: 0.10
Nodes (38): HfApi, Technology-matrix tests for completeness, evidence, and non-substitution., _required_revision(), test_frozen_live_matrix_has_weight_evidence_for_every_model_row(), test_hub_evidence_must_cover_every_model_and_preserve_revision_and_license(), test_matrix_rejects_dropped_system(), test_matrix_retains_all_systems_and_explicit_constraints(), freeze_matrix() (+30 more)

### Community 30 - "unirst/common.py"
Cohesion: 0.08
Nodes (42): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), Document, __getforminfo(), getLabelMapping() (+34 more)

### Community 31 - "ProductionAnalysisResult"
Cohesion: 0.10
Nodes (26): ProductionIngestCache, Path, Integrity-checked, same-filesystem atomic cache for semantic ingest results., Small local file cache keyed only by a complete analytical fingerprint., FailureStage, ProductionAnalysisResult, ProductionIngestError, RuntimeError (+18 more)

### Community 32 - "Path"
Cohesion: 0.08
Nodes (17): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Offline UniRST corpus document conversion., Write the bracketed tree into a file Remove the original extension, keep only… (+9 more)

### Community 33 - "candidates.py"
Cohesion: 0.12
Nodes (37): BaseModel, DiGraph, DiscourseSignal, CandidateMode, compute_structural_features(), generate_secondary_edge_candidates(), iter_candidate_batches(), iter_secondary_edge_candidates() (+29 more)

### Community 34 - "dmrst/common.py"
Cohesion: 0.09
Nodes (38): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), __getforminfo(), getLabelMapping(), getParse() (+30 more)

### Community 35 - "dmrst/data.py"
Cohesion: 0.09
Nodes (16): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Offline DMRST corpus document conversion., Write the bracketed tree into a file Remove the original extension, keep only… (+8 more)

### Community 36 - "finalize_selection.py"
Cohesion: 0.09
Nodes (32): Create an identity-preserving single-partition view of the frozen final cache., select_final_partition(), _aggregate_final(), finalize_selection(), _load_receipts(), main(), _mean_full(), Path (+24 more)

### Community 37 - "RstDocument"
Cohesion: 0.12
Nodes (30): Lossless document representation for discourse parsing., RstDocument, Any, DiGraph, Knowledge graph export bridges for Rhetorical Structure Theory analyses., Convert an RstAnalysis tree/graph into a typed NetworkX DiGraph. Args:…, Serialize discourse analysis to W3C Turtle RDF format., Serialize discourse analysis to W3C JSON-LD graph structure. (+22 more)

### Community 38 - "compute_calibration_error"
Cohesion: 0.09
Nodes (29): Adversarial and numerical edge-case tests for calibration math. Tests…, test_calibration_summary_handles_empty_inputs(), test_compute_calibration_error_boundary_cases(), test_temperature_scaler_handles_extreme_overflow_underflow_logits(), test_temperature_scaler_handles_uniform_zero_logits(), test_temperature_scaler_homogeneous_labels_does_not_crash(), Path, Unit tests for offline probability calibration and temperature scaling. (+21 more)

### Community 39 - "dmrst/utils_dis_thiago.py"
Cohesion: 0.14
Nodes (32): Offline DMRST corpus span node., RST tree node used by the DMRST corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), cleanChildren() (+24 more)

### Community 40 - "DataManager"
Cohesion: 0.09
Nodes (15): collect(), DataManager, Any, Data, Node, Path, :param corpus: str - from {'GUM', 'RST-DT', 'RuRSTB', 'RST-DT-tr',} :param…, One-way import of a published HF pickle → relation labels only. (+7 more)

### Community 41 - "common.sh"
Cohesion: 0.08
Nodes (17): check-prerequisites.sh script, check_dir(), check_file(), get_feature_paths(), get_repo_root(), has_jq(), _persist_feature_json(), resolve_specify_init_dir() (+9 more)

### Community 42 - "DataManager"
Cohesion: 0.09
Nodes (14): collect(), DataManager, Data, Node, Path, :param corpus: str - from {'GUM', 'RST-DT', 'RuRSTB'} :param cross_validation:…, One-way import of a published HF pickle → relation labels only., :param number: int - fold number :param lang: str - (main) language :param… (+6 more)

### Community 43 - "test_erst_checkpoint.py"
Cohesion: 0.12
Nodes (31): ErstCalibrationState, ErstCheckpointLicenses, ErstCheckpointMetrics, ErstCheckpointProvenance, ErstCheckpointResearchEvidence, ErstFeatureSchema, Content identities for every feature and decoding contract., Immutable experiment evidence used to construct a checkpoint. (+23 more)

### Community 44 - "ingest/contracts.py"
Cohesion: 0.14
Nodes (27): ingest_result_from_json(), Validate and deserialize canonical production-ingest JSON., AnalysisAnchor, AnalysisStatus, CacheStatus, ConversionActivity, Disposition, DuplicateFinding (+19 more)

### Community 45 - "properties"
Cohesion: 0.06
Nodes (32): schema_version, additionalProperties, pattern, type, pattern, type, type, type (+24 more)

### Community 46 - "DiscourseUnit"
Cohesion: 0.11
Nodes (12): DiscourseUnit, Exporter, ForestExporter, Path, Recursively populate the text attribute from full_text using node character…, Serialize this discourse tree to RS3 XML format., A node in a binary Rhetorical Structure Theory (RST) discourse tree., RS3 XML document exporter for a single DiscourseUnit tree. (+4 more)

### Community 47 - "PredictorDMRST"
Cohesion: 0.10
Nodes (17): PredictorDMRST, Any, Data, device, dtype, Path, Takes data with word level tokenization, run current transformer tokenizer and…, Splits a batch into multiple smaller with given size. (+9 more)

### Community 48 - "structure.js"
Cohesion: 0.18
Nodes (30): act(), add_node(), count_children(), count_multinuc_children(), count_span_children(), create_node_div(), crel(), delete_node() (+22 more)

### Community 49 - "test_blake3_hashing.py"
Cohesion: 0.10
Nodes (30): BaseModel, Path, Unit tests for workbench.hashing (BLAKE3 & SHA-256 hybrid engine)., _SampleModel, test_blake3_digest_matches_reference(), test_canonical_json_bytes_ordering(), test_canonical_json_digest_model_support(), test_canonical_json_digest_rejects_unknown_algo() (+22 more)

### Community 50 - "load_repository_environment"
Cohesion: 0.11
Nodes (29): HfTokenSource, load_repository_environment(), _nonempty_environment_value(), BaseModel, Path, StrEnum, Supported Hugging Face token environment variables in precedence order., Validated evidence for one explicit repository-root environment load. (+21 more)

### Community 51 - "Parser"
Cohesion: 0.08
Nodes (17): Parser, Return the safe recursive-analysis capacity in the parser's limiting unit., Public façade for the DMRST and UniRST parser families. The family is resolved…, Parse a document using predefined EDUs., parser_cpu(), fixture, Real DMRST end-to-end model parsing into a typed RstAnalysis contract., Real UniRST end-to-end multilingual model parse into RstAnalysis. (+9 more)

### Community 52 - "ParserInput"
Cohesion: 0.13
Nodes (19): ParserInput, Any, Path, Minimal legacy parser-input leaf record required for safe model inventory…, Mutable historical parser record with no corpus or training behavior., Return the parser's exact limiting-unit count for this materialized input., dump_relation_inventory(), _ensure_parent_module() (+11 more)

### Community 53 - "load_markdown"
Cohesion: 0.10
Nodes (28): build_parser(), load_markdown(), LoadResult, Tokenise a markdown source string into a ``markdown-it-py`` token stream. The…, The output of ``load_markdown``. ``tokens`` is the body token stream (front-…, Construct a configured ``MarkdownIt`` instance. The ``front_matter`` plugin is…, Tokenise ``source_text`` and split out the YAML front-matter., MarkdownIt (+20 more)

### Community 54 - "protocol.py"
Cohesion: 0.10
Nodes (26): ExperimentConfigurationBundle, BaseModel, Exact typed configuration for all ten mandatory systems., build_experiment_protocol(), _environment_lock_sha256(), freeze_protocol_artifacts(), BaseModel, Path (+18 more)

### Community 55 - "DocumentToken"
Cohesion: 0.11
Nodes (20): inference_mode, DocumentToken, Edu, A single token aligned with character coordinates., Create an RstDocument with full token and EDU coordinates., An elementary discourse unit (EDU) with character and token spans., Hierarchical multi-stage discourse parsing and section stitching., A extracted section slice with coordinate offsets. (+12 more)

### Community 56 - "BasePredictor"
Cohesion: 0.13
Nodes (20): BasePredictor, Mixin-style base with shared tokenization, batching and offset utils. Not…, Given word span boundaries, recount for subwords., Validate untrusted input as a sequence of EDU strings. Typed ``object`` because…, Concatenate `edus` with single-space separators and return the joined text plus…, Map EDU character spans onto token boundaries. Args: offsets: ``(start, stop)``…, test_char_spans_to_token_breaks_aligned(), test_char_spans_to_token_breaks_empty_offsets_raises() (+12 more)

### Community 57 - "dmrst_parser/src/parser/parsing_net.py"
Cohesion: 0.10
Nodes (13): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+5 more)

### Community 58 - "test_serialization.py"
Cohesion: 0.13
Nodes (24): Any, BaseModel, PydanticDiscourseUnit, Typed Pydantic model for RST trees — optional, requires the ``pydantic`` extra.…, Validated, JSON-serialisable representation of one DiscourseUnit RST tree node.…, Build a ``PydanticDiscourseUnit`` from a ``DiscourseUnit`` tree (recursive)., Reconstruct a ``DiscourseUnit`` tree from this model (recursive)., JSON-serialisation helpers for the RST trees produced by ``isanlp_rst``. The… (+16 more)

### Community 59 - "test_base_predictor.py"
Cohesion: 0.17
Nodes (26): DeviceProbe, Resolve the compute device from the string API (or the deprecated int).…, Immutable snapshot of which accelerators the host exposes. Production code uses…, Probe the real host (CUDA, then MPS, else CPU-only)., resolve_device(), Unit tests for BasePredictor helpers — no model downloads, fast., CUDA wins over MPS when both are available (API contract; rare on macOS)., macOS primary path: no CUDA → MPS. (+18 more)

### Community 60 - "verify_gum_corpus_manifest.py"
Cohesion: 0.10
Nodes (17): CorpusSourceIdentity, ErstCheckpointComponent, ErstCheckpointFile, datetime, field_validator, Text-free identity for one source in a private corpus checkout., One declared, content-addressed file in an eRST completion bundle., Reload contract for one explicit eRST completion component. (+9 more)

### Community 61 - "test_erst_decoder.py"
Cohesion: 0.12
Nodes (24): DecodeRejectionReason, ErstCheckpointFileRole, ErstDecodeReceipt, HardNegativeStrategy, StrEnum, Reconciled proof of threshold selection and formal eRST constraints., Frozen training-negative ranking algorithms., The only formal reasons an above-threshold eRST edge may be rejected. (+16 more)

### Community 62 - "semantic_sha256"
Cohesion: 0.13
Nodes (15): _analysis_semantic_payload(), _canonical_edus(), model_validator, Self, canonical_json_bytes(), _json_value(), Any, Canonical analytical identities for production source ingest. (+7 more)

### Community 63 - "universal_parser/src/parser/segmenters.py"
Cohesion: 0.11
Nodes (9): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter, parametrize, PyTorch RNN dropout is inter-layer only. A 1-layer LSTM with non-zero dropout…, test_tony_one_layer_lstm_does_not_warn() (+1 more)

### Community 64 - "FrozenEvaluationAdapter"
Cohesion: 0.21
Nodes (14): FinalEvaluationCorpusPayload, Test-only payload created after champion freeze, with no train/dev source paths., FrozenEvaluationAdapter, _PeftModelType, CandidateScoringFunction, device, Module, Path (+6 more)

### Community 65 - "universal_parser/predictor.py"
Cohesion: 0.10
Nodes (16): parse_corpora_config(), ``config['data']['corpora']`` is sometimes a Python-literal string., relation_table_from_txt(), Data, getLabelOrdered(), nucs_and_rels(), Any, ArrayLike (+8 more)

### Community 66 - "test_unirst_pickle_security.py"
Cohesion: 0.14
Nodes (25): _EvilReduce, _local_shell(), parametrize, Path, Adversarial / inventory-load tests for UniRST pickle handling. No HF downloads,…, A planted eval-gadget pickle must not load; loader returns None., Pickle-only packaging (no relation_table_*.txt) still yields labels., When both exist, plain text wins — pickle must not override labels. (+17 more)

### Community 67 - "test_discourse_unit.py"
Cohesion: 0.10
Nodes (17): Group, An elementary discourse unit (EDU) leaf element for RS3 XML., A composite structural group element for RS3 XML., A root group element for RS3 XML., Register transparent `isanlp.annotation_rst` in sys.modules if not present., register_isanlp_compat(), Root, Segment (+9 more)

### Community 68 - "._detect_family_from_model_dir"
Cohesion: 0.13
Nodes (9): Any, device, dtype, Path, Validate and load one immutable child of the production model store., Inspect a local checkpoint directory and infer the parser family. Returns…, Read ``path`` as JSON. Returns ``None`` if the file is missing, unreadable, or…, If both signatures are present, UniRST wins (more specific). (+1 more)

### Community 69 - "smoke_test.py"
Cohesion: 0.15
Nodes (24): _assert_tree_aligned(), _check(), _check_from_edus(), _check_parse_rst(), _collect_leaves(), _expect_raises(), main(), Path (+16 more)

### Community 70 - "test_transformer_segmenter.py"
Cohesion: 0.16
Nodes (21): compute_metrics(), Training script for fine-tuning Transformer EDU discourse segmenters on…, Compute precision, recall, and F1 for B-EDU boundary detection., Path, slow, test_compute_metrics_math(), test_parse_disrpt_tok_mock(), test_parse_rs4_to_sentences() (+13 more)

### Community 71 - "RS4Document"
Cohesion: 0.17
Nodes (20): analysis_to_rs4(), Convert an RstDocument and RstAnalysis back into an RS4Document., Any, Faithful RS4 XML reader and writer for GUM eRST and classical RST., An individual text segment (<segment>) in RS4 XML., A span or multinuclear group (<group>) in RS4 XML., A secondary edge (<secedge>) in RS4 XML., A discourse signal (<signal>) in RS4 XML. (+12 more)

### Community 72 - "PredictorUniRST"
Cohesion: 0.15
Nodes (8): PredictorUniRST, device, dtype, txt (published) → JSON (native) → legacy pickle (labels only)., Load ``relation_table_<variant>.txt`` using corpus aliases., Count distinct ``label_classifiers.<N>.*`` indices in a state dict. Returns…, OOB idx must fail on config alone — never reach torch.load., TestUniRSTArgValidation

### Community 73 - "DUConverter"
Cohesion: 0.13
Nodes (15): DUConverter, Parses the tree predictions given in a string format. Args: description: Tree…, Takes the model outputs and converts them into isanlp binary trees. Returns:…, Selects the discourse unit description for given constituent. Args: start: DU…, Constructs the DiscourseUnit binary tree. Args: root: Index of the root…, Produces EDUs in isanlp format from the model predictions. Args: tokens: List…, Unit tests for ``isanlp_rst.utils.du_converter.DUConverter``. Focuses on the…, When the first gold token already covers the whitespace-stripped predicted… (+7 more)

### Community 74 - "BoundaryAwareSpanEncoder"
Cohesion: 0.11
Nodes (15): AttentionPooling, BoundaryAwareSpanEncoder, device, dtype, PretrainedConfig, PreTrainedTokenizerBase, Tensor, Learned attention pooling over sequence representations. (+7 more)

### Community 75 - "docling_rst_quality_check.py"
Cohesion: 0.16
Nodes (20): DoclingDocument, PictureItem, main(), Any, Phase 0 steps 6 and 7 — long-input smoke and determinism check. Step 6: parse a…, Build a structural signature of a tree for equality comparison. Captures…, tree_signature(), collect_leaves() (+12 more)

### Community 76 - "ToNySegmenter"
Cohesion: 0.14
Nodes (5): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter

### Community 77 - "rs4_to_document_and_analysis"
Cohesion: 0.18
Nodes (18): Convert an RS4Document into an RstDocument and an RstAnalysis., rs4_to_document_and_analysis(), _analysis(), Promotion assessment protects EDU quality and structural-boundary gains., test_edu_boundary_f1_detects_regression_without_using_source_text(), test_preparation_identity_requires_exact_contract_preparation_and_text(), test_structural_gate_counts_pre_feature_cross_boundary_relation_and_macro_fix(), test_structural_gate_rejects_cross_boundary_relation_mislabelled_local() (+10 more)

### Community 78 - "test_parser_attention.py"
Cohesion: 0.07
Nodes (21): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+13 more)

### Community 79 - "._graph_inputs"
Cohesion: 0.14
Nodes (11): GraphAttentionConfig, Complete-primary-tree edge-featured graph-attention configuration., _edge_feature(), _EdgeGraphAttentionLayer, _GraphScorer, device, Path, PreTrainedModel (+3 more)

### Community 80 - "to_html"
Cohesion: 0.29
Nodes (7): PathLike, Convert an ``.rs3`` file into HTML. Parameters ---------- rs3_path: Path to the…, to_html(), Path, Unit tests for viewer convenience helpers in ``isanlp_rst``., When ``html_path`` is set, ``to_html`` must write the file AND return the HTML…, test_to_html_returns_string_and_writes_file()

### Community 81 - "test_parse_result.py"
Cohesion: 0.19
Nodes (16): Parse text and return a typed RST root instead of the legacy mapping payload.…, extract_root_tree(), ParseFailedError, Any, RuntimeError, Helpers for unpacking ``Parser`` / predictor call results., Return ``result['rst'][0]``, or raise :class:`ParseFailedError`. Preferred over…, Raised when a parse result has no usable RST root tree. (+8 more)

### Community 82 - "ParsingNet"
Cohesion: 0.19
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 83 - "model_validator"
Cohesion: 0.17
Nodes (4): _canonical_model_hash(), ErstCheckpointBuildSpec, model_validator, Authoritative inputs used to construct an eRST completion bundle.

### Community 84 - "Parsing Network Logic"
Cohesion: 0.18
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 85 - "PureTransformerParsingNet"
Cohesion: 0.21
Nodes (12): Any, cky_discourse_tree_decode(), ParsedRstTreeSpan, Vectorized deep biaffine attention and dynamic CKY discourse tree decoding., A constituent span in the decoded RST discourse tree., Exact CKY dynamic programming chart decoder for hierarchical RST discourse…, Pure Transformer Vectorized Discourse Parser package., PureTransformerParsingNet (+4 more)

### Community 86 - "BiMPM"
Cohesion: 0.25
Nodes (7): BiMPM, device, Tensor, :param v1: (batch, seq_len, hidden_size) :param v2: (batch, seq_len,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, Inputs can be of infinite length, hence BiMPM matching can cause OOM. This is a…, LSTM

### Community 87 - "._resolve_family"
Cohesion: 0.21
Nodes (3): When both family and version are set, version must belong to family., Explicit family must match detectable signatures when present., TestResolveFamily

### Community 88 - "ParsingNetBottomUp"
Cohesion: 0.22
Nodes (8): _Node, ParsingNetBottomUp, Any, Tensor, Bottom-up transition-based parser. This module reuses the encoder, segmenters…, Reconstructs the gold tree from pre-order traversal., Return gold transition sequence in postorder., ParsingNet

### Community 89 - ".divide_chunks"
Cohesion: 0.40
Nodes (4): T, Yield chunks of size `n` from `_list` (handles empty lists)., test_divide_chunks_basic(), test_divide_chunks_empty()

### Community 90 - "base_predictor.py"
Cohesion: 0.14
Nodes (12): _device_from_legacy_int(), _device_from_spec(), _mps_available(), _OffsetToken, device, Protocol, Reproduce the historical ``cuda_device: int`` selection exactly. ``-1`` -> CPU.…, Minimal razdel-token surface used by offset remapping. (+4 more)

### Community 91 - "probe_erst_tokenizers.py"
Cohesion: 0.20
Nodes (13): One pinned tokenizer's fast/parity/MPS compatibility evidence., TokenizerProbeResult, _encoding_payload(), main(), _payload_hash(), probe_mandatory_tokenizers(), _probe_target(), Any (+5 more)

### Community 92 - "model_authority.py"
Cohesion: 0.15
Nodes (10): Immutable upstream model revisions selected by the v4 research protocol., ModernTreeParserTrainer, PretrainedConfig, Tensor, Modern training recipe for Pure Transformer RST Tree Parsers (ModernBERT / XLM-…, Immutable evaluation metrics receipt., Trainer for Pure Transformer Vectorized RST Parsers., Run a single training epoch. (+2 more)

### Community 93 - "BinaryTree"
Cohesion: 0.20
Nodes (8): BinaryTree, Node, Path, Offline DMRST binary-tree corpus conversion., :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 94 - "BinaryTree"
Cohesion: 0.20
Nodes (8): BinaryTree, Node, Path, Offline UniRST binary-tree corpus conversion., :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 95 - "._load_torch_weights"
Cohesion: 0.14
Nodes (8): AbstractContextManager, Any, Path, Recursively remap ``.start``/``.end`` of leaf/internal nodes from the tokenized…, Map an inferred tree onto authoritative predefined-EDU spans. Transformer…, Load a PyTorch state dict with ``weights_only=True``. All checkpoints published…, Return a context manager enabling autocast for inference. When ``self._dtype``…, test_load_torch_weights_pure_tensors()

### Community 96 - "Data"
Cohesion: 0.18
Nodes (12): Data, getLabelOrdered(), nucs_and_rels(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…, One batched parser example. Field order matches the historical constructor., parametrize (+4 more)

### Community 97 - "RS4Reader"
Cohesion: 0.19
Nodes (11): Parse an RS4 XML file into an RS4Document., Reads and validates RS4 XML files., RS4Reader, extract_headers_from_path(), main(), Path, CLI tool to extract declared relation and signal inventories from RS4 files., Scan a path (file or directory) and extract unique relations and signal types. (+3 more)

### Community 98 - "rs3tohtml"
Cohesion: 0.32
Nodes (13): rs3tohtml(), Create a private SQLite file for one render; unlink in ``finally``., _resolve_dbpath(), setup_db(), temporary_db(), Path, Viewer hardening: XXE posture, HTML escape, per-render SQLite., test_rs3tohtml_escapes_basename_in_header() (+5 more)

### Community 99 - "TemperatureCalibration"
Cohesion: 0.20
Nodes (12): test_temperature_fit_is_deterministic_and_does_not_increase_development_nll(), apply_temperature(), _binary_nll(), fit_temperature(), BaseModel, model_validator, ndarray, Deterministic dev-only temperature and edge-threshold calibration. (+4 more)

### Community 100 - "CrossEncoderConfig"
Cohesion: 0.14
Nodes (9): _CrossEncoder, CrossEncoderConfig, BaseModel, model_validator, Path, PreTrainedModel, PreTrainedTokenizerBase, Tensor (+1 more)

### Community 101 - "str2bool"
Cohesion: 0.17
Nodes (12): dtype, Robust string-to-bool conversion used in configs., Normalise a dtype spec to a ``torch.dtype``. Accepts: * ``None`` -> ``float32``…, str2bool(), parametrize, Default is fp32 on every device — measured fp32 wins on MPS for typical inputs;…, test_resolve_dtype_default_is_float32(), test_resolve_dtype_passthrough() (+4 more)

### Community 102 - "installed_acceptance.py"
Cohesion: 0.22
Nodes (10): Path, Writes RS4Document objects to well-formed RS4 XML., Serialize an RS4Document to an XML string., Write an RS4Document to an XML file., RS4Writer, _assert_offline_distributions_absent(), main(), Path (+2 more)

### Community 103 - "TransformerBoundarySpanEncoder"
Cohesion: 0.19
Nodes (8): Tensor, Boundary-aware span representations for pure transformer discourse parsing., Pool token representations. Args: hidden_states: (B, L, D) token embeddings…, Encodes discourse spans using boundary tokens and learned attention pooling.…, Encode arbitrary token spans in parallel. Args: sequence_hidden_states: (B,…, Learned attention pooling over token hidden states within a span., TransformerBoundarySpanEncoder, TransformerSpanAttentionPooling

### Community 104 - "DocLang Fixture Verification"
Cohesion: 0.22
Nodes (12): FixtureParityError, FixtureParityReceipt, _GithubEntry, _Manifest, BaseModel, RuntimeError, Verify local DocLang fixtures against an immutable upstream GitHub commit., Raised when local, manifest, and upstream fixture authority diverge. (+4 more)

### Community 105 - "buildTree"
Cohesion: 0.21
Nodes (13): buildTree(), buildTreeThiago(), checkcontent(), convert_parens_in_rst_tree_str(), createtext(), processtext(), Preprocessing token list for filtering '(' and ')' in text (from DPLP, by…, Create text from a list of tokens (from DPLP, by Yangfeng Ji) :type lst: list… (+5 more)

### Community 106 - "DeepBiaffineScorer"
Cohesion: 0.18
Nodes (8): device, dtype, DeepBiaffineScorer, Tensor, Deep Biaffine Scoring for span splitting, nuclearity, and rhetorical relations.…, Score pairs of adjacent spans (left, right). Args: left_spans: (B, N, D)…, PretrainedConfig, PreTrainedTokenizerBase

### Community 107 - "._guess_token_offsets"
Cohesion: 0.17
Nodes (10): Build offset converter from word tokens and optional (start, end) pairs. If…, Best-effort alignment of already-tokenized `tokens` to raw `text`. Used when…, The fix: a missing token must raise rather than silently fall back., Token at the very end should match cleanly., test_guess_token_offsets_at_text_boundary(), test_guess_token_offsets_raises_on_miss(), test_guess_token_offsets_simple(), test_guess_token_offsets_token_longer_than_text() (+2 more)

### Community 108 - "EncoderRNN"
Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 109 - "CRF"
Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from https://github.com/kmkurn/pytorch-…, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 110 - ".parse_rst"
Cohesion: 0.18
Nodes (6): Any, Data, Takes word-level tokenized data and converts it to transformer subword inputs., Splits a batch into multiple smaller batches of the given size. Note:…, Parse text into an RST tree. Args: text: Original document text. tokens:…, Parses multiple texts in batched forward passes using UniRST. Args: texts:…

### Community 111 - "EncoderRNN"
Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 112 - "CRF"
Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from https://github.com/kmkurn/pytorch-…, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 113 - "MultipleRunnerGeneral"
Cohesion: 0.23
Nodes (5): range, MultipleRunnerGeneral, Offline DMRST multiple-run experiment orchestration. For monolingual…, Running training with second language injection of ``mixed`` %, :param corpus: (str) - 'GUM' or 'RST-DT' :param lang: (str) - 'en' or 'ru'…

### Community 114 - "test_transformer_parser.py"
Cohesion: 0.17
Nodes (11): Unit tests for Pure Transformer Vectorized Discourse Parser (ParsingNetV5)., Verify document tree decoding produces valid ParsedRstTreeSpan hierarchy., Verify TransformerBoundarySpanEncoder encodes arbitrary spans in parallel., Verify DeepBiaffineScorer computes u^T W v + U u + V v + b correctly., Verify CKY dynamic programming reconstructs a full projective discourse tree., Verify end-to-end forward pass and multi-task loss computation., test_boundary_span_encoder_pooling(), test_cky_discourse_tree_decoder() (+3 more)

### Community 115 - "Discriminator"
Cohesion: 0.20
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 * 19 * 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 116 - "tree_stats"
Cohesion: 0.27
Nodes (10): find_cdu(), _is_leaf(), Any, Analytical helpers for parsed RST trees. These functions operate on…, Classify an RST relation label as subject-matter or presentational. Follows…, Compute structural diagnostics for an RST tree. Returned dict keys: ``depth``…, Locate the Central Discourse Unit (CDU) of an RST tree. Descends from the root…, relation_category() (+2 more)

### Community 117 - "cleanup.py"
Cohesion: 0.31
Nodes (10): collect_junk(), _display(), is_junk_dir(), is_junk_file(), main(), Path, Remove regenerable junk from the repo: bytecode, tool caches, temp files. Does…, Delete ``paths``. Returns the number of paths acted on. (+2 more)

### Community 118 - "_Predictor"
Cohesion: 0.25
Nodes (10): _FakeNode, _Predictor, Stand-in for isanlp.DiscourseUnit with the attributes used by remap., Minimal concrete subclass (BasePredictor is ABC)., Unary node = DUConverter bug; surface it rather than patch it., test_remap_tree_offsets_binary(), test_remap_tree_offsets_leaf(), test_remap_tree_offsets_unary_raises() (+2 more)

### Community 120 - "MultipleRunnerGeneral"
Cohesion: 0.25
Nodes (4): MultipleRunnerGeneral, Offline UniRST multiple-run experiment orchestration. For monolingual…, Running training with second language injection of ``mixed`` %, :param corpora: corpus names, e.g. ['GUM'] or ['RST-DT'] :param lang: 'en' or…

### Community 121 - "MpsMemorySampler"
Cohesion: 0.20
Nodes (4): test_disabled_mps_sampler_has_no_measurement_side_effect(), MpsMemorySampler, Measured MPS allocation sampling for independent experiment runs., Sample driver allocations during a run because PyTorch exposes no MPS peak API.

### Community 122 - "test_cleanup.py"
Cohesion: 0.29
Nodes (8): fixture, Path, Unit tests for ``scripts/cleanup.py`` (stdlib-only project cleaner)., test_collects_bytecode_caches_and_temp_not_source(), test_dry_run_does_not_delete(), test_remove_deletes_junk_keeps_source_and_protected(), test_skips_git_and_pixi_trees(), tree()

### Community 123 - "parseXML"
Cohesion: 0.29
Nodes (7): getRelationsType(), parseXML(), _Element, _ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, readRS3Annotation()

### Community 124 - "_StructuralClassifier"
Cohesion: 0.24
Nodes (5): BaseModel, Tensor, Frozen finite optimization and decoding configuration., _StructuralClassifier, StructuralConfig

### Community 125 - "smoke.py"
Cohesion: 0.29
Nodes (9): CommandCategory, CommandReceipt, _execute(), main(), BaseModel, Path, Execute every retained offline command to a bounded, evidence-bearing start., One canonical retained command and its bounded-start contract. (+1 more)

### Community 126 - "ErstCheckpointVerificationReceipt"
Cohesion: 0.28
Nodes (7): ErstCheckpointVerificationReceipt, Machine-readable proof that a bundle reloaded and passed its graph vector., main(), Path, Fail-closed clean-process verifier for an eRST completion bundle., Strict-reload a bundle, run its test vector, and emit a typed receipt., verify_checkpoint()

### Community 127 - "train_segmenter"
Cohesion: 0.22
Nodes (8): download_dataset(), Path, Download open DISRPT / GUM discourse segmentation datasets for model training., Download DISRPT segmentation dataset files to target directory., Any, Path, Fine-tune a Transformer model for EDU segmentation., train_segmenter()

### Community 128 - "verify_model_licensing.py"
Cohesion: 0.36
Nodes (8): audit_technology_matrix(), LicenseAuditReceipt, main(), ModelLicenseRecord, BaseModel, Path, Verify commercial license compliance for candidate and released model weights.…, Audit the research technology matrix for license compliance.

### Community 129 - "test_doclang_fixture_parity.py"
Cohesion: 0.22
Nodes (6): BaseModel, parametrize, Path, Pinned upstream parity and locked-validator tests for DocLang fixtures., test_locked_doclang_validator_accepts_every_upstream_fixture(), _UpstreamManifest

### Community 131 - "test_runtime_provenance.py"
Cohesion: 0.25
Nodes (7): _clear_runtime_caches(), fixture, MonkeyPatch, Installed-version and source-revision provenance boundaries., test_source_revision_is_separate_from_semantic_version(), test_unexpected_metadata_failure_is_not_hidden(), test_unknown_is_only_used_when_distribution_metadata_is_absent()

### Community 132 - "parseXML"
Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element, _ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 133 - "EduSegmentationDataset"
Cohesion: 0.25
Nodes (5): Dataset, EduSegmentationDataset, Any, Tensor, PyTorch Dataset for fine-tuning Transformer EDU segmenters with subword…

### Community 134 - "SecondaryEdgeInferenceDataset"
Cohesion: 0.32
Nodes (4): Tensor, Runtime tensor encoding for eRST secondary-edge candidates., Encode candidate pairs for released eRST scorer inference., SecondaryEdgeInferenceDataset

### Community 135 - "offending_tool"
Cohesion: 0.43
Nodes (6): is_content_free(), looks_like_path(), main(), offending_tool(), Return (tool, path) for the first file-reading invocation, else None.…, True when this invocation cannot print a line of file content. Every argument…

### Community 136 - "SignalPattern"
Cohesion: 0.33
Nodes (5): _pattern(), BaseModel, field_validator, One auditable token-sequence trigger and its raw relation compatibility., SignalPattern

### Community 137 - "verify_markdown_manifest.py"
Cohesion: 0.48
Nodes (6): _is_approved_exclusion(), main(), _manifest_paths(), Verify and lint the complete repository Markdown manifest., _repository_markdown(), verify_manifest()

### Community 138 - "clean_install.py"
Cohesion: 0.57
Nodes (6): _install_and_run(), main(), Path, Create clean core/formats wheel installs and execute installed acceptance., _run(), _venv_python()

### Community 139 - "findFile"
Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 140 - "findFile"
Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 141 - "AblationPlan"
Cohesion: 0.29
Nodes (6): AblationDefinition, AblationPlan, BaseModel, model_validator, Exact intervention represented by one required ablation run family., Complete, hashed intervention plan frozen before ablation execution.

### Community 142 - "ConfigReader"
Cohesion: 0.29
Nodes (4): ConfigReader, Any, Path, Offline DMRST training configuration reader.

### Community 143 - "ConfigReader"
Cohesion: 0.29
Nodes (4): ConfigReader, Any, Path, Offline UniRST training configuration reader.

### Community 144 - "InvalidSegmenterCheckpointError"
Cohesion: 0.33
Nodes (5): InvalidSegmenterCheckpointError, device, dtype, ValueError, Raised when a path is not a complete, trained EDU-segmentation checkpoint.

### Community 145 - "bench.py"
Cohesion: 0.47
Nodes (5): main(), Performance benchmark for isanlp_rst across devices and dtypes. Usage: pixi run…, Run parser n times after a warm-up. Return median seconds and tree shape., _shape(), _time_parse()

### Community 146 - "test_public_api.py"
Cohesion: 0.40
Nodes (3): _module_exists(), The canonical ingest package is the only production source-ingest surface., test_obsolete_envelopes_and_entry_modules_are_absent()

### Community 147 - "test_megadoc_stress.py"
Cohesion: 0.40
Nodes (5): _generate_synthetic_megadoc(), Megadoc 50,000-word long-context stress test suite., Generate a deterministic 50,000+ word multi-chapter Markdown document., Ingest and verify a 50,000+ word document with memory profiling., test_megadoc_ingest_and_boundary_integrity()

### Community 148 - "_HierarchicalAdapterModel"
Cohesion: 0.40
Nodes (3): _HierarchicalAdapterModel, PreTrainedModel, Tensor

### Community 149 - "cuda_smoke.py"
Cohesion: 0.60
Nodes (4): _assert_aligned(), _collect_leaves(), main(), CUDA verification script — to be run on a real NVIDIA host. Usage: pixi run…

### Community 150 - "smoke_iterate"
Cohesion: 0.50
Nodes (4): main(), Path, Smoke-iterate Docling JSON fixtures via docling-core's canonical walker. Phase…, smoke_iterate()

### Community 154 - "test_wave4_contracts.py"
Cohesion: 0.50
Nodes (3): The core parser remains isolated from optional source-format dependencies., Core ``isanlp_rst.parser`` must not require the formats extra., test_parser_imports_without_docling_core()

### Community 155 - "production_smoke.py"
Cohesion: 0.67
Nodes (3): _distribution_members(), main(), Smoke-test the installed production package without loading model weights.

## Knowledge Gaps
- **22 isolated node(s):** `no-assumptions-check.sh script`, `isanlp_rst`, `common.sh script`, `additionalProperties`, `pattern` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Work-memory lessons

**Known dead ends** — questions that led nowhere; don't re-derive.
- "Should the new isanlp_rst be 4.0.1, and does its public API expose everything the provider should expose?" -> `Parser`, `RstAnalysis`, `Production Ingest API`

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RstAnalysis` connect `RstAnalysis` to `erst/runner.py`, `erst/contracts.py`, `gum_validator.py`, `CorpusPartition`, `contracts/__init__.py`, `ProductionIngestor`, `contracts/erst.py`, `DiscourseSignal`, `NuclearityPatternEnum`, `parser.py`, `test_integration.py`, `ProductionAnalysisResult`, `candidates.py`, `RstDocument`, `test_erst_checkpoint.py`, `ingest/contracts.py`, `test_erst_decoder.py`, `semantic_sha256`, `RS4Document`, `rs4_to_document_and_analysis`, `._graph_inputs`, `installed_acceptance.py`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `RstDocument` connect `RstDocument` to `erst/runner.py`, `gum_validator.py`, `CorpusPartition`, `RstAnalysis`, `contracts/__init__.py`, `ProductionIngestor`, `prepare.py`, `DiscourseSignal`, `parser.py`, `test_integration.py`, `ProductionAnalysisResult`, `candidates.py`, `test_erst_checkpoint.py`, `ingest/contracts.py`, `DocumentToken`, `test_transformer_segmenter.py`, `RS4Document`, `rs4_to_document_and_analysis`, `installed_acceptance.py`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `Parser` connect `Parser` to `gum_validator.py`, `RstAnalysis`, `contracts/__init__.py`, `validate_model_release`, `bench.py`, `DiscourseSignal`, `SourceArtifact`, `parser.py`, `cuda_smoke.py`, `DummyPredictor`, `production_smoke.py`, `test_integration.py`, `RstDocument`, `test_erst_checkpoint.py`, `DiscourseUnit`, `DocumentToken`, `._detect_family_from_model_dir`, `smoke_test.py`, `test_transformer_segmenter.py`, `docling_rst_quality_check.py`, `test_parse_result.py`, `._resolve_family`, `installed_acceptance.py`?**
  _High betweenness centrality (0.050) - this node is a cross-community bridge._
- **Are the 35 inferred relationships involving `RstAnalysis` (e.g. with `ProvenanceRecord` and `FailureCodeEnum`) actually correct?**
  _`RstAnalysis` has 35 INFERRED edges - model-reasoned connections that need verification._
- **Are the 64 inferred relationships involving `Parser` (e.g. with `HierarchicalSectionStitcher` and `DiscourseUnit`) actually correct?**
  _`Parser` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `RstDocument` (e.g. with `InputFidelityEnum` and `document_from_dict()`) actually correct?**
  _`RstDocument` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `SourceArtifact` (e.g. with `_doclang_anchors()` and `_docling_anchors()`) actually correct?**
  _`SourceArtifact` has 27 INFERRED edges - model-reasoned connections that need verification._