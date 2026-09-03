# Implementation Plan: Rhetorical Discourse Analysis Machine Architecture

**Branch**: `006-rhetorical-discourse-machine` | **Created**: 2026-09-01 |
**Reconciled**: 2026-09-03 | **Spec**: [spec.md](spec.md)

> The repository works on `master`; the branch label is the Spec Kit feature identity,
> not a live Git branch.

## Summary

Feature 006 is the umbrella architecture and completion contract for the Rhetorical
Discourse Analysis Machine. The repository migration and the aggregate, RST, Dung,
IBIS, Toulmin, and Walton implementations now exist. The remaining implementation work
is to make the already-present Toulmin and Walton providers decision-closed, specify and
build SDRT and PDTB, expose one supported seven-provider composition, and prove the
result against SC-012. Each technique keeps its native contract; the aggregate preserves
outcomes without flattening them.

The live production topology is one installable `rdam` package with a sub-package per
technique. This supersedes the 2026-09-01 proposal for separate top-level technique
directories and an `isanlp_rst` compatibility import. Historical model/runtime identity
strings remain data compatibility identifiers only.

## Technical Context

**Language/Version**: Python 3.14 (`requires-python = ">=3.14"`; Pixi-locked)

**Primary dependencies**: hatchling; Pydantic v2 contracts; Pydantic AI for LLM-backed
providers; PyTorch and Transformers for RST; optional Docling and DocLang format
adapters; the vendored Central_Configs framework-identity projection.

**Storage**: repository files and optional local content-addressed analysis/model stores;
no database or remote control plane.

**Testing**: pytest through Pixi; Ruff; Pyright strict; markdown lint; production-boundary
inspection; wheel/sdist build and clean-install gates when distribution proof is needed.

**Target platform**: one local macOS arm64 machine, MPS-aware with CPU fallback and
explicit CUDA paths where the RST stack supports them.

**Core constraints**:

- `rdam/` never imports or packages `workbench/` material.
- `rdam.rst` remains directly usable and semantically independent of aggregation.
- Capability queries construct no model client, load no weights, and make no network
  request.
- All seven techniques are required; a `not_implemented` capability fails SC-012.
- Every technique implementation has a decision-closed, cross-checked feature before it
  is accepted as complete.
- LLM-backed providers identify their configured model and implement the shared typed
  failure and bounded-retry contracts at the external boundary.

## Constitution Check

| Principle | Current compliance condition |
|---|---|
| I. Evidence Before Claims | Capability and completion claims are re-probed from the live package; historical evidence is labelled by date and never treated as current. |
| II. One Production Quality Bar | Every provider and changed Python file passes the same Python 3.14, lint, type, and test standards. |
| III. Solo-Local Simplicity and Scope Fidelity | One package, one process, explicit provider composition; no team, tenant, queue, or distributed infrastructure. |
| IV. Honest Verification and Reproducible Evidence | Focused tests precede full Pixi gates; SC-012 is proved by a production composition test, not inferred from package presence. |
| V. Canonical Contracts and Current Specifications | `spec.md` owns requirements; technique features own native contracts; Central_Configs owns framework identities; Docling/DocLang work verifies current upstream specifications first. |

No constitution exception is accepted or required.

## Production Structure

```text
Rhetorical_Discourse_Analysis_Machine/
├── rdam/
│   ├── machine.py          # independent-outcome aggregation
│   ├── contracts.py        # aggregate and provider contracts
│   ├── frameworks.py       # packaged Central identity projection
│   ├── rst/                # RST/eRST provider and native ingest contract
│   ├── dung/               # Dung provider
│   ├── ibis/               # IBIS provider
│   ├── toulmin/            # Toulmin provider
│   ├── walton/             # Walton provider
│   ├── sdrt/               # required by FR-031; created with its provider
│   └── pdtb/               # required by FR-031; created with its provider
├── ontology/               # vendored identity authority and consumer schema
├── workbench/              # all candidates, corpora, training, and evaluation
├── tests/                  # production verification; research tests isolated below it
├── tools/                  # boundary and distribution tooling
├── specs/                  # architecture and technique decisions
├── scripts/                # local operational commands
├── docs/                   # user and technical documentation
└── models/                 # local immutable RST model releases
```

Each technique directory is a sub-package of `rdam`, never a top-level import and never
a container for a second `production/` directory. `rdam.machine` depends only on public
provider declarations and native results. Providers may depend on the shared aggregate
contract semantics but never on another technique's internals.

## Implementation Phases

1. **Reconcile architecture authority**: update Feature 006 contracts, research,
   quickstart, evidence, and durable governance to the live package and removed
   promotion ruling (T013, T017, T018).
2. **Close provider decisions**: create and cross-check Toulmin, Walton, SDRT, and PDTB
   technique features; audit already-present providers before accepting them (T014,
   T015).
3. **Complete the machine**: implement SDRT and PDTB, add the supported seven-provider
   composition, and prove 7/7 capabilities without import-time work (T015, T016).
4. **Converge and certify**: refresh documentary evidence, run cross-artifact analysis,
   run applicable Pixi gates, and mark only demonstrated tasks complete (T019).

## Complexity Tracking

No enterprise or multi-process mechanism is justified. LLM transport retry logic is
provider-local because it is required at a real transient boundary; it is not a general
job system.
