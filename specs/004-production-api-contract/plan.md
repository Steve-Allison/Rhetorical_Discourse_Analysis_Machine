# Implementation Plan: World-Class Production API Contract

**Feature identifier**: `004-production-api-contract`  
**Git checkout**: `master` (no before-plan branch hook is configured)  
**Date**: 2026-08-29  
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/004-production-api-contract/spec.md`

## Summary

Replace the incomplete 4.0.0 production ingest surface with one provider-owned,
strictly typed and self-contained contract. `prepare()` will return every
provider-owned preparation value; `analyse()` will return a validated outcome
that embeds the full preparation outcome; typed exceptions will carry
serializable completed-stage failures; offline capability discovery will make
optional and model-identity boundaries explicit; and versioned schemas,
public-surface inventory, canonical persistence, clean-install conformance, and
tracked release artifacts will make the contract dependable across local
development machines.

Analysis is also made decision-complete. A resolved `AnalysisPolicy` selects
the output formalism and evidence detail; the outcome retains the exact
analysed document, primary and eRST decision evidence, composite component
identity, refinement provenance, both-endpoint anchors, recombination receipt,
and validation receipt. Production adapters may normalize backend-specific
values into this contract but may not reduce a decoded tree, overwrite a model
decision without trace, orphan a signal, or discard a provider receipt.

The incompatibility requires `isanlp_rst` 5.0.0 and serialized production
contract 2.0.0. The work changes the public contract and orchestration around
existing inference; it does not change model architecture, inference
mathematics, source-format meaning, or downstream project schemas.

## Technical Context

**Language/Version**: Python 3.14, strict Mode A with native deferred annotation
evaluation

**Primary Dependencies**: PyTorch 2.13; Pydantic 2.13.x; RFC 8785 canonical JSON;
`packaging`; Python `importlib.metadata` and `importlib.resources`; PyPA `build`
1.6.x for release reports; existing Docling, DocLang, and Markdown packages in
the optional `formats` extra

**Storage**: Canonical JSON filesystem cache; packaged JSON Schema and public
surface resources; version-controlled wheel, sdist, receipt, and receipt digest
under `dist/5.0.0/`

**Testing**: pytest; Ruff; Pyright strict Mode A; markdownlint-cli2; deterministic
mutation and byte-parity tests; isolated core/formats wheel-install tests;
production-boundary artifact validators; second-machine receipt verification

**Target Platform**: Local Python 3.14 library on macOS Apple Silicon as the
reference machine, while preserving the existing supported MPS, CUDA, and CPU
runtime dispatch

**Project Type**: Installable local Python library with optional source-format
dependencies and no hosted service

**Performance Goals**: Preparation excluding inference completes within 2
seconds for 100,000 characters and 15 seconds for 1,000,000 characters on the
reference machine, each measured over five post-warm-up runs; capability
discovery performs no model load, network access, or analysis

**Constraints**: Offline-capable; one person and one machine at runtime; core
import independent of optional format packages; immutable public values; no
raw private source text in default failure rendering; fail closed on incomplete
evidence; no partial multi-unit success; no model or scientific changes; no
downstream-specific fields; no silent truncation, EDU capping, approximate
token allocation, root-only tree projection, or evidence loss at backend
handoffs; no public raw tensors, embeddings, activations, unrestricted charts,
training-only fields, or private workbench records

**Scale/Scope**: Six source forms; nine lifecycle failure stages; complete
inventory for every valid source item; analysed and empty-primary analysis
success variants; preparation-only intentional non-analysis; provider
unavailability and processing-failure records; one current write contract and an
explicit read-version registry; two output formalisms (`rst_tree`,
`erst_graph`); decision-complete evidence by default and optional normalized
distributions; every active production backend and analysis handoff covered by
a loss audit

## Constitution Check

### Pre-design gate

| Gate | Result | Evidence |
|---|---|---|
| One canonical provider authority | PASS | All source forms remain behind `SourceArtifact`; preparation, analysis, persistence, and failures use one `isanlp_rst.production` contract |
| World-class Python 3.14 | PASS | Strict closed models, tagged unions, exact identities, no suppressions, generated projections, and fail-closed validators are required |
| Solo local scale | PASS | No service, RBAC, CI bureaucracy, hosted signing, or enterprise infrastructure is introduced |
| Optional dependency boundary | PASS | Core import/discovery remains model-free and format-extra-free; missing extras become typed unavailability |
| Scientific integrity | PASS | Parser architecture, learned weights, inference mathematics, and interpretation are unchanged |
| Evidence before completion | PASS | Installed-wheel conformance, deterministic build comparison, receipt validation, and second-machine verification are release gates |
| Provider ownership | PASS | Only evidence created, consumed, validated, or derived by `isanlp_rst` is exposed; no CSM schema is copied |

### Post-design gate

The Phase 1 design preserves every pre-design result. The model and contracts
use one provider envelope; generated schemas and documentation are projections,
not new authorities; optional source dependencies remain lazy; tracked
artifacts are bounded to versioned promoted releases; and no inference or
source-format semantic change is planned.

**Post-design result**: PASS. No justified constitution violation exists.

## Project Structure

### Documentation for this feature

```text
specs/004-production-api-contract/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── production-api-v2.md
│   ├── analysis-evidence.md
│   ├── serialization-and-compatibility.md
│   └── distribution-and-public-surface.md
├── evidence/
│   ├── source-spec-currency.md
│   ├── pre-release-quality.json
│   ├── performance.json
│   ├── scope-audit.md
│   ├── source-release-gates.json
│   ├── source-release.json
│   ├── artifact-verification.json
│   ├── second-machine-candidate-verification.json
│   └── release-certification.json
├── checklists/
│   └── requirements.md
└── tasks.md
```

`tasks.md` is generated and maintained by the `speckit-tasks` stage. Evidence
records follow the lifecycle and authority defined in
`contracts/distribution-and-public-surface.md`; they are not an additional
installed API surface.

### Production source and tests

```text
isanlp_rst/
├── __init__.py
├── _version.py
├── parser.py
├── contracts/
│   └── ...                         # existing RST/eRST analysis contracts
├── ingest/
│   ├── __init__.py                 # one supported production import surface
│   ├── contracts/
│   │   ├── __init__.py             # public contract re-exports
│   │   ├── base.py                 # strict base, versions, exact quantities
│   │   ├── source.py               # artifact, contract, representations
│   │   ├── preparation.py          # policy, inventory, plan, outcome
│   │   ├── analysis.py             # success variants and execution evidence
│   │   ├── inference.py            # policies, analysed document, decisions, receipts
│   │   ├── failure.py              # stage-specific persisted failures
│   │   └── capabilities.py         # capability and parser identity contracts
│   ├── capabilities.py             # offline discovery
│   ├── serialization.py            # canonical envelope and compatibility registry
│   ├── validation.py               # complete cross-contract invariants
│   ├── public_surface.py            # manifest loader and reconciliation
│   ├── public-surface.json          # public membership/classification authority
│   ├── schemas/                     # generated Draft 2020-12 projections
│   ├── service.py                   # public lifecycle orchestration
│   ├── prepare.py                   # internal source preparation
│   ├── identity.py                  # semantic request/result identities
│   ├── cache.py                     # validated typed cache persistence
│   └── _*.py                        # existing internal format adapters
├── model_loading/
│   └── release.py                   # immutable model-release identity
├── py.typed
└── build-provenance.json            # generated in isolated build roots only

tools/production_boundary/
├── build.py                         # exact-commit, double-build promotion
├── contracts.py                     # strict release receipt and evidence records
├── artifacts.py                     # artifact and receipt validation
├── clean_install.py                 # isolated installed-wheel proof
└── __main__.py

tests/
├── ingest/
│   └── production_ingest/
│       ├── test_public_surface.py
│       ├── test_capabilities_offline.py
│       ├── test_preparation_outcome.py
│       ├── test_analysis_outcomes_v2.py
│       ├── test_analysis_policy.py
│       ├── test_analysed_document.py
│       ├── test_primary_inference_evidence.py
│       ├── test_erst_completion_evidence.py
│       ├── test_refinement_provenance.py
│       ├── test_recombination_receipt.py
│       ├── test_validation_receipt.py
│       ├── test_backend_evidence_loss.py
│       ├── test_failure_stages.py
│       ├── test_serialization_v2.py
│       ├── test_semantic_mutations.py
│       ├── test_analysis_validation.py
│       ├── test_cache.py
│       └── test_conformance_matrix.py
├── production_boundary/
│   ├── test_release_receipt.py
│   ├── test_reproducible_build.py
│   └── test_clean_install_v2.py
└── fixtures/
    └── ...                          # all source forms and failure stages

docs/
├── production-source-ingest.md
├── production-offline-boundary.md
└── production-api-contract.md

dist/5.0.0/
├── isanlp_rst-5.0.0-py3-none-any.whl
├── isanlp_rst-5.0.0.tar.gz
├── release-receipt.json
└── release-receipt.sha256
```

**Structure decision**: Convert the 779-line `ingest/contracts.py` module into a
cohesive `ingest/contracts/` package while retaining the same internal import
namespace and exposing supported values only from `isanlp_rst.ingest`. This
keeps each contract family reviewable without adding a second library or
service. Runtime models define field semantics; the public-surface manifest
defines membership and support classification; schemas and docs are generated
or reconciled projections.

## Design and Implementation Strategy

### Phase A: Establish version and public authority

**Files**: `pyproject.toml`, `isanlp_rst/_version.py`,
`isanlp_rst/__init__.py`, `isanlp_rst/ingest/__init__.py`,
`isanlp_rst/ingest/public_surface.py`,
`isanlp_rst/ingest/public-surface.json`, `isanlp_rst/py.typed`

1. Set the distribution version to 5.0.0 and production write contract to
   2.0.0.
2. Remove the duplicate runtime version constant and read installed version
   authority with `importlib.metadata`.
3. Declare the complete public import surface and compatibility guarantees.
4. Add reconciliation that compares manifest membership with exports,
   importability, signatures, enums, schemas, and documentation anchors.

**Success criterion**: one command reports zero public-surface mismatches and
the installed package, metadata, runtime, and receipt all report 5.0.0.

### Phase B: Build the complete typed contract

**Files**: `isanlp_rst/ingest/contracts/`,
`isanlp_rst/ingest/serialization.py`, `isanlp_rst/ingest/schemas/`

1. Introduce one strict, closed, recursively revalidated base model.
2. Model typed source representations, complete inventory dispositions,
   transformations, policies, plans, preparation outcome, analysis variants,
   capabilities, and stage-specific failures.
3. Separate semantic and execution evidence structurally.
4. Generate Draft 2020-12 schemas and require byte parity with committed
   packaged projections.

**Success criterion**: no invalid cross-state contract can be constructed;
every public top-level record round-trips through canonical bytes; generated
schemas byte-match committed resources.

### Phase C: Expose complete preparation

**Files**: `isanlp_rst/ingest/prepare.py`,
`isanlp_rst/ingest/service.py`, `isanlp_rst/ingest/validation.py`, internal
format adapters only where necessary to pass through already-harvested values

1. Return a `PreparationOutcome` instead of discarding the inventory, source
   contract, policy evidence, and plan.
2. Preserve every valid source item as primary discourse or typed retained
   material with exactly one disposition and explicit duplicate relation.
3. Make transformations and planning policy inspectable.
4. Validate complete coverage, mappings, boundaries, and exact identities.

**Success criterion**: across every source-form and mixed-content fixture, 100%
of valid items are public and have one explainable final disposition, with zero
unexplained coverage.

If this phase changes Docling or DocLang harvest meaning rather than merely
exposing existing values, implementation pauses for the mandated current
upstream specification and package-version comparison before editing.

### Phase D: Preserve decision-complete analysis evidence and fail closed

**Files**: `isanlp_rst/ingest/service.py`,
`isanlp_rst/ingest/validation.py`, `isanlp_rst/ingest/cache.py`,
`isanlp_rst/ingest/contracts/analysis.py`,
`isanlp_rst/ingest/contracts/inference.py`,
`isanlp_rst/ingest/contracts/failure.py`

Additional producer files are `isanlp_rst/parser.py`,
`isanlp_rst/transformer_parser/`, `isanlp_rst/english/relations/primer.py`,
`isanlp_rst/english/erst/completer.py`, `isanlp_rst/erst/decoder.py`, and
`isanlp_rst/hierarchical/stitcher.py`. They are touched only to retain or map
provider values the production pipeline genuinely creates; trained mathematics
and selection behaviour remain unchanged.

1. Resolve and embed a closed `AnalysisPolicy` covering output formalism,
   evidence detail, marker refinement, relation interpretation, validation, and
   lossy-input handling.
2. Embed the complete preparation outcome and exact `AnalysedDocument` in both
   analysis success variants.
3. Preserve primary segmentation/tree/relation/nuclearity decisions and
   uncertainties, with normalized distributions only at the requested evidence
   level.
4. Preserve marker before/after refinements, eRST signal/candidate/score links,
   the full decoder receipt, and the composite component identity.
5. For multi-unit analysis, emit a compact deterministic recombination receipt
   with complete local-to-global mappings rather than duplicating local graphs.
6. Validate RST tree, eRST DAG, both-endpoint anchors, evidence links, unit
   completeness, and identity consistency; return a typed validation receipt.
7. Translate every lifecycle failure into a safe stage-specific payload and
   wrap it in an idiomatic chained exception.
8. Retain all and only completed-stage evidence; never persist partial success.

**Success criterion**: every backend and handoff passes the evidence-loss audit;
every returned node and edge traces to the analysed substrate and creating
decision; every refinement, accepted eRST edge, recombination, and validation
decision has its typed receipt; and each documented success state and lifecycle
failure is reachable with exactly the allowed evidence.

### Phase E: Add offline capability and deterministic persistence

**Files**: `isanlp_rst/ingest/capabilities.py`,
`isanlp_rst/ingest/serialization.py`, `isanlp_rst/ingest/cache.py`, packaged
schemas and provenance

1. Discover all source forms and optional availability without importing
   adapters or loading a model.
2. Distinguish immutable release, mutable instance, unidentified, and
   not-configured parser identity states and state cache eligibility explicitly.
3. Canonicalize the documented semantic projection with RFC 8785 and SHA-256.
4. Dispatch reload through an explicit compatibility registry and reject
   unsupported versions or malformed I-JSON before use.

**Success criterion**: offline core discovery predicts optional-source
availability accurately; cached and uncached identical semantic requests yield
byte-identical semantic payloads; every semantic mutation changes its identity
and execution-only mutations do not.

### Phase F: Prove the installed release

**Files**: `.gitignore`, `pyproject.toml`, `tools/production_boundary/`,
`dist/5.0.0/`, `specs/004-production-api-contract/evidence/`, production
documentation, and conformance tests

1. Remove the blanket `dist/` ignore and keep build scratch outside the
   repository.
2. Correct all public documentation from runtime and manifest facts, run every
   source-only quality gate, and commit the exact clean source candidate.
3. Double-build wheel and sdist from that named source commit through the sdist
   with `SOURCE_DATE_EPOCH`; require identical SHA-256 hashes.
4. Run artifact validation plus local core and formats acceptance against those
   chosen bytes in genuine isolated environments with checkout-path exclusion
   and networking disabled after installation.
5. Add the verified wheel, sdist, source identity, and local artifact evidence
   in an untagged candidate-artifact commit.
6. Verify those exact committed bytes on a second supported development machine
   without rebuilding and return canonical candidate-verification evidence.
7. Persist that evidence, the canonical release receipt, and detached digest in
   a certification commit; push and tag that commit without changing artifact
   bytes.
8. On the second machine, fetch the release tag, verify the final receipt and
   artifact bytes, install the tagged wheel, and run complete installed
   conformance and quickstart acceptance without rebuilding.
9. Add the resulting `release-certification.json` in a separate
   post-certification evidence commit. Do not move the release tag or alter any
   certified file under `dist/5.0.0/`.

**Success criterion**: every required quality gate passes against the tracked
wheel; artifact and receipt validation reports zero mismatch; the second
machine verifies both the candidate bytes and the final tagged receipt without
rebuilding; `git ls-files dist/5.0.0` lists all four promoted files; and the
post-certification evidence commit leaves the release tag and all four file
hashes unchanged.

## Requirement Traceability

| Requirements | Owning design and implementation phase | Acceptance authority |
|---|---|---|
| FR-001, FR-003, FR-025, FR-029, FR-030, FR-033, FR-034 | Shared lifecycle boundary in Phases C-D | [production-api-v2.md](./contracts/production-api-v2.md) and negative-import conformance |
| FR-002, FR-032, FR-039 | Public authority in Phases A and F | Public-surface reconciliation reports zero mismatch |
| FR-004-FR-008, FR-026-FR-028 | Complete preparation in Phase C | [data-model.md](./data-model.md), all-form and mixed-content fixtures |
| FR-009-FR-018 | Validated outcomes and typed failures in Phase D | Success-state, all-stage failure, graph, anchor, coverage, privacy, and atomicity tests |
| FR-019-FR-024, FR-040-FR-041 | Serialization, compatibility, capabilities, and identity in Phase E | [serialization-and-compatibility.md](./contracts/serialization-and-compatibility.md), round-trip and mutation matrix |
| FR-031, FR-035-FR-038 | Installed consumer boundary in Phases E-F | Core/formats isolated installs and zero-private-import adapter fixture |
| FR-042-FR-044 | Durable release in Phase F | [distribution-and-public-surface.md](./contracts/distribution-and-public-surface.md), tracked artifact/receipt and second-machine proof |
| FR-045-FR-046 | Dated Phase 0 comparison | [research.md](./research.md) with every material gap resolved or rejected |
| FR-047-FR-053 | Typed request, formalism, evidence policy, and exact analysed substrate in Phase D | [analysis-evidence.md](./contracts/analysis-evidence.md), policy/identity and no-silent-loss tests |
| FR-054-FR-058 | Primary decision, refinement, eRST score/signal/decoder evidence in Phase D | Producer handoff and evidence-link conformance tests |
| FR-059-FR-064 | Composite identity, validation/recombination receipts, both-endpoint anchors, and lossless adapters in Phase D | Receipt, anchor, mapping, and backend loss-audit tests |
| FR-065-FR-067 | Public evidence boundary, honest unavailability, and every-handoff coverage in Phases D-F | Public-surface negative tests and installed conformance matrix |

## Verification Plan

The implementation phase must provide Pixi tasks that make these checks
repeatable from the repository root:

```bash
pixi run -e offline lint
pixi run -e offline typecheck
pixi run -e offline mdlint
pixi run -e offline production-api-contract
pixi run -e offline production-ingest-determinism
pixi run -e offline production-ingest-performance
pixi run -e offline build-production
pixi run -e offline validate-production-artifacts
pixi run -e offline production-ingest-clean-install
pixi run -e production production-boundary
pixi run -e production production-clean-install
```

`production-api-contract` must include:

- public-surface, schema, and documentation reconciliation;
- all six source forms and mixed retained content;
- preparation-only, analysed, and empty-primary success paths;
- all nine failure stages, including provider unavailability;
- core installation without optional format distributions;
- rich outcome, capability, and failure round-trips;
- semantic mutation and execution-only negative controls;
- graph, anchor, coverage, and cache corruption failures;
- cached/uncached canonical semantic-byte equality;
- typed output-formalism and evidence-detail policy mutation coverage;
- exact analysed tokens, EDUs, boundaries, mappings, and fail-closed truncation
  or approximation behaviour;
- primary split, relation, nuclearity, segmentation evidence, and marker
  before/after refinements;
- eRST candidate, signal, score, calibration links, and exact decoder receipts;
- composite model identity, recombination receipts, validation receipts, and
  both-endpoint anchors;
- deliberate evidence-removal mutations for every production backend and
  handoff, plus negative public-surface checks for forbidden scientific
  internals.

Release promotion additionally records exact output from the build report,
artifact validator, clean-install checks, full quality gates, and candidate
second-machine verification in the receipt or named evidence digests. Final
tagged-receipt verification is recorded separately after certification because
it cannot truthfully be an input to the receipt it verifies. No release is
complete from an editable-checkout test alone.

## Migration and Compatibility

- `isanlp_rst` 4.x and production contract 1.x remain historical immutable
  releases; their artifacts are not overwritten.
- 5.0.0 writes only contract 2.0.0.
- The initial 5.0.0 read registry supports 2.0.0. A 1.x migration is added only
  if a concrete persisted 1.x payload can be transformed without inventing the
  evidence absent from that payload. Otherwise the loader returns a typed
  unsupported-version failure.
- Removed format-specific public APIs remain absent and receive no aliases.
- Downstream adapters migrate to the installed `isanlp_rst.ingest` exports and
  must not import private modules or reconstruct missing provider evidence.
- No downstream repository is modified by Feature 004.

## Complexity Tracking

None. The design adds no constitution violation requiring justification. The
contract package split, generated projections, and release receipt are direct
responses to the required public evidence, compatibility, and distribution
scope rather than general-purpose infrastructure.
