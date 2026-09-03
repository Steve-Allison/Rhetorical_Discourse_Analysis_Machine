# Feature Specification: IBIS Provider

**Feature**: `012-ibis-provider`

**Created**: 2026-09-02

**Reconciled**: 2026-09-03

**Status**: Complete

## User Story 1 — Validate a native gIBIS structure (Priority: P1)

As an analyst, I supply issue, position, and argument nodes with typed links and receive
an exact validation verdict without repair, extraction, or judgement.

**Independent test**: Every 3 × 3 × 8 kind-pair/relation combination agrees with the
declared grammar, and malformed direct or mapping construction is rejected identically.

### Acceptance scenarios

1. Nodes have unique non-empty ids, non-blank text, and an issue/position/argument kind.
2. Links reference known distinct nodes and use a relation permitted for their endpoint kinds.
3. Every position responds to exactly one issue; every argument supports or objects to exactly one position.
4. Duplicate links and invalid public direct construction are rejected.

## User Story 2 — Organise deliberation without judging it (Priority: P2)

As an analyst, I receive each issue with its positions, supporting/objecting arguments,
issue relations, and structural gaps, without validity, strength, or acceptability scores.

**Independent test**: A representative structure produces an exact deterministic map and
round-trips through its native payload unchanged.

### Acceptance scenarios

1. Map order follows supplied node/link order.
2. Issues without positions, positions without arguments, and isolated nodes are named.
3. `extraction` is always `null` because this provider never extracts from text.

## User Story 3 — Use IBIS through the aggregate machine (Priority: P3)

As a machine consumer, I receive truthful capability, native IBIS results, explicit
lineage, source provenance, and stable typed failures.

**Independent test**: Aggregate requests distinguish supplied, explicitly derived,
text-only, malformed, and undeclared-formalism cases.

### Acceptance scenarios

1. The deterministic provider is available and requires structured input.
2. Derived structures retain the exact upstream technique/result identity while extraction remains null.
3. Text-only input is unavailable rather than inferred or failed.
4. Grammar violations and undeclared formalisms are non-retryable typed failures.

## Requirements

- **FR-001**: The provider MUST validate only supplied or explicitly derived IBIS structures and MUST NOT extract them from text.
- **FR-002**: Public node, link, structure, and mapping construction MUST enforce the same invariants.
- **FR-003**: The eight declared relations MUST accept exactly the endpoint-kind combinations in `GRAMMAR`.
- **FR-004**: Node ids MUST be unique non-empty strings and node text MUST contain non-whitespace content.
- **FR-005**: Links MUST be unique, reference declared distinct nodes, and satisfy their typed relation.
- **FR-006**: Position and argument attachment cardinalities MUST be exactly one under their permitted attachment relations.
- **FR-007**: The deliberation map MUST reorganise only supplied content and MUST NOT score or judge it.
- **FR-008**: Native structure and map serialization MUST be deterministic and round-trippable.
- **FR-009**: Results MUST record `input_origin`, `extraction: null`, grammar `gibis-v1`, structure, and map.
- **FR-010**: Explicit derivation MUST retain the upstream technique and exact result identity.
- **FR-011**: The provider MUST declare `Technique.IBIS`, the canonical IBIS CURIE, formalism `ibis_structure`, and id `rdam.ibis/gibis-grammar-v1`.
- **FR-012**: Provenance MUST derive its revision from the shipped grammar and provider source bytes.
- **FR-013**: Production code MUST remain deterministic, local, and free of offline dependencies.

## Success criteria

- **SC-001**: All 72 endpoint-kind/relation combinations match `GRAMMAR`.
- **SC-002**: Direct-constructor and payload counterexamples fail with `StructureError`.
- **SC-003**: Representative native payloads round-trip exactly and maps remain deterministic.
- **SC-004**: Missing, malformed, derived, and successful aggregate cases retain their distinct typed outcomes.
- **SC-005**: IBIS, static, boundary, ontology, and complete repository gates pass.

## Scope

This feature covers the gIBIS issue-position-argument dialect and deterministic structural
organisation. It does not extract from prose, judge arguments, add later Compendium node
types, or perform Dung-style formal evaluation.
