# Data Model: Rhetorical Discourse Analysis Machine Architecture

**Feature**: 006 | **Date**: 2026-09-01 | **Sources**: [spec.md](spec.md) Key Entities, [research.md](research.md)

Architecture-level entities every follow-on feature implements against. Feature 006
defines their meaning, fields, relationships, and state machines; feature 007 gives them
typed form (Python contracts plus the `rdam.linkml.yaml` application profile). Nothing
here constrains a technique's *native* result payload — that is each provider's own
versioned contract (FR-012, FR-013).

## Entity catalogue

### TechniqueProductionBoundary

The exclusive production home for one discourse framework.

| Field | Type | Rules |
|---|---|---|
| `technique_id` | `coe:` curie | Required. One of the canonical concepts under `coe:artifact/narrative/analytical_frameworks_taxonomy` (FR-002; research D6). |
| `boundary_name` | string | Required. Exactly one of `rst`, `pdtb`, `sdrt`, `toulmin`, `walton`, `dung`, `ibis` (FR-002). One-to-one with `technique_id`. |
| `state` | enum | `approved_name` (no directory exists) or `active` (a provider was implemented, so the directory exists) — FR-002, spec edge case "production directory with no implementation" is thereby unrepresentable. |
| `provider` | Provider ref (0..1) | Present iff `state = active`. |

Validation: a boundary directory on disk without a provider is a contract
violation (SC-007); a boundary never contains a `production/` subdirectory (FR-003);
boundary directories are not importable packages (spec Assumptions).

### Workbench

The single non-production authority (FR-004). Singleton; root `workbench/`.

| Field | Type | Rules |
|---|---|---|
| `candidates` | collection | Candidate implementations per technique, each traceable to exact code/config/model artifacts. |
| `evidence` | collection | Corpora, runs, benchmarks, checkpoints — all experimentation state lives here and only here (FR-004). |

Validation: no production import may resolve into `workbench.*` and no distributable may
contain workbench members (FR-006, SC-003; enforced per research D5).

### Provider

An independently callable implementation for one technique.

| Field | Type | Rules |
|---|---|---|
| `provider_id` | string | Required, stable. |
| `technique_id` | `coe:` curie | Required; matches its boundary. Single-valued: a provider belongs to exactly one boundary. |
| `formalisms` | set of Formalism | Required, non-empty. Each declared result-kind the provider can emit, with its own `coe:` identity and its own capability state (see below). The eRST ruling lives here. |
| `capability` | CapabilityState | Required; the provider's standing state (FR-020). Each formalism additionally reports its own state — a provider can be `available` while one of its formalisms is `unavailable(reason)`. |
| `contract_version` | semver | Required; versions the technique-native result contract (FR-012). |
| `provenance` | struct | Required: exact code version, configuration, and model identity where applicable, plus the licence the code and any model weights carry (FR-021). |

### Formalism (value type)

One result-kind a provider emits, in the provider's own terms.

| Field | Type | Rules |
|---|---|---|
| `formalism_id` | string | Required; provider-owned name (e.g. `rst_tree`, `erst_graph`). |
| `technique_id` | `coe:` curie | Required; the canonical identity this result-kind carries. May differ from the provider's `technique_id` only for a concept in the same taxonomy scheme that the same provider natively produces. |
| `capability` | CapabilityState | Required; per-formalism, with the same states and stable reasons as the provider's. |

**Ruling on eRST (analysis finding U1, closed 2026-09-01).** The RST provider serves two
canonical identities — `…/discourse_structure_framework/rst` and `…/erst` — while
belonging to one boundary. It is modelled as **one provider with two formalisms**, not
two providers and not a multi-valued `technique_id`: the `rst/` boundary and its provider
bind to `…/rst`; the provider declares formalisms `rst_tree → …/rst` and
`erst_graph → …/erst`, each with its own capability state. This is exactly what the
running implementation already does — `describe_capabilities()` reports `rst_tree` and
`erst_graph` as separate `formalism_capabilities` under one provider, and `erst_graph` is
independently `unavailable` when no validated completion bundle is loaded (verified in
[evidence/rst-surface-audit.md](evidence/rst-surface-audit.md)) — and it references
Central's `erst` concept canonically without redefining it (capability contract §Identity
binding). Boundary-to-`technique_id` stays one-to-one; identity resolution stays
eight-for-eight.

### CapabilityState (value type)

| State | Meaning | Required payload |
|---|---|---|
| `available` | Provider accepts requests | — |
| `unavailable` | The provider cannot run | `reason`: stable, enumerated string (FR-020, SC-010) |
| `failed` | Provider errored on this request | typed error with a mandatory retryability classification (`retryable` / `not_retryable` / `unknown`; see the capability contract's machine-wide standard); never fabricated output (FR-020, SC-007) |

Transitions: `unavailable → available` when the thing that was missing is supplied —
the provider is implemented, or its model is configured and resolves; `available →
unavailable` when that state is withdrawn. `failed` is per-request, not a standing state.
An unavailable or failed provider never yields a stub or dummy structure (SC-007).

### NativeTechniqueResult

One technique's result in its own theory's terms.

| Field | Type | Rules |
|---|---|---|
| `technique_id` | `coe:` curie | Required; the identity of the **formalism** that produced this result (for the RST provider: `…/rst` for `rst_tree`, `…/erst` for `erst_graph`). |
| `formalism_id` | string | Required; the producing provider's declared formalism. |
| `contract_version` | semver | Required (FR-012). |
| `payload` | provider-native | Opaque to the machine layer; retains the semantics of exactly one framework — never renamed, removed, or reinterpreted by aggregation (FR-013, SC-004). |
| `source_identity` | struct | Required: source anchors surviving from ingest (FR-011 lineage). |
| `provenance` | struct | Required: producing provider identity + version. |

Validation: for structured-input techniques, the payload's input section distinguishes
`supplied` from `explicitly derived` (Dung, FR-016) and automated extraction into IBIS
structure is separately identified (FR-017). Claim/premise extraction alone must not be
labelled a Toulmin or Walton result (FR-019).

### AggregateAnalysis

A collection of independent provider outcomes — not a replacement theory (spec Key
Entities).

| Field | Type | Rules |
|---|---|---|
| `source_identity` | struct | Required; one source, shared anchors. |
| `outcomes` | map technique → Outcome | Each Outcome is exactly one of: `result` (NativeTechniqueResult), `unavailable(reason)`, `failed(error)` (FR-014, SC-005). |
| `lineage` | ProviderDependencyReference[] | All cross-provider consumption edges (FR-015). |

Validation: a successful outcome survives aggregation with zero lost fields or changed
semantic values (SC-004); one provider's failure never suppresses another's success
(SC-005); there is no merged node-and-edge view (FR-013).

### ProviderDependencyReference

| Field | Type | Rules |
|---|---|---|
| `consumer_provider` | provider id + version | Required. |
| `upstream_artifact` | result identity | Required: the exact upstream NativeTechniqueResult consumed (FR-015). |
| `upstream_provider` | provider id + version + model identity | Required; missing upstream identity is a validation failure (spec edge case). |

Both native outputs stay separate; the reference records consumption, never merging.

### MigrationSafetyState

| Field | Type | Rules |
|---|---|---|
| `live_processes` | inventory | Must be empty of protected workbench workloads (FR-026, SC-008). |
| `run_reconciliation` | inventory | Every checkpoint/run/output committed, archived, or owner-marked discardable (research D8). |
| `owner_confirmation` | dated record | Required before any file move (spec Assumptions). |

## State machines

**Boundary lifecycle**: `approved_name → active` when the technique is first
implemented; the directory is created in the same change. No reverse transition — a
removed provider leaves the boundary `active` with capability `unavailable(not_implemented)`.

**Provider capability**: `unavailable(not_implemented) → available` when the provider is
implemented; `available → unavailable(model_unavailable)` when a configured model stops
resolving — with per-request `failed` outcomes that never alter the standing state of
other techniques (SC-010, FR-030).

## Relationships

```text
TechniqueProductionBoundary 1—0..1 Provider —1..* Formalism —* NativeTechniqueResult
AggregateAnalysis —* Outcome(result | unavailable | failed)
AggregateAnalysis —* ProviderDependencyReference —> NativeTechniqueResult (upstream)
MigrationSafetyState — gates → repository migration (one-shot)
```
