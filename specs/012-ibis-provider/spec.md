# Feature 012: IBIS Provider

**Status**: implemented and promoted 2026-09-02 | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-002, FR-012, FR-017, FR-020, FR-022 (formal clause), FR-024; [006 promotion-evidence contract](../006-rhetorical-discourse-machine/contracts/promotion-evidence.md) §Formal techniques; [008 promotion system](../008-promotion-system/spec.md); [010 §Single package](../010-repository-migration/spec.md) (layout) | **Owner ruling**: "build it all" (2026-09-02)

The second provider after RST, second in the spec's order because — like Dung — it is
formal, deterministic, and verifiable by proof and property test rather than by corpus.
IBIS (Kunz & Rittel 1970) records deliberation as issues, positions, and arguments; the
typed link grammar implemented is gIBIS's (Conklin & Begeman 1988).

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| Sub-package `rdam.ibis` created on first promotion (FR-002); never a top-level `ibis` (the PyPI Ibis dataframe library's import name) | `rdam/ibis/` inside the single `rdam` package | boundary inspection `valid: true`, 106 production modules |
| Records what was said; extracts nothing from text (FR-017) | `provider.py` requires structured input, records `input_origin: supplied` and `extraction: None`; a text-only request is `unavailable(missing_structured_input)`, not a failure | `tests/ibis/test_provider.py::test_supplied_structure_is_validated_and_mapped_with_no_extraction`, `…test_text_only_request_is_unavailable_not_failed` |
| The gIBIS link grammar, exactly | `grammar.py`: `GRAMMAR` (the permitted from-kind/to-kinds per relation, transcribed in the module docstring), `ATTACHMENT` (a position responds to exactly one issue; an argument supports or objects to exactly one position), unique ids, no self-links; a structure that breaks a rule is refused as malformed, never repaired | `tests/ibis/test_grammar.py::TestLinkTyping` (all 3 × 3 × 8 kind–kind–relation combinations against the table), `TestAttachment` |
| The analysis is organisation, not judgement | `deliberation_map`: each issue with its positions and each position's supporting and objecting arguments, issue–issue relations, and gap observations (issues without positions, positions without arguments, isolated nodes); no validity, strength, or acceptability is computed | `TestDeliberationMap` |
| Output-quality evidence for a formal technique (FR-022) | correctness arguments in the decision (link typing, attachment, map-as-reorganisation); property tests exhaustive over the type table | `tests/ibis` (12 tests) |
| Capability only via a `promote` decision naming the exact artifact (FR-020, FR-023) | `resources/promotion-decision.json` packaged with the provider; `artifact_identity` = digest of `grammar.py` + `provider.py`; a source change without a new decision → `unavailable(no_promoted_implementation)` | `test_stale_decision_does_not_promote`, `test_promote_decision_naming_this_source_is_available` |
| Declared to the machine with its canonical identity | `technique_curie(Technique.IBIS)` = `coe:concept/analytical_frameworks_taxonomy/argumentation_framework/ibis`; formalism `ibis_structure`; structured input required | `TestDeclaration` |

## Promotion decision

`workbench/promotions/ibis/rdam.ibis-gibis-grammar-v1-promote-2026-09-02.json`,
outcome **promote** — every evidence class admissible: formal quality (correctness
arguments and property tests), calibration declared absent (deterministic), latency
measured on this machine, compatibility verified in both pixi environments, provenance
naming commit `6a647b6` and the source digest, licensing MIT (own code). Packaged as
`rdam/ibis/resources/promotion-decision.json`; provider id `rdam.ibis/gibis-grammar-v1`.

## Limitations recorded in the decision

Supplied structures only (no extraction from text — by design, FR-017); the gIBIS
grammar only (later dialects such as Compendium's map, list, and decision nodes are not
represented); no argument strength or acceptability — formal evaluation of an argument
graph is the Dung provider's job.

## Gates

See [evidence/gates.md](evidence/gates.md).
