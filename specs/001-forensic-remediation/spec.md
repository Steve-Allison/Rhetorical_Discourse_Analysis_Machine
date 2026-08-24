# Feature Specification: isanlp-rst 4.0.0 Forensic Remediation

**Feature Branch**: `codex/spec-kit-adoption`

**Created**: 2026-08-24

**Status**: Approved for implementation

**Input**: User-approved replacement plan, “isanlp-rst 4.0.0 World-Class Forensic Remediation”

## Scope authority

This specification replaces every earlier remediation plan. The immutable before-state is
`forensic_code_review_report.md` plus the existing `graphify-out/` evidence at reviewed commit
`4ae828d44cbd3d3b80edbf7e7fcacc0fa13f08e0`. The implementation MUST close all twelve numbered
findings and every additional defect listed in FR-001. No item may be narrowed, deferred, or
declared out of scope without a new user decision.

Promotion is fail-closed. Release 4.0.0 may ship corrected interfaces and reproduced baseline
capability without a new canonical eRST checkpoint. It MUST NOT publish a checkpoint or SOTA claim
unless every promotion gate in FR-024 passes.

## User Scenarios & Testing

### User Story 1 - Trustworthy format-native analyses (Priority: P1)

As a local parser user, I need Docling, DocLang, and Markdown results to carry exact text and real
coordinates so that evaluation, caching, provenance, and downstream graph logic are truthful.

**Why this priority**: Current wire objects validate structurally while carrying fabricated content
and spans, which invalidates downstream evidence.

**Independent Test**: Parse nested fixtures through all three entry points, serialize and reload the
results, and prove exact source-text round trips, contiguous EDU ordinals, ancestor coverage, option
parity, correct provenance, and filename-sensitive cache behavior.

**Acceptance Scenarios**:

1. **Given** a three-EDU nested tree, **When** it is projected to any supported format, **Then** every
   EDU and relation has required text, a half-open source character span, and a one-based inclusive
   EDU span derived from descendant leaves.
2. **Given** valid DocLang 0.7 containing metadata heads at nested depths, **When** body content is
   harvested, **Then** metadata is excluded and eligible text and tails occur exactly once.
3. **Given** equal bytes under distinct source basenames, **When** caching is enabled, **Then** the
   second source cannot inherit the first source's provenance.

---

### User Story 2 - Formally correct eRST completion (Priority: P1)

As a discourse researcher, I need eRST candidate generation and decoding to implement the published
formalism so that valid cyclic, non-projective, concurrent, reverse-direction, and primary-overlap
secondary edges are not silently forbidden.

**Why this priority**: The current decoder and candidate filters contradict the formal task.

**Independent Test**: Run a synthetic conformance matrix whose valid examples vary cycle,
projectivity, direction, primary overlap, concurrency, and signal licensing; compare accepted graphs
to the formal constraints.

**Acceptance Scenarios**:

1. **Given** two distinct primary-tree nodes and a sufficient licensed signal, **When** a secondary
   edge is proposed, **Then** it is eligible regardless of primary connectivity, cycle creation,
   non-projectivity, or an existing reverse edge.
2. **Given** no sufficient signal, a self-loop, an invented node, or an exact directed duplicate,
   **When** decoding runs, **Then** the edge is rejected with typed evidence.
3. **Given** the same document and configuration, **When** candidates are generated for train, dev,
   test, test2, or inference, **Then** the candidate set is identical before training-only negative
   sampling and no gold label controls candidate existence.

---

### User Story 3 - Reproducible corpus and benchmark evidence (Priority: P1)

As a solo model developer, I need document-level corpus receipts and a reproduced published baseline
before architecture comparisons so that performance evidence has no split leakage or silent loss.

**Why this priority**: A model comparison is invalid until corpus, scorer, and baseline parity are
established.

**Independent Test**: From a clean checkout and private corpus location, reconstruct hashed official
splits, run five baseline seeds, and reproduce the published gold/gold metrics within the declared
tolerance using the official scorer.

**Acceptance Scenarios**:

1. **Given** GUM V12.1.0 source data, **When** the loader runs, **Then** every document is assigned by
   the official document partition and source hashes are disjoint across partitions.
2. **Given** a malformed, missing, or empty corpus input, **When** loading or training runs, **Then**
   the process fails with a Pydantic receipt and named failures rather than continuing.
3. **Given** the reproduced ELECTRA system, **When** five gold/gold seeds are scored, **Then** mean
   Span, Relation, and Full are each within 0.02 absolute of 0.389, 0.205, and 0.184.

---

### User Story 4 - Evidence-based architecture promotion (Priority: P2)

As the package owner, I need all mandatory systems evaluated under one frozen protocol so that a
canonical checkpoint is selected only for a statistically and operationally superior system.

**Why this priority**: “Best model” is a measured outcome, not a model-name preference.

**Independent Test**: Validate immutable protocol hashes, identical candidate/split/scorer inputs,
seed coverage, ablations, paired statistics, one-time final evaluation, calibration, CPU/MPS parity,
memory, and latency evidence.

**Acceptance Scenarios**:

1. **Given** the frozen dev protocol, **When** screening completes, **Then** all nine mandatory systems
   have success or explicit incompatibility receipts and none is silently dropped.
2. **Given** a candidate champion, **When** promotion gates are evaluated, **Then** publication occurs
   only if every correctness, significance, test, calibration, memory, latency, and parity threshold
   passes.
3. **Given** no qualifying champion, **When** 4.0.0 is released, **Then** no canonical checkpoint or
   SOTA claim is emitted.

---

### User Story 5 - Secure and reloadable completion bundles (Priority: P2)

As a local inference user, I need a self-contained safe checkpoint so that a clean machine can verify
and reproduce eRST completion without training data or unsafe pickle deserialization.

**Why this priority**: The existing training artifact is not a loadable parser capability.

**Independent Test**: Save a completion bundle, validate all hashes, reload every state dictionary
strictly on a clean process, download by immutable private revision, and compare decoded graphs.

**Acceptance Scenarios**:

1. **Given** an `erst_graph` request without a validated completion bundle, **When** parsing begins,
   **Then** a precise capability error is raised.
2. **Given** a complete bundle, **When** it is reloaded on CPU and MPS, **Then** model outputs and
   decoded graphs match the pre-save evidence within declared floating-point tolerance.
3. **Given** repository-root `.env`, **When** private download is required, **Then** `HF_TOKEN` is used
   with `HUGGINGFACEHUB_API_TOKEN` fallback without logging or committing either value.

---

### User Story 6 - Honest 4.0.0 release candidate (Priority: P2)

As the maintainer, I need every production file and release artifact to satisfy the declared quality
bar so that green checks represent the complete product.

**Why this priority**: Exclusions, suppressions, warnings, incomplete lint scope, and unsafe build
contents currently create false-green evidence.

**Independent Test**: Run the exact release-candidate validation ledger from a fresh environment,
inspect outputs and archives, regenerate Graphify, secret-scan, clean-install, and verify Git/HF
publication state.

**Acceptance Scenarios**:

1. **Given** the full production tree, **When** Pyright, Ruff, Markdown lint, tests, and warnings-as-
   errors run, **Then** there are zero type errors, zero production suppressions, and zero warnings.
2. **Given** built wheel and sdist, **When** archive members are inspected, **Then** secrets, `.env`,
   corpus files, checkpoints, caches, and local experiments are absent.
3. **Given** all release gates passed or truthfully failed, **When** publication closes, **Then** the
   forensic report contains a closure row and exact evidence for every finding and new defect.

### Edge Cases

- Degenerate one-EDU documents and deeply skewed trees MUST preserve valid spans without recursion
  failure or fabricated relations.
- Unicode, combining characters, XML tails, nested metadata heads, virtual text, CDATA, tables,
  lists, code, formulae, pages, groups, headings, and threaded DocLang fragments MUST not duplicate
  or lose eligible content.
- Result cache entries from pre-bump schemas MUST miss; corrupt cache files MUST fail safely without
  returning stale provenance.
- Secondary signals may overlap and may license multiple concurrent relations; identical directed
  node pairs may not be duplicated.
- No candidates, zero training steps, missing corpus, malformed files, missing checkpoint members,
  bad hashes, incompatible configs, and unavailable accelerators MUST be explicit failures.
- Test and test2 MUST be inaccessible to training/tuning code before a champion-manifest hash is
  frozen.
- CUDA absence MUST be reported as unverified; CPU or MPS results cannot imply CUDA behavior.

## Requirements

### Functional Requirements

- **FR-001**: The remediation MUST close F-01 through F-12 and the additional defects: cache keys
  omit source basename; candidate generators diverge between training and inference; gold labels
  influence negative candidate creation; candidate/distance/degree/DAG restrictions violate eRST;
  no-candidate and zero-step runs can appear successful; `model.pt` is not a parser-loadable
  checkpoint; absent first-epoch improvement can yield no checkpoint; eRST requests can instantiate
  random heads; signal licensing is incomplete; and coarse labels lose the raw GUM inventory.
- **FR-002**: `forensic_code_review_report.md` and the existing `graphify-out/` directory MUST remain
  the immutable before-state until the final closure update and regeneration step.
- **FR-003**: The package version MUST be 4.0.0; release dependencies MUST pin PyTorch 2.13.x,
  Transformers 5.15.x, setuptools 84.x, Docling Core 2.92.x, DocLang 0.7.x, and immutable model/corpus
  revisions recorded in `research.md`.
- **FR-004**: Environment loading MUST resolve the repository-root `.env` explicitly. `HF_TOKEN` is
  canonical and `HUGGINGFACEHUB_API_TOKEN` is fallback. Secret values MUST never enter logs, tracked
  files, manifests, reports, artifacts, or model repositories.
- **FR-005**: All three format wire schemas MUST require `text`, half-open `char_span`, and one-based
  inclusive `edu_span` on serialized EDUs and relations; schema versions MUST become Docling 1.2,
  DocLang 1.1, and Markdown 1.1.
- **FR-006**: `_rst_common/_flatten.py` MUST compute leaf order and ancestor coverage once, all format
  mappers MUST consume it, and one shared conversion MUST produce `RstAnalysis` without fabricated
  fields.
- **FR-007**: DocLang harvesting MUST implement one metadata-aware walker and one eligibility policy
  shared by harvest and every boundary detector, including every table/list/code/formula/page/group/
  heading option. Metadata heads apply at any depth.
- **FR-008**: All 42 local DocLang fixtures MUST use `.dclg`; fixture counts and upstream parity MUST
  be derived from the filesystem/API rather than maintained in prose.
- **FR-009**: Software version MUST resolve from installed `isanlp-rst` distribution metadata, using
  `"unknown"` only when metadata does not exist. Source revision and semantic version MUST remain
  separate. Cache identity MUST include normalized source basename and schema version.
- **FR-010**: Signals MUST preserve type, subtype, overlapping token anchors, confidence, and detector
  provenance and cover the eRST-permitted orphan discourse markers and morphosyntactic triggers.
- **FR-011**: A single signal-licensed candidate generator MUST serve training, dev, test, test2, and
  inference. It MUST consider any ordered pair of distinct primary nodes and MUST NOT reject cycles,
  non-projectivity, reverse direction, primary overlap, concurrent relations, or distance/degree.
- **FR-012**: Canonical decoding MUST enforce only sufficient signal, no self-loop, no invented node,
  and no exact duplicate for the same directed node pair.
- **FR-013**: Corpus boundaries MUST include Pydantic `CorpusLoadReceipt`, `CorpusLoadFailure`, and
  split-manifest models. `load_gum_erst_corpus_with_receipt(..., fail_on_error=True)` MUST be primary;
  the list API MUST be a fail-closed wrapper.
- **FR-014**: GUM V12.1.0 at commit `22fdf87f9c71c96bcc771461d06e689b1f90020d` MUST use the official
  train/dev/test/test2 document partitions, record per-source SHA-256/licence/count evidence, and
  prove document/source-hash disjointness. Hard negatives are training-only; evaluation uses the
  complete licensed candidate space.
- **FR-015**: Training and output MUST preserve raw GUM eRST relations and separately derive the
  canonical ontology concept. Evaluation MUST use the official eRST secondary Span, direction/
  Nuclearity, Relation, and Full metrics.
- **FR-016**: The signal-marked ELECTRA published baseline MUST be reproduced for five seeds on the
  pinned corpus/scorer. Comparisons MUST stop if mean gold/gold Span 0.389, Relation 0.205, and Full
  0.184 are not each reproduced within 0.02 absolute.
- **FR-017**: A frozen Pydantic `ExperimentProtocol` MUST control candidate sets, splits, scorer,
  seeds, inputs, hardware evidence, threshold/calibration tuning, ablations, test isolation, and
  champion hash. Training code MUST be unable to load test/test2.
- **FR-018**: All nine mandatory systems in the approved plan MUST be evaluated or carry a verified
  incompatibility receipt. Screening seeds are 17/42/73; finalists within 0.02 dev Full receive seeds
  17/29/42/73/101 and full tuning.
- **FR-019**: Comparisons MUST use 10,000 document-level paired bootstrap resamples with Holm
  correction, report gold/gold and predicted/predicted settings, and include all specified ablations.
- **FR-020**: An eRST bundle MUST use safetensors and a Pydantic `ErstCheckpointManifest` covering
  every component, config, immutable revision, file hash, feature schema, corpus/split hash, protocol,
  metric, licence, and provenance field. Model construction MUST use bundled config and
  `load_state_dict(..., strict=True)`.
- **FR-021**: The parser argument MUST be `erst_scorer_checkpoint`; raw backbone directories MUST be
  invalid, and `erst_graph` without a validated completion bundle MUST raise an explicit error.
- **FR-022**: A promoted bundle MUST pass save/reload parity and clean-machine private download from
  `steve-allison-sensei/isanlp-rst-erst-v4` at an immutable commit before release metadata is pinned.
- **FR-023**: Full-tree Pyright MUST report zero errors with no production exclusions, suppressions,
  blanket `noqa`, warning filters, or Transformers logger mutation. Optional imports MUST be typed and
  lazy; runtime tokenizers MUST be fast and parity tested. `PYTHONWARNINGS=error` MUST pass unit,
  integration, import, CPU, and MPS paths. Markdown lint MUST cover all tracked Markdown except
  generated Spec Kit projections and the intentional syntax fixture.
- **FR-024**: A canonical checkpoint may be promoted only if it beats the strongest reproduced
  baseline by at least 0.02 mean dev Full; has Holm-corrected paired-bootstrap lower CI above zero;
  beats untouched test Full by at least 0.01; regresses no test Span/direction/Relation metric by more
  than 0.005; achieves ECE <=0.05 and non-worse Brier; processes the longest test document without
  truncation/OOM; stays at or below 24 GB peak RSS on the 48 GB Apple M5 Max; has MPS p95 latency at
  most 2x ELECTRA; selects faster/smaller within a 0.005 tie; and produces equivalent CPU/MPS graphs.
- **FR-025**: Release verification MUST include all tests and representative paths, Docling/DocLang
  conformance, full Pyright, Ruff, all tracked Markdown, build, dependency audit, secret scan,
  Graphify regeneration, persisted-output inspection, clean archive inspection, clean install, CPU,
  and MPS. CUDA MUST be named unverified.
- **FR-026**: The forensic report MUST gain a closure row for every original and new defect with exact
  commands, outputs, hashes, and unverified platforms. Logical contract, eRST, quality, and release
  commits MUST be pushed to `origin/codex/spec-kit-adoption`; final Git status MUST be clean.

### Key Entities

- **AuthoritativeProjection**: Shared flattened tree evidence containing node identity, leaf ordinal,
  ancestor leaf coverage, source text, and character coordinates.
- **DiscourseSignal**: Typed signal with span anchors, type/subtype, confidence, and detector provenance.
- **SecondaryEdgeCandidate**: Immutable internal candidate built without gold-dependent existence.
- **CorpusLoadReceipt / CorpusLoadFailure**: Validated corpus coverage and named failure evidence.
- **SplitManifest**: Immutable document/source hash partition authority.
- **ExperimentProtocol**: Frozen comparison inputs, seeds, gates, and isolation rules.
- **ExperimentRunReceipt**: Hashed configuration, runtime, predictions, scores, and failure evidence.
- **ErstCheckpointManifest**: Complete reloadable bundle authority and integrity record.
- **PromotionDecision**: Fail-closed evaluation of every release/promotion threshold.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every nested format fixture round-trips exact source text and real spans; Parseval document
  EDU count equals actual leaf count for all three formats.
- **SC-002**: Current upstream Docling and all 42 upstream-matched DocLang valid fixtures conform under
  the pinned release, with harvest/boundary option parity tests passing.
- **SC-003**: Synthetic eRST conformance accepts all and only the formally licensed edge cases; train,
  dev, test, test2, and inference candidate identity tests pass.
- **SC-004**: Corpus receipts report zero silent losses and zero cross-partition document/hash overlap.
- **SC-005**: The five-seed ELECTRA baseline meets all three ±0.02 reproduction bounds before any
  architecture comparison is accepted.
- **SC-006**: All mandatory systems have reproducible run receipts; promotion either passes every
  FR-024 gate or produces an explicit no-promotion decision with no SOTA claim.
- **SC-007**: A promoted checkpoint, if any, downloads privately at a pinned immutable revision,
  verifies every hash, and reproduces its recorded graph on CPU and MPS without training data.
- **SC-008**: Full-tree Pyright, Ruff, tracked-Markdown lint, warnings-as-errors, unit/integration tests,
  package build, audit, secret scan, clean install, all five parser smokes, format/API/cache/eRST paths,
  and Graphify health checks pass on the exact release candidate with no undisclosed skip.
- **SC-009**: Wheel and sdist inspection finds zero credentials, `.env`, corpus data, model weights,
  caches, or local experiment artifacts.
- **SC-010**: Final report identifies pushed commit IDs, any immutable model revision, exact commands
  and outputs, clean Git status, and CUDA as unverified on this Apple Silicon host.

## Locked Assumptions

- Release boundary is 4.0.0 and all three wire-schema bumps are mandatory.
- There is no compatible legacy eRST checkpoint to preserve.
- The five primary parser variants and their trained inference mathematics remain unchanged.
- GUM V12.1.0 is the current release at execution-time verification on 2026-08-24.
- CUDA is unavailable on the target Apple Silicon machine and remains unverified.
- `.env` remains ignored and only operation-relevant credentials are used.
- GUM corpus data and derived weights remain private because underlying text licences are mixed and
  include non-commercial restrictions.
