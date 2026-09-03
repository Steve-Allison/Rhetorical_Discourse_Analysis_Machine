# Feature Specification: Dung Abstract Argumentation Provider

**Feature**: `011-dung-provider`

**Created**: 2026-09-02

**Reconciled**: 2026-09-03

**Status**: Complete

## User Story 1 — Evaluate a supplied framework exactly (Priority: P1)

As an analyst, I supply a finite argument-and-attack framework and receive its grounded,
complete, preferred, and stable extensions without text inference or approximation.

**Independent test**: Known examples and exhaustive three-argument frameworks satisfy
the formal definitions; over-capacity frameworks fail rather than return partial results.

### Acceptance scenarios

1. A valid framework returns every extension in deterministic supplied-argument order.
2. Grounded semantics are calculated independently as the least characteristic-function fixed point.
3. Unknown attack endpoints, duplicate or empty arguments, malformed attacks, and invalid capacities are rejected.
4. A framework above the declared capacity produces a typed non-retryable failure.

## User Story 2 — Preserve explicit input lineage (Priority: P2)

As an analyst, I can distinguish a framework supplied directly from one I explicitly
derived from another technique result, with the exact upstream result identity retained.

**Independent test**: Direct and derived provider requests produce distinct `input_origin`
values, and only a derived request carries its exact upstream technique and digest.

### Acceptance scenarios

1. A direct structured input records `input_origin: supplied`.
2. An explicitly derived input records `input_origin: explicitly_derived` plus the named upstream result.
3. Raw text without a framework is unavailable with `missing_structured_input`, not inferred or failed.

## User Story 3 — Use the provider through the aggregate machine (Priority: P3)

As a machine consumer, I receive a truthful Dung declaration, native result, provenance,
and typed deterministic failures through the common provider contract.

**Independent test**: `Machine([DungProvider()])` exposes the canonical framework and
formalism identities, returns native Dung payloads, and preserves provider failure codes.

### Acceptance scenarios

1. Capability is available because the deterministic provider can run when imported.
2. The declaration requires structured input and exposes only `dung_extensions`.
3. Provenance names `rdam.dung`, the installed distribution version, MIT licence, and a digest of provider source.
4. An undeclared formalism and malformed framework produce stable non-retryable failure codes.

## Requirements

- **FR-001**: The provider MUST evaluate only supplied or explicitly derived structured frameworks and MUST NOT infer a framework from raw text.
- **FR-002**: A framework MUST contain unique non-empty argument names and attacks whose endpoints both name declared arguments.
- **FR-003**: Public framework construction and mapping construction MUST enforce the same invariants.
- **FR-004**: Evaluation capacity MUST be a positive non-boolean integer and MUST be enforced before exhaustive enumeration.
- **FR-005**: Grounded, complete, preferred, and stable extensions MUST implement the stated Dung definitions exactly.
- **FR-006**: Extension output MUST be deterministic and respect supplied argument order.
- **FR-007**: Results MUST include the validated framework, all four semantics, algorithm name/version/capacity, and input origin.
- **FR-008**: Explicit derivation MUST retain the upstream technique and exact result identity.
- **FR-009**: Missing structured input MUST be unavailable; malformed, over-capacity, and undeclared-formalism requests MUST be typed non-retryable failures.
- **FR-010**: The provider MUST declare `Technique.DUNG`, the canonical Dung CURIE, formalism `dung_extensions`, and provider id `rdam.dung/exhaustive-subset-v1`.
- **FR-011**: Provenance MUST derive its source revision from the shipped semantics and provider source bytes.
- **FR-012**: Production code MUST remain deterministic, local, and free of offline dependencies.

## Success criteria

- **SC-001**: Every one of the 512 directed attack graphs over three arguments satisfies the semantics invariants.
- **SC-002**: At least 200 seeded random frameworks of one to eight arguments satisfy the same invariants reproducibly.
- **SC-003**: All malformed-structure and capacity counterexamples fail with their specified type/code.
- **SC-004**: Repeated evaluation produces byte-equivalent payload ordering.
- **SC-005**: Dung, aggregate-machine, static, boundary, and complete repository gates pass.

## Scope

This feature covers exact exhaustive semantics for bounded finite frameworks and the
`rdam` provider adapter. It does not derive arguments from text, add approximation,
introduce other argumentation semantics, or change aggregate contracts.
