# Specification Quality Checklist: Rhetorical Discourse Analysis Machine Architecture

**Purpose**: Validate specification completeness and quality before proceeding to planning

**Created**: 2026-08-31

**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No `[NEEDS CLARIFICATION]` markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validation iteration 1 passed all checklist items.
- Exact boundary names and the preserved `isanlp_rst` import name are approved product constraints, not implementation choices.
- Validation iteration 2 (2026-08-31, owner-approved amendments): scope fixed as permanently analysis-only with generation owned downstream; FR-002 now binds each boundary to its canonical Central_Configs framework identifier and defers directory creation to first promotion; FR-022 adds formal-technique correctness evidence; FR-025 stages specification so technique-provider features follow workbench evidence instead of preceding all migration; assumptions record ontology binding (identity only, never inventory constraint), provider priority (Dung, IBIS, SDRT, Toulmin/Walton, PDTB-if-ever), and the no-top-level-import-name rule. The `coe:` identifier binding and package-naming rule are approved product constraints, not implementation choices. All checklist items re-verified against the amended text.
- Validation iteration 3 (2026-09-01, post-`$speckit-analyze`): the follow-on feature family grows to eleven members — repository migration is now its own decision-closed feature carrying baseline capture, migration safety, packaging verification, and identity adoption (analysis finding I1); SC-009 updated to match. Findings U1 (eRST capability representation) and I2 (`tests/offline/research` ownership) are folded into tasks T012 and T004 respectively for in-pass resolution. Zero critical findings; constitution alignment clean.
- Validation iteration 4 (2026-09-01, owner ruling): the estate division of analytical labour is recorded — the machine is the sole authority for technique-native structures at every tier (heavy LLM-assisted analysis included, promotion-gated); AI_Skills `concept-extract` is the bounded Lite annotation tier (vocabulary-typed spans only, never native structures); Content_Structuring_Machine is the primary named consumer via public contracts with no analysis semantics of its own, and its needs are named design input to the aggregate-contract and RST-adapter features. Structures = machine, annotations = Lite skill, meaning = Central_Configs.
- Validation iteration 5 (2026-09-01, owner ruling): the iteration-4 division-of-labour wording is superseded. The machine is a standalone centre of excellence for discourse/argumentation analysis: sole authority for technique-native structures at every tier, delivering findings downstream through its public contracts to whichever consumers exist, privileging none — no consumer's needs shape its contracts, semantics, or roadmap, and other projects and skills are outside this specification's scope entirely.
- Validation iteration 6 (2026-09-01, owner-prompted audit): the standardised-patterns register (`contracts/standardised-patterns.md`) maps the twelve shared runtime patterns — failure algebra, retryability/retry, semantic identity and canonical serialization, composite identity and cache eligibility, atomic persistence, validation receipts, execution evidence, capability reporting, safe boundary projections, source acquisition/anchoring, model loading/device handling, and gate evidence records — each with its verified reference authority in the RST provider, a binding adopt-semantics-not-code rule, and its FR-029 extraction trigger. The P10 ingest-reuse question is a named obligation of the SDRT feature. No shared library is created; FR-029 still gates extraction per pattern.
- The specification is decision-closed and ready for `$speckit-plan`; no clarification pass is required.

---

## Completion note (2026-09-01, T012)

Feature 006 ships governance artifacts, so its acceptance is documentary. This note
records honestly which success criteria are **demonstrated now** and which are
**deferred**, with the deferral authority. Evidence lives in
[`../evidence/`](../evidence/).

### Demonstrated now

| Criterion | Demonstrated by | Result |
|---|---|---|
| **SC-001** — every top-level path has exactly one named owner, zero ambiguous | T004, [`evidence/boundary-audit.md`](../evidence/boundary-audit.md) | **MET for the current tree.** Five unowned path classes (`config/`, `dist/`, `examples/`, `graphify-out/`, root files) were found and resolved by extending the roster; the one two-owner candidate (`tests/offline/research`, analysis finding I2) was ruled to `tests/` under FR-007's distinction-within-`tests/` allowance. Note: SC-001's own enumeration names only the techniques, workbench, verification, aggregation, and planning material — narrower than the tree it must cover. The audit was run against the **full** tree, which is the stricter reading. |
| **SC-007** — zero unavailable techniques represented by stubs or fabricated structures | T004 | **MET.** All nine approved boundary directories (`rst`, `pdtb`, `sdrt`, `toulmin`, `walton`, `dung`, `ibis`, `machine`, `ontology`) are absent. Not one was created speculatively. |
| **FR-002** — identity binding to the canonical taxonomy | T006, [`evidence/identity-binding-audit.md`](../evidence/identity-binding-audit.md) | **MET.** All eight `coe:` identifiers resolve at Central `origin/main` (`33a1b7c`) with matching ids, labels, and scheme membership. Zero dangling identifiers. |
| **FR-025** — cross-artifact consistency check for this feature | T011 | **MET.** Six findings (2 HIGH, 3 MEDIUM, 1 LOW), all resolved in the same pass. Zero critical, zero constitution violations. |
| **FR-027** — existing artifacts assessed, not presumed complete | T007, [`evidence/promotion-gap-audit.md`](../evidence/promotion-gap-audit.md) | **MET, and it bit.** The promotion flow was read in full and found to lack output-quality, calibration, and latency evidence entirely; licensing is a hardcoded constant. Three Feature-005-era defects were found live and fixed forward: the promotion tool fabricated the evidence string `"GUM-12.1.0 Parseval evaluation verified"` when no receipt existed (that literal sits in the promoted `e5ea56cd620f` release); the contract-named smoke script could not pass against the archived-family `Parser`; and the published 5.0.0 wheel had been replaced by an ad hoc build without provenance and failed `validate-production-artifacts` behind a commit message claiming clean-room certification (rst-surface-audit defect 4 — pair retired and rebuilt reproducibly with owner authorisation). |

### Deferred, with authority

Deferral authority throughout is [`../spec.md`](../spec.md) §Scope Boundaries, which
states that feature 006 does not move files, implement the aggregate contract or
orchestration runtime, adopt any non-RST provider, or certify features 004/005.

| Criterion | Deferred to | Note |
|---|---|---|
| **SC-002** — 100% RST equivalence post-migration | Repository migration feature | The comparison itself needs a migration to compare against. Everything 006 can do is done: the preservation contract is evidence-backed (T002), and every baseline command was **run and is green** (T003): `test-all` 868 passed, `production-api-contract` 244 passed, `smoke-full-mps` PASS on both releases — after fixing the smoke script, which loaded archived families and could never have passed (rst-surface-audit defect 3). FR-026 was checked, not assumed: no training process was live. |
| **SC-003** — zero workbench imports and zero workbench distributable members | Aggregate-contract feature (007) | The `production-boundary` gate is green today (`valid: true`, zero violations), but the research-D5 extension implementing **both** checks does not exist. The green result certifies the current rule set only. |
| **SC-004, SC-005, SC-010** — aggregate behaviour and provider independence | Aggregate-contract feature (007) | No aggregate runtime exists to test. |
| **SC-006** — promotion evidence completeness | Workbench-promotion-system feature | **Not met by the existing flow** — see the T007 gap list. Artifact identity is strong; output quality is absent. |
| **SC-008** — migration safety state | Repository migration feature | Failing by design today: live workbench runs and unreconciled artifacts exist. This is exactly what FR-026 blocks on. |
| **SC-009** — eleven decision-closed follow-on features | Each follow-on feature | 006 is the first; the remaining eleven are enumerated in spec Assumptions. |
| **SC-011** — single-person, single-machine operability | Standing constraint | No feature-006 artifact introduces multi-user, distributed, or enterprise machinery. |

### eRST capability representation — analysis finding U1, **resolved 2026-09-01**

One provider (`isanlp_rst`) serves two canonical identities — `…/rst` and `…/erst` —
while `Provider.technique_id` was single-valued and one-to-one with its boundary, so the
data model could not express what the provider actually does. Two options were open:
a multi-valued `technique_id` (matches Central, which registers `erst` as a sibling
concept), or eRST as a declared result-kind of the RST capability (matches the running
code, where `describe_capabilities()` reports `rst_tree` and `erst_graph` as separate
`formalism_capabilities` under one provider).

**Ruling: one provider, two declared formalisms, each with its own canonical identity
and capability state.** The boundary and provider bind to `…/rst`; the provider declares
`rst_tree → …/rst` and `erst_graph → …/erst`. This satisfies both constraints at once —
it keeps boundary-to-identity one-to-one, references Central's `erst` concept
canonically without redefining it, and is byte-for-byte what the implementation does
today (`erst_graph` reports `unavailable` on its own when no completion bundle is
loaded; the rewritten smoke asserts it is refused, never fabricated). Recorded in
[`data-model.md`](../data-model.md) §Formalism and
[`contracts/capability-declaration.md`](../contracts/capability-declaration.md)
§Identity binding clause 4; feature 007 implements it, it does not re-decide it.

The same undercount had surfaced in [`quickstart.md`](../quickstart.md) V7 ("seven
curies" against a contract binding eight); corrected.
