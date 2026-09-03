# Research: IBIS Provider

## Decision 1 — Treat gIBIS as a typed native grammar

**Decision**: Keep the eight relations and their permitted endpoint kinds as explicit data.

**Rationale**: The finite table can be tested exhaustively and remains inspectable.

## Decision 2 — Enforce invariants in immutable values

**Decision**: Validate public `Node`, `Link`, and `IbisStructure` construction as well as mapping decoding.

**Rationale**: Equivalent native structures must not become valid or invalid based on construction path.

## Decision 3 — Reorganise without judgement

**Decision**: Map issues, positions, pro/con arguments, relations, and structural gaps only.

**Rationale**: IBIS records deliberation. Argument acceptability belongs to a different technique.

## Decision 4 — Keep lineage caller-explicit

**Decision**: Record derivation only from a supplied upstream reference and always report extraction as null.

**Rationale**: This provider validates and organises; it performs no automated extraction.
