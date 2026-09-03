# Feature 011: Dung Abstract Argumentation Provider

**Status**: implemented 2026-09-02; relocated to `rdam.dung` the same day | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-002, FR-012, FR-016, FR-020, FR-024 | **Owner ruling**: "build it all" (2026-09-02)

> **Amended 2026-09-02**: the promotion-evidence gate was removed by owner ruling (see [006 spec](../006-rhetorical-discourse-machine/spec.md)). Capability now means the provider can run. The correctness arguments and property tests below are unchanged and still hold; what is gone is the ceremony that stood between them and `available`.

The first provider after RST, first in the spec's order because it is formal,
deterministic, and verifiable by proof and property test rather than by corpus.

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| Boundary `dung/` created on first implementation (FR-002); import name `rdam_dung`, never `dung` | `dung/rdam_dung/`, distribution `rdam-dung`, depends on `rdam` only | boundary inspection `valid: true`, 104 production modules |
| Formal evaluation of a supplied or explicitly derived framework, never raw-text inference (FR-016) | `semantics.py`: `ArgumentationFramework.from_payload`, extensions under grounded, complete, preferred, stable semantics as Dung (1995) defines them (definitions in the module docstring); `provider.py` requires structured input and records `input_origin: supplied` | `tests/dung/test_provider.py::test_supplied_framework_is_evaluated_and_never_derived_from_text`, `…missing_structured_input_is_unavailable_not_failed` |
| Exactness over approximation | complete extensions by exhaustive enumeration under a declared capacity (14); grounded independently by fixed-point iteration; over-capacity input is a typed `not_retryable` failure | `TestValidation::test_capacity_is_enforced_not_approximated`, `test_over_capacity_is_refused_not_approximated` |
| Correctness for a formal technique: arguments and property tests against the definitions | correctness arguments in the module docstring; invariants tested exhaustively over all 512 three-argument frameworks and 200 seeded random frameworks up to eight arguments, plus textbook cases | `tests/dung/test_semantics.py` (20 tests) |
| Capability is explicit and the provider names its own source (FR-020) | the semantics are exact and deterministic, so the provider is `available` whenever it is imported; `provenance.source_revision` is the digest of `semantics.py` + `provider.py` | `TestDeclaration::test_the_provider_is_available_and_names_its_own_source` |
| Declared to the machine with its canonical identity | `technique_curie(Technique.DUNG)` = `coe:concept/analytical_frameworks_taxonomy/argumentation_framework/dung`; formalism `dung_extensions` | `TestDeclaration` |

## Provenance

**Relocation (owner ruling 2026-09-02, [010 §Single package](../010-repository-migration/spec.md))**:
the provider moved to `rdam/dung` inside the single `rdam` package; its provider id is
`rdam.dung/exhaustive-subset-v1` and its source digest changed with the import lines.

**Lineage (FR-015/FR-016, [007 §Lineage](../007-aggregate-contract/spec.md))**: the
provider records `input_origin: supplied | explicitly_derived` and, when derived, the
caller's named upstream result.

The provider declares its own provenance to the machine: package `rdam.dung`, the
distribution version, the digest of `semantics.py` + `provider.py` as `source_revision`,
and licence MIT (own code).

## Limitations

Capacity 14 arguments (exhaustive); grounded/complete/preferred/stable only; supplied
frameworks only. A labelling-based algorithm or additional semantics would be new work.

## Gates

See [evidence/gates.md](evidence/gates.md).
