# Raw-material ingest and preparation: forensic analysis

**Project:** `isanlp_rst`  
**Assessment date:** 25 August 2026  
**Working tree assessed:** `codex/spec-kit-adoption`, HEAD `bf953a73cba6413d03888262e96c1ca45f861fc4`  
**Scope:** Three systems assessed separately: production document ingest and RST/eRST serving; offline model-development data preparation; and research/evaluation data preparation. The review covers the explicit promotion boundary required between them.  
**Method:** Report-only forensic review of the actual working tree, local corpora and generated artifacts, plus current upstream specifications and focused runtime proof. No production code was changed.

> **Working-tree caveat:** the repository already contained material uncommitted changes before this review. Findings describe the code and artifacts actually present on disk on 25 August 2026, not necessarily the checked-in HEAD alone.

## Executive verdict

There is **not one ingest process** in this repository. There are three systems with different users, failure modes and quality verdicts. Combining them into one score would be architecturally misleading.

### 1. Production document ingest and analysis serving

**Verdict: strong and useful, but not yet world-class.** The Docling, DocLang and Markdown adapters use current dependencies, defensive loaders, stable result contracts and unusually good source anchoring. Existing classical production parsing is not invalidated by the training defects identified elsewhere in this report. Production quality is held back by relevance-poor inclusion defaults, flatten-first parsing, failure to use detected source structure during inference, lossy table handling, a current-valid DocLang construct that is rejected, and incomplete analytical cache identity.

### 2. Offline model-development data preparation

**Verdict: not production-grade; one route is critically invalid.** The Transformer EDU-segmenter preparation path reads the wrong DISRPT column, loses 2,766 of 2,790 GUM development EDU boundaries in a live measurement, truncates document-sized examples and mixes PDTB connective targets into an RST EDU task. The legacy DMRST/UniRST corpus compilers are also insufficiently governed. These findings invalidate checkpoints prepared through the affected route; they do **not** prove that every released classical parser or every production parse is invalid. Model lineage must determine impact.

### 3. Research and evaluation preparation

**Verdict: excellent source governance, inefficient materialization and an untruthful evidence field.** The governed GUM v12.1/eRST corpus authority is a world-class foundation: immutable revision, official splits and licences, source hashes, fail-closed checks and deterministic receipts. The downstream eRST experiment cache is not world-class: it expands 301 documents into 16,676,352 JSON records and 39.87 GiB, while every development shard declares zero positives even when its records contain gold edges.

### Separate scorecard

| System | Area | Verdict | Why |
| --- | --- | --- | --- |
| Production | Docling/DocLang/Markdown adapters | **Strong engineering; not yet world-class discourse ingest** | Secure/current loading, reversible source anchors and deterministic results; but flatten-first parsing and relevance-poor defaults. |
| Production | Parser serving | **Operationally viable** | Real classical-model and format-adapter routes passed; long-document and structure-aware serving are not fully integrated. |
| Model development | Transformer EDU preparation | **Critically invalid** | Wrong official label column, task mixing and unreported truncation. |
| Model development | Legacy DMRST/UniRST preparation | **Below production standard** | Silent document loss, heuristic gold mutation, loose schemas and no source-to-example receipt. |
| Research | GUM v12.1/eRST authority | **World-class foundation** | Immutable authority, hashes, official splits/licences, typed failures and reproducible receipts. |
| Research | eRST candidate materialization | **Correctness-oriented but grossly inefficient and evidentially inconsistent** | Complete logical space, but 39.87 GiB of repeated JSON and false dev-positive manifest counts. |
| Cross-system | Model promotion boundary | **Missing** | Production cannot currently prove which governed preparation pipeline, dataset manifest and evaluation receipt created every served checkpoint. |

### Immediate decisions by system

#### Production

1. Make “prose eligible for RST” a first-class preparation policy. Code, raw HTML, table cells, duplicated slide notes and machine-authored picture descriptions must not silently join authored prose.
2. Route detected document structure into `Parser.parse_hierarchical()` rather than using it only as post-hoc output annotation.

#### Model development

1. Quarantine the Transformer EDU-segmenter training path. Do not train or promote a checkpoint whose lineage includes the current `scripts/train_segmenter.py` preparation route.
2. Determine the lineage of every currently served checkpoint before inferring production impact. Unknown lineage is a release-evidence gap, not proof of model failure.

#### Research

1. Retain the GUM/eRST authority layer as the research-data standard.
2. Correct the eRST manifest and replace denormalized complete-candidate storage without changing logical candidate membership.

#### Promotion boundary

1. Admit a model to production only through an immutable release manifest containing its checkpoint hash, task, source-data manifest, preparation fingerprint, code revision and official evaluation receipts.

## 1. Three systems currently sharing one repository

The repository contains four raw-material flows, but they belong to three operational systems and must not be conflated:

1. **Production analysis serving:** plain text or pre-segmented EDUs accepted by `Parser`, plus Docling JSON, DocLang `.dclg` XML and Markdown files prepared for immediate inference.
2. **Offline model development:** classical RS3/DIS-style treebanks converted by the DMRST and UniRST managers, plus DISRPT `.tok` and local RS4 data transformed into Transformer segmentation examples.
3. **Research and evaluation:** pinned GUM v12.1.0 RS4 converted into typed primary/eRST analyses and signal-sufficient secondary-edge candidates.

Training is relevant to production only at the **model-promotion boundary**. A training defect affects production when a served checkpoint can be traced to that defective preparation route. Production source adapters and classical inference do not become invalid merely because defective training utilities coexist in the repository.

The resulting topology is:

```text
Runtime documents
  Docling JSON / DocLang XML / Markdown
    -> validate or load
    -> choose eligible content
    -> concatenate spans with synthetic separators
    -> detect source boundaries
    -> parse one flat main string + one flat string per table
    -> map EDUs/relations back to source anchors
    -> format-specific immutable result
    -> optional projection to shared FormatRstAnalysis

Classical parser training
  RS3/DIS corpora
    -> custom XML/tree readers
    -> repair + clean + binarize gold trees
    -> .edus + .lisp
    -> mutable ParserInput JSON/pickle
    -> unmanifested Data objects

Neural segmentation training
  DISRPT 2023 .tok + local GUM RS4 fixtures
    -> reconstruct space-joined text
    -> derive B-EDU labels
    -> truncate/pad to 512 subwords
    -> Transformer token-classification training

eRST secondary-edge training
  pinned GUM v12.1 RS4
    -> secure XML read
    -> RstDocument + gold RstAnalysis
    -> all signal-sufficient ordered node pairs
    -> deterministic train hard-negative selection
    -> complete dev candidate materialization
    -> experiment harness / scorer
```

The runtime adapters are modern but need stronger content and structural policy. The governed eRST authority is modern and exemplary. The classical model-development path remains compatibility-era, while the current Transformer segmentation preparation path is invalid.

### 1.1 Required dependency boundary

Co-location in one repository is acceptable for a solo local project. Runtime coupling is not. The world-class boundary is:

```text
Shared contracts
  RstDocument, source anchors, task/label types, preparation receipts
       ^                         ^
       |                         |
Production runtime          Offline model development
  document adapters           governed corpora
  released model loader       preparation + training
  parser + analysis            official evaluation
       ^                         |
       |                         v
       +--- immutable model release manifest

Research harness
  may consume shared contracts and governed corpora
  must not be imported by production
```

Required rules:

- Production packages never import corpus acquisition, training or research modules.
- Model development may reuse the exact canonical preparation contracts used by production.
- Research artifacts remain disposable derivations, never production authorities.
- Training dependencies and corpora are absent from the production environment unless explicitly invoked offline.
- A released model crosses into production only through an immutable, verified manifest; production never selects a loose experiment checkpoint directly.

## 2. What is genuinely strong

### 2.1 Research: GUM/eRST source governance is the best part of the project

`isanlp_rst/erst/corpus.py:29-32` pins the exact GUM revision, split authority, licence inventory and GENTLE licence revision. `parse_gum_corpus_authority()` derives document partitions and conservative licence classes from the pinned authority rather than an ad hoc local list (`corpus.py:113-157`). The loader then:

- rejects missing corpus or authority files;
- validates pinned split and licence hashes;
- sorts RS4 sources;
- rejects symlinks and paths outside the corpus root;
- hashes every source;
- rejects duplicate IDs, duplicate bytes and unauthorized documents;
- records typed failures and fails closed by default;
- retains document boundaries through partition assignment; and
- emits document, corpus and split receipts (`corpus.py:301-528`).

A fresh verification during this review passed for **301 sources** at exact revision `22fdf87f9c71c96bcc771461d06e689b1f90020d`, with partitions `211 train / 32 dev / 32 test / 26 test2`. The regenerated receipt SHA-256 exactly matched the persisted authority: `79e119e02028462b900ddb811a96d85ba0582c1f7207d7c836ba4967ac6172b6`.

That design—canonical upstream revision, source hashes, licence class, official split before flattening, typed failure receipts, deterministic identity—is the correct baseline for every training-data path in this repository.

### 2.2 Production: format-native adapters preserve useful provenance

The Docling, DocLang and Markdown adapters all preserve span-to-source mappings:

- Docling JSON pointers (`self_ref`);
- DocLang local-name XPaths and thread IDs; and
- Markdown block references plus source line ranges.

They use deterministic serialization, immutable slotted dataclasses and shared tree flattening. They retain boundary memberships and expose a single `to_format_analysis()` projection through the central analysis contract. Their loaders are generally defensive: Docling uses the official Pydantic model loader; DocLang disables entity resolution, DTD loading and network access; Markdown rejects non-UTF-8 input. Furniture is excluded by default in Docling and DocLang, and code/formulas are excluded by default in DocLang.

### 2.3 Production: current Docling and DocLang dependencies are actually current

Live PyPI metadata and the Pixi environment both reported:

- [`docling-core` 2.92.0](https://pypi.org/project/docling-core/); and
- [`doclang` 0.7.3](https://pypi.org/project/doclang/), including the Saxon Schematron backend.

All four Docling fixtures declare document schema `1.10.0` and load successfully with `DoclingDocument.load_from_json()` under 2.92.0. Current `iterate_items()` and `ContentLayer` signatures were inspected at runtime. The 42 local DocLang fixtures exactly matched names and SHA-256 hashes at the current upstream commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd` using `scripts/verify_doclang_fixtures.py`.

This is current evidence—not an inference from the lock file or old notes.

### 2.4 Production: shared mapping and tree validation are thoughtfully engineered

The shared flattening path validates binary shape, parent/child span containment, node reuse and cycles, then maps character and EDU spans back to source anchors. The interval-overlap index avoids naive full scans for every mapping. These are meaningful quality strengths.

### 2.5 Production: model reuse and caches can make batch ingest efficient

The adapters accept an injected parser, which avoids a model reload per document. A real CPU run loaded `gumrrg` once in 10.247 seconds, then parsed a representative Docling fixture in 0.917 seconds, a namespaced DocLang fixture in 0.092 seconds and a Markdown document in 0.127 seconds. Optional disk caches are atomic, schema-sensitive and corruption-tolerant. These are sensible solo-machine optimizations.

## 3. Critical findings

Severity definitions used here:

- **P0 – stop the affected system:** the current path can create materially false training data or invalidate analytical claims. It does not automatically stop an operationally separate system.
- **P1 – high:** systematic quality, contract or reproducibility failure; remediate before calling the affected system world-class.
- **P2 – material:** bounded defect or debt that reduces trust, efficiency or maintainability.
- **P3 – improvement:** worthwhile refinement after correctness and governance are secure.

### F-01 — P0 — Model development: the DISRPT loader reads the wrong column and destroys EDU labels

**Evidence.** `parse_disrpt_tok_file()` assigns `parts[2]` to `seg_col` (`isanlp_rst/segmentation/dataset.py:65-71`). Official DISRPT 2023 GUM `.tok` files are ten-column token files: token text is column 2 and `BeginSeg=Yes` is in column 10. The included unit test instead creates a bespoke three-column mock with `Seg=B-EDU` in column 3 (`tests/test_transformer_segmenter.py:96-107`), so the test proves compatibility with an invented format rather than the downloaded data.

**Measured impact.** On the official `eng.rst.gum_dev.tok` fetched directly from the configured DISRPT 2023 authority:

| Measure | Value |
| --- | ---: |
| Tokens | 21,743 |
| Official `BeginSeg=Yes` boundaries | 2,790 |
| Boundaries emitted by this loader | 24 |
| Boundaries lost | 2,766 |
| Effective recall against the file’s boundary markers | **0.86%** |

The 24 retained positives are merely the forced first token of each reconstructed document-sized record. This is not a small compatibility bug. It changes the supervised learning problem into “predict document start,” so any checkpoint trained through this path is untrustworthy.

**Action.** Disable the training entry point until a format-specific, fail-closed parser reads the official column schema, validates every row width and label vocabulary, and reconciles observed boundary counts against a pinned manifest. Add at least one unmodified official `.tok` fixture; do not synthesize a reduced mock.

### F-02 — P0 — Model development: the same training path mixes PDTB connective detection into RST EDU segmentation

**Evidence.** The fetcher selects `eng.rst.gum`, `eng.rst.rstdt` **and** `eng.pdtb.pdtb` by default (`scripts/fetch_disrpt_data.py:10-32`, `43`). The training script recursively consumes every `_train.tok` and `_dev.tok` without retaining corpus or framework identity (`scripts/train_segmenter.py:81-99`).

DISRPT explicitly distinguishes the targets: RST/eRST `.tok` segmentation finds discourse-unit starts, while PDTB-style `.tok` prediction identifies discourse-connective spans. See the official [DISRPT 2025 repository](https://github.com/disrpt/sharedtask2025#types-of-data), lines 186-190 in its current README. They are not interchangeable B-EDU labels.

**Impact.** Once F-01 is fixed, the generic `"Seg=B"` test at `dataset.py:69` would still map PDTB B-Conn-style targets into B-EDU. The default dataset composition would therefore train the RST segmenter on semantically different labels.

**Action.** Define the training task explicitly. For an RST EDU segmenter, admit only corpora whose `seg_style` is EDU, retain framework/corpus IDs in every example and require an approved dataset manifest. Any cross-formalism multi-task experiment must have separate heads or target namespaces and an ablation proving benefit; it must not be the default ingest path.

### F-03 — P0 — Model development: long DISRPT examples are silently truncated during training

**Evidence.** The malformed reader reconstructed GUM dev as 24 document-sized records, not sentence windows. `EduSegmentationDataset` then applies `max_length=512` and `truncation=True` with no overflow windows or dropped-token receipt (`dataset.py:162-212`). The official GUM dev sample contains 21,743 word tokens; 24 × 512 provides an absolute upper bound of 12,288 subword positions before special tokens, and real subword expansion reduces coverage further.

Inference has a related skew: `TransformerEduSegmenter.segment()` splits by input lines and truncates each line at 512 subwords. Text after the last model-visible token remains attached to the last EDU, but no boundary can be predicted inside that tail (`transformer_segmenter.py:136-188`).

**Impact.** Training omits a large, unreported fraction of labels. Serving treats overflow as a single EDU. The model sees different chunk semantics in training and inference.

**Action.** Build overflow-aware windows aligned to official sentence/document metadata, with stride, de-duplicated loss masks and an exact coverage receipt. Fail if any gold boundary is unrepresented. Use the identical window builder in training, evaluation and serving.

### F-04 — P1 — Production: source structure is detected after flattening and does not constrain the parse

**Evidence.** Each adapter concatenates eligible spans using synthetic `\n\n`, detects headings/pages/slides/groups/turns, then calls the legacy parser once on the entire flat string (`docling/_entry.py:205-213`, `doclang/_entry.py:291-299`, `markdown/_entry.py:210-218`). Boundaries are passed only to `flatten_tree()` to annotate overlap memberships after the model has already built its tree. Tables are independently flattened and mini-parsed as plain strings.

The project already has `Parser.parse_hierarchical()`, which parses local sections, models macro relationships between section roots and stitches a valid global tree (`isanlp_rst/parser.py:321-340`). None of the three adapters uses it.

**Impact.** Slide boundaries, speaker turns, headings and pages cannot prevent implausible cross-boundary EDUs or guide discourse structure. Long inputs over 200,000 characters fail with “chunk upstream” despite an in-repository hierarchical parser. Source structure is metadata on the result, not raw material for the model.

**Action.** Make every adapter emit a canonical `RstDocument` with exact source-aligned boundaries before parsing. Use `parse_document()` for simple prose and `parse_hierarchical()` for multi-section/long documents. Retain a macro tree across sections rather than independently parsing and abandoning cross-section relations.

### F-05 — P1 — Production: defaults inject material that is not reliably part of the authored RST discourse

**Evidence.** Defaults currently include:

- Docling picture descriptions, slide notes and table cells (`docling/_entry.py:71-74`);
- Markdown fenced/indented code, raw HTML and table cells (`markdown/_entry.py:73-75`); and
- all harvested table cell strings separated by blank lines, without row delimiters or column/header semantics (`docling/harvester.py:115-167`).

Markdown raw HTML is “stripped” with the regex `<[^>]+>` (`markdown/harvester.py:48,85-91`), which preserves script/style bodies and is not a content extractor. Docling traverses picture children unconditionally and emits picture descriptions when present (`docling/harvester.py:96-110`).

A live measurement on the PPTX fixture found that enabling the default slide-note policy grew the primary RST input from 8,767 to 15,667 characters. One 1,378-character note block occurred **five times**, contributing 6,890 repeated characters—44% of the final input. Whether the duplication originated in Docling or the source is immaterial to the downstream risk: the parser receives five copies and can invent relations between them.

**RST relevance assessment.**

| Content class | Default today | Recommended RST role |
| --- | --- | --- |
| Authored prose, headings, list text, transcript turns | Included | Primary discourse, with explicit structure. |
| Slide notes | Included in Docling | Separate authored-notes channel; include only under an explicit presentation profile, with exact-duplicate anomaly handling. |
| Machine-authored picture descriptions | Included when present | Side evidence; never primary discourse by default. Record producer/confidence. |
| Code blocks | Included in Markdown | Exclude by default. Route to a code-aware analysis only when explicitly requested. |
| Raw HTML block bodies | Included in Markdown | Parse with an HTML content policy; exclude script/style/navigation. Never regex-strip arbitrary HTML into prose. |
| Tables | Parsed as separate linear discourse | Preserve structurally. RST-parse only under an explicit, validated linearization policy or a model trained for tabular discourse. |
| Furniture/background/formulas | Mostly excluded | Keep excluded unless a named profile requests them. |

**Action.** Introduce named inclusion profiles, with `prose_only` as the default. Record every included, excluded, deduplicated and transformed source span in a preparation receipt. Keep non-prose as side channels so fidelity does not require contaminating the RST stream.

### F-06 — P1 — Production: current-valid DocLang nested tables are explicitly rejected

**Evidence.** The current [DocLang specification’s table section](https://github.com/doclang-project/doclang/blob/main/spec.md#tables) says a cell may contain any semantic element, including a nested table, and provides a nested-table example. `reject_nested_tables()` raises `UnsupportedDoclangError` for exactly that construct and instructs users to flatten upstream (`isanlp_rst/doclang/harvester.py:44-62`).

This was reproduced with a minimal namespaced DocLang 0.7 document: `doclang.validate()` passed; `parse_doclang()` failed with `UnsupportedDoclangError`.

**Impact.** The adapter is current at the package/fixture level but not fully compliant with the current specification. “Flatten upstream” is also the wrong fidelity response: it destroys table nesting before this project can receipt or reverse the transformation.

**Action.** Represent tables recursively, give each table its own structural path and preserve nested cell ancestry. If analysis of nested tables is not supported, accept and retain the structure while marking its analysis status `not_analyzed`; do not require upstream destruction.

### F-07 — P1 — Model development: the legacy corpus compilers can silently shrink and mutate gold data

The DMRST and UniRST managers are near-duplicates with separate drift. Material defects include:

- hard-coded relative input/output directories and constructor side effects (`dmrst_parser/data_manager.py:89-123`; `universal_parser/data_manager.py:102-146`);
- global `random.seed(42)` at module import and split selection over partly unsorted globs (`dmrst_parser/data_manager.py:23,490-501`);
- mutable `ParserInput` records that accept arbitrary extra attributes and carry no schema version, document identity, source hash, corpus revision or transform receipt (`dmrst_parser/data_manager.py:26-69`; `universal_parser/data_manager.py:26-74`);
- RS3 conversion through `.edus` and `.lisp` intermediates with no manifest (`dmrst_parser/data_manager.py:343-375,757-764`);
- missing prepared documents printed and skipped in train/dev/test (`dmrst_parser/data_manager.py:403-460`; `universal_parser/data_manager.py:441-500`);
- translated RST-DT conversion errors printed and suppressed (`universal_parser/data_manager.py:389-395`);
- `GUM10-tr` and `RST-DT-tr` paths with empty dev/test partitions (`universal_parser/data_manager.py:529-553`);
- relation repairs tied in comments to GUM v9.1 while the current governed corpus is GUM v12.1 (`dmrst_parser/data_manager.py:111-116`); and
- extensive custom RS3 repairs, lonely-node cleaning and heuristic binarization that transform the gold tree but produce no per-document change ledger.

**Impact.** A training run can complete after losing documents, changing relations, inventing roots and choosing an order-sensitive split, with no machine-readable evidence of what changed. Green model evaluation cannot identify which source material actually reached training.

**Action.** Retire both managers behind one canonical corpus compiler. Every source document must either yield a versioned, typed prepared example plus a transformation receipt or fail the build. Preserve original IDs and relations; record each repair as an explicit, reviewable operation. Split manifests must be immutable and checked for document/hash leakage before example flattening.

### F-08 — P1 — Research: the eRST candidate cache is 39.87 GiB for 16.68 million repeated JSON records

**Evidence from the current workspace:**

| Partition | Documents | Candidates | Gold positives | Physical size |
| --- | ---: | ---: | ---: | ---: |
| Train complete | 211 | 14,778,264 | 1,082 | 35.48 GiB |
| Dev complete | 32 | 1,898,088 | present in records | 4.40 GiB |
| Total | 243 | 16,676,352 | — | **39.87 GiB** |

The selected training artifact is only 5,410 records / 13 MiB (1,082 positives plus deterministic hard negatives). Complete train shards therefore consume 35.48 GiB after selection even though the experiment payload uses `selected/train.jsonl`.

The generator deliberately considers every ordered node pair for which any sufficient signal overlaps either node (`isanlp_rst/erst/candidates.py:206-310`). Each JSON row repeats source/target text, signal IDs/types/subtypes and character spans. This gives comprehensive membership but exceptionally poor storage locality and extreme class imbalance: train positives are approximately **0.0073%** of complete train candidates.

**Impact.** The cache is reproducible but not effective or efficient for one local machine. It increases I/O, verification time, backup cost and the chance that generated artifacts dominate the workspace. “Bounded memory” is true but incomplete as a quality claim; disk amplification matters.

**Action.** Preserve candidate completeness as a logical iterator, not as denormalized JSON. Recommended sequence:

1. Keep source RS4 + governed receipt + deterministic generator version as authority.
2. Keep the 13 MiB selected train artifact and its identity receipt.
3. Generate development candidates per document on demand, or store a compressed columnar representation with text/signals normalized once per document.
4. Do not retain complete train shards after the selected artifact is verified unless a measured workflow consumes them.
5. If candidate pruning is introduced, prove **100% gold-edge recall** on train and dev before comparing model quality.

### F-09 — P1 — Research: the eRST cache manifest makes false claims about dev positives

**Evidence.** `_write_candidate_shard()` increments `positive_count` only inside `if partition == TRAIN` (`research_harness/erst/data.py:298-334`). Consequently every dev shard in the persisted manifest declares `positive_count: 0`.

That is false. For example, `GUM_academic_exposure.rs4` contains seven secondary edges; live candidate generation produced seven gold candidates, and the stored dev JSONL contains seven `"is_gold_edge":true` records. The same check found gold records in 30 of the 32 dev shards. The manifest validator reconciles only total dev candidate count and hashes, not positive counts (`data.py:157-172`).

**Impact.** The candidate files used for evaluation retain the gold labels, so this does not by itself erase dev positives. It does mean the supposedly authoritative evidence boundary is untrue and cannot support class-balance, coverage or evaluation claims.

**Action.** Count positives for every partition, validate shard counts by streaming records once, and require `positive_count == gold secondary-edge count` for the source analysis. Regenerate the manifest and dependent identities after correcting the implementation.

### F-10 — P2 — Production: cache identity can return analytically stale results

The shared result cache deliberately excludes `tool_version` from the key (`isanlp_rst/_rst_common/_cache.py:8-9`). Source bytes, schema version, knobs and model identity are included, which is good; however:

- code changes that alter harvesting/mapping without a result-schema bump can reuse old analysis;
- DocLang cache lookup occurs before current XML validation (`doclang/_entry.py:215-227`), and the key omits the `doclang` validator/schema package version;
- Docling cache identity omits `docling-core` version and fixture document schema version as separate governed fields; and
- an injected parser is keyed using `id(parser)`, which is process-local and prevents durable cross-process reuse.

**Action.** Key analytical caches by a stable pipeline fingerprint: source SHA-256, canonical basename only if output semantics require it, upstream document/schema version, validator/converter package versions, inclusion profile digest, canonical model checkpoint/revision, relation inventory digest and code/source revision. Validate before cache lookup when validation semantics can change.

### F-11 — P2 — Research/model development: RS4 import is secure but not fully fail-closed semantically

The RS4 reader correctly disables entities, DTDs, network access and huge trees (`isanlp_rst/erst/rs4.py:9-15`). The converter, however:

- reconstructs document text by inserting one space between every EDU and tokenizes with `str.split()` (`converter.py:39-78`);
- emits empty sentence/paragraph boundaries;
- silently assigns EDU 1 to a group whose yield is empty (`converter.py:112-123`);
- infers an edge’s nuclearity pattern from only the child relation and parent type (`converter.py:157-178`); and
- de-duplicates repeated signal-token indices during import.

The current GUM v12.1 corpus produced no out-of-range signal-token references in a 301-document audit, so there is no evidence of current signal-token loss from bounds filtering. The concern is contract rigor: malformed or future-valid RS4 structures can be normalized rather than rejected, and reconstruction is not demonstrably round-trip lossless.

**Action.** Add RS4 structural validation before conversion: unique IDs, exactly one rooted connected primary structure, valid parent targets, non-empty group yields, relation/header consistency, contiguous token/EDU anchors where required, secondary-edge endpoint existence and exact signal-token preservation. Produce an import receipt with normalization counts and round-trip probes.

### F-12 — P2 — Cross-system: tests are broad but certify implementation shape more than raw-material truth

The project’s 844 passing non-slow tests, clean Ruff result and zero-error Pyright run are valuable. They did not catch F-01 because the test fixture copied the implementation’s assumed three-column shape. DocLang fixture parity is exact, but the mirrored upstream valid set does not currently contain the nested-table example from the normative specification. Docling fixtures explicitly lack a multi-speaker VTT, dominant scanned/OCR PDF, multi-level PDF headings and a simple prose fallback document.

**Action.** Create a semantic ingest conformance suite whose authorities are immutable external specimens and invariants, not mocks shaped around current code. For every route, assert source coverage, exclusions, boundary counts, no silent truncation, stable anchors, transform receipts and downstream gold metrics.

## 4. Is the runtime ingest effective?

**For small, mostly prose documents: yes.** The adapters load, harvest, parse and map back to source locations correctly enough to be useful. Real model runs succeeded for all three formats. The format-specific results are deterministic and easy to serialize.

**For heterogeneous production documents: only partly.** The parser is given a synthetic text whose block adjacency, separators and content mixture are artifacts of harvesting. Structure cannot influence the parse. Tables are removed from their document context and interpreted as prose. Long documents fail rather than use the available hierarchical route. Repeated or machine-generated content is not classified as a separate evidence channel.

**For trustworthy comparative analysis: not yet.** The result says what the model inferred over the harvested string, but there is no single preparation receipt that lets a consumer answer:

- What source bytes and upstream schema created this analysis?
- Exactly which source elements were included, excluded, duplicated or transformed?
- What percentage of eligible source text reached the model?
- Which separators and table linearizations were synthetic?
- Were any tokens, labels or boundaries truncated?
- Which cache/pipeline fingerprint produced the result?

Those answers are essential raw-material quality, not optional observability.

## 5. Is the ingest process state of the art?

### 5.1 Against current discourse-processing practice

The [DISRPT 2025 shared task](https://aclanthology.org/2025.disrpt-1.1/) covers 39 datasets, 16 languages and six formalisms, and reports separate treebanked/plain segmentation metrics. Its best mean segmentation F1 was 91.57 (treebanked) and 87.38 (plain). Current systems retain framework/language identity, use official validation/evaluation scripts and treat sentence/window preparation as part of the modeling problem. The project’s segmentation input does none of those reliably today.

For full RST parsing, recent work includes multilingual unified parsing across 18 treebanks ([UniRST, 2025](https://aclanthology.org/2025.codi-1.17/)), bilingual GUM-based end-to-end parsing ([Chistova, 2024](https://aclanthology.org/2024.findings-acl.577/)) and large-model bottom-up parsing on RST-DT, Instr-DT and GUM ([Maekawa et al., 2024](https://aclanthology.org/2024.eacl-long.171/)). “SOTA” is not one architecture, but current practice expects clean official splits, task-correct labels, end-to-end evaluation and transparent corpus composition.

For eRST, the current theory explicitly includes secondary, non-projective/concurrent relations and token-anchored signals ([Zeldes et al., 2025](https://aclanthology.org/2025.cl-1.3/)). The project’s governed GUM v12.1 path is aligned with that direction and is the closest subsystem to SOTA-quality ingest.

### 5.2 Separate SOTA answers

**Production document ingest and serving is not yet SOTA, but it is operationally credible.** Format currency, defensive loading, deterministic contracts and source anchors are strong. It needs explicit content-class policy, structure-aware parsing, loss receipts, complete DocLang handling and stable cache identity. This verdict stands independently of training-data defects.

**Offline model-development preparation is not SOTA and the reviewed Transformer segmentation route is invalid.** The critical deficiencies are task correctness, official-format conformance, overflow coverage and model lineage. Legacy corpus compilation also lacks the governance required for trustworthy retraining.

**Research/evaluation preparation is mixed.** GUM/eRST source authority is SOTA-quality data governance. Candidate materialization is neither efficient nor evidentially reliable in its present form, although its logical completeness is defensible.

**The production-promotion boundary is below SOTA because it is not explicit.** A served model needs immutable proof connecting checkpoint bytes to governed data, preprocessing, code and official evaluation. Without that boundary, training findings cannot be scoped confidently to affected production models.

## 6. Target architecture: separate systems, shared contracts

The right redesign is not one operational pipeline that handles documents, training corpora and experiments alike. It is three isolated systems using a small shared contract layer, joined only by an immutable model-release boundary.

```text
Shared contract package (no I/O, training or model execution)
  SourceArtifact identity
  RstDocument + source anchors
  task-specific EDU/relation/eRST label types
  PreparationPolicy + PreparationReceipt
  ModelReleaseManifest

Production runtime
  Docling / DocLang / Markdown / text
    -> production loader + validator
    -> authored-content inventory and policy
    -> PreparedRstDocument
    -> released model identified by ModelReleaseManifest
    -> parse_document / parse_hierarchical
    -> persisted RstAnalysis

Offline model development
  governed RS3 / RS4 / DISRPT corpus authority
    -> corpus-specific validator
    -> task-specific compiler
    -> immutable split + preparation receipts
    -> training + official evaluation
    -> candidate ModelReleaseManifest
    -> explicit promotion into production model store

Research/evaluation harness
  governed corpus snapshots + shared contracts
    -> experimental candidates / features / ablations
    -> disposable caches and experiment receipts
    -> no production imports and no implicit promotion
```

### Required invariants

1. **Production isolation:** production imports only runtime and shared-contract packages; it never imports corpus acquisition, trainers or research harnesses.
2. **One authority per system:** source bytes and hashes are immutable, but production documents, governed corpora and disposable experiments have separate stores and lifecycles.
3. **Shared semantics, not shared operations:** coordinate, label and receipt contracts are common; loaders, dependencies, commands and caches remain system-specific.
4. **No silent loss:** every skipped span, document, token, label, edge or overflow region is either forbidden or receipted in the system that transformed it.
5. **No task mixing:** EDU, connective, relation and eRST-edge labels have distinct types.
6. **Split before flattening in model development:** assign a corpus document to an official partition before examples or candidates exist.
7. **Release compatibility:** a promoted model manifest proves that production normalization and coordinates satisfy the model’s declared input contract; production does not reproduce the training pipeline.
8. **Reversible normalization:** preserve original text/IDs and a mapping through every synthetic separator or repair.
9. **Fail closed on gold:** malformed annotation never becomes a warning plus a smaller model-development or evaluation corpus.
10. **System-specific cache identity:** production analysis fingerprints, training derivations and research caches cannot collide or substitute for one another.
11. **Explicit promotion only:** no experiment checkpoint is served until its manifest, official metrics and bytes are verified and copied into the immutable production model store.

## 7. Prioritized remediation roadmap

These are independent workstreams, not phases of one mixed ingest pipeline. Priority is ordered within each system; workstreams may proceed independently. Only model promotion crosses a system boundary.

### Model development A — stop invalid material entering models (immediate)

| Action | Success criterion |
| --- | --- |
| Block or remove the current default `train_segmenter` route. | It cannot produce a checkpoint until conformance tests pass. |
| Implement an official DISRPT parser for the pinned version. | Exact row/column validation; official GUM dev yields all 2,790 declared starts in the reviewed specimen; corrupt/unknown labels fail. |
| Separate EDU and connective tasks. | An RST EDU manifest cannot contain PDTB `seg_style=Conn`; the type system makes accidental mixing impossible. |
| Add overflow windows shared by train/eval/inference. | Every gold token and boundary has exactly one scored training position; coverage receipt is 100%; no unreported truncation. |
| Quarantine existing neural segmenter checkpoints of unknown preparation lineage. | Each promoted checkpoint names source manifest, code revision, window policy, seed and official evaluation receipt. |

### Production — build the production preparation boundary

| Action | Success criterion |
| --- | --- |
| Add typed `SourceArtifact`, `PreparationPolicy`, `PreparedRstDocument` and `PreparationReceipt` contracts. | Unknown fields fail; hashes and counts reconcile; serialization round-trips. |
| Make `prose_only` the default policy. | Code, raw HTML, tables, slide notes and picture descriptions do not enter primary RST text unless explicitly enabled. |
| Preserve side channels. | Excluded content retains source anchors, kind, reason and optional later analysis route. |
| Add anomaly detection. | Exact repeated notes/blocks are flagged; policy decides retain/deduplicate, and the receipt records it. |
| Route boundaries into parsing. | Adapters call `parse_document()` or `parse_hierarchical()` with canonical boundaries; post-hoc memberships remain traceability, not the only use of structure. |
| Support current-valid nested DocLang tables. | The specification’s nested-table example validates, ingests without destructive flattening and preserves recursive paths. |

### Model development B — replace legacy corpus conversion

| Action | Success criterion |
| --- | --- |
| Consolidate DMRST and UniRST preparation into one compiler. | One implementation and one versioned example contract; legacy readers are adapters only. |
| Pin corpus sources, licences and splits. | Every included document is in an authority manifest with source SHA-256; no partition hash overlaps. |
| Receipt tree repairs and relation mappings. | Every normalization has original value, new value, rule ID and count; a zero-change corpus proves byte/semantic preservation. |
| Fail on missing outputs. | Expected document count equals prepared document count; no `print` + `continue` on gold. |
| Remove unversioned `.edus`/`.lisp` authority. | Derived intermediates are optional caches keyed by compiler fingerprint; canonical examples remain reconstructible from source. |
| Establish tokenizer parity. | Gold and inference offsets use one canonical policy, with round-trip tests for punctuation, Unicode and whitespace. |

### Research — make eRST preparation efficient and truthful

| Action | Success criterion |
| --- | --- |
| Correct and validate dev positive counts. | Manifest counts equal streamed JSON and source gold-edge counts for every shard. |
| Replace denormalized complete-train JSON. | Complete train does not consume 35.48 GiB after selection; selected train remains reproducible from source + generator identity. |
| Normalize or stream dev candidates. | Development scoring stays document-bounded; candidate completeness and gold recall remain 100%; disk and wall time are measured. |
| Add amplification budgets. | Receipt reports source bytes, prepared bytes, candidate count, compression ratio, generation time and peak RSS. |
| Validate candidate strategy. | Any pruning is compared with the complete iterator and proves no gold loss before model evaluation. |

### Cross-system promotion — prove release quality without runtime coupling

Create a promotion suite that consumes independent evidence from each system. It must not make production execute training or research code. Coverage should include:

- current Docling JSON schema and all relevant content layers;
- current DocLang normative examples, including nested rich tables and threads;
- Markdown prose, HTML, code, tables and hostile/malformed inputs;
- multi-speaker VTT, repeated slide notes, dominant OCR PDF and long multi-section documents;
- pinned DISRPT 2025 RST/eRST EDU data with official scorer;
- GUM v12.1 primary RST and eRST secondary/signal gold;
- RST-DT only under its valid local licence and official split protocol; and
- round-trip source anchors and persisted analysis artifacts.

The gate should require:

- zero silent source/document/token/label loss;
- 100% expected-source and split-manifest reconciliation;
- 100% gold candidate recall before sampling;
- exact reproducibility from source hashes and one command;
- no cached result across a changed analytical fingerprint;
- official segmentation and Parseval/eRST metrics reported per corpus and track;
- real CPU/MPS latency, peak memory and disk amplification; and
- rendered/persisted output inspection, not only unit-test success.

## 8. Recommended implementation order

There is no single cross-repository sequence. Use these independent orders:

### Production runtime

1. Define the small shared source-anchor, preparation-receipt and release-manifest contracts without adding training dependencies to production.
2. Implement `prose_only` and migrate Markdown first because it exposes code/HTML/table policy clearly.
3. Migrate DocLang, including nested tables and validator-version cache identity.
4. Migrate Docling, adding repeated-note and content-origin evidence.
5. Wire all adapters to `parse_document()` / `parse_hierarchical()` and central `RstAnalysis`.
6. Benchmark and promote the production candidate independently of any retraining effort.

### Offline model development

1. Fix F-01 through F-03 before producing another Transformer segmentation checkpoint.
2. Establish official evaluation and lineage receipts, then retrain and compare the candidate with the currently released model.
3. Consolidate legacy corpus managers behind task-specific, governed compilers.
4. Produce a candidate release manifest; do not write directly into the production model store.

### Research/evaluation

1. Correct the false eRST development-positive manifest counts.
2. Compact or stream eRST candidates without changing their logical membership.
3. Measure candidate recall, storage amplification and scorer parity inside the research environment.

### Promotion

1. Verify the candidate model manifest, checkpoint hash, preparation authority and official metrics.
2. Copy the immutable release package into the production model store through an explicit promotion command.
3. Run production compatibility and representative document checks without installing or invoking the trainer or research harness.

Do not block production-ingest improvements on retraining, and do not treat a corrected training pipeline as proof that production document preparation is good. Each system must pass its own acceptance gates.

## 9. Actionable metrics dashboard

Metrics belong to the system that creates the evidence. They should not be collapsed into one generic ingest dashboard:

| System | Metric | Purpose |
| --- | --- | --- |
| Production | Source hash, schema/package revision and preparation-policy digest | Establish document-analysis and cache identity. |
| Production | Characters/tokens by content class | Show what entered the parser as authored RST discourse. |
| Production | Included/excluded/deduplicated/transformed spans | Make content policy auditable. |
| Production | Original-to-prepared coverage and anchor round-trip failures | Detect lossy document conversion. |
| Production | Ingest/parse time, peak RSS, prepared bytes | Measure effectiveness on one machine. |
| Model development | `sources_expected / observed / accepted / failed` | Detect missing or silently skipped corpus documents. |
| Model development | Gold labels expected/emitted/dropped | Stop segmentation or relation corruption. |
| Model development | Overflow windows and unscored positions | Prevent silent training/evaluation truncation. |
| Model development | Corpus documents and source hashes per split | Detect leakage. |
| Model development | Gold tree repairs by rule | Expose annotation mutation. |
| Research | Candidate count, positives, gold recall and amplification | Control eRST completeness and efficiency. |
| Research | Experiment cache identity, wall time and peak RSS | Keep disposable derivations reproducible and bounded. |
| Promotion | Checkpoint hash, task, source manifest, preparation fingerprint, code revision and official metrics | Prove exactly what model production is serving. |
| Promotion | Production compatibility result | Prove the released model accepts the production input contract without importing training code. |

## 10. Verification evidence from this review

### Current upstream/specification checks

- `docling-core`: installed 2.92.0; live PyPI latest 2.92.0.
- `doclang`: installed 0.7.3; live PyPI latest 0.7.3; validator signature and Saxon backend confirmed.
- Docling fixtures: 4/4 schema `1.10.0` fixtures loaded under current `DoclingDocument`.
- DocLang fixtures: 42 local / 42 upstream, exact current names and hashes at commit `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`.
- Normative DocLang nested-table specimen: upstream validation passed; project ingest rejected it.
- GUM: official latest release is [V12.1.0](https://github.com/amir-zeldes/gum/releases); local nested checkout is clean at exact tag/revision.

### Production runtime checks

- Real `gumrrg` CPU smoke: DMRST and UniRST basic/raw/presegmented routes passed.
- Real source adapters: representative Docling, current-valid namespaced DocLang and Markdown parses completed successfully with one reused model.
- Docling PPTX note audit: default inclusion added 6,900 characters, 6,890 of them from a five-times repeated block.

### Model-development checks

- Official DISRPT GUM dev audit: 2,790 declared EDU starts versus 24 produced by the project loader.
- This review did not establish that the currently served classical checkpoints were built through that Transformer preparation route. The P0 result applies to affected training lineage, not automatically to every production parse.

### Research/evaluation checks

- Fresh GUM corpus verification: 301 sources, all official partitions, succeeded; receipt reproduced exactly.
- Current eRST candidate cache: 16,676,352 records, 39.87 GiB; selected train 5,410 records / 13 MiB.
- Dev cache manifest: all 32 shards state zero positives; direct source/candidate checks demonstrate those claims are false.
- GUM RS4 signal-token audit: 301 documents / 44,509 signals; no out-of-range token references. Forty-two repeated token references were de-duplicated across ten documents by current conversion.

### Automated checks

```text
pixi run test
844 passed, 73 deselected in 16.29s

Focused format/cache/parser/segmenter suite
397 passed, 23 deselected in 4.39s

pixi run lint
All checks passed!

pixi run typecheck
0 errors, 0 warnings, 0 informations

pixi run smoke
PASS — all checks succeeded
```

The 73 slow tests were not run as one complete suite. Representative real-model and real-adapter routes were run separately, as listed above. This review did not train a new model; therefore it does not claim a fresh end-to-end model-quality score.

## 11. Complete-file review scope

The following repository files were read in full before their behavior was used in this report:

- Project authority: `AGENTS.md`, `CLAUDE.md`, `.claude/rules/architecture.md`, `.claude/rules/code-standards.md`, `.claude/rules/commands.md`, `.claude/rules/no-assumptions.md`, `pyproject.toml`.
- All Python files under `isanlp_rst/docling/`, `isanlp_rst/doclang/`, `isanlp_rst/markdown/` and `isanlp_rst/_rst_common/`.
- Central analysis: `isanlp_rst/parser.py`, `isanlp_rst/base_predictor.py`, `isanlp_rst/contracts/document.py`, `isanlp_rst/contracts/analysis.py`, `isanlp_rst/contracts/serialization.py`, `isanlp_rst/contracts/enums.py`.
- Classical corpus preparation: `isanlp_rst/dmrst_parser/data_manager.py`, `isanlp_rst/universal_parser/data_manager.py`, `isanlp_rst/dmrst_parser/src/corpus/data.py`, `common.py`, `binary_tree.py`, `span_node.py`, `utils_rs3.py`.
- Segmentation: `isanlp_rst/segmentation/dataset.py`, `isanlp_rst/segmentation/transformer_segmenter.py`, `scripts/fetch_disrpt_data.py`, `scripts/train_segmenter.py`, `tests/test_transformer_segmenter.py`.
- eRST: `isanlp_rst/erst/corpus.py`, `rs4.py`, `converter.py`, `candidates.py`, `sampling.py`, `scripts/train_erst_scorer.py`, `scripts/verify_gum_corpus_manifest.py`, `scripts/derive_gum_erst_relations.py`, `research_harness/erst/data.py`.
- Fixture and parity authority: all four `tests/fixtures/*/README.md` files and `scripts/verify_doclang_fixtures.py`.

Graph-based repository queries were used only to locate and cross-check call paths; every file relied on substantively was then read in full.

## Final assessment

The repository should not be described as one ingest system.

- **Production document ingest and serving** is operationally viable and well engineered in several respects. It needs explicit relevance policy, structure-aware parsing, complete format handling and stronger receipts to become world-class. Its real-model checks passed, and the defective Transformer training path does not by itself invalidate existing classical production analysis.
- **Offline model-development preparation** is not trustworthy enough for new model releases. The reviewed Transformer EDU route is critically invalid, and legacy corpus compilation cannot yet prove exact source-to-example lineage.
- **Research/evaluation preparation** contains the project’s strongest governance in the GUM/eRST authority, alongside an inefficient and partly untruthful candidate-cache evidence layer.
- **Model promotion** is the missing architectural seam. Until every served checkpoint has an immutable release manifest, the project cannot reliably translate a training finding into a scoped production impact statement.

The route to world-class is not to blend these systems into one larger framework. It is to keep production, model development and research operationally isolated; share only small typed semantic contracts; and require explicit, evidence-backed promotion of immutable model releases. That separation preserves the project’s strongest work while preventing experimental data machinery from becoming part of the production runtime.
