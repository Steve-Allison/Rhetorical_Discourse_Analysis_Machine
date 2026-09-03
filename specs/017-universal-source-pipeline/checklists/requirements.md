# Specification Quality Checklist: Universal Source Pipeline

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
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

## Coverage

Every requirement traces to a criterion, and every criterion to a check in
[quickstart.md](../quickstart.md).

| Requirement group | FRs | Criteria |
|---|---|---|
| Relocation and ownership | FR-001..FR-006 | SC-010, SC-017 |
| One inventory | FR-007..FR-011 | SC-001, SC-002 |
| Declared projections | FR-012..FR-019 | SC-003, SC-004, SC-005, SC-006 |
| Speaker identity | FR-020..FR-022 | SC-007, SC-008 |
| Capacity and planning | FR-023..FR-025 | SC-009 |
| Format coverage | FR-026, FR-027 | SC-001 |
| Caching | FR-028..FR-031 | SC-011, SC-012 |
| Concurrency | FR-032..FR-036 | SC-013, SC-014 |
| Alignment and boundaries | FR-037..FR-039 | SC-015 |
| Whole feature | — | SC-016, SC-017 |

## Notes

Two items are recorded as passing with an argument rather than ticked by default.

**"No implementation details" and "written for non-technical stakeholders".** The Context
section names modules, files, and specific contract fields, and FR-001 to FR-006 name
`rdam.ingest`, `rdam.rst.ingest`, `PreparedRstDocument`, `ParserCapacity`, and the persisted
identifier `isanlp_rst.production` 2.0.0. Judged a pass on three grounds:

1. The identifiers **are** the requirement. FR-004 — that persisted contract identifiers must
   not change — is unstatable without naming them.
2. The Context section's precision is what makes the feature honest. The claim that justifies
   the whole projection model is that `primary_classes` is one global tuple excluding
   `TABLE`. Stated abstractly it is an opinion; stated with the field name it is checkable.
3. It matches the established authority. Features 006 and 009–016 are written this way, and
   the constitution names `AGENTS.md`/`CLAUDE.md` as binding operational authorities whose
   conventions apply. The sole stakeholder owns the codebase.

Everything outside Context and the relocation requirements is written in outcome terms.
SC-013 says "materially less wall-clock time than the sum", not a thread count. SC-004 says
grounds anchor to the cells they came from, not how linearisation is implemented.

**Scope.** This feature is larger than the relocation it began as, following the owner
ruling of 2026-09-03 not to split it. That is a deliberate scope decision, not accretion:
delivering the pipeline alone would hand all seven techniques the RST projection, producing
confabulated Toulmin grounds and speaker-less SDRT — analyses that look correct and are not.
Under constitution principle III, omitting required behaviour is a defect rather than
simplicity. The projection model is the smallest design that makes the pipeline correct for
the machine that now exists.

## Constitution compliance

Against `.specify/memory/constitution.md` v2.0.0:

| Principle | How this spec complies |
|---|---|
| I. Evidence Before Claims | Every Context row was verified on 2026-09-03 by reading `contracts/source.py` and `contracts/preparation.py` **in full**, not by grep. The three findings that most shaped the design — `CapacityUnit` already offering `token_count`, `TransformationRecord` existing but having no table parameter kind, and no speaker field anywhere — would each have been got wrong from a partial read. Parser concurrency on MPS is carried as an open risk (research R8), not asserted. |
| II. One Production Quality Bar | SC-017 forbids introducing any suppression and requires every gate green. FR-005 forbids analytical change to RST, checked by the classified baseline comparison. |
| III. Solo-Local Simplicity | FR-039 forbids distributed execution, queues, and schedulers. Requirements are declared by providers from their formalism, never exposed as caller knobs, so no hypothetical configurability is introduced. |
| IV. Honest Verification | Every success criterion names a runnable check. SC-011's "zero model requests" is enforced by `ALLOW_MODEL_REQUESTS = False` rather than trusted. The model is the only mocked boundary. |
| V. Canonical Contracts | FR-001 gives ingest one owner; FR-002 preserves the RST surface by re-export rather than duplication; FR-006 renames technique-named contracts with aliases so no competing name appears; FR-026 keeps the capability report the sole authority on source forms. |

## Deliberate exclusions

Recorded so they are not mistaken for oversights:

- **Automating cross-technique input derivation** — FR-038 forbids it; 006 FR-015 makes
  caller declaration deliberate.
- **Inferring speakers with a model** — FR-022 forbids it. Fabricating participants is
  fabricating analysis.
- **Deprecating `rdam.rst.ingest`** — retained indefinitely pending a separate owner ruling.
- **Changing the persisted contract identifiers** — FR-004; a separate owner ruling.
- **Widening RST's admitted content** — its requirement reproduces today's policy exactly,
  which is what makes SC-010 achievable.
