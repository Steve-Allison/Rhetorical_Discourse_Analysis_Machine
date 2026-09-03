# Contract: Native Walton Result

**Feature**: 014 | **Authority**: [../spec.md](../spec.md)

- Technique: canonical Walton framework identity.
- Formalism: `walton_schemes`.
- Payload: ordered `instances`, aggregate counts, `scheme_set`, and extraction evidence.
- Each instance names one supported scheme, its conclusion, exactly its premise roles,
  uniquely reported critical questions, and the complete derived open-question set.
- Empty instances means no supported scheme was found; it is not unavailability.
- Invalid catalogue references or role/question structures never become partial results.
- Provenance contains package and contract versions, source digest, exact model identity,
  licence, and the scheme-set identity carried by the payload.
- Typed failures retain retryability and observed attempt evidence; no provider result
  answers an open critical question.
