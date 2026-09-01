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
| `state` | enum | `approved_name` (no directory exists) or `active` (directory exists because a provider promoted) — FR-002, spec edge case "production directory with no promoted implementation" is thereby unrepresentable. |
| `provider` | Provider ref (0..1) | Present iff `state = active`. |

Validation: a boundary directory on disk without a promoted provider is a contract
violation (SC-007); a boundary never contains a `production/` subdirectory (FR-003);
boundary directories are not importable packages (spec Assumptions).

### Workbench

The single non-production authority (FR-004). Singleton; root `workbench/`.

| Field | Type | Rules |
|---|---|---|
| `candidates` | collection | Candidate implementations per technique, each traceable to exact code/config/model artifacts (FR-023). |
| `evidence` | collection | Corpora, runs, benchmarks, checkpoints, promotion evidence — all experimentation state lives here and only here (FR-004). |

Validation: no production import may resolve into `workbench.*` and no distributable may
contain workbench members (FR-006, SC-003; enforced per research D5).

### Provider

An independently callable, promoted implementation for one technique.

| Field | Type | Rules |
|---|---|---|
| `provider_id` | string | Required, stable. |
| `technique_id` | `coe:` curie | Required; matches its boundary. |
| `capability` | CapabilityState | Required; see state machine below (FR-020). |
| `contract_version` | semver | Required; versions the technique-native result contract (FR-012). |
| `provenance` | struct | Required: exact code version, configuration, and model identity where applicable (FR-023); licence decision reference (FR-021). |

### CapabilityState (value type)

| State | Meaning | Required payload |
|---|---|---|
| `available` | Provider accepts requests | — |
| `unavailable` | No promoted implementation, or withheld | `reason`: stable, enumerated string (FR-020, SC-010) |
| `failed` | Provider errored on this request | typed error with a mandatory retryability classification (`retryable` / `not_retryable` / `unknown`; see the capability contract's machine-wide standard); never fabricated output (FR-020, SC-007) |

Transitions: `unavailable → available` only via a PromotionDecision with outcome
`promote`; `available → unavailable` via `withhold`/`retire`; `failed` is per-request,
not a standing state. An unavailable or failed provider never yields a stub or dummy
structure (SC-007).

### NativeTechniqueResult

One technique's result in its own theory's terms.

| Field | Type | Rules |
|---|---|---|
| `technique_id` | `coe:` curie | Required. |
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

### PromotionDecision

| Field | Type | Rules |
|---|---|---|
| `candidate` | workbench artifact identity | Required: exact evaluated code, config, model assets, corpus partitions (FR-023). |
| `technique_id` | `coe:` curie | Required. |
| `evidence` | struct | Required, evaluated separately: output quality, calibration, latency/resource, runtime/packaging compatibility, provenance, licensing (FR-021). Output-quality evidence: gold data + theory-specific metrics + baselines + uncertainty for empirical techniques; correctness arguments + property tests against formal definitions for formal techniques (FR-022). |
| `outcome` | enum | `promote` \| `withhold` \| `replace` \| `retire`. |
| `recommendation` | text | Required; states strengths and limitations (spec US4). |

Validation: installation/engineering success alone never satisfies the evidence
requirement (spec Assumptions); comparisons across candidates for one technique use the
same declared partitions, metrics, and criteria (US4 scenario 2).

### MigrationSafetyState

| Field | Type | Rules |
|---|---|---|
| `live_processes` | inventory | Must be empty of protected workbench workloads (FR-026, SC-008). |
| `run_reconciliation` | inventory | Every checkpoint/run/output committed, archived, or owner-marked discardable (research D8). |
| `owner_confirmation` | dated record | Required before any file move (spec Assumptions). |

## State machines

**Boundary lifecycle**: `approved_name → active` (first promotion; directory created in
the same change) — no reverse transition; a retired provider leaves the boundary
`active` with capability `unavailable(retired)`.

**Provider capability**: `unavailable(no_promoted_implementation) → available`
(promotion) → `unavailable(withheld | retired | replaced)` (decision) — with
per-request `failed` outcomes that never alter the standing state of other techniques
(SC-010, FR-030).

## Relationships

```text
TechniqueProductionBoundary 1—0..1 Provider —* NativeTechniqueResult
AggregateAnalysis —* Outcome(result | unavailable | failed)
AggregateAnalysis —* ProviderDependencyReference —> NativeTechniqueResult (upstream)
Workbench —* candidate —0..1 PromotionDecision —> Provider (on promote)
MigrationSafetyState — gates → repository migration (one-shot)
```
