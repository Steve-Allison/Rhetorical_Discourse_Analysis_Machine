# Implementation Plan: World-Class Production Source Ingest

**Branch**: `codex/002-production-source-ingest` | **Date**: 2026-08-25 | **Spec**: [spec.md](spec.md)

## Summary

Create one canonical, installable production-ingest boundary for plain text, pre-segmented EDUs, Markdown, DoclingDocument JSON, and DocLang XML/archive sources. Every route will validate before trust, inventory the complete source before selecting text, apply one named authored-discourse policy, preserve excluded material as anchored side-channel evidence, construct a reversible prepared document, analyse it through deterministic structure-aware subdivision, and return a persisted `ProductionAnalysisResult` with a reconciled preparation receipt.

The implementation reuses the current format loaders, the released `Parser`, the shared tree projector, and the completed production/offline package boundary. It changes no trained architecture or inference mathematics. Runtime code remains wholly inside the built `isanlp_rst` wheel; Gold Set content, metric scoring, inspection, and promotion evidence remain repository-only or offline and cannot be imported by production.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Pydantic 2; lxml 6; markdown-it-py 4 with mdit-py-plugins; current `docling-core` 2.92.0 / DoclingDocument 1.10.0; current `doclang[schematron-saxon]` 0.7.3; existing PyTorch/Transformers parser runtime; stdlib `hashlib`, `json`, `zipfile`, and atomic filesystem operations

**Storage**: Source files supplied by the caller; optional private local content-addressed JSON cache; private local Gold Set root plus text-free repository manifests/evidence; no database or network service

**Testing**: pytest, Ruff, Pyright, current upstream fixture parity, property/invariant tests, cache corruption/identity tests, exact built-wheel clean-install tests, real released-model CPU/MPS runs, frozen baseline/candidate Gold Set comparison, and direct inspection receipts

**Target Platform**: One local macOS machine, CPU and Apple MPS; production remains an ordinary importable Python wheel and runs offline after dependencies and model assets are installed

**Project Type**: Installable Python analysis library with repository-only promotion tooling and an offline evaluation workbench

**Performance Goals**: Preparation only, excluding model inference, completes within 2 seconds for each conforming 100,000-character source and within 15 seconds for the 1,000,000-character promotion source on the designated machine; every run records preparation timing and peak RSS; correctness gates precede performance

**Constraints**: Small-volume excellence; complete source accounting; reversible anchors; no manual cleaning; validation before cache lookup; no silent partial result, truncation, loss, duplication, fallback, or benchmark exception; deterministic semantic output; unchanged released model and inference mathematics; no training/evaluation/runtime coupling; no services, queues, concurrency framework, or mass-throughput design

**Scale/Scope**: One user, one machine, five source families, a minimum 20-source deeply inspected Gold Set, at least 12 adjudicated EDU/RST sources, and at least one 1,000,000-character structured source

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Evidence before claims**: PASS. Planning inspected the complete feature specification, constitution, current production/offline boundary, the production parser/contracts, all format adapters, all shared format helpers, the hierarchy implementation, packaging metadata, current PyPI releases, installed API signatures, upstream normative fixtures, and primary current-practice sources. Version and fixture claims were re-run on 2026-08-25.
- **One production quality bar**: PASS. The design replaces unsafe defaults and silent omissions; it does not suppress checkers, preserve known-invalid behavior, or change parser mathematics to make promotion easier.
- **Solo-local simplicity**: PASS. One in-process service, one strict contract family, one optional local cache, one compact Gold Set, and existing Pixi environments. No enterprise infrastructure or hypothetical extension framework is introduced.
- **Scope fidelity**: PASS. Runtime source ingest only. Training corpora, training examples, model fitting/selection, experiment caches, and research workflows are excluded. Repository-only release assessment is separated from runtime implementation.
- **Canonical contracts**: PASS. `isanlp_rst.ingest` owns the only public source/preparation/result contract. Format-specific code is private implementation detail; no legacy format entry point or compatibility envelope remains.
- **Current Docling/DocLang contracts**: PASS. `docling-core` 2.92.0 and `doclang` 0.7.3 are current and already pinned. The design accounts for Docling 1.10.0 validation/version normalization, all current content layers, full DocLang XSD+Schematron validation, valid empty namespace, current 42 `.dclg` specimens, `.dclx` archives, element-head metadata, and recursive tables.
- **Production distribution boundary**: PASS. All runtime changes live under `isanlp_rst`; no production import may reach `workbench`, `tools`, `tests`, corpora, benchmarks, or local evidence. Built-wheel acceptance proves the boundary outside the checkout.
- **Honest verification**: PASS. Completion requires real persisted prepared documents, receipts, analyses, built artifacts, clean installs, current normative specimens, model-backed Gold Set results, per-source reports, and direct inspection—not unit status alone.

Post-design re-check: PASS. No constitution exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/002-production-source-ingest/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── preparation-and-provenance.md
│   ├── production-api.md
│   └── promotion-evidence.md
└── tasks.md                       # generated by speckit-tasks, not this command
```

### Source Code (repository root)

```text
isanlp_rst/                        # sole installable production authority
├── ingest/
│   ├── __init__.py               # public production ingest surface
│   ├── contracts.py              # strict immutable source/preparation/result contracts
│   ├── identity.py               # canonical source, pipeline, model, result digests
│   ├── policy.py                 # named versioned authored-discourse policies
│   ├── prepare.py                # inventory reconciliation, selection, mapping, coverage
│   ├── subdivision.py            # structure-first complete analysis-unit planning
│   ├── cache.py                  # validated, integrity-checked semantic cache
│   └── service.py                # ProductionIngestor orchestration
├── contracts/
│   ├── document.py               # existing RstDocument; strengthen aligned-input invariants
│   ├── analysis.py               # existing RstAnalysis remains parser result authority
│   └── serialization.py          # deterministic production-result round trip
├── doclang/                      # private XML/archive validation helpers used by ingest
├── markdown/                     # private token loader used by ingest
├── hierarchical/stitcher.py      # consume prepared subdivision tree and preserve provenance
├── model_loading/                # immutable released-model identity authority
├── parser.py                     # unchanged inference engine; expose stable capability identity
└── _version.py                   # independent canonical-ingest and changed envelope versions

tests/
├── fixtures/production_ingest/   # redistributable normative/conformance fixtures only
├── production_ingest/            # contract, policy, coverage, identity, cache, integration tests
└── test_production_boundary.py    # production import/artifact regression checks

tools/production_ingest/           # repository-only Gold Set runner/report/inspection tooling
specs/002-production-source-ingest/evidence/
                                   # text-free manifests, frozen expectations, candidate receipts
workbench/evaluation/rst/ # existing canonical Parseval scorer; never imported by runtime
```

**Structure Decision**: Add one small `isanlp_rst.ingest` production package as the sole public source-ingest authority. Keep only the private Markdown and DocLang helpers required by that package; consume `docling-core` directly and remove the obsolete public format packages, entry points, result envelopes, and caches. Do not create a parallel adapter hierarchy or a third shared distribution. Gold content and scoring stay outside the wheel.

## Implementation Strategy

### 1. Freeze authorities and baseline evidence

Record current package/spec identities, the exact released model bundle, the current production outputs for every Gold Set source, and the scoring/inspection rubric before candidate behavior exists. Verify current Docling/DocLang specimens without modifying them. Reject mutable or manually cleaned promotion sources.

### 2. Introduce strict canonical ingest contracts and identities

Implement `SourceArtifact`, `SourceContractIdentity`, `NativeAnchor`, `ContentInventoryItem`, `PreparationPolicy`, `Disposition`, `PreparedSegment`, `PreparedRstDocument`, `SubdivisionPlan`, `AnalysisAnchor`, `PreparationReceipt`, `ExecutionReceipt`, `ProductionAnalysisResult`, and typed failures. Canonical digests cover raw identity, validation semantics, adapter/preparation behavior, policy, stable released-model bytes, and result contract. Runtime timestamps/cache status/timing remain evidence but are excluded from semantic equality.

### 3. Build complete inventory adapters before content selection

- Plain text: retain supplied characters and deterministic paragraph structure.
- Pre-segmented EDUs: retain each supplied EDU and make every inserted separator synthetic and anchored.
- Markdown: inventory all parsed block/inline classes and source line/range evidence; parse raw HTML as a real tree and explicitly classify script, style, navigation, and markup.
- DocLang: validate with current full XSD+Schematron semantics, accept valid empty namespace, securely read `.dclg`, `.dclg.xml`, and `.dclx`, inventory all semantic/head/structural elements, and represent nested tables recursively.
- Docling: preserve raw declared schema metadata before the current loader normalizes it, validate with 2.92.0, enumerate all content layers/groups/items, and reconcile top-level collections with tree traversal.

Every valid source element receives exactly one inventory identity before policy is applied. Unknown-but-valid content is retained as unsupported/side-channel rather than dropped.

### 4. Apply one named authored-discourse policy

Ship `authored_prose_v1` as the production default and only public preparation policy. Include authored prose, titles/headings, meaningful list items, and authored turns. Exclude code, formulas, raw markup, scripts/styles/navigation, furniture/background/invisible content, machine picture descriptions, notes, and table structure from primary RST by default while retaining all of them. Exact duplicates are always reported; no authored repetition is removed unless a future explicitly specified named policy requests reversible deduplication.

### 5. Construct a reversible prepared document and prove coverage

Build prepared text only from mapped source segments and declared synthetic segments. Preserve source text by default; prohibit implicit Unicode normalization; record any line-ending, whitespace, or format-required normalization with an exact before/after mapping. Reconcile inventory counts and prepared character coverage before analysis. A gap, overlap, wrong-source anchor, unresolved native reference, or unreceipted transformation fails closed.

### 6. Replace flat/oversize parsing with deterministic structural analysis

Derive an ordered hierarchy from headings, sections, groups, pages/slides, lists, turns, and document fallback. Determine safe unit capacity from the loaded parser/model capability contract rather than a format hard limit. Partition at meaningful boundaries first; recursively subdivide an oversized unit using sentence/paragraph evidence and a deterministic last-resort range splitter. Context overlap, if any, is explicitly non-output context and cannot duplicate stitched EDUs.

Analyse local units with the unchanged released model, derive anchored nuclear-spine macro representations instead of arbitrary 300-character prefixes, recursively analyse higher structural levels, and stitch one coherent `RstAnalysis`. Preserve local versus macro relation origin and remap every node/edge through prepared ranges to native source anchors. Pre-segmented EDU boundaries are indivisible.

### 7. Make cache behavior analytical and fail-closed

Validate/decode the source and establish source-contract identity before cache access. Key entries by canonical source, source contract/validator, policy, preparation implementation, model release, and result contract digests. Verify envelope version, payload digest, source identity, and semantic digest on load. A changed identity is a normal miss; a corrupt or contradictory entry is an actionable failure, never a silent hit or silent miss. If a parser lacks a stable released-model digest, analysis may run but durable caching is disabled and receipted.

### 8. Migrate public routes without reintroducing independent pipelines

Expose `analyse_source()` and `ProductionIngestor.prepare()/analyse()` from the installed package. Route all five source forms through the canonical service. Remove the old `parse_markdown`, `parse_docling`, and `parse_doclang` functions and their independent envelopes/caches entirely; no backward-compatibility surface is required. Bump only the canonical project-owned result envelope when its shape changes; never conflate it with upstream Docling/DocLang versions.

### 9. Build production-only conformance and repository-only promotion evidence

Run source validation, preparation, caching, analysis, persistence/reload, determinism, long-document coverage, and failure cases from the exact built wheel installed outside the repository with no offline packages or data. Keep the minimum 20-source Gold Set and direct inspection tooling repository-only/private. Generate baseline and candidate results with the clean production wheel; score frozen serialized results separately with the existing offline Parseval authority so production never imports evaluation code and no scorer is duplicated.

### 10. Promote only after ordered gates pass

Evaluate source validity, inclusion/exclusion, coverage, provenance, downstream EDU/RST quality, determinism, then performance. Report every source and source form. Any per-source regression, modified normative fixture, manual cleanup, hidden exception, incomplete inspection, or unresolved current-practice gap blocks promotion. Rebuild the final wheel/sdist once, re-run boundary/artifact checks, clean installs, full tests, CPU/MPS evidence, and inspect every final persisted candidate artifact.

## Requirement Traceability

| Specification obligations | Design authority | Acceptance authority |
|---|---|---|
| FR-001–004: forms, production-only scope, immutable identity, current validation | `SourceArtifact`, source-contract identity, canonical API | Validity and clean-wheel gates |
| FR-005–013: complete inventory, authored relevance, HTML/tables, dispositions, duplicates | Inventory adapters and `authored_prose_v1` | Inventory/relevance gate with frozen per-item expectations |
| FR-014–018: boundaries, structure-first long-source analysis, complete subdivision | `SubdivisionPlan` and recursive macro/micro strategy | Structure gate and million-character source |
| FR-019–024: reversible preparation, anchors, receipts, reconciliation, fail-closed coverage | Prepared segments, native/analysis anchors, semantic/execution receipts | Mapping/provenance gate at 100% coverage |
| FR-025–029: analytical identity, cache correctness, determinism, actionable failure, no partial success | Canonical fingerprints, verified atomic cache, typed failures | Ten-run/cache-corruption and failure gates |
| FR-030–035: current upstream proof, unchanged model, local operation, feature-003 boundary, dated comparison | Research decisions 2–5 and 14; scope guardrails | Normative specimens, identical-model record, clean install, SOTA matrix |
| FR-036–045: immutable deep Gold Set, per-source protected metrics, direct inspection, bounded SOTA | Promotion-evidence contract | Ordered gates with no waiver field |
| FR-046: no enterprise or mass-throughput scope | Technical constraints and solo-local architecture | Bounded local batch proof |
| SC-001–006 | Inventory, selection, anchors, determinism, cache, normative conformance | Gates 1–5 |
| SC-007–012 | Long-document, performance, failure, no-cleanup, receipt, isolation outcomes | Million-character, performance, failure, direct receipt, clean-wheel evidence |
| SC-013–020 | Gold Set scale/depth, protected quality, structural gain, per-source inspection, SOTA, no shortcuts, local batch | Gates 4–8 and final decision rule |

## Scope and Boundary Guardrails

- No training corpus, label generation, example preparation, model fitting, tuning, selection, or research experiment enters this feature.
- Gold Set annotations are release evidence, not training content; they remain outside `isanlp_rst` and the production wheel.
- The existing offline Parseval scorer remains canonical and is used only after clean production runs have emitted serialized results.
- Feature 002 does not move packages or redesign environments. It consumes the completed feature 003 boundary and must keep its artifact/import gates green.
- A pre-existing production/offline ownership defect, if found during implementation, is corrected as a feature 003 boundary repair rather than hidden inside ingest contracts.

## Complexity Tracking

No constitution violations. The new `ingest` package is the minimum cohesive boundary needed to stop five source routes from owning duplicate policy, identity, coverage, cache, and receipt behavior. Secure `.dclx` reading uses the current format contract and stdlib ZIP handling; it does not add a conversion service or the full Docling application dependency.
