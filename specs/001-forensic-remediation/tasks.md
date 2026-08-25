# Tasks: isanlp-rst 4.0.0 Forensic Remediation

**Input**: All design documents in `specs/001-forensic-remediation/`

**Tests**: Mandatory. Tests are written before or with each implementation and must fail for the
target defect before the fix unless the test is a new capability with no prior executable boundary.

**Format**: `[ID] [P?] [Story] task — concrete success criterion`

## Phase 1: Governed baseline and dependency authority

- [x] T001 [US6] Preserve and read the complete `forensic_code_review_report.md`, root/project rules,
  and current `graphify-out/` before-state — reviewed commit and mutation statement remain intact.
- [x] T002 [US6] Create and validate `spec.md`, `plan.md`, `research.md`, `data-model.md`, contracts,
  experiment protocol, quickstart, checklist, and finding matrix — no placeholder or unresolved
  clarification remains.
- [x] T003 [US6] Revalidate PyPI/source/corpus/model revisions and licences in `research.md` without
  exposing `.env` values — each selected dependency/model has an immutable evidence anchor.
- [x] T004 [US6] Run the read-only Spec Kit consistency analysis over `spec.md`, `plan.md`, and
  `tasks.md`; resolve no artifact after analysis unless the result is clean or the user separately
  approves the reported remediation.
- [x] T005 [US6] Update `pyproject.toml` to package 4.0.0 and pins for torch 2.13.x, Transformers
  5.15.x, setuptools 84.x, Docling Core 2.92.x, DocLang 0.7.3, safetensors/Pydantic; regenerate
  `pixi.lock` through Pixi — locked runtime versions and hashes match `research.md`.
- [x] T006 [US5] Add explicit repository-root `.env` loading in `isanlp_rst/erst/environment.py` with
  `HF_TOKEN` canonical and `HUGGINGFACEHUB_API_TOKEN` fallback plus tests — canonical/fallback/missing/
  no-log cases pass.
- [x] T007 [US6] Add schema/version constants and release metadata in `isanlp_rst/_version.py` and
  format packages — installed package and each envelope report their required independent versions.

**Checkpoint**: Frozen artifacts are consistent; locked dependencies install; secrets remain ignored.

## Phase 2: Trustworthy format-native analyses

### Shared projection and public contracts

- [x] T008 [US1] Add failing nested-tree semantic tests in `tests/test_format_projections.py` for exact
  `text`, half-open `char_span`, one-based leaf-contiguous `edu_span`, and ancestor coverage across all
  formats.
- [x] T009 [US1] Extend `isanlp_rst/_rst_common/_flatten.py` with one immutable authoritative
  projection that computes leaf order/coverage once — degenerate/deep trees and nested fixtures pass.
- [x] T010 [US1] Add one shared projection-to-`RstAnalysis` conversion in
  `isanlp_rst/_rst_common/_projection.py`; export it from `_rst_common/__init__.py` — fabricated
  text/span construction is absent from format packages.
- [x] T011 [US1] Refactor Docling/DocLang/Markdown `mapper.py` and `schema.py` files to consume shared
  projection and require fields; set envelope versions 1.2/1.1/1.1 — all serializer/deserializer and
  exact-source-slice tests pass.
- [x] T012 [US1] Add downstream regression tests for `eval/parseval.py`, `erst` structural features,
  and `hierarchical/stitcher.py` using nested format projections — EDU counts/spans agree in every
  consumer.

### Provenance and cache identity

- [x] T013 [US1] Implement distribution-metadata package version resolution in
  `isanlp_rst/_rst_common/_runtime.py` with genuine-missing-only `unknown` — installed editable/wheel
  and missing-distribution tests pass.
- [x] T014 [US1] Replace hardcoded parser/format provenance in `contracts/document.py`, `parser.py`,
  and all `_entry.py` files; keep source revision separate — real parse reports 4.0.0.
- [x] T021 [US1] Add failing cache tests in `tests/test_result_cache.py` for equal bytes under different
  basenames, schema bumps, and behavior options.
- [x] T022 [US1] Extend `_rst_common/_cache.py` and `_identity.py` cache key with normalized source
  basename and envelope schema — pre-bump entries miss and filename provenance cannot cross-hit.
- [x] T023 [US1] Inspect persisted cache JSON from each format after hit/miss tests — stored provenance,
  model revision, package version, schema, and source basename match the request.

### DocLang current-spec compliance

- [x] T015 [US1] Add `isanlp_rst/doclang/eligibility.py` value model carrying every prose/table/list/
  code/formula/page/group/heading/layer option — harvester and boundaries accept the same instance.
- [x] T016 [US1] Replace all DocLang broad `itertext()` paths in `harvester.py` with one recursive
  metadata-aware exactly-once text/tail walker — nested description/summary/custom heads never enter
  body text while captions do.
- [x] T017 [US1] Route prose, list, table, code, formula and virtual-text harvest through the single
  walker/policy; add nested XML/CDATAs/tails tests — every eligible fragment occurs exactly once.
- [x] T018 [US1] Route document/page/group/heading/fallback boundary membership through the same
  eligibility policy in `boundaries.py` — exhaustive option-matrix membership equals harvest.
- [x] T019 [US1] Rename all 42 `tests/fixtures/doclang/*.dclg.xml` files to `.dclg` and update exact
  references without altering fixture contents — local and upstream basename sets are equal.
- [x] T020 [US1] Replace stale fixture-count prose/assertions with derived filesystem/API parity tests;
  validate all 42 under locked `doclang[schematron-saxon]` — no maintained numeric prose claim remains.

**Checkpoint**: G-FORMAT, G-DOCLANG, G-PROVENANCE, and G-CACHE pass with warnings as errors.

## Phase 3: Formally correct, evidence-backed eRST

### Signals and candidates

- [x] T024 [US2] Extend `contracts/analysis.py` and add `erst/signals.py` for typed signal type/subtype,
  overlapping token/character anchors, confidence, detector provenance, and compatible raw relations —
  Pydantic serialization/overlap tests pass.
- [x] T025 [US2] Implement the single complete `erst/candidates.py` generator over every ordered pair
  of distinct primary nodes using signals/tree/sentence/head/direction/distance/primary relation/
  learned compatibility — no gold input participates in membership.
- [x] T026 [US2] Replace candidate creation in `erst/dataset.py`, `english/erst/completer.py`, training,
  dev/test/test2, and inference with T025; stream batches without truncation — identity/property tests
  match across modes before training-only sampling.

### Corpus integrity and partitions

- [x] T027 [US3] Add Pydantic `CorpusLoadFailure`, `CorpusDocumentReceipt`, `CorpusLoadReceipt`, and
  `SplitManifest` in `contracts/erst.py` with forbidden extras and invariant validators.
- [x] T028 [US3] Implement `load_gum_erst_corpus_with_receipt(..., fail_on_error=True)` in
  `erst/corpus.py`; make the list API a fail-closed wrapper — every rejected path is named/sanitized.
- [x] T029 [US3] Parse GUM V12.1.0 `splits.md` authority and classify document/source licences from the
  pinned inventory — every corpus document has one official partition and licence class.
- [x] T030 [US3] Hash sources and assert document/source-hash disjointness before candidate flattening —
  duplicate or misplaced sources fail manifest validation.
- [x] T031 [US3] Restrict hard-negative sampling to train and retain complete candidates on dev/test/
  test2 — per-document candidate/edge/signal counts reconcile in receipts.
- [x] T032 [US3] Add fail-closed tests for missing corpus, malformed RS4, zero accepted docs, zero
  candidates, zero training steps, absent checkpoint, and first-epoch non-improvement — none produces
  a successful receipt.
- [x] T033 [US3] Add official partition and candidate identity integration tests over a private corpus
  manifest (corpus text excluded from Git) — train/dev/test/test2 IDs/hashes are disjoint and stable.

### Formal decoder, labels, scorer

- [x] T034 [US2] Add a formal synthetic conformance fixture/test matrix for cyclic, non-projective,
  concurrent, reverse-direction, primary-overlap, duplicate, self-loop, invented-node, and signal-
  sufficient/insufficient examples.
- [x] T035 [US2] Replace `erst/dag_decoder.py` with `erst/decoder.py` enforcing only the four current
  formal constraints; remove canonical DAG/distance/degree/ancestry/primary-overlap caps — T034 passes.
- [x] T036 [US2] Update imports/public exports/docs and delete dead `AcyclicDagDecoder` references —
  no stale class/config name remains in tracked authoritative files.
- [x] T037 [US2] Require fast tokenizers and request special-token masks/offset mappings in
  `erst/neural_scorer.py`; add exact padded/unpadded lexical boundary tests — SEP/pad is never selected.
- [x] T038 [US2] Reprobe every mandatory tokenizer on Python 3.14/MPS; convert and parity-test any
  viable SentencePiece artifact or emit incompatibility receipt — no warning suppression is used.
- [x] T039 [US2] Derive and persist the complete raw GUM eRST relation inventory from train; separate
  raw prediction from ontology adapter concept — both values survive serialization/scoring.
- [x] T040 [US2] Implement the repository-governed eRST scorer in `eval/erst_scorer.py`; report
  secondary Span/direction/Relation/Full with endpoint-yield mathematical tests — generic
  classification F1 cannot satisfy comparison gates.

### Secure completion bundle and parser capability

- [x] T041 [US5] Add `ErstCheckpointManifest` and safetensors bundle save/load in
  `erst/checkpoint.py`, including detector/scorer/graph/tokenizer/calibration/relations/decoder/test
  vector — every file is listed and hashed.
- [x] T042 [US5] Instantiate every component from bundled config and strict-load state dictionaries;
  reject raw backbone dirs, pickle files, missing/unlisted/mismatched members — adversarial bundle
  tests pass.
- [x] T043 [US5] Rename parser argument to `erst_scorer_checkpoint` in `parser.py` and format/API
  callers; an `erst_graph` request without a validated completion bundle raises typed capability error.
- [x] T044 [US5] Add save/reload and CPU/MPS parity tests plus a clean-process bundle verifier — graph,
  raw labels, signals, and calibrated outputs match tolerance with no training-data access.

**Checkpoint**: G-SIGNAL, G-ERST, G-CORPUS, G-SCORER, G-TRAIN, and G-BUNDLE pass.

## Phase 4: Eliminate all hidden quality debt

- [x] T045 [US6] Capture the current independent full-tree Pyright baseline and categorize all errors
  by file/root cause in a private work log; no suppression is introduced.
- [x] T046 [US6] Repair every error in `isanlp_rst/dmrst_parser/src/**` while preserving trained
  architecture/math; run focused tests after each dependency cluster — zero errors in that tree.
- [x] T047 [US6] Repair every error in `isanlp_rst/universal_parser/src/**`, remove both Pyright
  exclusions in `pyproject.toml`, and run full Pyright — zero errors/warnings across included product.
- [x] T048 [US6] Exhaustively locate and remove production `type: ignore`, `pyright: ignore`, blanket
  `noqa`, warning filters, and Transformers logger mutations by fixing causes — tracked production scan
  returns zero forbidden suppressions.
- [x] T049 [US6] Convert optional backends to typed lazy imports and fix originating LSTM/embedding/
  tokenizer warnings — `PYTHONWARNINGS=error` passes import, unit, integration, eRST, CPU, and MPS.
- [x] T050 [US6] Build a tracked Markdown manifest and classify only generated Spec Kit projections
  and the intentional syntax fixture as excluded — every other tracked `.md` is in lint scope.
- [x] T051 [US6] Fix authoritative Markdown in place and regenerate derived projections from authority;
  do not hand-edit generated copies — full intended markdownlint passes.
- [x] T052 [US6] Run Ruff, full Pyright, warnings-as-errors fast/full tests, and all five primary CPU/MPS
  smoke variants; repair the MPS pointer-attention warning with an algebraically equivalent reduction
  and the discovered left/right BiMPM operand defect — no primary topology/math regression or warning
  remains.

**Checkpoint**: G-STATIC, G-RUNTIME, and G-DOCS pass without false-green exclusions.

## Phase 5: Implement and execute the technology comparison

### Internal evaluation foundations

- [x] T053 [US3] Validate `ErstScorer` endpoint-yield Span, direction, Relation, and Full behavior,
  corpus document/hash disjointness, and complete dev candidates — frozen mathematical and corpus
  contract tests pass without any external-artifact dependency; executable test-path isolation
  remains part of T054-T055.
- [x] T054 [US3] Implement frozen Pydantic `ExperimentProtocol`, `ExperimentRunReceipt`,
  `StatisticalComparison`, `ChampionManifest`, `FinalEvaluationReceipt`, and `SelectionDecision`
  boundaries; remove the obsolete authority/blocker contracts, scripts, tests, and tracked no-run
  decisions — forbidden extras, hashes, positive-run invariants, and test isolation are executable.
- [x] T055 [US3] Implement the shared experiment runner and index — every run uses identical governed
  candidates/splits/scorer inputs, records checkpoint/prediction/resource evidence, and retains
  failures without granting or denying permission to implement another system.

### Mandatory technology systems

- [x] T056 [US4] Freeze the practical technology matrix from immutable model revisions, licences,
  Python-3.14/MPS/tokenizer compatibility, memory feasibility, and intended product role — no
  mandatory system is replaced or dropped and no external publication controls execution.
- [ ] T057 [US4] Implement structural-only, text-only, existing dual-encoder, ELECTRA cross-encoder,
  and signal-rule reference systems — identical candidates/splits/scorer/hardware receipts verified.
- [ ] T058 [US4] Implement ModernBERT-base/large signal-aware cross-encoders and screening runs for
  seeds 17/42/73 — both have complete receipts.
- [ ] T059 [US4] Implement XLM-R-large hierarchical adapter/contrastive system and screening runs —
  fast tokenizer/parity/licence/resource gates recorded.
- [ ] T060 [US4] Implement Qwen3-4B PEFT generative edge decoder with explicit no-edge outcome and
  screening runs — <=24 GB feasibility and MPS evidence recorded or explicit incompatibility receipt.
- [ ] T061 [US4] Implement edge-featured graph-attention fusion over strongest text representation and
  complete predicted primary tree; run screening — no candidate/tree truncation.
- [ ] T062 [US4] Advance every system within 0.02 dev Full to seeds 17/29/42/73/101 with dev-only
  threshold/temperature tuning and all eight required ablations — no test/test2 access in receipts.
- [ ] T063 [US4] Compute calibration, p50/p95 latency, OS RSS/MPS memory, longest-doc completion,
  CPU/MPS parity, and 10,000 paired document bootstrap with Holm correction — reproducible comparison
  artifacts hash to the protocol.
- [ ] T064 [US4] Freeze a dev-selected `ChampionManifest`, execute one-time untouched test/test2 only
  after successful screening, and emit the evidence-backed `SelectionDecision` — no missing
  implementation or no-run receipt may satisfy this task.

**Checkpoint**: G-COMPARISON passes with every mandatory implementation and run disposition complete;
a `no_selection` result is valid only after the comparison itself is complete.

## Phase 6: Exact release candidate and publication

- [ ] T065 [US6] Freeze the exact publication candidate commit and run one fresh locked install plus
  full dependency-aware validation ledger from `quickstart.md`; persist exact outputs and durations.
- [ ] T066 [US6] Build wheel/sdist in a fresh temporary directory and inspect every member/hash — no
  `.env`, credentials, corpus, model binaries, caches, or local experiment data is present.
- [ ] T067 [US6] Run `pip-audit` and secret scans over tracked files, build artifacts, and intended
  commits; name unauditable VCS dependencies — zero actionable vulnerability or secret disclosure.
- [ ] T068 [US6] Clean-install the wheel and exercise representative Docling/DocLang/Markdown/API/
  cache/five-parser/signal/candidate/eRST/bundle CPU/MPS paths; inspect persisted outputs.
- [ ] T069 [US5] If T064 selected a checkpoint, privately upload the verified bundle to
  `steve-allison-sensei/isanlp-rst-erst-v4`, pin returned immutable commit, clean-download/reverify;
  otherwise set canonical checkpoint null and perform no upload.
- [ ] T070 [US6] Align the installed Graphify package with the active skill version; update
  `forensic_code_review_report.md` with closure rows for every F/N defect, exact commands/results/
  hashes and CUDA unverified; regenerate a directed graph and require both raw-extraction and
  persisted-graph diagnostics to show no missing/dangling/self-loop or lossy collapsed relation — no
  version drift or filtered false green remains.
- [ ] T071 [US6] Create logical contract/eRST/quality/release commits, stage all intended artifacts,
  push `origin codex/spec-kit-adoption`, and verify final clean status plus pushed commit IDs.

**Final acceptance**: All applicable gates pass, every non-passing comparison/selection outcome is
explicit, Git is clean and pushed, and there is no undisclosed failed or skipped check.

## Dependencies and execution order

```text
T001-T004
  -> T005-T007
  -> format stream T008-T023
  -> eRST stream T024-T044
  -> quality stream T045-T052
  -> internal scorer/protocol/runner T053-T055
  -> technology systems and comparison T056-T064
  -> release T065-T071
```

- T009 blocks T010-T012; T015 blocks T016-T018; T021 blocks T022-T023.
- T024-T026 block corpus candidate counts and all model work.
- T027-T033 and T034-T040 both block checkpoint/training/research.
- T041-T044 block production eRST and any publication.
- T053 validates internal metrics; T054-T055 establish shared execution evidence. No result in these
  tasks blocks implementing T056-T061.
- T064 determines whether T069 uploads or records no selection; it never excuses missing comparison
  work.
- T065-T070 must target the same candidate; any source change invalidates the run and requires one new
  fresh complete validation.

## Implementation strategy

Work sequentially on the single local machine. Use focused dependency-aware checks inside phases and
one full release-candidate run. Mark a task `[x]` only after its concrete success criterion has been
observed. A failed mandatory experiment may close only with a local incompatibility receipt after its
implementation and attempted execution; a no-run or external-authority diagnosis never counts.
