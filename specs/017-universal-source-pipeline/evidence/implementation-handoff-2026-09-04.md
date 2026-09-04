# Feature 017 implementation handoff — 2026-09-04

## Resume instruction

Continue `$speckit-implement 017` from this checkpoint. The entire 91-task feature
remains approved and in scope. Do not restart the design discussion or split the feature.
This handoff follows the owner's session-hygiene rule after repeated clarification.

Workspace: `/Users/steveallison/AI_Projects+Code/Rhetorical_Discourse_Analysis_Machine`.
Branch: `master`; baseline HEAD `a856857f4d5801a5c3fad9ec15e243e17b7bd434`.
Recheck live state before relying on either. No commit, push, branch switch, or publication
is authorized. The worktree was already dirty; preserve unrelated changes, especially
the large set of staged Graphify deletions. Ingest moves were made with `git mv` and
are staged; subsequent edits are generally unstaged.

## Decisions already settled

- Separate responsibilities: `rdam/machine.py` is generic orchestration;
  `rdam/composition.py` assembles the seven concrete providers. Only composition imports
  technique packages. `rdam.production_machine` directly exports that factory.
- **No backwards compatibility.** No `rdam.rst.ingest` shim, old ingest type aliases,
  old attribute, or forwarding factory. Canonical names are `rdam.ingest`,
  `PreparedDocument`, `AnalysisCapacity`, and `AnalysisPlan.capacity`.
- `capacity` is also the JSON field. Old payloads need not load. Persisted contract
  names/versions and runtime identifiers remain as specified by FR-004. No publication
  or separate schema-version change was made.
- Preserve actual RST analysis behavior and trained architecture/inference math.
- One inventory, many provider-declared projections; tables and speakers are mandatory,
  not optional follow-ups. Four workers remain the default, with ordered aggregation.
- No subagents unless separately requested. Python and checks run through locked Pixi.

## Implemented checkpoint

The 25-module ingest package and resources moved to `rdam/ingest`. Production, test,
tool, and script imports were migrated. Loader/resource/packaging/coverage paths were
corrected; schemas and the public-surface manifest were regenerated. Boundary ownership
is explicit and generic machine imports are checked. Inventory completeness is tested
across six forms, and persisted identifiers are asserted directly.

Compatibility-only tests were replaced by `tests/ingest/test_canonical_contracts.py`
and `test_canonical_surface.py`. The parser-specific type
`rdam.rst.model_loading.ParserCapacity` is a distinct contract and remains. The internal
harvesting adapter still uses `rdam/ingest/contracts/legacy.py`; removing its internal
models has not been implemented. Do not confuse them with the removed public aliases.

Feature spec, plan, research, data model, source-pipeline contract, and tasks reflect
the owner-approved clean break. Checklist markers are reviewer-owned and unchanged.

## Verification

Detailed commands and prior failures are in [baseline.md](baseline.md).

- Canonical contracts/surface/composition: **8 passed in 3.64 seconds**.
- Fast suite, rerun after the final comparator test: **1,490 passed, 138 deselected
  in 43.46 seconds**.
- Baseline comparator, including changed-limit and invalid-reference cases:
  **15 passed in 2.88 seconds**.
- Lint: **All checks passed**. Strict typing: **0 errors, 0 warnings, 0 informations**.
- Production boundary: **145 modules, valid true, zero violations**.
- Real DMRST comparison: **zero analytical differences**, exit 0. It reports
  32 approved field-rename differences, 34 derived-digest differences, 40 execution
  differences. The comparator checks complete capacity equality for the rename and
  checks plan-identity references against each record's own embedded plan.
- `git diff --check`: exit 0.
- Editable-source import check with and without formats: valid true; canonical ingest
  loaded in both. This is not wheel certification.
- Final Graphify AST update: exit 0; **12,086 nodes, 24,596 edges, 1,128 communities**.
  No semantic extraction or LLM relabeling. Graph files are not test evidence.

The clean-break full suite completed: **1,571 passed, 56 skipped in 318.41 seconds**.
It collected before the final comparator-reference test was added; the subsequent
15-test comparator run and 1,490-test fast run cover that addition. No test session is
left running. The earlier compatibility-bearing full run was **1,568 passed, 56 skipped
in 313.99 seconds** and is historical evidence only.

## Remaining work and gates

Read `tasks.md` for current checkbox authority. **T001–T022 and T073 are checked**;
T018 and T022 were reverified after the clean break.
**T023–T072 and T074–T091 remain unimplemented/unverified.**

Next: requirement/projection contracts and pure `project(inventory, requirement)`.
T029 is the blocking gate: RST's requirement must reproduce the existing policy, route
through projection, and preserve the real baseline. No user-story migration begins
before it passes. Then implement source entry points and inventory-once, per-provider
table admission, speaker identity, per-requirement capacity, cache projection identity,
declared parallel safety/lifetime repair, anchor alignment, documentation, and full gates.

Useful source context from the previous complete reads:

- `prepare_source` currently inventories, applies the default policy, builds segments,
  transformations, boundaries, plan, coverage, and evidence. Extract reusable pure
  assembly rather than duplicate this implementation or inventory a second time.
- `inventory_source` currently returns items and source-contract identity, not a typed
  `ContentInventory` wrapper. Define that shared input consistently with the data model.
- Default primary classes are TITLE, HEADING, PARAGRAPH, LIST_ITEM, TURN; RST must keep them.
- RST provider currently rebuilds a text artifact and calls `ProductionIngestor.analyse`;
  routing a projection must eliminate that second inventory without changing native results.
- Machine locks every provider and retains non-weak-referenceable providers strongly;
  T079–T080 must replace that behavior using declared safety and bounded ownership.
- SourceArtifact metadata identity is not the machine's raw-bytes source identity.
  Keep their meanings distinct. Recheck the `from_path` model-copy identity concern
  before integrating new source constructors.

Known incomplete checks: repository Markdown lint previously failed with 47 issues in
eight `.codex/skills/graphify` files; no suppression was introduced. Actual clean-room
wheel installation remains unverified. Existing clean-install task defaults name a
retired ModernBERT release and need reconciliation if that workflow is used. Native
format projection/table geometry changes require renewed upstream currency checks.

Current-format checks earlier in this work established Docling 2.94.1 and DocLang 0.7.3;
DocLang upstream commit was `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd`.
Those are dated observations, not a substitute for checking upstream before new
Docling/DocLang harvest, fixture, or contract changes.

## Real baseline command

Preserve both baseline directories; `baseline-dmrst-current` is the comparison authority.

```bash
HF_HUB_OFFLINE=1 pixi run --locked rst-baseline compare \
  --baseline specs/017-universal-source-pipeline/evidence/baseline-dmrst-current \
  --store /Users/steveallison/.cache/isanlp_rst/model-releases \
  --release-id gumrrg-eb1d5745f3a1 --device cpu
```

No `.specify/extensions.yml` was present. Recheck hooks on resume, read the implementation
skill and required instruction files, and preserve the approved scope and decisions.
