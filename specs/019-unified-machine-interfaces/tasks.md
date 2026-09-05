# Tasks: Unified Machine Interfaces

**Input**: Feature 019 spec, plan, research, data model and contracts.
**Status**: 46/48 active tasks verified; T044/T052 await successful inference
with a real trained eRST bundle. Final fast suite: 2685 passed; live cases:
10 passed; all four clean-install variants passed. Not 100% complete.
Owner correction: remove evaluation bureaucracy; use tests and cold critics.
Checked tasks denote only the specific work and verification recorded below.
**Tests**: Required by FR-025–FR-026 and SC-001–SC-013. Write regression tests
before corresponding repairs; record their failing baseline, then passing result.

Format: `- [ ] T### [P?] [US#?] action with paths`. Paths are repository-relative.
[P] means independent files after the phase prerequisites; it does not authorize
additional agents or concurrent mutation of shared modules.

## Phase 1: Setup and evidence baseline

- [X] T001 Reproduce the three native integrity defects using real validators and preserve the diagnostic commands/results in implementation notes in specs/019-unified-machine-interfaces/tasks.md; inspect current git changes without altering unrelated work. (FR-031, FR-032, FR-033; SC-010)
- [X] T002 Check current Docling/DocLang upstream specs, accepted versions, pins, lock and fixtures before touching rdam/ingest/contracts/source.py; reconcile any relevant stale contract/fixture behavior under AGENTS.md and record exact outcomes in specs/019-unified-machine-interfaces/research.md. (FR-008, FR-027; SC-001)
- [X] T003 Preserve valid pre-change native/aggregate v1 artifacts and expected digests under tests/interfaces/fixtures/historical/; capture old Walton partial/default-open behavior as historical evidence rather than deleting its test history. (FR-022, FR-034; SC-010)
T004–T007 withdrawn by the owner's 2026-09-04 correction: no reference-pack,
scorer or bulk-baseline prerequisite. T001–T003 preserve the relevant baseline.
The former evaluator work is not implementation progress and must not block T008.

## Phase 2: Shared contracts — blocks story implementation

- [X] T008 Split per-contract versions and add current native v2/aggregate v2/request/preparation/error/guide models in rdam/contracts.py and rdam/interpretation.py, with explicit historical v1 models/digest rules in rdam/historical.py; enforce nonempty unique ordered technique selection and preserve native formalism/exact requested scope. (FR-001, FR-002, FR-009, FR-010, FR-011, FR-022, FR-034; SC-002)
- [X] T009 Add immutable typed configuration and exact precedence/path resolution in rdam/configuration.py, covering all documented RST/LLM/Dung/execution settings and schema/evidence-policy identities without secrets or HTTP imports. (FR-003, FR-004, FR-023; SC-006)
- [X] T010 Add strict SourceEvidenceSpan contracts in rdam/ingest/contracts/evidence.py and shared source construction/base64 handling in rdam/ingest/contracts/source.py; ensure text/EDUs/bytes/path identity and .txt/.text inference agree. (FR-008, FR-009, FR-033; SC-003)
- [X] T011 Implement shared strict codecs, version registry and safe operation-error contracts in rdam/serialization.py and rdam/contracts.py; test duplicate/unknown keys, non-finite values, malformed Unicode/base64 and missing/mismatched digests in tests/interfaces/test_codecs.py. (FR-013, FR-016, FR-022, FR-034; SC-006)

Checkpoint: current/historical contracts can be validated and persisted without
model execution. Native semantic fixes below are mandatory before AI readiness.

## Phase 3: US5 — Correct native analysis and make it AI-ready (P1)

**Goal**: Correct producing-boundary semantics, then provide inline explanations
and loss-declared views. **Independent test**: real native validators/providers
produce corrected records; saved-record interpretation requires no machine run.

- [X] T012 [P] [US5] Add complete/missing/duplicate/out-of-range/not_assessable/source-evidence tests in tests/walton/test_schemes.py and tests/walton/test_provider.py, including addressed-note-only rejection and reconciled state counts. (FR-031; SC-010)
- [X] T013 [P] [US5] Add explicit/reconstructed/undetermined warrant, valid/forged span, required-reason and qualification-count tests in tests/toulmin/test_argument.py and tests/toulmin/test_provider.py. (FR-032; SC-010)
- [X] T014 [P] [US5] Add metadata-label exclusion, typed alignment relationships, repeated matches, Unicode offsets, wrong projection/anchors and projection-free provider tests in tests/machine/test_alignment.py. (FR-033; SC-009, SC-010)
- [X] T015 [P] [US5] Add historical reader/digest and incompatible-cache tests in tests/interfaces/test_historical.py and tests/llm/test_cache_key_completeness.py; prohibit fabricated CQ coverage, warrant origin and upgraded evidence roles. (FR-022, FR-034; SC-010)
- [X] T016 [P] [US5] Implement NI-01 in rdam/walton/schemes.py and rdam/walton/provider.py: complete explicit question coverage, not_assessable/reason, validated addressed evidence, catalogue-ordered output and exact counts; update extraction instructions and assessment algorithm/provider version without changing the scheme catalogue. (FR-031, FR-034)
- [X] T017 [P] [US5] Implement NI-02 in rdam/toulmin/argument.py and rdam/toulmin/provider.py: required warrant_origin/evidence/reason, source validation, qualified_layout_count and versioned instructions/provider output; retain native six-element semantics and non-restatement checks. (FR-032, FR-034)
- [X] T018 [US5] Replace arbitrary string discovery in rdam/ingest/alignment.py with typed provider-selected fields; update rdam/pdtb/provider.py, rdam/sdrt/provider.py, rdam/toulmin/provider.py and rdam/walton/provider.py to declare valid evidence roles and source spans, including direct requests without projections. (FR-029, FR-033)
- [X] T019 [US5] Bind corrected output-schema/evidence-policy/instruction identities and current envelope/provider versions in native provider declarations, rdam/_provider_provenance.py and rdam/_result_cache.py; retain old cache files but reject them for current execution. (FR-023, FR-034)
- [X] T020 [US5] Implement native-owned descriptors in rdam/rst/interpretation.py, rdam/pdtb/interpretation.py, rdam/sdrt/interpretation.py, rdam/toulmin/interpretation.py, rdam/walton/interpretation.py, rdam/dung/interpretation.py and rdam/ibis/interpretation.py; bind descriptors through their provider.py declarations, including historical_unavailable handling. (FR-028, FR-029; SC-009)
- [X] T021 [US5] Implement pure guide binding and select_analysis/ViewRequest/AnalysisView in rdam/interpretation.py plus deterministic summarise in rdam/summary.py; preserve whole selected outcomes, original status/context, exclusion pointers and historical limitations. (FR-019, FR-028, FR-029, FR-030; SC-008, SC-009)
- [X] T022 [US5] Exercise every native-meanings and NI-01–NI-04 regression case in tests/interfaces/test_ai_usage.py using real contracts/providers; prove pointer resolution, unchanged selected native bytes and zero model/network/source-acquisition work during views. (FR-025, FR-028, FR-029, FR-030, FR-031, FR-032, FR-033, FR-034; SC-009, SC-010)

Checkpoint: warnings do not substitute for the T016–T019 repairs. External-model
fixtures prove validation behavior only; actual source support is checked by
focused real-model tests and cold critique in T044 and T048–T052.

## Phase 4: US1 — One primary Python machine (P1)

**Goal**: Shared configured preparation/analysis. **Independent test**: direct
production_machine discovers/prepares/analyses with correct outcomes and evidence.

- [X] T023 [US1] Add shared configuration, preparation completeness, inventory/projection call-count, eRST lookup and requested-only status tests in tests/machine/test_interfaces.py. (FR-001, FR-005, FR-006, FR-007, FR-010, FR-011; SC-002, SC-004, SC-008)
- [X] T024 [US1] Wire MachineConfig through rdam/composition.py and all seven existing provider.py modules; forward every documented policy/model/capacity setting to its actual native implementation, with lazy capability-only discovery. (FR-003, FR-004, FR-005; SC-004, SC-006)
- [X] T025 [US1] Expose Machine.prepare and share its full inventory/policies/warnings/projection operation with analyse in rdam/machine.py; derive provider receipts without re-harvesting or pretending persisted preparation is replay input. (FR-006, FR-007; SC-008)
- [X] T026 [US1] Implement request-ordered v2 outcomes, retained upstream separation, eRST boundary lookup, guide binding and truthful completion in rdam/machine.py; preserve typed failures and native propagation of unexpected defects. (FR-001, FR-010, FR-011, FR-013; SC-002)
- [X] T027 [US1] Update rdam/machine.py cache keys and rdam/_execution.py eligibility checks to bind native envelope/provider/schema/evidence/configuration identities, including Dung capacity and immutable RST components; verify operational settings do not falsify analytical identity. (FR-023, FR-034; SC-003)
- [X] T028 [US1] Export the coherent public API from `rdam/__init__.py` and update current composition/source-entry consumers and tests in tests/machine/test_composition.py and tests/machine/test_source_entry_points.py; remove replaced factory arguments rather than add wrappers. (FR-001, FR-024; SC-006)

## Phase 5: US3 — Explicit structures and lineage (P1)

**Goal**: Model-free Dung/IBIS with truthful identity. **Independent test**: valid
structured-only/mixed requests use real providers without invented prose or graphs.

- [X] T029 [US3] Add structured-only/mixed/missing/malformed and upstream-collision fixtures in tests/interfaces/test_structured.py, including no stable Dung extensions versus one empty extension and an IBIS issue without positions. (FR-012; SC-002)
- [X] T030 [US3] Implement for_structured and for_edus request constructors in rdam/contracts.py and validate explicit input scope/identity; reconcile Dung/IBIS input schemas with rdam/dung/semantics.py and rdam/ibis/grammar.py, rejecting unknown structure fields instead of silently discarding them. (FR-008, FR-009, FR-012, FR-024; SC-006)
- [X] T031 [US3] Complete explicit historical/current lineage validation in rdam/contracts.py and rdam/machine.py; extend tests/interfaces/test_structured.py to prove retained success never changes requested status and retained eRST collides with requested RST correctly. (FR-010, FR-011, FR-012, FR-034; SC-002)

## Phase 6: US2 — Unified CLI (P1)

**Goal**: Predictable installed command. **Independent test**: real subprocess
input/output/exit behavior matches contracts/cli.md and protected files survive.

- [X] T032 [P] [US2] Add exhaustive grammar/stdin/literal-path/precedence/help/diagnostic tests in tests/interfaces/test_cli.py, covering every documented flag and invalid repetition/combination. (FR-014, FR-015, FR-016, FR-017, FR-024; SC-006)
- [X] T033 [P] [US2] Add no-clobber/force/alias/symlink/hardlink/race/disk/interruption/broken-pipe tests in tests/interfaces/test_output.py, including publication failure after partial analysis. (FR-018; SC-005)
- [X] T034 [US2] Implement one strict argparse grammar and input materialization path in rdam/cli.py, invoking shared Machine/codecs for capabilities, prepare and analyse; preserve complete aggregate output with 0/3/4 analytical exits and safe 1/2 failures. (FR-001, FR-014, FR-015, FR-016, FR-017)
- [X] T035 [US2] Implement atomic no-clobber publication, explicit safe replacement, input-alias protection and safe stderr diagnostics in rdam/_output.py; handle 130/141 without suppressing errors or writing diagnostics over results. (FR-013, FR-016, FR-017, FR-018; SC-005)
- [X] T036 [US2] Add `rdam/__main__.py` and the rdam entry point in pyproject.toml; remove obsolete rdam/rst/cli.py transports and migrate their tests/active references without a compatibility wrapper. (FR-014, FR-024)
- [X] T037 [US2] Wire summary/view/schema/version commands in rdam/cli.py to shared pure functions and add installed subprocess parity tests in tests/interfaces/test_cli.py, proving no config/model work for saved views and short-circuit discovery. (FR-019, FR-024, FR-030; SC-004, SC-008)

## Phase 7: US4 — Optional local HTTP parity (P2)

**Goal**: Same records over bounded loopback transport. **Independent test**:
a real server handles current requests and corrected native outputs identically.

- [X] T038 [US4] Add optional HTTP dependencies and the default development extra in pyproject.toml's project.optional-dependencies and tool.pixi tables; resolve pixi.lock through Pixi and prove core-only imports do not require Starlette/Uvicorn. (FR-020, FR-024, FR-027; SC-007)
- [X] T039 [US4] Add real-loopback route/media/framing/Host/Origin/size/deadline/admission/disconnect tests in tests/interfaces/test_http.py, including explicit pre-ASGI error limitations. (FR-020, FR-021; SC-005)
- [X] T040 [US4] Implement shared-codec versioned routes and canonical raw-byte responses in rdam/http.py, including prepare/analyse/view/summary/schema/version, fixed Machine configuration and no provenance dereferencing. (FR-001, FR-009, FR-020, FR-030; SC-003)
- [X] T041 [US4] Implement loopback startup, bounded POST admission/body reading, off-event-loop execution, safe lifecycle diagnostics and honest disconnect/shutdown behavior in rdam/http.py and serve wiring in rdam/cli.py. (FR-013, FR-020, FR-021)
- [X] T042 [US4] Prove real Python/CLI/HTTP corrected-native parity in tests/interfaces/test_parity.py with identical materialized requests and real providers; isolate model fixtures at external protocol boundaries and retain declared execution-field exclusions only. (FR-025, FR-030, FR-034; SC-003, SC-010)

## Phase 8: Cross-cutting verification and documentation

- [X] T043 Extend tools/production_boundary/schemas.py and tools/production_boundary/public_surface.py to generate all current/historical machine/native/input schemas and installed CLI/HTTP metadata; regenerate rdam/ingest/schemas/ and rdam/ingest/public-surface.json from models, not hand-edited copies. (FR-022, FR-024, FR-034; SC-006)
- [ ] T044 Add every acceptance-matrix source/technique/formalism row and actual-model grounding case to tests/interfaces/test_parity.py and tests/interfaces/test_model_backed.py; cover all six source forms, seven boundaries and eRST without internal canned-result mocks. (FR-008, FR-025, FR-026; SC-001, SC-003, SC-009, SC-010)
- [X] T045 Add the field/flag/requirement coverage inventory in tests/interfaces/test_contract_inventory.py and reconcile README.md, active docs/ API examples and specs/019-unified-machine-interfaces/quickstart.md with corrected native semantics and the installed command. (FR-024, FR-027, FR-028, FR-034; SC-001, SC-006)
- [X] T046 Run focused and applicable full Pixi tests, lint and type checks; record actual outputs/failures in completion notes in specs/019-unified-machine-interfaces/tasks.md. Do not mark skipped external-model checks passed or weaken inherited assertions to hide changed semantics. (FR-025, FR-026, FR-027; SC-001, SC-004, SC-005, SC-008, SC-010)
- [X] T047 Extend tools/production_boundary/installed_acceptance.py and exercise the built candidate wheel in core/core+http/formats/formats+http environments, proving rdam entry points, optional imports, corrected schemas/results and absence of rdam-rst. (FR-024, FR-026; SC-007)

- [X] T048 Add focused real-provider semantic cases in tests/interfaces/test_model_backed.py for Walton states, Toulmin origins and evidence support, including the adversarial distinctions in contracts/analytical-quality.md. Use existing model configuration/opt-in and retries; no custom evaluation runner. (FR-025, FR-035–FR-038; SC-011, SC-012)
- [X] T049 Execute focused real-model cases and launch a cold-critic agent to inspect the source, actual outputs, changed code and test coverage. Record concrete findings and observed test results here; no approval records or corpus quotas. (FR-035–FR-038; SC-011, SC-012)
- [X] T050 Fix substantiated semantic errors and critic findings in the affected native providers, validators or alignment; add regression tests and rerun affected checks. Do not change an expected answer merely to fit model output. (FR-031–FR-038; SC-010, SC-012, SC-013)
- [X] T051 Complete cold-critic review of actual plans, code, tests and outputs against intended use; resolve substantiated defects and record any remaining failures in tasks.md. No separate SOTA study or certification exercise is required. (FR-027, FR-038; SC-013)

- [ ] T052 Repeat applicable full checks and installed-wheel acceptance from T046/T047 after final repairs, complete every active acceptance-matrix row with actual model-backed/local-artifact results, run the required Graphify code update, review the exact candidate diff and report remaining unverified rows in specs/019-unified-machine-interfaces/tasks.md; perform no commit/tag/publication without separate authorization. (FR-026, FR-027, FR-034, FR-038; SC-001, SC-009, SC-010, SC-012, SC-013)

## Dependencies and execution order

Native baseline → shared contracts → US5 native integrity/AI view → US1 machine →
US3 structures → US2 CLI → US4 HTTP → installed/model-backed tests and cold critique.
No owner review or evaluator prerequisite blocks native changes.
All P1 stories precede P2 HTTP. US5 appears first because every delivered
interface must consume corrected native data. Native validators and saved-record
views are independently testable before production Machine assembly is complete.

T048–T052 follow the installed candidate checks. T050 returns to native repairs
and affected tests when concrete failures are found.

Within US5, T012–T015 precede fixes; T016/T017 may run independently after shared
contracts; T018 follows both; T019–T022 integrate sequentially. Shared modules
remain serialized. T032/T033 are independent after earlier story completion.

## Parallel examples by story

- US5: Walton and Toulmin regression files (T012/T013); then their distinct native
  repairs (T016/T017). Shared alignment/cache/guide integration stays sequential.
- US1: execute source-entry and composition test commands concurrently after T028;
  do not edit machine.py concurrently with cache/outcome work.
- US3: execute Dung and IBIS native test commands independently after T031;
  shared request/lineage implementation stays sequential.
- US2: CLI grammar and filesystem-publication test authoring (T032/T033).
- US4: execute protocol and parity tests independently after T042 using different
  OS-selected ports; http.py lifecycle/route edits stay sequential.

## Implementation strategy

The first useful increment is corrected native records and their directly usable
Python machine (US5 + US1), followed by structured workflows and CLI, then HTTP.
These are verification checkpoints, not permission to omit later scope. Complete
every story and the required installed/model-backed analytical-quality checks before claiming the
feature implemented. World-class applies equally to plans, implementation, tests
and evidence; a checklist or numerical score never waives a known defect. A missing external prerequisite remains explicitly unverified.

No task requires a PR, team approval, new release system, remote publication or
compatibility wrapper. Existing source licensing and production/workbench
separation remain mandatory throughout.

## Implementation notes — 2026-09-04

The owner withdrew the annotation/scoring process after the notes below were
written. Historical review gates and evaluator results below are retained only
as a record of the discarded work, not current requirements or blockers.
The full native/API/CLI/HTTP implementation remains required.

### T001: reproduced, not repaired

Initial `git status --short` reported only
`?? specs/019-unified-machine-interfaces/`. No pre-existing production edits were
present. Read the complete native validators and alignment implementation before
running this diagnostic against them:

```sh
pixi run python - <<'PY'
from rdam.walton.schemes import SchemeInstance
from rdam.toulmin.argument import ToulminLayout
from rdam.ingest.alignment import _strings
instance = SchemeInstance.model_validate({'scheme_id':'sign','conclusion':'Rain is likely.','premises':{'finding':'Dark clouds are visible.','indicated':'Rain is likely.'}})
print('Walton reported assessments:', len(instance.critical_questions))
print('Walton derived open questions:', len(instance.open_questions))
print('Toulmin explicitness field:', 'warrant_origin' in ToulminLayout.model_fields)
print('Alignment candidates for a status label:', _strings({'status':'open'}))
PY
```

Observed output, exit 0:

```text
Walton reported assessments: 0
Walton derived open questions: 2
Toulmin explicitness field: False
Alignment candidates for a status label: (('/status', 'open'),)
```

This is a deliberately authored validator probe, not a model output, reviewed
semantic reference or measured corpus failure rate. T016–T019 remain required
repairs; the baseline checkbox makes no claim that these defects are fixed.

Existing focused tests, before any native changes:

```sh
pixi run pytest tests/walton/test_schemes.py tests/toulmin/test_argument.py tests/machine/test_alignment.py -q
```

Observed: `118 passed in 1.33s`, exit 0. These passing historical tests do not
exercise or establish the required corrected semantics.

### T002: preflight completed on resumption

The upstream metadata, lock/installed versions, fixture comparison and conformance
test results are recorded in research.md. The initial partial Docling read was
completed through EOF on resumption, including current loading/version/traversal
and content-layer definitions. The four relevant upstream/installed function
bodies matched under AST comparison. Explicit fixture loading/traversal and
version-acceptance results are in research.md. Corrected the stale fixture README
API reference and scoped its old observations honestly. No source/format
production file was changed.

### T003: preserved and verified

Saved three native v1 specimens and one aggregate v1 specimen, plus fixed digest
expectations and capture limitations, in tests/interfaces/fixtures/historical/.
Read all six saved files in full. All four records passed canonical byte
round-trip and fixed semantic/artifact digest checks; exit 0. The README retains
the executed command. Only the external model boundary was replaced with authored
responses; these records are not live-model quality evidence or reviewed gold.

### Initial pause: T004 owner review and independent references

`tests/interfaces/fixtures/quality` does not exist. No reviewed reference pack,
frozen protocol, proven scorer or comparable T007 model baseline is claimed.
The analytical-quality contract requires Steve's source-first review and prevents
the implementation context from inspecting held-out sources/gold before candidate
selection. Self-authored cases cannot be relabelled as independent held-out data.
An independent reference-authoring context and Steve's review are needed before
the native changes, in the order required above. No review or agent delegation
has been assumed. T004–T007 and T008–T052 remain unchecked.

Validation of the 14 feature Markdown files and historical README before these
status notes: `markdownlint-cli2` reported `Summary: 0 issues in 0 files`
over 15 files, exit 0. This is documentation validation, not feature acceptance.
The Spec Kit extensions file is absent; no implementation hooks are registered.
Production code, entry points and dependencies remain unchanged. No commit, tag,
push or publication was performed. Feature 019 is not implemented or certified.

### Resumed implementation: T004 preparation and T005/T006 evaluator work

The owner directed continuation after the unnecessary delegation question. An
independent reference-authoring context prepared the proposed T004 pack; the
implementation context did not inspect held-out sources or annotations. The
reference author owns the content-bearing review.md. Root validation reads bytes
programmatically and reports aggregate structural facts only; it is not manual
semantic review of held-out material.

The first persisted pack passed strict source-span, digest and family-membership
validation: 680 cases, 137 families, no encoded coverage gaps and 680 pending owner
reviews. Readiness correctly rejected it with:
`source-first owner review, near-duplicate review and frozen membership are required`.
All proposed annotations remain pending. T004 is not checked until Steve reviews
the sources/annotations and membership is frozen. No model baseline was run.

T005 tests were written before their scoring implementation. The initial command
failed collection with `ModuleNotFoundError: No module named 'tests.interfaces.quality'`.
Subsequent tests exposed a real strictness defect: integer `1` was accepted as
literal boolean `true` by a Pydantic Literal field. The new regression failed
with `DID NOT RAISE ValidationError`; an explicit boolean validator repaired the
underlying behavior without suppression. Added explicit overall-verdict tests:
undefined precision cannot hide zero recall or another measured failure.

Current focused command: `pixi run pytest tests/interfaces -q` →
`87 passed in 0.11s`, exit 0. This covers scorer and reference-validator unit
examples, not native model quality. Scope includes one-to-one alternatives,
duplicate penalties, wrong/missing classes, failure/empty denominators,
unsupported evidence, exact rational thresholds, confusion matrices, per-case
and per-family errors, descriptive Wilson intervals, strict references and
unreviewed/undersized reference handling. Hand-authored unit sources are
implementation-visible development cases, never held-out gold.

T006 has working strict test-only records and deterministic scoring in
tests/interfaces/quality/{models,scoring,references}.py. protocol.json records the
numerical policy and its approved Markdown authority digest. It is not yet a
frozen executable run protocol with reviewed reference/scorer/configuration
bindings; T006 therefore remains unchecked. The first three-phase dependency
chain remains intact: no native production repair preceded reviewed references
and the pre-change baseline.

Added tests/interfaces to the existing strict Pyright include list. No dependency,
runtime entry point or production Python was changed. The initial full fast-suite
run reported `1723 passed, 147 deselected in 63.36s`; later test additions require
the final repeat below. Initial full lint passed; full typecheck reported
`0 errors, 0 warnings, 0 informations`. Graphify's required code-only refresh
completed without an LLM call; its community-name freshness warning is navigation
metadata, not a runtime or quality verdict.

### Final checks and source-first review handoff

After the last evaluator code changes:

- `pixi run test`: `1734 passed, 147 deselected in 59.99s`, exit 0.
- `pixi run lint`: `All checks passed!`, exit 0.
- `pixi run typecheck`: `0 errors, 0 warnings, 0 informations`, exit 0.
- `pixi run pytest tests/interfaces -q`: `87 passed in 0.11s`, exit 0.
- Markdown validation of the 14 feature files, historical README and Docling
  fixture README: 16 files, zero issues. The independent reference author also
  validated review.md with markdownlint, exit 0, and reported no issue codes.
- `git diff --check`: exit 0. This checks tracked changes, not the untracked
  feature/reference files; their Markdown, JSON and Python checks are above.
- Required Graphify AST-only update: exit 0, no LLM execution. No semantic
  relabeling was performed. No implementation hooks exist in .specify/extensions.yml.

Final programmatic pack validation, without exposing source/annotation content
to the implementation context: 680 cases, 137 families, zero coverage gaps,
680 pending reviews. Digests verified after the author's QA corrections:

- cases.jsonl: `385bdba2fb633f7c70d4f9a28cbba337542f6eb4c3ae1f41b925bbc4590bf56e`
- manifest reference identity: `ed01f0c90dfb1e99dc5c75b8d0b21ef0ef81858bff3247ac8264772a6dda3ee4`
- review.md: `4c3b6a9528b70b21057a74059de493d5c02978eb22a562ea335826fb77aa1dbf`

The source-first review artifact is tests/interfaces/fixtures/quality/review.md,
with 170 source panels and 680 collapsed boundary annotation panels. Opening it
for Steve was queued by the app. The independent author's semantic QA comprised
source-by-source authoring and targeted checks, not a second independent audit
of every serialized annotation. Two connective annotations and one native-role
omission were corrected. Proposed semantics, near-duplicate independence and
acceptable alternatives still need Steve's review; none is labelled approved.

Completed tasks: T001, T002, T003 and T005. T004 preparation is delivered but its
owner review/freeze is pending. T006 evaluator components are implemented but its
complete frozen execution protocol is not finished. T007 and production work
T008–T052 have not been executed. Spec Kit dependency enforcement pauses further
execution at the actual source-first review prerequisite, not at permission to
prepare it. No native fixes, unified CLI, HTTP parity, model-quality acceptance,
wheel certification, commit, tag, push or publication is claimed.

### Owner correction applied: ordinary tests and cold critique

Removed the annotation/scoring prerequisites from the active specification,
plan, task dependencies and contracts. Cold critique identified the unnecessary
machinery and two remaining acceptance-reference errors; both were corrected.
The abandoned evaluator, its 87 dedicated tests and proposed corpus were moved
to ignored build/feature019-discarded-evaluation-zDNmxi for recovery. Historical
native fixtures remain in tests/interfaces/fixtures/historical/. No bulk model
run was started. T008 is no longer blocked by owner review or corpus preparation.

Verification after removal: pixi run test reported 1647 passed, 147 deselected
in 62.68s; lint passed; typecheck reported zero errors/warnings/informations.
Markdown checks reported zero issues across 262 files before the final wording
corrections. Graphify AST update completed without model calls; community labels
remain partly stale. No production implementation is claimed by this cleanup.

### Implementation and ordinary regression verification

The current implementation replaces the old RST CLI with the machine-wide
`rdam` command. Python, CLI and optional HTTP use the same configured machine,
request codecs and canonical records. Native integrity repairs, inline AI reading
guides, saved-record views, structured inputs, historical readers, generated
schemas and safe output publication are implemented. No evaluator or owner
annotation prerequisite was reintroduced.

Read the implementation, specification and affected tests in full before edits;
the principal reviewed files include rdam/contracts.py, configuration.py,
machine.py, composition.py, interpretation.py, serialization.py, cli.py, http.py,
the native provider/output/interpretation modules, the interface test files,
packaging tools and active API documentation. Spec Kit implementation controlled
task execution; Context7 verified external-library API/dependency choices;
Graphify was used for navigation, not as test evidence.

Cold critics inspected native outputs and executable contracts. Reproduced
findings repaired in this pass include deontic permission being counted as an
epistemic qualifier; duplicate projection execution; saved views accepting a
different prepared source or missing successful-provider configuration; source
wire validation bypassing UTF-8/EDU constraints; eRST JSON Schema accepting the
RST formalism; and omitted historical schema names in capability discovery.
Four preparation/view regressions failed before repair and then passed.

Observed checks after their applicable repairs:

- Python/CLI/real-loopback HTTP parity: 24 passed in 121.51s. Full canonical bytes
  match; no semantic fields are removed. The four LLM techniques use fixtures
  only at the external OpenAI response boundary, not inside providers.
- Field/flag/schema inventory plus machine and historical identifier regressions:
  444 passed in 3.36s.
- Machine, AI-use and codec regressions: 105 passed.
- Real-loopback HTTP protocol/lifecycle suite: 90 passed in 34.39s.
- Native schema suite: 96 passed, 2 skipped in 27.84s. Both skips require the
  missing real eRST bundle and are not recorded as passed.
- Source-artifact regressions, including a multibyte character crossing the
  DocLang detection-prefix boundary: 5 passed in 0.11s.
- Focused actual OpenAI model cases: initial 7 passed; the permission versus
  epistemic-modality repair passed both affected cases in 14.45s; added PDTB
  causal-negation and SDRT Explanation/source-attachment cases both passed in
  19.17s. A cold critic inspected the actual outputs. These are focused tests,
  not a claimed universal model-quality guarantee.
- Ruff: All checks passed. Strict Pyright: 0 errors, 0 warnings, 0 informations.
- Runnable structured CLI quickstart produced a complete Dung/IBIS aggregate
  and a saved-record summary without model inference.

The first four-environment candidate install passed core, core+HTTP, formats and
formats+HTTP, including actual CPU RST inference, Python/CLI semantic parity,
52 packaged machine schemas and optional-import boundaries. The final source
repairs require the repeat recorded below; this earlier candidate is not being
substituted for final-source acceptance.

The earlier full-suite runs exposed obsolete CLI/schema assertions and a strict
nested preparation conversion error. Those failures were repaired, not ignored:
the latest failing run was 2 failed, 2234 passed, 163 deselected. The affected
tests and 24 parity tests now pass; the final full-suite repeat is in progress.

### Remaining real-artifact prerequisite

Acceptance A06's successful eRST execution remains unverified. The configured
environment and scoped workspace/cache searches contain no complete trained eRST
bundle; ISANLP_RST_ERST_CHECKPOINT is unset and default discovery returns None.
Screening weights are not the manifest-bound completion bundle required by the
native runtime. Missing-bundle behavior is tested, but cannot prove successful
graph inference. T044 and T052 remain unchecked for this reason. No substitute
model, fabricated graph or skipped test is accepted as proof.

No commit, tag, push or external publication has been performed.

### Final semantic repair and verification

A fresh live rerun exposed a real Toulmin error, not a transport defect: the
provider reconstructed a badge-to-admission licence but labelled its origin
undetermined, then imported an explicitly irrelevant fictional rule as a
rebuttal. The original reconstruction expectation failed. The cold critic
confirmed the distinction; no expected origin was changed to fit the output.

Clarified the producing prompt and origin/evidence field descriptions: origin
means stated versus inferred provenance, not warrant truth or availability of
a verbatim sentence. Reconstruction cites the actual inference; undetermined
is reserved for genuinely damaged/ambiguous origin. Explicitly irrelevant
material cannot be assigned an argument role without a source connection.
Added the missing no-distractor-rebuttal assertion. Stopped the obsolete
in-progress verification runs and rebuilt/regenerated from the repaired source.

Actual repair controls: 3 passed, 7 deselected in 37.20s. All three outputs used
one output attempt and one transport attempt. The cold critic read every output:
explicit licence retained its quotation and no permission qualifier; the
unstated licence was reconstructed with the actual inference at offsets 148:228
and no rebuttal; damaged origin remained undetermined/ambiguous_source. No
further concrete semantic defect was observed in those outputs.

Actual CPU RST inference through Python, CLI and HTTP: 1 passed in 34.63s using
gumrrg-eb1d5745f3a1. Each transport ran real inference with loaded components,
validated primary evidence and a nonempty tree. Native and aggregate semantic
digests matched; only native-declared execution fields were excluded.

Final-source Ruff passed; strict Pyright reported 0 errors, 0 warnings,
0 informations; production-boundary inspection reported valid=true with
176 modules and no violations. Wheel and source archive built successfully.
Final full-suite, ten-case live and four-install results follow when completed.

The full regression run completed: 2658 passed, 164 deselected in 417.14s.
All four candidate environments passed again, including real CPU RST inference
and all 52 machine schemas. These runs precede the final lifecycle repair below.

The ten-case live run reported 2 failed, 8 passed in 126.87s. The cold critic
read all ten records and identified one incorrect test requirement: a valid
quotation omitted only the terminal full stop. Corrected that assertion to
require every lexical word while preserving exact source-slice validation;
six deterministic positive/truncation/offset controls passed. The saved actual
output passes the corrected assertion without another model call.

The other failure was genuine: Walton exhausted three evidence-validation
attempts. Its generic retry message concealed both the failed field and the
actual literal location. Added non-mutating numeric location feedback and report
all invalid spans together, preserving ambiguity for repeated quotations and
rejecting absent quotations. Before repair, three feedback cases failed; then
two all-errors cases failed. All six now pass; combined native tests report
123 passed in 0.84s. No automatic evidence repair or increased retry budget.

That run also exposed async SDK clients being retained across closed event
loops. The shared boundary is being repaired to own client construction and
closure within each async run. T050/T051 remain open until that repair and its
actual-output verification complete. The prior live failures are not hidden by
the green deterministic suite.

The lifecycle repair is now verified: real SDK/model adapter tests exercise
OpenAI, Anthropic and Google, with 15 passing cases for repeated synchronous
success/failure, deadline, cancellation, transport exhaustion and concurrency.
Every client is closed on the loop that made its requests. No blanket catch,
warning filter or additional retry was introduced. Dedicated tests are included
in configured strict Pyright. The migrated schema seam remains at the external
model boundary; schema/evidence tests reported 102 passed, 2 eRST skips.

Final live run on repaired production code: 10 passed, 6 deselected in 122.65s
using openai:gpt-5.6-sol. All ten actual-model cases ran; the six deselections
are the deterministic punctuation/lexical-span controls, separately verified.
The remaining eRST successful-inference test is implemented using the native
bundle resolver: real RST passed and eRST explicitly skipped (1 passed,
1 skipped in 30.65s). A supplied invalid bundle fails validation rather than
being skipped or replaced.

An upstream Google SDK deprecation warning remains visible:
google/genai/types.py:42 uses typing._UnionGenericAlias, scheduled for removal
in Python 3.17. This is third-party code, not a suppressed RDAM warning or a
failed client-lifecycle test. No dependency fork was introduced.

The final cold critic read all ten actual outputs. Walton's previously failing
case now has four addressed and two open questions; its reliability quotation
at 171:213 is exact, and its note correctly calls the offered reason inadequate.
It used three attempts within the existing budget. Damaged-origin Toulmin and
PDTB each used two; the other seven cases each used one (14 total attempts).
No further concrete semantic error, client-cleanup error or warning appeared in
that live run. This proves these cases, not universal semantic infallibility.

Direct artifact/source comparison found no stale packaged files: 248 wheel
package files and 253 source-archive files match the current checkout bytes.

### Final regression and installed-candidate results

The lifecycle change exposed four obsolete external-model test fixtures in
tests/llm/test_provider_consistency.py, tests/toulmin/test_provider.py,
tests/machine/test_alignment.py and tests/machine/test_interfaces.py. The first
full run reported 3 failed, 2669 passed, 165 deselected and 7 setup errors.
Migrated those fixtures to per-run model contexts without changing analytical
assertions; all 96 affected tests passed (1 deselected).

The final fast suite ran in three disjoint parallel partitions using the same
`not slow and not stress` filter:

- tests/interfaces/test_cli.py: 145 passed in 157.98s.
- tests/interfaces/test_parity.py: 24 passed in 135.42s.
- Every other test: 2516 passed, 165 deselected, 1 warning in 135.56s.

Final Ruff: All checks passed. Strict Pyright: 0 errors, 0 warnings,
0 informations. Markdown validation: 263 files, zero issues. The required
AST-only Graphify refresh completed without model calls (27727 nodes,
44514 edges); community names remain partially stale navigation metadata.
`git diff --check` passed. The active checklist contains 46 checked tasks and
the two explicitly blocked tasks below.

Total: 2685 passed, zero failures or errors. The warning is the upstream Google
SDK deprecation documented above. Complete outputs are in ignored
build/feature019-final-{cli,parity,other}-tests.log.

The final wheel's isolated core, core+http, formats and formats+http installs
all passed, including pip dependency checks, 52 packaged machine schemas,
canonical round trips, actual CPU RST inference and installed CLI semantic
parity. Both HTTP variants also passed HTTP parity. External networking was
disabled during acceptance. The complete result is in
build/feature019-install-candidate/completed-clean-install.log; wheel and source
archive are in the same directory. No production source changed after the build.

Successful eRST inference (A06) remains unverified because its trained completion
bundle is absent. Its executable acceptance test explicitly skips in that case;
invalid supplied bundles fail. T044 and T052 remain unchecked, not waived.
No commit, tag, push or external publication was performed.

### Production-readiness repair — 2026-09-05

A post-implementation readiness audit ran the repository's dedicated Python 3.14
production-modernization gate, which found 20 unsuppressed issues: seven export
order findings, five collapsible conditions, four excess-blank-line findings and
four list-construction findings across 15 `rdam/` files. These were real gate
failures despite the ordinary Ruff suite being green. All were repaired without
changing analytical contracts, retry policy or inference behavior.

Current evidence after the repairs:

- `pixi run lint-production-modern`: All checks passed.
- `pixi run lint`: All checks passed.
- `pixi run typecheck`: 0 errors, 0 warnings, 0 informations.
- Focused interfaces, persistence, public-surface and affected-provider suite:
  1007 passed, 20 deselected in 327.83s.
- Full fast suite in three disjoint partitions: 145 CLI tests, 24 parity tests
  and 2516 remaining tests passed; total 2685 passed, 165 deselected, zero
  failures. The remaining visible warning is the upstream Google SDK Python
  3.17 deprecation already documented above.
- Fresh actual-model run: 10 passed, 6 deterministic controls deselected in
  109.99s using `openai:gpt-5.6-sol`.
- Fresh real local RST/eRST check: RST passed; eRST skipped because the resolver
  returned no trained completion bundle (1 passed, 1 skipped in 31.07s).
- Fresh wheel and source archive built. Core, core+http, formats and
  formats+http isolated installs all passed with external networking disabled,
  real CPU RST inference, 52 schemas and Python/CLI/HTTP parity where installed.
- All 248 packaged `rdam` files in both the wheel and source archive are
  byte-identical to the repaired checkout.
- Production boundary: valid=true, 176 production modules, zero violations.
  Production import check: valid=true. Markdown: 263 files, zero issues.
- Required Graphify AST update completed without model calls.

The supported Python, unified CLI and optional local HTTP code is ready for solo
local production use. eRST graph completion is not operational until a valid
trained bundle is supplied; capability discovery reports that absence rather
than advertising false availability. A06, T044 and T052 therefore remain
explicitly incomplete. No external package publication was requested or
performed.
