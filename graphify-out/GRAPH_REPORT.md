# Graph Report - isanlp_rst  (2026-08-29)

## Corpus Check
- Large corpus: 511 files · ~494,938 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 4403 nodes · 11507 edges · 178 communities (155 shown, 23 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 852 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 171

## God Nodes (most connected - your core abstractions)
1. `RstAnalysis` - 159 edges
2. `Parser` - 113 edges
3. `RstDocument` - 100 edges
4. `SpanNode` - 68 edges
5. `RstNode` - 67 edges
6. `SourceArtifact` - 67 edges
7. `CorpusPartition` - 66 edges
8. `DiscourseUnit` - 64 edges
9. `ProductionIngestor` - 61 edges
10. `PrimaryRelationEdge` - 55 edges

## Surprising Connections (you probably didn't know these)
- `test_tracked_train_inventory_is_hash_valid_and_raw_to_concept_complete()` --uses--> `RawRelationInventory`  [INFERRED]
  tests/integration/test_erst_relations.py → isanlp_rst/contracts/erst.py
- `test_source_revision_is_separate_from_semantic_version()` --calls--> `resolve_source_revision()`  [EXTRACTED]
  tests/unit/test_runtime_provenance.py → isanlp_rst/_provenance.py
- `DummyPredictor` --uses--> `DiscourseUnit`  [INFERRED]
  tests/integration/test_batch_inference.py → isanlp_rst/annotation_rst.py
- `GumGoldValidator` --uses--> `DiscourseUnit`  [INFERRED]
  tests/offline/gum_validator.py → isanlp_rst/annotation_rst.py
- `test_discourse_unit_internal_node()` --calls--> `DiscourseUnit`  [EXTRACTED]
  tests/unit/test_discourse_unit.py → isanlp_rst/annotation_rst.py

## Import Cycles
- 3-file cycle: `workbench/corpus/unirst/__init__.py -> workbench/corpus/unirst/data_manager.py -> workbench/corpus/unirst/data.py -> workbench/corpus/unirst/__init__.py`
- 3-file cycle: `workbench/corpus/dmrst/__init__.py -> workbench/corpus/dmrst/data_manager.py -> workbench/corpus/dmrst/data.py -> workbench/corpus/dmrst/__init__.py`

## Communities (178 total, 23 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (101): Exception, load_repository_environment(), _nonempty_environment_value(), BaseModel, Path, Explicit, non-logging repository environment loading for eRST operations., Validated evidence for one explicit repository-root environment load., Load only ``<repository_root>/.env`` and resolve the supported HF token.… (+93 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (98): CorpusPartition, Official GUM document partitions., _protocol(), Regression tests for calibration, statistics, resources, and system constraints., _receipt(), _resource(), test_bootstrap_and_holm_are_reproducible_and_content_hashed(), test_screening_completeness_requires_every_system_seed_disposition() (+90 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (79): NuclearityPatternEnum, Nuclearity pattern for primary relation edges., analysis_to_rs4(), Conversion utilities between RS4 DOM, DiscourseUnit, and typed contracts., Convert an RstDocument and RstAnalysis back into an RS4Document., Convert an RS4Document into an RstDocument and an RstAnalysis., rs4_to_document_and_analysis(), RS4 XML processing, eRST data structures, and converters. (+71 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (103): ErstCalibrationState, ErstCheckpointBuildSpec, ErstCheckpointComponent, ErstCheckpointFile, ErstCheckpointFileRole, ErstCheckpointLicenses, ErstCheckpointManifest, ErstCheckpointMetrics (+95 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (73): Native Rhetorical Structure Theory (RST) tree annotations and RS3…, Complete discourse analysis result., RstAnalysis, Lossless document representation for discourse parsing., RstDocument, NodeKindEnum, OutputFormalismEnum, Discourse tree or graph node kind. (+65 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (69): Path, Causal tests for the production/offline boundary authority., test_ambiguous_relevant_path_fails_closed(), test_artifact_dependencies_are_read_from_metadata(), test_authority_classifies_each_surface(), test_commit_export_build_cannot_package_stale_build_tree(), test_direct_production_to_offline_import_reports_complete_path(), test_forbidden_sdist_member_is_named() (+61 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (69): DiscourseSignal, BaseModel, Discourse analysis result models and graph structures., Immutable identity of the detector or source that produced a signal., Typed, anchored discourse signal; overlaps are explicitly permitted., SignalDetectorProvenance, AnnotationStatusEnum, How a discourse signal entered the analysis. (+61 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (71): DoclangIngestError, InvalidDoclangError, ValueError, Failures raised by the private DocLang source loader., A DocLang archive violates bounded local ZIP safety invariants., Base class for DocLang validation and archive-loading failures., The XML file is not a valid DocLang document., UnsafeDoclangArchiveError (+63 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (62): Production-safe released-model contracts and loaders., canonical_json_bytes(), load_model_release(), ModelFile, ModelReleaseError, ModelReleaseIdentity, ModelReleaseManifest, PromotionReceipt (+54 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (67): FormatRstAnalysis, Composite analysis for structured documents (Docling, DocLang, Markdown)., ProvenanceRecord, Document input models and coordinate representation., Create an RstDocument from pre-segmented EDU strings. Note: Character offsets…, Provenance pointer to the source document., Provenance and derivation record., SourceReference (+59 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (48): calc_metrics(), get_batch_metrics(), get_eval_data_parseval(), get_eval_data_rst_parseval(), get_macro_metrics(), get_measurement(), get_micro_metrics(), get_seg_measure() (+40 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (49): PrivateCorpusVerificationReceipt, Full-source and sampled-candidate verification for the private corpus., _candidate(), Focused system serialization and private candidate-cache contract tests., test_candidate_cache_round_trips_gold_fields_and_overlapping_signal_spans(), test_signal_aware_serialization_preserves_each_exact_overlapping_anchor(), test_text_only_serialization_contains_no_signal_or_structure_tokens(), ChampionManifest (+41 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (52): AnalysisStatus, _identify_path(), _media_type(), Path, _raw_contract(), SourceArtifact, SourceForm, inventory_source() (+44 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (42): ba(), Ea(), Fa(), fb(), ga(), ha(), b(), hb() (+34 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (47): inference_mode, Execution timing profile in milliseconds., TimingRecord, DocumentToken, Edu, Create an RstDocument from raw text without pre-segmented EDUs., A single token aligned with character coordinates., Create an RstDocument with full token and EDU coordinates. (+39 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (50): AnalysisAnchor, AnalysisUnit, Disposition, DuplicateFinding, PreparationPolicy, PreparedRange, PreparedRstDocument, PreparedSegment (+42 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (53): HfApi, One pinned tokenizer's fast/parity/MPS compatibility evidence., Hashed Python/Transformers/MPS compatibility receipt for mandatory tokenizers., TokenizerCompatibilityReceipt, TokenizerProbeResult, _encoding_payload(), main(), _payload_hash() (+45 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (56): AnchorKind, AuthorshipRole, ContentClass, ContentInventoryItem, DispositionKind, NativeAnchor, StrEnum, RawContractDeclaration (+48 more)

### Community 18 - "Community 18"
Cohesion: 0.07
Nodes (50): AsyncBrowser, AsyncPage, AsyncPlaywright, Browser, T, Render an ``.rs3`` file to PNG (works in both sync and async environments)., Render an ``.rs3`` file to PDF. The viewer exposes only an asynchronous PDF…, Execute `coro` to completion and return its result, regardless of asyncio state. (+42 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (40): ingest_result_from_json(), Validate and deserialize canonical production-ingest JSON., ProductionIngestCache, Path, Integrity-checked, same-filesystem atomic cache for semantic ingest results., Small local file cache keyed only by a complete analytical fingerprint., CacheStatus, ExecutionReceipt (+32 more)

### Community 20 - "Community 20"
Cohesion: 0.07
Nodes (46): AblationAdapter, AblationDefinition, AblationPlan, AblationResult, canonical_ablation_plan(), BaseModel, model_validator, Frozen, model-neutral ablation definitions and evidence boundaries. (+38 more)

### Community 21 - "Community 21"
Cohesion: 0.07
Nodes (41): DecodeRejectionReason, ErstDecodeReceipt, Reconciled proof of threshold selection and formal eRST constraints., The only formal reasons an above-threshold eRST edge may be rejected., Complete evidence for one ordered primary-tree node pair., SecondaryEdgeCandidate, DecodedErstEdges, ErstSecondaryEdgeDecoder (+33 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (49): add_node(), add_seg(), count_children(), count_multinuc_children(), count_span_children(), delete_document(), delete_node(), generic_query() (+41 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (40): Dataset, Immutable upstream model revisions selected by the v4 research protocol., InvalidSegmenterCheckpointError, device, dtype, ValueError, Raised when a path is not a complete, trained EDU-segmentation checkpoint., download_dataset() (+32 more)

### Community 24 - "Community 24"
Cohesion: 0.11
Nodes (44): RST tree node used by the universal parser corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), buildTree(), buildTreeThiago() (+36 more)

### Community 25 - "Community 25"
Cohesion: 0.10
Nodes (46): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+38 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (45): areAdjacent(), binarizeTreeGeneral(), buildNodes(), cleanEDU(), cleanEmbedded(), cleanLonelyCDU(), cleanLonelyEDU(), cleanTree() (+37 more)

### Community 27 - "Community 27"
Cohesion: 0.09
Nodes (45): _assert_aligned(), _collect_leaf_units(), _collect_leaves(), dmrst_gumrrg_cpu(), dmrst_rstdt_cpu(), dmrst_rstreebank_cpu(), fixture, parametrize (+37 more)

### Community 28 - "Community 28"
Cohesion: 0.08
Nodes (39): FinalEvaluationReceipt, One-time untouched test evaluation bound to a frozen champion., _aggregate_final(), finalize_selection(), _load_receipts(), main(), _mean_full(), Path (+31 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (39): Document, get_depth(), get_left_right(), NODE, NodeMap, RST tree node types and parent-chain attribute walks., EDU used by the segmenter, not by the structurer., Set graphical nesting depth of ``orig_node`` from the parent chain. RST… (+31 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (33): _analysis_semantic_payload(), _canonical_edus(), model_validator, Self, canonical_json_bytes(), _json_value(), Any, Path (+25 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (43): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), Document, __getforminfo(), getLabelMapping() (+35 more)

### Community 32 - "Community 32"
Cohesion: 0.08
Nodes (39): addLabels(), backprop(), BFTbin(), checkTree(), countLabels(), __getforminfo(), getLabelMapping(), getParse() (+31 more)

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (16): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Offline DMRST corpus document conversion., Write the bracketed tree into a file Remove the original extension, keep only… (+8 more)

### Community 34 - "Community 34"
Cohesion: 0.09
Nodes (16): associate_tree_edus(), Corpus, DisDocument, Document, getFiles(), Path, Offline UniRST corpus document conversion., Write the bracketed tree into a file Remove the original extension, keep only… (+8 more)

### Community 35 - "Community 35"
Cohesion: 0.08
Nodes (28): AbstractContextManager, BasePredictor, Any, Path, Mixin-style base with shared tokenization, batching and offset utils. Not…, Recursively remap ``.start``/``.end`` of leaf/internal nodes from the tokenized…, Map an inferred tree onto authoritative predefined-EDU spans. Transformer…, Given word span boundaries, recount for subwords. (+20 more)

### Community 36 - "Community 36"
Cohesion: 0.08
Nodes (21): _mps_available(), Robust string-to-bool conversion used in configs., True when this host has a usable MPS (Apple Silicon Metal) backend., str2bool(), PredictorDMRST, Any, Data, device (+13 more)

### Community 37 - "Community 37"
Cohesion: 0.10
Nodes (33): PrimaryRelationEdge, Find the root node if present., Look up a node by its ID., A node in a discourse tree or graph., A directed primary rhetorical relation edge with nuclearity., A directed secondary rhetorical relation edge without nuclearity., RstNode, SecondaryRelationEdge (+25 more)

### Community 38 - "Community 38"
Cohesion: 0.10
Nodes (34): audit_technology_matrix(), LicenseAuditReceipt, main(), ModelLicenseRecord, BaseModel, Path, Verify commercial license compliance for candidate and released model weights.…, Audit the research technology matrix for license compliance. (+26 more)

### Community 39 - "Community 39"
Cohesion: 0.14
Nodes (32): Offline DMRST corpus span node., RST tree node used by the DMRST corpus readers., SpanNode, _apply_node_content(), binarizeTreeRight(), binarizeTreeRightThiago(), bTree(), cleanChildren() (+24 more)

### Community 40 - "Community 40"
Cohesion: 0.07
Nodes (21): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.13
Nodes (29): check-prerequisites.sh script, check_dir(), check_file(), find_specify_root(), format_speckit_command(), get_current_branch(), get_feature_paths(), get_invoke_separator() (+21 more)

### Community 42 - "Community 42"
Cohesion: 0.10
Nodes (14): Data, One batched parser example. Field order matches the historical constructor., collect(), DataManager, Any, Node, Path, :param corpus: str - from {'GUM', 'RST-DT', 'RuRSTB', 'RST-DT-tr',} :param… (+6 more)

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (31): _device_from_legacy_int(), _device_from_spec(), DeviceProbe, device, Reproduce the historical ``cuda_device: int`` selection exactly. ``-1`` -> CPU.…, Resolve the compute device from the string API (or the deprecated int).…, Immutable snapshot of which accelerators the host exposes. Production code uses…, Probe the real host (CUDA, then MPS, else CPU-only). (+23 more)

### Community 44 - "Community 44"
Cohesion: 0.10
Nodes (26): CandidateDocumentSelection, CandidateSelectionReceipt, Complete-versus-selected counts for one already-partitioned document., Hashed evidence that only train candidates were sampled., main(), Derive the raw eRST relation inventory from the official GUM train partition., Persist a text-free train-derived raw relation inventory., LoadedGumCorpus (+18 more)

### Community 45 - "Community 45"
Cohesion: 0.09
Nodes (25): OntologyAdapter, Return canonical Central ontology URI for a coarse discourse concept., Return canonical Central ontology URI for a nuclearity pattern., Return canonical document-scoped URI for a discourse unit node., Adapts and resolves model outputs and corpus labels against the pinned ontology., Strip embedded (-e) and nuclearity (-s/-n) suffixes from RST-DT labels., Resolve a raw corpus label to its canonical label and coarse concept., load_ontology_lock() (+17 more)

### Community 46 - "Community 46"
Cohesion: 0.06
Nodes (32): schema_version, additionalProperties, pattern, type, pattern, type, type, type (+24 more)

### Community 47 - "Community 47"
Cohesion: 0.18
Nodes (31): act(), add_node(), count_children(), count_multinuc_children(), count_span_children(), create_node_div(), crel(), delete_node() (+23 more)

### Community 48 - "Community 48"
Cohesion: 0.08
Nodes (17): Parser, Return the safe recursive-analysis capacity in the parser's limiting unit., Public façade for the DMRST and UniRST parser families. The family is resolved…, Parse a document using predefined EDUs., parser_cpu(), fixture, Real DMRST end-to-end model parsing into a typed RstAnalysis contract., Real UniRST end-to-end multilingual model parse into RstAnalysis. (+9 more)

### Community 49 - "Community 49"
Cohesion: 0.11
Nodes (11): collect(), DataManager, Node, Path, :param corpus: str - from {'GUM', 'RST-DT', 'RuRSTB'} :param cross_validation:…, One-way import of a published HF pickle → relation labels only., Makes self.mixed_train_* versions with 100% train files from first language and…, Take all rs3 documents and save them in the same directory as *.edus and *.lisp… (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.13
Nodes (22): ConversionActivity, ProductionIngestor, One in-process authority for production source preparation and analysis., RecordingParser, test_analysis_uses_canonical_prepared_document_and_disables_cache_for_mutable_parser(), test_empty_primary_discourse_returns_explicit_status_without_parser_call(), ImmutableEmptyParser, Path (+14 more)

### Community 51 - "Community 51"
Cohesion: 0.10
Nodes (28): build_parser(), load_markdown(), LoadResult, Tokenise a markdown source string into a ``markdown-it-py`` token stream. The…, The output of ``load_markdown``. ``tokens`` is the body token stream (front-…, Construct a configured ``MarkdownIt`` instance. The ``front_matter`` plugin is…, Tokenise ``source_text`` and split out the YAML front-matter., MarkdownIt (+20 more)

### Community 52 - "Community 52"
Cohesion: 0.13
Nodes (27): Unpickler that only reconstructs inventory leaf types + containers.…, RestrictedUnpickler, _EvilReduce, _local_shell(), parametrize, Path, Adversarial / inventory-load tests for UniRST pickle handling. No HF downloads,…, A planted eval-gadget pickle must not load; loader returns None. (+19 more)

### Community 53 - "Community 53"
Cohesion: 0.11
Nodes (20): Counter, DirectedSpanKey, K, main(), Path, Smoke-iterate Docling JSON fixtures via docling-core's canonical walker. Phase…, smoke_iterate(), UnorderedSpanKey (+12 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (9): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter, parametrize, PyTorch RNN dropout is inter-layer only. A 1-layer LSTM with non-zero dropout…, test_tony_one_layer_lstm_does_not_warn() (+1 more)

### Community 55 - "Community 55"
Cohesion: 0.14
Nodes (26): CorpusAuthorityEntry, GumCorpusAuthority, One document assignment derived from immutable upstream authority., Hashed interpretation of pinned GUM split and licence authorities., Return the upstream authority entry for one exact document ID., test_authority_parser_rejects_missing_partition_or_inventory_marker(), _document_receipt(), _failure() (+18 more)

### Community 56 - "Community 56"
Cohesion: 0.21
Nodes (14): FinalEvaluationCorpusPayload, Test-only payload created after champion freeze, with no train/dev source paths., FrozenEvaluationAdapter, _PeftModelType, CandidateScoringFunction, device, Module, Path (+6 more)

### Community 57 - "Community 57"
Cohesion: 0.14
Nodes (24): CorpusDocumentReceipt, CorpusLicenseClass, CorpusLoadFailure, CorpusLoadReceipt, HardNegativeStrategy, StrEnum, Pydantic boundaries for private GUM/eRST corpus loading and partitioning., Sanitized failure for one source or corpus-level load step. (+16 more)

### Community 58 - "Community 58"
Cohesion: 0.15
Nodes (23): Any, BaseModel, PydanticDiscourseUnit, Typed Pydantic model for RST trees — optional, requires the ``pydantic`` extra.…, Validated, JSON-serialisable representation of one DiscourseUnit RST tree node.…, Build a ``PydanticDiscourseUnit`` from a ``DiscourseUnit`` tree (recursive)., JSON-serialisation helpers for the RST trees produced by ``isanlp_rst``. The…, Serialise a ``DiscourseUnit`` RST tree to a nested, JSON-ready dict.… (+15 more)

### Community 59 - "Community 59"
Cohesion: 0.10
Nodes (14): CandidateIdentityProbe, CorpusSourceIdentity, datetime, field_validator, Text-free identity for one source in a private corpus checkout., Determinism evidence for one private document without candidate text., _validate_relative_source_path(), main() (+6 more)

### Community 60 - "Community 60"
Cohesion: 0.16
Nodes (18): Minimal legacy parser-input leaf record required for safe model inventory…, dump_relation_inventory(), _ensure_parent_module(), ensure_unirst_module_aliases(), import_relation_table_from_legacy_pickle(), load_relation_inventory_json(), parse_corpora_config(), Path (+10 more)

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (23): HardNegativeSamplingConfig, Deterministic training-only hard-negative selection configuration., compute_edge_metrics(), epoch_improves(), Any, Path, Training script for fine-tuning NeuralSecondaryEdgeScorer on GUM eRST treebanks., Reject zero-step runs before a scheduler or success receipt can exist. (+15 more)

### Community 62 - "Community 62"
Cohesion: 0.13
Nodes (9): Any, device, dtype, Path, Validate and load one immutable child of the production model store., Inspect a local checkpoint directory and infer the parser family. Returns…, Read ``path`` as JSON. Returns ``None`` if the file is missing, unreadable, or…, If both signatures are present, UniRST wins (more specific). (+1 more)

### Community 63 - "Community 63"
Cohesion: 0.13
Nodes (10): PredictorUniRST, Data, device, dtype, txt (published) → JSON (native) → legacy pickle (labels only)., Load ``relation_table_<variant>.txt`` using corpus aliases., Count distinct ``label_classifiers.<N>.*`` indices in a state dict. Returns…, Splits a batch into multiple smaller batches of the given size. Note:… (+2 more)

### Community 64 - "Community 64"
Cohesion: 0.15
Nodes (24): _assert_tree_aligned(), _check(), _check_from_edus(), _check_parse_rst(), _collect_leaves(), _expect_raises(), main(), Path (+16 more)

### Community 65 - "Community 65"
Cohesion: 0.14
Nodes (13): GraphAttentionConfig, Complete-primary-tree edge-featured graph-attention configuration., _edge_feature(), _EdgeGraphAttentionLayer, GraphAttentionAdapter, _GraphScorer, device, Path (+5 more)

### Community 66 - "Community 66"
Cohesion: 0.13
Nodes (15): DUConverter, Parses the tree predictions given in a string format. Args: description: Tree…, Takes the model outputs and converts them into isanlp binary trees. Returns:…, Selects the discourse unit description for given constituent. Args: start: DU…, Constructs the DiscourseUnit binary tree. Args: root: Index of the root…, Produces EDUs in isanlp format from the model predictions. Args: tokens: List…, Unit tests for ``isanlp_rst.utils.du_converter.DUConverter``. Focuses on the…, When the first gold token already covers the whitespace-stripped predicted… (+7 more)

### Community 67 - "Community 67"
Cohesion: 0.10
Nodes (10): PayloadT, test_disabled_mps_sampler_has_no_measurement_side_effect(), MpsMemorySampler, Measured MPS allocation sampling for independent experiment runs., Sample driver allocations during a run because PyTorch exposes no MPS peak API., ExperimentIndexStore, Path, Atomic, append-only receipt and index persistence. (+2 more)

### Community 68 - "Community 68"
Cohesion: 0.12
Nodes (14): Group, An elementary discourse unit (EDU) leaf element for RS3 XML., A composite structural group element for RS3 XML., A root group element for RS3 XML., Register transparent `isanlp.annotation_rst` in sys.modules if not present., register_isanlp_compat(), Root, Segment (+6 more)

### Community 69 - "Community 69"
Cohesion: 0.11
Nodes (15): AttentionPooling, BoundaryAwareSpanEncoder, device, dtype, PreTrainedTokenizerBase, Tensor, Learned attention pooling over sequence representations., Move the complete scorer while keeping its runtime contract synchronized. (+7 more)

### Community 70 - "Community 70"
Cohesion: 0.13
Nodes (19): ExperimentConfigurationBundle, BaseModel, Exact typed configuration for all ten mandatory systems., build_experiment_protocol(), _environment_lock_sha256(), BaseModel, Path, Build and freeze the executable eRST experiment protocol. (+11 more)

### Community 71 - "Community 71"
Cohesion: 0.16
Nodes (20): DoclingDocument, PictureItem, main(), Any, Phase 0 steps 6 and 7 — long-input smoke and determinism check. Step 6: parse a…, Build a structural signature of a tree for equality comparison. Captures…, tree_signature(), collect_leaves() (+12 more)

### Community 72 - "Community 72"
Cohesion: 0.14
Nodes (5): LinearSegmenter, PointerSegmenter, device, Tensor, ToNySegmenter

### Community 73 - "Community 73"
Cohesion: 0.13
Nodes (11): ParserInput, Any, Path, Mutable historical parser record with no corpus or training behavior., Return the parser's exact limiting-unit count for this materialized input., Data, :param number: int - fold number :param lang: str - (main) language :param…, :param lang: str - (main) language :param mixed: int - percentage for other… (+3 more)

### Community 74 - "Community 74"
Cohesion: 0.13
Nodes (21): gold_edus(), _gold_path(), gumrrg_cpu(), fixture, parametrize, Path, slow, GUM gold RST fixtures — real documents with human trees to compare against. The… (+13 more)

### Community 75 - "Community 75"
Cohesion: 0.13
Nodes (14): getLabelOrdered(), nucs_and_rels(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…, orthogonal_(), Tensor, Device-aware orthogonal weight initialisation for Apple Silicon MPS. PyTorch's… (+6 more)

### Community 76 - "Community 76"
Cohesion: 0.12
Nodes (15): test_generative_outcomes_are_unique_and_include_explicit_no_edge(), GenerativeDecoderAdapter, _label_tokens(), _load_peft(), _PeftApi, device, Module, Path (+7 more)

### Community 77 - "Community 77"
Cohesion: 0.13
Nodes (6): _canonical_model_hash(), datetime, field_validator, model_validator, One model-neutral signal-aware pairwise candidate., SignalMarkedExample

### Community 78 - "Community 78"
Cohesion: 0.25
Nodes (18): CorpusFailureType, Stable machine-readable corpus failure categories., _authority(), _corpus_root(), Path, Authority-backed, fail-closed GUM/eRST corpus loading tests., test_authority_parser_assigns_official_partitions_and_conservative_licences(), test_document_with_no_sufficient_signal_cannot_be_accepted() (+10 more)

### Community 79 - "Community 79"
Cohesion: 0.13
Nodes (9): DecoderRNN, DefaultLabelClassifier, DefaultPlusBiMPMClassifier, PointerAtten, device, Tensor, :param transformer: transformers.PreTrainedModel - LM encoder :param word_dim:…, :param input_size: int - input size :param hidden_size: int - hidden size of… (+1 more)

### Community 80 - "Community 80"
Cohesion: 0.16
Nodes (10): GumGoldValidator, GumValidationReport, Path, Validator that verifies model predictions or processed files against GUM gold…, Validate an RstAnalysis against a GUM gold fixture., Validate a legacy DiscourseUnit tree against a GUM gold fixture., Validate a processed JSON or RS4 file against a GUM gold fixture., Run the neural parser against a GUM gold document and validate results. (+2 more)

### Community 81 - "Community 81"
Cohesion: 0.12
Nodes (15): test_temperature_scaler_handles_extreme_overflow_underflow_logits(), test_temperature_scaler_handles_uniform_zero_logits(), test_temperature_scaler_homogeneous_labels_does_not_crash(), Path, test_temperature_scaler_fit_and_predict(), _golden_section_search_1d(), Any, ndarray (+7 more)

### Community 82 - "Community 82"
Cohesion: 0.13
Nodes (10): DiscourseUnit, Recursively populate the text attribute from full_text using node character…, A node in a binary Rhetorical Structure Theory (RST) discourse tree., Recursively clear the text attribute across the tree to save memory., Reconstruct a ``DiscourseUnit`` tree from this model (recursive)., DummyPredictor, test_discourse_unit_slotted_attributes_strictly_enforced(), Path (+2 more)

### Community 83 - "Community 83"
Cohesion: 0.19
Nodes (16): Parse text and return a typed RST root instead of the legacy mapping payload.…, extract_root_tree(), ParseFailedError, Any, RuntimeError, Helpers for unpacking ``Parser`` / predictor call results., Return ``result['rst'][0]``, or raise :class:`ParseFailedError`. Preferred over…, Raised when a parse result has no usable RST root tree. (+8 more)

### Community 84 - "Community 84"
Cohesion: 0.19
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.19
Nodes (15): Adversarial and numerical edge-case tests for calibration math. Tests…, test_calibration_summary_handles_empty_inputs(), test_compute_calibration_error_boundary_cases(), Unit tests for offline probability calibration and temperature scaling., test_compute_calibration_error_perfect(), test_calibration_ece_hand_computed(), test_calibration_error_mismatched_and_empty(), CalibrationBin (+7 more)

### Community 86 - "Community 86"
Cohesion: 0.22
Nodes (8): BiMPM, device, Tensor, :param v1: (batch, seq_len, hidden_size) :param v2: (batch, seq_len,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, :param v1: (batch, seq_len1, hidden_size) :param v2: (batch, seq_len2,…, Inputs can be of infinite length, hence BiMPM matching can cause OOM. This is a…, LSTM

### Community 87 - "Community 87"
Cohesion: 0.18
Nodes (9): ParsingNet, Any, device, Module, Tensor, Input: input_sentence: [batch_size, length] input_EDU_breaks: e.g.…, :param cur_encoder_outputs: torch.FloatTensor - EDU embeddings of shape…, :param token_ids: list - token ids of shape (n_tokens,) :param edu_breaks: list… (+1 more)

### Community 88 - "Community 88"
Cohesion: 0.16
Nodes (14): MonkeyPatch, parametrize, Isolated wheel runner fails closed before executing ambiguous candidates., test_baseline_runner_requires_full_immutable_commit(), test_candidate_runner_rejects_invalid_determinism_run_counts(), test_candidate_runner_rejects_nonexistent_wheel(), test_candidate_runner_requires_model_store_and_release_as_one_identity(), _git() (+6 more)

### Community 89 - "Community 89"
Cohesion: 0.21
Nodes (16): _analysis(), Promotion assessment protects EDU quality and structural-boundary gains., test_edu_boundary_f1_detects_regression_without_using_source_text(), test_preparation_identity_requires_exact_contract_preparation_and_text(), test_structural_gate_counts_pre_feature_cross_boundary_relation_and_macro_fix(), test_structural_gate_rejects_cross_boundary_relation_mislabelled_local(), assess_candidate_preparation(), _edu_boundary_f1() (+8 more)

### Community 90 - "Community 90"
Cohesion: 0.18
Nodes (6): Exporter, ForestExporter, Path, Serialize this discourse tree to RS3 XML format., RS3 XML document exporter for a single DiscourseUnit tree., RS3 XML exporter for a collection of DiscourseUnit trees.

### Community 92 - "Community 92"
Cohesion: 0.21
Nodes (3): When both family and version are set, version must belong to family., Explicit family must match detectable signatures when present., TestResolveFamily

### Community 93 - "Community 93"
Cohesion: 0.22
Nodes (14): _candidate(), parametrize, Promotion authority rejects mutable, contradictory, or waiver-bearing evidence., _source_result(), test_candidate_identity_rejects_changed_or_partial_digests(), test_promotion_decision_cannot_contradict_a_failed_gate_or_inspection(), CandidateIdentity, PromotionDecision (+6 more)

### Community 94 - "Community 94"
Cohesion: 0.22
Nodes (8): _Node, ParsingNetBottomUp, Any, Tensor, Bottom-up transition-based parser. This module reuses the encoder, segmenters…, Reconstructs the gold tree from pre-order traversal., Return gold transition sequence in postorder., ParsingNet

### Community 95 - "Community 95"
Cohesion: 0.24
Nodes (13): inspect_candidate_outputs(), inspection_status_by_id(), Path, Fail-closed direct inspection of private candidate outputs., Inspect every persisted preparation/result without exporting source text., _segments_reconstruct(), _git(), main() (+5 more)

### Community 96 - "Community 96"
Cohesion: 0.20
Nodes (8): BinaryTree, Node, Path, Offline DMRST binary-tree corpus conversion., :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 97 - "Community 97"
Cohesion: 0.20
Nodes (8): BinaryTree, Node, Path, Offline UniRST binary-tree corpus conversion., :return: convert a dmrg file into a string., :return: find a index which separate the left and right child., :return: a binary tree., :param text_file_path: text contains sentence and paragraph information. :param…

### Community 98 - "Community 98"
Cohesion: 0.32
Nodes (13): HfTokenSource, StrEnum, Supported Hugging Face token environment variables in precedence order., _clear_hf_tokens(), CaptureFixture, MonkeyPatch, Path, Repository-root environment loading and Hugging Face credential precedence. (+5 more)

### Community 99 - "Community 99"
Cohesion: 0.32
Nodes (13): rs3tohtml(), Create a private SQLite file for one render; unlink in ``finally``., _resolve_dbpath(), setup_db(), temporary_db(), Path, Viewer hardening: XXE posture, HTML escape, per-render SQLite., test_rs3tohtml_escapes_basename_in_header() (+5 more)

### Community 100 - "Community 100"
Cohesion: 0.25
Nodes (10): _source(), test_gold_manifest_enforces_depth_forms_risks_and_rst_gold(), test_gold_manifest_rejects_shallow_set(), _EvidenceModel, GoldSetManifest, GoldSource, ProvenanceClass, BaseModel (+2 more)

### Community 101 - "Community 101"
Cohesion: 0.22
Nodes (12): FixtureParityError, FixtureParityReceipt, _GithubEntry, _Manifest, BaseModel, RuntimeError, Verify local DocLang fixtures against an immutable upstream GitHub commit., Raised when local, manifest, and upstream fixture authority diverge. (+4 more)

### Community 102 - "Community 102"
Cohesion: 0.21
Nodes (13): buildTree(), buildTreeThiago(), checkcontent(), convert_parens_in_rst_tree_str(), createtext(), processtext(), Preprocessing token list for filtering '(' and ')' in text (from DPLP, by…, Create text from a list of tokens (from DPLP, by Yangfeng Ji) :type lst: list… (+5 more)

### Community 103 - "Community 103"
Cohesion: 0.17
Nodes (10): Build offset converter from word tokens and optional (start, end) pairs. If…, Best-effort alignment of already-tokenized `tokens` to raw `text`. Used when…, The fix: a missing token must raise rather than silently fall back., Token at the very end should match cleanly., test_guess_token_offsets_at_text_boundary(), test_guess_token_offsets_raises_on_miss(), test_guess_token_offsets_simple(), test_guess_token_offsets_token_longer_than_text() (+2 more)

### Community 104 - "Community 104"
Cohesion: 0.21
Nodes (5): Parse a document using predefined EDU boundaries., Any, Takes word-level tokenized data and converts it to transformer subword inputs., Parse text into an RST tree. Args: text: Original document text. tokens:…, Parses multiple texts in batched forward passes using UniRST. Args: texts:…

### Community 105 - "Community 105"
Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 106 - "Community 106"
Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from https://github.com/kmkurn/pytorch-…, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 107 - "Community 107"
Cohesion: 0.18
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 * 19 * 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 108 - "Community 108"
Cohesion: 0.23
Nodes (6): EncoderRNN, Module, Input: [batch, length] Output: encoder_output: [batch, length, hidden_size]…, :param edu_embeddings: torch.FloatTensor - Subwords embeddings of shape…, Sliding window for encoding long sequences., Encodes the sequence of tokens, returns two matrices: for left and right texts.

### Community 109 - "Community 109"
Cohesion: 0.23
Nodes (4): CRF, Conditional random field. modified from https://github.com/kmkurn/pytorch-…, Compute the conditional negative log likelihood of a sequence of tags given…, Find the most likely tag sequence using Viterbi algorithm. Args: emissions…

### Community 110 - "Community 110"
Cohesion: 0.23
Nodes (5): range, MultipleRunnerGeneral, Offline DMRST multiple-run experiment orchestration. For monolingual…, Running training with second language injection of ``mixed`` %, :param corpus: (str) - 'GUM' or 'RST-DT' :param lang: (str) - 'en' or 'ru'…

### Community 111 - "Community 111"
Cohesion: 0.17
Nodes (8): _CrossEncoder, CrossEncoderConfig, BaseModel, model_validator, Path, PreTrainedModel, Tensor, Frozen model, serialization, optimization, and decoding configuration.

### Community 112 - "Community 112"
Cohesion: 0.20
Nodes (10): dtype, Normalise a dtype spec to a ``torch.dtype``. Accepts: * ``None`` -> ``float32``…, parametrize, Default is fp32 on every device — measured fp32 wins on MPS for typical inputs;…, test_resolve_dtype_default_is_float32(), test_resolve_dtype_passthrough(), test_resolve_dtype_string_parsing(), test_resolve_dtype_unknown_string_raises() (+2 more)

### Community 113 - "Community 113"
Cohesion: 0.20
Nodes (6): Discriminator, device, Module, Tensor, (batch, colors, height, width) (5, 3, 20, 80) 16 * 19 * 1 = 304, Discriminator used in adversarial learning; Based on the code from…

### Community 114 - "Community 114"
Cohesion: 0.20
Nodes (10): IO, PathLike, Render an RST tree and, optionally, display it inline. This is a light-weight…, Convert an ``.rs3`` file into HTML. Parameters ---------- rs3_path: Path to the…, render(), to_html(), Path, Unit tests for viewer convenience helpers in ``isanlp_rst``. (+2 more)

### Community 115 - "Community 115"
Cohesion: 0.27
Nodes (10): find_cdu(), _is_leaf(), Any, Analytical helpers for parsed RST trees. These functions operate on…, Classify an RST relation label as subject-matter or presentational. Follows…, Compute structural diagnostics for an RST tree. Returned dict keys: ``depth``…, Locate the Central Discourse Unit (CDU) of an RST tree. Descends from the root…, relation_category() (+2 more)

### Community 116 - "Community 116"
Cohesion: 0.31
Nodes (10): collect_junk(), _display(), is_junk_dir(), is_junk_file(), main(), Path, Remove regenerable junk from the repo: bytecode, tool caches, temp files. Does…, Delete ``paths``. Returns the number of paths acted on. (+2 more)

### Community 117 - "Community 117"
Cohesion: 0.25
Nodes (10): _FakeNode, _Predictor, Stand-in for isanlp.DiscourseUnit with the attributes used by remap., Minimal concrete subclass (BasePredictor is ABC)., Unary node = DUConverter bug; surface it rather than patch it., test_remap_tree_offsets_binary(), test_remap_tree_offsets_leaf(), test_remap_tree_offsets_unary_raises() (+2 more)

### Community 118 - "Community 118"
Cohesion: 0.25
Nodes (4): MultipleRunnerGeneral, Offline UniRST multiple-run experiment orchestration. For monolingual…, Running training with second language injection of ``mixed`` %, :param corpora: corpus names, e.g. ['GUM'] or ['RST-DT'] :param lang: 'en' or…

### Community 119 - "Community 119"
Cohesion: 0.29
Nodes (8): fixture, Path, Unit tests for ``scripts/cleanup.py`` (stdlib-only project cleaner)., test_collects_bytecode_caches_and_temp_not_source(), test_dry_run_does_not_delete(), test_remove_deletes_junk_keeps_source_and_protected(), test_skips_git_and_pixi_trees(), tree()

### Community 120 - "Community 120"
Cohesion: 0.29
Nodes (9): CommandCategory, CommandReceipt, _execute(), main(), BaseModel, Path, Execute every retained offline command to a bounded, evidence-bearing start., One canonical retained command and its bounded-start contract. (+1 more)

### Community 121 - "Community 121"
Cohesion: 0.22
Nodes (6): BaseModel, parametrize, Path, Pinned upstream parity and locked-validator tests for DocLang fixtures., test_locked_doclang_validator_accepts_every_upstream_fixture(), _UpstreamManifest

### Community 123 - "Community 123"
Cohesion: 0.25
Nodes (7): _clear_runtime_caches(), fixture, MonkeyPatch, Installed-version and source-revision provenance boundaries., test_source_revision_is_separate_from_semantic_version(), test_unexpected_metadata_failure_is_not_hidden(), test_unknown_is_only_used_when_distribution_metadata_is_absent()

### Community 124 - "Community 124"
Cohesion: 0.39
Nodes (8): _analysis_payload(), _compare(), main(), Any, Run and compare deterministic production behavior across the codeline split., run(), _sha256_json(), _tree_payload()

### Community 125 - "Community 125"
Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element, _ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 126 - "Community 126"
Cohesion: 0.22
Nodes (9): getRelationsType(), parseXML(), _Element, _ElementTree, Path, a group's ``type`` attribute tells us whether the group node represents a span…, Write files similar to the .edus files in the RST DT for the other RST…, readRS3Annotation() (+1 more)

### Community 127 - "Community 127"
Cohesion: 0.28
Nodes (5): BaseModel, Tensor, Frozen finite optimization and decoding configuration., _StructuralClassifier, StructuralConfig

### Community 128 - "Community 128"
Cohesion: 0.43
Nodes (7): FreezeAuthority, freeze_baseline(), _git(), Path, Immutable pre-candidate authority and baseline-wheel preparation freeze., Build the immutable baseline wheel and record isolated legacy prepared inputs., _run_isolated_baseline()

### Community 129 - "Community 129"
Cohesion: 0.43
Nodes (6): is_content_free(), looks_like_path(), main(), offending_tool(), Return (tool, path) for the first file-reading invocation, else None.…, True when this invocation cannot print a line of file content. Every argument…

### Community 130 - "Community 130"
Cohesion: 0.29
Nodes (4): field_validator, Require valid half-open anchors while retaining overlap and order., Require non-empty, unique raw relation labels., Require unique non-negative token identifiers without reordering.

### Community 131 - "Community 131"
Cohesion: 0.48
Nodes (6): _is_approved_exclusion(), main(), _manifest_paths(), Verify and lint the complete repository Markdown manifest., _repository_markdown(), verify_manifest()

### Community 132 - "Community 132"
Cohesion: 0.57
Nodes (6): _install_and_run(), main(), Path, Create clean core/formats wheel installs and execute installed acceptance., _run(), _venv_python()

### Community 133 - "Community 133"
Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 134 - "Community 134"
Cohesion: 0.29
Nodes (7): findFile(), getDisFiles(), Any, Path, Retrieve the edu file corresponding to the basename_dis, Read information from the edu file, and fill the fields tokendict and edudict…, readEduDoc()

### Community 135 - "Community 135"
Cohesion: 0.29
Nodes (4): ConfigReader, Any, Path, Offline DMRST training configuration reader.

### Community 136 - "Community 136"
Cohesion: 0.29
Nodes (4): ConfigReader, Any, Path, Offline UniRST training configuration reader.

### Community 137 - "Community 137"
Cohesion: 0.47
Nodes (5): main(), Performance benchmark for isanlp_rst across devices and dtypes. Usage: pixi run…, Run parser n times after a warm-up. Return median seconds and tree shape., _shape(), _time_parse()

### Community 138 - "Community 138"
Cohesion: 0.40
Nodes (3): _module_exists(), The canonical ingest package is the only production source-ingest surface., test_obsolete_envelopes_and_entry_modules_are_absent()

### Community 139 - "Community 139"
Cohesion: 0.40
Nodes (4): _OffsetToken, Protocol, Minimal razdel-token surface used by offset remapping., Build offset converter from a list of `razdel.Token` objects.

### Community 140 - "Community 140"
Cohesion: 0.40
Nodes (4): T, Yield chunks of size `n` from `_list` (handles empty lists)., test_divide_chunks_basic(), test_divide_chunks_empty()

### Community 141 - "Community 141"
Cohesion: 0.60
Nodes (4): _assert_aligned(), _collect_leaves(), main(), CUDA verification script — to be run on a real NVIDIA host. Usage: pixi run…

### Community 144 - "Community 144"
Cohesion: 0.50
Nodes (4): getLabelOrdered(), Any, ArrayLike, Get the right order of lable for stacks manner. E.g. [8,3,9,2,6,10,1,5,7,11,4]…

### Community 147 - "Community 147"
Cohesion: 0.50
Nodes (3): The core parser remains isolated from optional source-format dependencies., Core ``isanlp_rst.parser`` must not require the formats extra., test_parser_imports_without_docling_core()

### Community 148 - "Community 148"
Cohesion: 0.67
Nodes (3): _distribution_members(), main(), Smoke-test the installed production package without loading model weights.

## Knowledge Gaps
- **22 isolated node(s):** `no-assumptions-check.sh script`, `common.sh script`, `isanlp_rst`, `$schema`, `$id` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RstAnalysis` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 6`, `Community 9`, `Community 11`, `Community 14`, `Community 15`, `Community 19`, `Community 21`, `Community 27`, `Community 30`, `Community 37`, `Community 50`, `Community 53`, `Community 55`, `Community 65`, `Community 74`, `Community 80`, `Community 89`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `RstDocument` connect `Community 4` to `Community 0`, `Community 2`, `Community 3`, `Community 37`, `Community 6`, `Community 9`, `Community 11`, `Community 14`, `Community 15`, `Community 80`, `Community 17`, `Community 50`, `Community 19`, `Community 23`, `Community 27`, `Community 124`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `Parser` connect `Community 48` to `Community 2`, `Community 3`, `Community 4`, `Community 8`, `Community 9`, `Community 137`, `Community 141`, `Community 14`, `Community 142`, `Community 19`, `Community 148`, `Community 23`, `Community 27`, `Community 62`, `Community 64`, `Community 71`, `Community 74`, `Community 80`, `Community 82`, `Community 83`, `Community 92`, `Community 124`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `RstAnalysis` (e.g. with `ProvenanceRecord` and `FailureCodeEnum`) actually correct?**
  _`RstAnalysis` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `Parser` (e.g. with `HierarchicalSectionStitcher` and `DiscourseUnit`) actually correct?**
  _`Parser` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `RstDocument` (e.g. with `InputFidelityEnum` and `document_from_json()`) actually correct?**
  _`RstDocument` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `SpanNode` (e.g. with `backprop()` and `BFTbin()`) actually correct?**
  _`SpanNode` has 49 INFERRED edges - model-reasoned connections that need verification._