# Feature 011: Dung Abstract Argumentation Provider

**Status**: implemented and promoted 2026-09-02; relocated to `rdam.dung` and re-promoted the same day (§Promotion decision) | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-002, FR-012, FR-016, FR-020, FR-022 (formal clause), FR-024; [006 promotion-evidence contract](../006-rhetorical-discourse-machine/contracts/promotion-evidence.md) §Formal techniques; [008 promotion system](../008-promotion-system/spec.md) | **Owner ruling**: "build it all" (2026-09-02)

The first provider after RST, first in the spec's order because it is formal,
deterministic, and verifiable by proof and property test rather than by corpus.

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| Boundary `dung/` created on first promotion (FR-002); import name `rdam_dung`, never `dung` | `dung/rdam_dung/`, distribution `rdam-dung`, depends on `rdam` only | boundary inspection `valid: true`, 104 production modules |
| Formal evaluation of a supplied or explicitly derived framework, never raw-text inference (FR-016) | `semantics.py`: `ArgumentationFramework.from_payload`, extensions under grounded, complete, preferred, stable semantics as Dung (1995) defines them (definitions in the module docstring); `provider.py` requires structured input and records `input_origin: supplied` | `tests/dung/test_provider.py::test_supplied_framework_is_evaluated_and_never_derived_from_text`, `…missing_structured_input_is_unavailable_not_failed` |
| Exactness over approximation | complete extensions by exhaustive enumeration under a declared capacity (14); grounded independently by fixed-point iteration; over-capacity input is a typed `not_retryable` failure | `TestValidation::test_capacity_is_enforced_not_approximated`, `test_over_capacity_is_refused_not_approximated` |
| Output-quality evidence for a formal technique (FR-022): correctness arguments and property tests against the definitions | correctness arguments in the module docstring and the decision; invariants tested exhaustively over all 512 three-argument frameworks and 200 seeded random frameworks up to eight arguments, plus textbook cases | `tests/dung/test_semantics.py` (20 tests) |
| Capability only via a `promote` decision (FR-020); the decision names the exact artifact (FR-023) | `resources/promotion-decision.json` packaged with the provider; `artifact_identity` = digest of `semantics.py` + `provider.py`; a source change without a new decision → `unavailable(no_promoted_implementation)` | `test_a_decision_about_other_code_does_not_promote_this_code`, `test_a_promote_decision_naming_this_source_makes_it_available` |
| Declared to the machine with its canonical identity | `technique_curie(Technique.DUNG)` = `coe:concept/analytical_frameworks_taxonomy/argumentation_framework/dung`; formalism `dung_extensions` | `TestDeclaration` |

## Promotion decision

`workbench/promotions/dung/rdam-dung-exhaustive-subset-v1-promote-2026-09-02.json`,
outcome **promote** — every evidence class admissible: formal quality (correctness
arguments and property tests), calibration declared absent (deterministic), latency
measured on this machine, compatibility verified in both pixi environments, provenance
naming commit `b5e35c5` and the source digest, licensing MIT (own code). This is the
machine's first `available` provider under the 008 gate.

**Relocation (owner ruling 2026-09-02, [010 §Single package](../010-repository-migration/spec.md))**:
the provider moved to `rdam/dung` inside the single `rdam` package; its provider id is
`rdam.dung/exhaustive-subset-v1` and its source digest changed with the import lines.
The same semantics were re-promoted by
`workbench/promotions/dung/rdam.dung-exhaustive-subset-v1-replace-2026-09-02.json`,
outcome **replace** (replaces `rdam_dung/exhaustive-subset-v1`), provenance naming
commit `6a647b6`; the packaged decision is `rdam/dung/resources/promotion-decision.json`.

## Limitations recorded in the decision

Capacity 14 arguments (exhaustive); grounded/complete/preferred/stable only; supplied
frameworks only. A labelling-based algorithm or additional semantics would be a new
candidate with its own decision.

## Gates

See [evidence/gates.md](evidence/gates.md).
