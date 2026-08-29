# Implementation Plan: Clean Production Codeline Separation

**Branch**: `codex/spec-kit-adoption` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Make the built `isanlp_rst` distribution the sole production authority and move corpus preparation, training, evaluation, experiments, and benchmarks behind an explicitly offline source and environment boundary. Keep runtime model definitions, safe released-checkpoint loading, public analysis contracts, adapters, and required resources in production. Enforce the one-way dependency with one ownership authority, a fast static/artifact gate, and a fresh wheel/sdist clean-install proof. Use one root Pixi workspace and lock with independently solvable `production` and `offline` environments; do not introduce another repository, service, registry, or shared package.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: PyTorch 2.13, Transformers 5.15, Pydantic 2, Hugging Face Hub, safetensors, isanlp; optional Markdown/Docling/DocLang adapters

**Storage**: Local immutable model-release directories and JSON receipts; no database

**Testing**: pytest, Ruff, Pyright, Setuptools build, wheel/sdist member inspection, isolated Pixi/venv smoke execution

**Target Platform**: One local macOS machine, CPU and available Apple MPS; artifact remains ordinary Python-compatible

**Project Type**: Installable Python library plus offline research/training workbench

**Performance Goals**: Routine boundary gate under 10 seconds; no production inference regression attributable to the split

**Constraints**: One repository; one production distribution; one offline workbench; one-way imports only; offline-capable installed runtime; identical released model bytes and inference mathematics; no enterprise infrastructure

**Scale/Scope**: Solo local project, small-volume excellence; all current runtime variants and retained offline commands

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **World-class floor**: PASS. The design proves artifact membership, dependency closure, imports, clean installation, parity, and negative cases; it does not substitute directory naming for separation.
- **Solo-local simplicity**: PASS. One repository, one distribution, one lock, two named environments, filesystem model promotion, and one boundary authority. No services, registries, roles, or deployment platform.
- **Declared assumptions**: PASS. The spec fixes one repository, production-owned shared contracts, unchanged inference, and independent feature 002 semantics.
- **Whole-file evidence**: PASS. Planning used the complete specification, constitution, packaging manifests, package initializers, runtime/checkpoint boundaries, and workbench manifests. Each implementation edit requires a fresh complete read of the target file.
- **Full scope**: PASS. Runtime isolation, offline retention, model promotion, parity, wheel and sdist checks, dependency separation, migration documentation, and ingest independence are all represented.
- **Evidence before done**: PASS. Completion requires actual built-artifact and installed-runtime output, not green repository tests alone.
- **Current format contracts**: NOT TRIGGERED. This feature does not change Docling/DocLang harvesting, mapping, fixtures, or documented schema behavior; their existing runtime routes are exercised unchanged.

Post-design re-check: PASS. No constitution exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/003-production-codeline-split/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── environment-and-artifact.md
│   ├── model-promotion.md
│   └── ownership-and-boundary.md
└── tasks.md
```

### Source Code (repository root)

```text
isanlp_rst/                         # production distribution authority
├── contracts/                     # production request/result/model contracts
├── dmrst_parser/                  # runtime predictor and minimal loadable architecture
├── universal_parser/              # runtime predictor and minimal loadable architecture
├── erst/                          # runtime eRST candidate/scorer/decoder/load path
├── segmentation/                  # runtime segmentation only
├── doclang/                       # production DocLang adapter
├── docling/                       # optional production Docling adapter
├── markdown/                      # optional production Markdown adapter
└── ...                            # parser, hierarchy, ontology, visualization, utilities

workbench/                 # single offline ownership namespace
├── corpus/                        # corpus acquisition/preparation and dataset records
├── training/                      # trainers, fitting, optimization, checkpoint creation
├── evaluation/                    # scoring, calibration, parity/evaluation harnesses
├── experiments/                   # run matrices, ablations, benchmarks, research systems
└── promotion/                     # validate and promote model-release candidates

workbench.research/                  # retained experiment implementation; offline-owned
scripts/                           # repository-only or offline commands, classified by authority
tests/                             # repository-only validation
tools/production_boundary/         # one fast boundary/artifact authority and validator
pyproject.toml                     # production package/deps plus Pixi production/offline envs
pixi.lock                          # one lock containing independently named environments
MANIFEST.in                        # source-distribution pruning to the production surface
```

**Structure Decision**: `isanlp_rst/` is the only publishable production namespace. Offline-only canonical modules move to `workbench/`; the existing `workbench.research/` remains an offline-owned implementation directory rather than being copied or repackaged. Runtime classes required by released checkpoints stay in production even when historically colocated with training; mixed modules are split at responsibility boundaries. A single machine-readable ownership authority classifies source and dependencies and also drives validation, so there is no duplicate production module allowlist.

## Implementation Strategy

1. Freeze the pre-split public-import, checkpoint-load, representative-result, warning/failure, and device evidence before moving code.
2. Introduce the ownership authority and validator first, initially describing the intended boundary; seed negative tests for direct, transitive, dependency, and artifact violations.
3. Extract minimal runtime records/model definitions from mixed modules. Move corpus builders, datasets used only for fitting, trainers, optimizers, evaluation scorers, multiple-run orchestration, and eRST research preparation into `workbench/`; update the workbench and tests to their canonical paths.
4. Make package discovery and `MANIFEST.in` publish only the production authority. Split dependencies into independently named Pixi `production` and `offline` environments in the single root manifest/lock; remove the obsolete nested workbench manifest after parity.
5. Retain production validation/loading of immutable model bundles and place creation/promotion in the offline workbench. Wrap already released assets without changing learned bytes.
6. Build wheel and sdist once for the completion candidate, inspect both, install the wheel with no repository path, execute every required production route, run offline command smokes, and compare the frozen parity evidence.

## Complexity Tracking

No constitution violations. The existing `workbench.research/` directory is retained within the single offline workbench ownership class because moving it adds churn without strengthening the installation or dependency boundary; it is never packaged in production.
