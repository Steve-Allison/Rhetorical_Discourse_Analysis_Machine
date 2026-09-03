# Research: Dung Abstract Argumentation Provider

## Decision 1 — Retain exact exhaustive enumeration

**Decision**: Enumerate all candidate subsets up to a declared capacity and refuse larger frameworks.

**Rationale**: This is exact, deterministic, auditable, and suitable for bounded frameworks
supplied by one analyst. Refusal is more truthful than an undeclared approximation.

## Decision 2 — Calculate grounded semantics independently

**Decision**: Iterate the monotone characteristic function from the empty set rather than
selecting a result from exhaustive complete extensions.

**Rationale**: Independent algorithms make the grounded/complete agreement a useful causal invariant.

## Decision 3 — Validate every public construction path

**Decision**: Enforce framework invariants in the immutable data type itself and retain
mapping-shape validation in `from_payload`.

**Rationale**: Exporting a public constructor that can create invalid frameworks would
make downstream semantics depend on how the same conceptual input was constructed.

## Decision 4 — Keep derivation caller-explicit

**Decision**: Accept an upstream reference only when the caller supplies it; never extract
arguments or attacks from prose or another technique result inside this provider.

**Rationale**: Dung semantics evaluate a graph; graph construction is a separate analytical act.
