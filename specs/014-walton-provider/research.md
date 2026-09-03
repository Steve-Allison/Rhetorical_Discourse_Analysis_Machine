# Research: Walton Provider

**Feature**: 014 | **Date**: 2026-09-03

## D1 — Supported scheme set is explicit and versioned

**Decision**: Production supports a declared subset with stable identifiers, exact
premise roles, and ordered critical questions. The result names the scheme-set version.

**Rationale**: A smaller explicit set is honest and testable; a claim to support the
entire literature without exact roles/questions would be unbounded and false.

## D2 — Exact-role validation

**Decision**: Every instance supplies every role its scheme declares and no other role.
Missing, blank, or unknown roles fail closed.

**Rationale**: Roles carry the scheme's semantics; treating them as generic premises
would flatten the theory.

## D3 — Open questions are findings, not blanks to fill

**Decision**: Unreported questions are open by default. Addressed questions require a
source-grounded note. The provider never supplies an answer.

**Rationale**: Critical questions expose what still needs examination. Model-authored
answers would turn analysis into fabrication.

## D4 — Model proposes, catalogue disposes

**Decision**: A model selects candidate schemes and fills their roles; deterministic
native validation is the only acceptance authority. Unsupported arguments are omitted,
not forced into the nearest scheme.

## D5 — Shared bounded attempts and independent identity

**Decision**: Feature 013's shared LLM boundary owns separate output/transport budgets
and evidence. Walton owns its instructions, native validator, model-bearing provider
identity, source digest, licence, and scheme-set identity.

**Rationale**: Retry mechanics are genuinely shared; Walton semantics are not.
