# Implementation Plan: isanlp-rst 4.0.0 Forensic Remediation

**Branch**: `codex/spec-kit-adoption` | **Date**: 2026-08-24 | **Spec**: [spec.md](spec.md)

**Input**: Approved feature specification at `specs/001-forensic-remediation/spec.md`

## Summary

Build a truthful 4.0.0 release in four governed implementation streams: shared format contracts;
formally correct and receipt-backed eRST; complete static/runtime quality; and executable technology
comparison, artifact, and release selection. Format work centralizes leaf/span projection and DocLang eligibility.
eRST work replaces heuristic/gold-dependent candidate generation and DAG decoding with a single
signal-licensed formal pipeline, governed partitions/scoring, Pydantic evidence boundaries, and
safetensors bundles. Technology work validates the repository scorer and reference systems, then
evaluates every mandatory architecture under one immutable internal protocol. Release work validates
the exact candidate on a fresh environment and names no canonical checkpoint unless all gates pass.

## Technical Context

**Language/Version**: Python 3.14.x; no `from __future__ import annotations`

**Primary Dependencies**: PyTorch 2.13.x, Transformers 5.15.x, safetensors 0.8.x, Pydantic 2.x,
Docling Core 2.92.x, DocLang 0.7.x, lxml, Hugging Face Hub, NetworkX, NumPy

**Storage**: Local immutable JSON manifests/receipts and safetensors bundles; private Hugging Face
model repository only for a selected checkpoint; private local corpus/experiment workspace excluded
from Git and package archives

**Testing**: pytest through locked Pixi, Pyright full tree, Ruff, markdownlint-cli2, repository-owned
eRST scorer contract tests, paired document bootstrap, pip-audit, secret scan, build/archive
inspection, CPU/MPS smokes

**Target Platform**: One Apple M5 Max machine with 48 GB unified memory; CPU and MPS verified; CUDA
explicitly unverified

**Project Type**: Python library and local research/training CLI

**Performance Goals**: No candidate truncation; longest test document completes without OOM; selected
model <=24 GB peak RSS; MPS p95 <=2x the reference cross-encoder; tied systems within 0.005 Full choose smaller
and faster

**Constraints**: No secrets in logs/artifacts; no public corpus/weights; no unsafe pickle checkpoint;
no test-driven tuning; no type/warning suppression; primary parser inference mathematics unchanged

**Scale/Scope**: Entire tracked Python tree, all tracked authoritative Markdown, three format-native
entry points, five primary parser variants, complete licensed GUM eRST candidate space, ten mandatory
technology configurations

## Constitution Check

*GATE: Must pass before Phase 0 research and again after design.*

| Principle | Pre-research evidence | Post-design disposition |
|---|---|---|
| Evidence before claims | Immutable report/Graphify before-state and finding matrix | Every task ends in checkable evidence; checkpoint selection is fail-closed |
| Python 3.14, modern typing | Full-tree repair is mandatory; no suppressions | Contracts are Pydantic at production boundaries; internal candidates remain immutable dataclasses |
| Solo local scale | One Apple machine, private artifacts, no team/enterprise systems | Direct local manifests and one private HF repo; no services or workflow bureaucracy |
| Current Docling/DocLang | 2026-08-24 upstream/PyPI evidence in `research.md` | Pins and conformance tests use current minors and immutable upstream commits |
| Locked Pixi | `pixi.toml` authority is `pyproject.toml`; lock exists | Every Python/test/build/audit command runs through `/Users/steveallison/.pixi/bin/pixi run --locked` |
| Secrets | `.env` ignored; names/scopes only, never values | Explicit root path loading, HF canonical/fallback key names, tracked/build scans |
| No trained-math drift | Primary parser variants are locked | Research additions are isolated under eRST; five primary smokes gate release |
| Full scope and no false green | All original/new defects enumerated | No exclusion, warning filter, truncation, skipped mandatory system, external implementation blocker, or hidden failed gate |

**Gate result**: PASS. No constitutional violation is justified or carried.

## Project Structure

### Documentation for this feature

```text
specs/001-forensic-remediation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── experiment-protocol.md
├── finding-evidence-matrix.md
├── quickstart.md
├── contracts/
│   ├── format-projection.md
│   ├── corpus-and-experiment.md
│   └── checkpoint-bundle.md
├── checklists/requirements.md
└── tasks.md
```

### Source and evidence paths

```text
isanlp_rst/
├── _rst_common/                 # shared projection, cache, version, identity
├── contracts/                   # public Pydantic analyses, signals, receipts
├── docling/                     # Docling loader/harvest/boundary/map/schema
├── doclang/                     # metadata-aware walker + one eligibility policy
├── markdown/                    # Markdown loader/harvest/boundary/map/schema
├── erst/                        # candidates, signals, decoder, scorer, corpus, bundle
├── english/erst/                # production completion integration
├── eval/                        # repository-owned eRST scorer + statistics
├── dmrst_parser/src/            # full type repair, unchanged trained mathematics
├── universal_parser/src/        # full type repair, unchanged trained mathematics
└── parser.py                    # explicit eRST checkpoint capability boundary
scripts/
├── train_erst_scorer.py
├── run_erst_experiments.py
├── evaluate_erst_champion.py
├── validate_erst_bundle.py
└── verify_release_candidate.py
tests/
├── fixtures/doclang/*.dclg
├── fixtures/erst/
└── test_*                       # unit, contract, integration, warning, CPU/MPS
experiments/                     # ignored private run data; never packaged
forensic_code_review_report.md   # immutable before-state, later closure ledger
graphify-out/                    # immutable before-state, regenerated at release
```

**Structure Decision**: Preserve the single-package repository. Shared truths live in
`_rst_common`/`contracts`; format adapters remain thin; research and production eRST use the same
candidate/decoder/bundle contracts; scripts orchestrate, never reimplement domain rules.

## Dependency-ordered implementation

### Phase 0 — Freeze authority and research protocol

**Files**: this Spec Kit directory only.

1. Record current package, source, corpus, model, licence, and hash evidence.
2. Freeze Pydantic data boundaries and exact wire/bundle contracts.
3. Freeze the experiment protocol before test data is reachable.
4. Map every finding/new defect to tasks, regression evidence, and release gates.

**Success criterion**: Spec Kit analysis reports no critical ambiguity or inconsistency; every defect
has an implementation task, regression test, and fail-closed gate before source changes.

### Phase 1 — Correct shared format contracts and provenance

**Files**: `pyproject.toml`, `pixi.lock`, `_rst_common/_flatten.py`, `_rst_common/_cache.py`,
`_rst_common/_identity.py`, `_rst_common/_runtime.py`, `contracts/analysis.py`, `contracts/document.py`,
all three format `schema.py`/`mapper.py`/`_entry.py`, DocLang loader/harvester/boundaries, format tests,
and 42 fixture paths/docs.

1. Pin 4.0.0 and current dependency minors; regenerate the Pixi lock.
2. Add one authoritative projection carrying leaf order, coverage, exact text, and real spans.
3. Route all format mappers and `RstAnalysis` conversion through it; bump wire schemas.
4. Implement one DocLang metadata-aware text/tail walker and one option-complete eligibility policy.
5. Resolve package version from distribution metadata and include normalized basename/schema in cache
   identity.
6. Rename fixtures and derive upstream/count parity.

**Success criterion**: Focused format, Parseval, cache, provenance, and DocLang conformance suites pass
with warnings as errors; old schema cache entries miss and source provenance cannot cross filenames.

### Phase 2 — Make eRST formally correct and evidence-backed

**Files**: `contracts/analysis.py`, new `contracts/erst.py`, `erst/dataset.py`, new signal/candidate/
decoder/corpus/bundle modules, `eval/erst_scorer.py`, `english/erst/completer.py`, `parser.py`, training
scripts, and eRST tests/fixtures.

1. Add Pydantic corpus, split, protocol, run, checkpoint, and selection boundaries.
2. Replace phrase heuristics with typed overlapping signals and detector provenance.
3. Build the single complete signal-licensed candidate generator; remove gold-dependent existence and
   all non-formal caps/filters.
4. Replace `AcyclicDagDecoder` with formal constraint decoding.
5. Load official GUM document partitions fail-closed with hashes/licences/disjointness evidence.
6. Preserve raw relation labels plus ontology projection; integrate repository-owned scorer metrics.
7. Implement complete safetensors bundle, strict reload, parser capability error, and parity validation.

**Success criterion**: Synthetic formal conformance, corpus-failure/disjointness, complete-candidate,
raw-label, scorer, bundle-hash/reload, and parser capability tests all pass on CPU and MPS.

### Phase 3 — Eliminate hidden quality debt

**Files**: all 36 previously excluded parser modules plus any suppression/warning/optional-import/
Markdown authority identified exhaustively; `pyproject.toml`; tests and docs.

1. Remove Pyright exclusions and repair all errors without changing trained inference mathematics.
2. Exhaustively remove production type/noqa/warning/logger suppressions by correcting causes.
3. Convert optional backends to typed lazy imports and enforce verified fast tokenizers.
4. Expand Markdown lint to all tracked authoritative files and fix/regenerate in authority order.
5. Make unit, integration, import, CPU, and MPS paths pass with `PYTHONWARNINGS=error`.

**Success criterion**: Zero full-tree type errors, zero production suppressions, zero warnings, full
tracked-authoritative Markdown coverage, and all five primary parser variants retain outputs/smokes.

### Phase 4 — Establish executable internal comparison baselines

**Files**: experiment scripts/configs and ignored private experiment outputs; checked-in only hashed
protocol/run summaries that contain no corpus text or model weights.

1. Materialize GUM V12.1.0 document splits and validate the repository-owned scorer against frozen
   contract fixtures.
2. Implement the missing Pydantic experiment protocol, run, statistics, champion, and final-evaluation
   boundaries plus the shared runner.
3. Run the existing dual-encoder, structural-only, text-only, signal-rule, and ELECTRA reference
   systems on identical train/dev inputs and seeds.
4. Persist checkpoints, manifests, predictions, scorer output, runtime profile, and variance; a failed
   reference run remains a visible local failure but does not block implementing other systems.

**Success criterion**: A clean checkout validates scorer behavior and produces complete reference-run
receipts. Every mandatory architecture remains implementable regardless of any one reference result.

### Phase 5 — Research-grade architecture selection

**Files**: eRST model/config modules, experiment scripts, frozen manifests, private artifacts.

1. Implement and run every mandatory system using identical inputs and screening seeds.
2. Advance every system within 0.02 dev Full; tune only on dev with five finalist seeds.
3. Run required ablations, calibration, CPU/MPS parity, memory/latency, 10,000 paired bootstrap, and
   Holm comparisons.
4. Freeze champion hash before the one-time untouched test/test2 evaluation.
5. Evaluate all selection thresholds and emit `selected` or `no-selection`.

**Success criterion**: Every mandatory system has a complete success/incompatibility receipt; any
canonical selection satisfies every threshold. Otherwise the comparison closes without a canonical
checkpoint and without treating missing implementation as an acceptable outcome.

### Phase 6 — Release verification and publication

**Files**: exact release source, report closure ledger, refreshed Graphify outputs, release metadata.

1. Run one fresh complete validation against the exact candidate after focused development checks.
2. Inspect representative persisted outputs, package archives, clean install, and private bundle reload.
3. Run audit and secret scans; name VCS unauditability and CUDA non-verification explicitly.
4. Align the Graphify package and skill versions, update every closure row, regenerate the directed
   graph, require clean raw and persisted integrity diagnostics, and record artifact hashes.
5. Commit logical contract/eRST/quality/release groups, stage all intended artifacts, push branch.

**Success criterion**: Clean Git status, pushed commit IDs, no undisclosed failed/skipped gate, clean
archive/install evidence, and immutable private model revision only if selection passed.

## Verification strategy

- Development uses focused tests selected by changed dependency boundaries.
- Each phase has a persisted evidence receipt; exit code alone is insufficient.
- The exact publication candidate receives one fresh full run: locked install; full tests; full
  warnings-as-errors; all five CPU/MPS smokes; format/API/cache/signal/candidate/eRST/bundle paths;
  Docling/DocLang conformance; Pyright; Ruff; Markdown; build; audit; secret scan; archive inspection;
  clean install; Graphify regeneration/health; Git/HF state.
- CUDA is not run on this host and is reported unverified.

## Complexity Tracking

The earlier external-evidence gate violated scope fidelity by preventing mandatory implementations
from starting. This corrected plan removes that gate. The model experiment matrix is required by the
approved scope, not an abstraction or scaling choice; private Hugging Face storage is the minimal
reproducible channel for a selected bundle.
