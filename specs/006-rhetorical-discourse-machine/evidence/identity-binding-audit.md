# Evidence: Canonical Identity Binding Audit

**Task**: T006 | **Contract**: [../contracts/capability-declaration.md](../contracts/capability-declaration.md) §Identity binding
**Requirement**: FR-002 | **Date**: 2026-09-01

## Resolution source

| Fact | Value |
|---|---|
| Repository | `/Users/steveallison/AI_Projects+Code/Central_Configs` |
| File | `ontology/data/domains/narrative/analytical_frameworks.yaml` |
| Resolved at | `origin/main` = `46056cddfeb01a526c270bdf3bace7911e779cc6` (= local `HEAD`; working tree clean for this file) |
| Registration commit | `f701df7` "Register the analytical-frameworks identity taxonomy (rdam-006)" — ancestor of `origin/main` |
| Amendment commit | `9c48ca6` "Amend argument_role to Toulmin's complete six-element layout" — ancestor of `origin/main` |
| Version-field retirement | `59283fc` "Type every threshold, define every description, retire artifact versions" (31 files, estate-wide) — ancestor of `origin/main` |
| Scheme | `coe:artifact/narrative/analytical_frameworks_taxonomy`, `status: canonical`, `last_updated: 2026-08-31`. No `version` field: retired deliberately at `59283fc`. |

## Identifier resolution — all eight

Each row was read from the taxonomy file. `id`, `label`, and scheme membership
(`in_scheme` plus `broader`) were compared against the contract's §Identity binding
clause 1. All eight resolve exactly.

| # | Contract identifier | Resolved `id` | `label` | `in_scheme` | `broader` | `status` |
|---|---|---|---|---|---|---|
| 1 | `…/discourse_structure_framework/rst` | `coe:concept/analytical_frameworks_taxonomy/discourse_structure_framework/rst` | Rhetorical Structure Theory | taxonomy | `…/discourse_structure_framework` | canonical |
| 2 | `…/discourse_structure_framework/erst` | `…/discourse_structure_framework/erst` | Enhanced Rhetorical Structure Theory | taxonomy | `…/discourse_structure_framework` | canonical |
| 3 | `…/discourse_structure_framework/pdtb` | `…/discourse_structure_framework/pdtb` | Penn Discourse Treebank | taxonomy | `…/discourse_structure_framework` | canonical |
| 4 | `…/discourse_structure_framework/sdrt` | `…/discourse_structure_framework/sdrt` | Segmented Discourse Representation Theory | taxonomy | `…/discourse_structure_framework` | canonical |
| 5 | `…/argumentation_framework/toulmin` | `…/argumentation_framework/toulmin` | Toulmin Model | taxonomy | `…/argumentation_framework` | canonical |
| 6 | `…/argumentation_framework/walton` | `…/argumentation_framework/walton` | Walton Argumentation Schemes | taxonomy | `…/argumentation_framework` | canonical |
| 7 | `…/argumentation_framework/dung` | `…/argumentation_framework/dung` | Dung Abstract Argumentation | taxonomy | `…/argumentation_framework` | canonical |
| 8 | `…/argumentation_framework/ibis` | `…/argumentation_framework/ibis` | Issue-Based Information System | taxonomy | `…/argumentation_framework` | canonical |

`in_scheme` is `coe:artifact/narrative/analytical_frameworks_taxonomy` for all eight.
Both parent concepts (`discourse_structure_framework`, `argumentation_framework`) are
declared `top_concepts` of the scheme. **Zero dangling `coe:` identifiers.** FR-002's
binding is verified against the live authority, pre-vendoring.

## Concepts present in Central but not bound by this contract

Recorded so a future feature does not mistake absence for oversight. Three canonical
concepts in the same scheme are deliberately unbound by feature 006:

| Concept | Why unbound |
|---|---|
| `…/argumentation_framework/argument_mining` | A *technique for producing* argument structure, not one of the seven technique boundaries. FR-019's truth-in-labelling rule requires the Toulmin and Walton native validators to refuse a generic claim/premise extraction rather than relabel it. |
| `…/communication_framework` and `…/communication_framework/pyramid_principle` | Prescriptive communication frameworks — the taxonomy's own description contrasts them with "the analytical frameworks that represent what an existing text or argument is". The machine is permanently analysis-only (spec §Scope Boundaries), so these are correctly outside it. |

## Resolved: the taxonomy carries no `version` field

An earlier pass of this audit (against `origin/main` = `33a1b7c`) found the local Central
HEAD had dropped `version: 1.0.0` from the taxonomy and flagged it as a possible
accident. Re-verified after Central was pushed: the removal is commit `59283fc` "Type
every threshold, define every description, **retire artifact versions**", which touched
31 files across every domain — a deliberate estate-wide schema change, now on
`origin/main`. `plan.md`'s "v1.0.0" citation was the stale reference and has been
corrected to cite the retirement. The taxonomy is identified by `id` and `last_updated`.
All eight concept identities were re-checked at `46056cd` and are byte-identical to the
full read recorded above (`git diff f96ea0d HEAD -- <file>` is empty).
