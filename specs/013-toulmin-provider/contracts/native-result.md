# Contract: Native Toulmin Result

**Feature**: 013 | **Authority**: [../spec.md](../spec.md)

- Technique: canonical Toulmin framework identity.
- Formalism: `toulmin_layout`.
- Contract version: semantic version owned by this provider.
- Payload: `layouts`, `layout_count`, `fully_qualified_count`, and `extraction` evidence.
- Each layout contains the mandatory core triad and only the optional native elements
  defined in [../data-model.md](../data-model.md).
- Empty `layouts` means the source presents no argument; it is not unavailability.
- Unknown fields, missing core elements, warrant restatements, and malformed rebuttals
  are validation failures and never reach the caller as results.
- Provenance names the `rdam.toulmin` package, package version, source digest, exact
  model identity, and licence.
- Typed failures retain code, failed operation, exception class, safe detail,
  retryability, and attempt evidence. The machine performs no retry of a provider
  outcome.
