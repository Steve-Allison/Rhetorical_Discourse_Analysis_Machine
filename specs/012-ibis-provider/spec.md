# Feature 012: IBIS Provider

**Status**: implemented 2026-09-02 | **Authority**: [006 spec](../006-rhetorical-discourse-machine/spec.md) FR-002, FR-012, FR-017, FR-020, FR-024; [010 §Single package](../010-repository-migration/spec.md) (layout) | **Owner ruling**: "build it all" (2026-09-02)

> **Amended 2026-09-02**: the promotion-evidence gate was removed by owner ruling (see [006 spec](../006-rhetorical-discourse-machine/spec.md)). Capability now means the provider can run. The correctness arguments and property tests below are unchanged and still hold; what is gone is the ceremony that stood between them and `available`.

The second provider after RST, second in the spec's order because — like Dung — it is
formal, deterministic, and verifiable by proof and property test rather than by corpus.
IBIS (Kunz & Rittel 1970) records deliberation as issues, positions, and arguments; the
typed link grammar implemented is gIBIS's (Conklin & Begeman 1988).

## What was built

| Requirement | Artifact | Proof |
|---|---|---|
| Sub-package `rdam.ibis` created on first implementation (FR-002); never a top-level `ibis` (the PyPI Ibis dataframe library's import name) | `rdam/ibis/` inside the single `rdam` package | boundary inspection `valid: true`, 106 production modules |
| Records what was said; extracts nothing from text (FR-017) | `provider.py` requires structured input, records `input_origin: supplied` and `extraction: None`; a text-only request is `unavailable(missing_structured_input)`, not a failure | `tests/ibis/test_provider.py::test_supplied_structure_is_validated_and_mapped_with_no_extraction`, `…test_text_only_request_is_unavailable_not_failed` |
| The gIBIS link grammar, exactly | `grammar.py`: `GRAMMAR` (the permitted from-kind/to-kinds per relation, transcribed in the module docstring), `ATTACHMENT` (a position responds to exactly one issue; an argument supports or objects to exactly one position), unique ids, no self-links; a structure that breaks a rule is refused as malformed, never repaired | `tests/ibis/test_grammar.py::TestLinkTyping` (all 3 × 3 × 8 kind–kind–relation combinations against the table), `TestAttachment` |
| The analysis is organisation, not judgement | `deliberation_map`: each issue with its positions and each position's supporting and objecting arguments, issue–issue relations, and gap observations (issues without positions, positions without arguments, isolated nodes); no validity, strength, or acceptability is computed | `TestDeliberationMap` |
| Correctness for a formal technique | correctness arguments (link typing, attachment, map-as-reorganisation); property tests exhaustive over the type table | `tests/ibis` (12 tests) |
| Capability is explicit and the provider names its own source (FR-020) | the grammar is exact, so the provider is `available` whenever it is imported; `provenance.source_revision` is the digest of `grammar.py` + `provider.py` | `TestDeclaration::test_the_provider_is_available_and_names_its_own_source` |
| Declared to the machine with its canonical identity | `technique_curie(Technique.IBIS)` = `coe:concept/analytical_frameworks_taxonomy/argumentation_framework/ibis`; formalism `ibis_structure`; structured input required | `TestDeclaration` |

## Provenance

Provider id `rdam.ibis/gibis-grammar-v1`. The provider declares its own provenance to the
machine: package `rdam.ibis`, the distribution version, the digest of `grammar.py` +
`provider.py` as `source_revision`, and licence MIT (own code).

**Lineage (FR-015/FR-017, [007 §Lineage](../007-aggregate-contract/spec.md))**: the
provider records `input_origin: supplied | explicitly_derived` and, when derived, the
caller's named upstream result; `extraction` stays `None`.

## Limitations

Supplied structures only (no extraction from text — by design, FR-017); the gIBIS
grammar only (later dialects such as Compendium's map, list, and decision nodes are not
represented); no argument strength or acceptability — formal evaluation of an argument
graph is the Dung provider's job.

## Gates

See [evidence/gates.md](evidence/gates.md).
