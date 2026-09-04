# Feature 017 baseline — 2026-09-03

Measured before production relocation at HEAD `a856857f4d5801a5c3fad9ec15e243e17b7bd434`.
The checkout already contained user-owned configuration, dependency, documentation, and
Graphify changes. No commits, resets, or index changes were made for this measurement.

## T001 measurements

| Measurement | Observed result |
| --- | --- |
| `rdam/rst/ingest/**/*.py` | 25 modules, 10,372 lines; counted programmatically with `splitlines()` |
| Python references to `rst.ingest` | 111 files across `rdam tests tools scripts workbench`, using `rg -l` |
| Markdown references to `rst.ingest` | 27 non-hidden files outside `graphify-out`, using `rg -l -g '*.md' -g '!graphify-out/**'` |
| `AggregateRequest` entry points | `for_text` only; `rdam/contracts.py` read in full |
| `pixi run --locked test` | 1,462 passed, 134 deselected in 41.47 seconds: 1,596 total |
| Primary capabilities | RST, PDTB, SDRT, Toulmin, Walton, Dung, IBIS all `available`, from `production_machine().capabilities()` |
| eRST formalism | `unavailable: model_unavailable`; not conflated with the RST boundary capability |
| Initial boundary | 144 modules, 11 `unmatched_ownership` violations, all beneath `.codex/` |
| Repaired boundary | 144 modules, `valid: true`, `violations: []` |

The boundary repair gives `.codex/` exactly one repository-control owner, matching the
existing `.agents/` and `.claude/` treatment. It does not make these files publishable.
The focused ownership and baseline-tool suite reported **8 passed in 2.62 seconds**.

## T002 real RST baseline

The old tool forced `family="modernbert"`, a family rejected by the production facade.
The repaired tool derives the family from the selected immutable release and requires
an explicit release ID instead of defaulting to a retired model.

Actual local store: `/Users/steveallison/.cache/isanlp_rst/model-releases`.
Selected DMRST release: `gumrrg-eb1d5745f3a1`.

```bash
HF_HUB_OFFLINE=1 pixi run --locked rst-baseline capture \
  --output specs/017-universal-source-pipeline/evidence/baseline-dmrst-current \
  --store /Users/steveallison/.cache/isanlp_rst/model-releases \
  --release-id gumrrg-eb1d5745f3a1 --device cpu
```

Capture succeeded with nine records: capabilities, preparations for all six source
forms, and actual model-backed text and EDU analyses. `baseline-dmrst/` preserves the
earlier capture under Docling 2.93.0; its immediate repeat was fully equivalent, with
zero differences. `baseline-dmrst-current/` is the comparison authority after updating
Docling to the current 2.94.1 release, before moving any production module.

The immediate repeat against `baseline-dmrst-current/` also reported
`equivalent: true`, `analytically_equivalent: true`, and zero differences.

No commit was made: the confirmed execution plan expressly excludes commits and pushes.

## Setup checkpoint verification

These are setup checks, not completion of Feature 017 or its relocation gates.

| Check actually run | Observed result |
| --- | --- |
| `pixi run --locked lint` | All checks passed |
| `pixi run --locked typecheck` | 0 errors, 0 warnings, 0 informations |
| `pixi run --locked test` | 1,464 passed, 138 deselected in 41.01 seconds |
| `pixi run --locked rst-format-test` | 242 passed in 6.18 seconds |
| `pixi run --locked production-boundary` | 144 modules, `valid: true`, `violations: []` |
| `pixi run --locked graphify-code` | Exit 0; 12,050 nodes, 24,517 edges, 1,156 communities |
| `pixi run --locked mdlint` | FAIL: 47 issues in eight pre-existing `.codex/skills/graphify` Markdown files |
| Direct Markdown lint of the two new evidence documents and two pipeline Markdown fixtures | 0 issues in 0 files; four files checked |

The repository-wide Markdown failures are in `SKILL.md` and the `references/`
files `add-watch.md`, `exports.md`, `extraction-spec.md`, `github-and-merge.md`,
`query.md`, `transcribe.md`, and `update.md`. They include missing fence languages,
heading-level jumps, list/fence spacing, and emphasis style. Those pre-existing skill
files were not edited in this implementation pass; the failures remain unresolved.

Graphify refreshed code structure only. It reported that 277 community names were
replaced with hub-derived names because the community set changed; semantic extraction
and LLM relabeling were not run. Existing staged graph deletions were not changed in
the index.

The Docling dependency was updated from 2.93.0 to 2.94.1 after checking the
[Docling PyPI metadata](https://pypi.org/pypi/docling-core/json). Current installed
`DoclingDocument.load_from_json`, `iterate_items`, `ContentLayer`, and `TableCell`
definitions were inspected. All four existing Docling fixtures and the new merged-cell
fixture load under schema 1.10.0. The installed DocLang version remains 0.7.3, matching
[DocLang PyPI metadata](https://pypi.org/pypi/doclang/json). The upstream main commit
`6d3b3d3c195d1f63333c5c5fcba8da17937a33bd` matches the vendored fixture manifest.
This records the specific currency checks made, not a claim that the entire upstream
specification was read or every new format behavior was implemented.

## Approved design decision — 2026-09-04

The owner approved separating provider assembly and orchestration, then explicitly
instructed implementation to proceed. Provider assembly now lives in
`rdam/composition.py`. At this checkpoint both public `production_machine` entry points
remained available; the later no-compatibility ruling below supersedes that choice.
The boundary checker rejects direct technique imports in `rdam/machine.py` and
allows concrete provider imports in composition. The plan records this amendment.

## Relocation checkpoint — T006–T018

All 25 ingest modules and their resources were moved with `git mv` to `rdam/ingest`.
Historical root exports and submodule imports resolve to the canonical objects, with
no duplicate contract classes. Test imports use the canonical path except deliberate
compatibility checks and historical public-manifest identifiers.

| Check actually run | Observed result |
| --- | --- |
| Composition tests | 3 passed |
| Explicit ownership, persisted identifiers, and compatibility tests | 6 passed |
| Six-format inventory completeness | 6 passed in 2.67 seconds |
| Lint | All checks passed |
| Strict typing | 0 errors, 0 warnings, 0 informations |
| Fast suite | 1,479 passed, 138 deselected in 45.97 seconds |
| Production boundary | 146 modules, `valid: true`, `violations: []` |
| Packaging/boundary tests after resource-path corrections | 35 passed in 6.46 seconds |
| Real DMRST baseline comparison | `analytically_equivalent: true`, `analytical_differences: {}` |

The baseline comparison is not byte equality: it reports 24 derived-digest and 40
execution differences, including source-adapter file hashes changed by relocation.
Direct assertions independently pin persisted contract versions, schema IDs, and
parser runtime names. No trained architecture or inference mathematics was changed.

Relative loader, schema, manifest, artifact-validation, and coverage paths were updated
for the relocation. Installed acceptance also contained the retired forced
`family="modernbert"`; this was removed so the selected release determines its family.
The actual clean-room installed-acceptance workflow has not been verified here.

This is a foundational checkpoint, not Feature 017 completion. T022, T029, provider
projections, source entry points, speakers, and the remaining feature gates follow.

Files read in full for this decision and checkpoint include `spec.md`, `plan.md`,
`tasks.md`, `rdam/machine.py`, `rdam/contracts.py`, `rdam/__init__.py`,
`rdam/rst/provider.py`, `rdam/rst/parser.py`, `pyproject.toml`,
`tools/production_boundary/authority.py`, `tools/production_boundary/rst_baseline.py`,
`tests/production_boundary/test_rst_baseline.py`,
`tests/production_boundary/test_codex_ownership.py`, and
`tests/stress/test_concurrency_stress.py`. During relocation all 25 ingest Python modules,
all test files whose imports changed, and the edited packaging helpers were read in full.

## No-compatibility checkpoint — 2026-09-04

The owner explicitly removed backwards-compatibility requirements and approved using
`capacity` in JSON as well as Python. FR-002, FR-006, the plan, research, data model,
source-pipeline contract, and task definitions now reflect that decision.

Removed the newly introduced `rdam/rst/ingest.py` shim and the forwarding factory in
`rdam/machine.py`. `rdam.production_machine` directly exports the implementation from
`rdam.composition`. Removed ingest's `PreparedRstDocument` and `ParserCapacity` aliases
and `AnalysisPlan.parser_capacity`; callers use `PreparedDocument`, `AnalysisCapacity`,
and `capacity`. The distinct RST model-release `ParserCapacity` remains a parser-specific
contract, not an alias. Internal harvesting still uses existing `contracts/legacy.py`
models; this checkpoint does not claim to have removed that internal implementation.

Updated active tool/script imports and regenerated the schemas and public-surface
manifest at the canonical package. Removed the two newly created compatibility-only
test files and replaced them with canonical-surface and canonical-contract tests.
Historical baseline JSON is unchanged. These removals are recoverable from this task's
patch history; no user data or Git history was deleted.

| Check actually run | Observed result |
| --- | --- |
| Canonical contracts, surface, and composition tests | 8 passed in 3.64 seconds |
| Fast suite, rerun with the final comparator test | 1,490 passed, 138 deselected in 43.46 seconds |
| Comparator tests after reference classification repair | 15 passed in 2.88 seconds |
| Lint | All checks passed |
| Strict typing | 0 errors, 0 warnings, 0 informations |
| Production boundary | 145 modules, `valid: true`, `violations: []` |
| Real DMRST comparison, all six preparations plus text/EDU analyses | `analytical_differences: {}`; exit 0 |
| `git diff --check` | Exit 0 |
| Final Graphify AST update | Exit 0; 12,086 nodes, 24,596 edges, 1,128 communities |
| Editable-source import check, with and without `--formats` | `canonical_ingest: true`, `valid: true` in both runs; not wheel certification |
| Direct Markdown lint of eight changed feature/evidence documents | 0 issues |

The first fast run failed collection because a mechanical rename also changed a
parser-release import in the test fixture; that import was restored to the distinct
parser-release type before the passing run above.

The import-check helper now reports canonical ingest from the modules actually loaded,
rather than incorrectly tying that fact to `--formats`; the duplicate format-only ingest
entry was removed. Both real command paths were run successfully.

The comparator explicitly reports 32 `contract_field_rename`, 34 `derived_digest`,
and 40 `execution` differences. It recognizes the approved capacity rename only when
the complete values match and neither record contains both names. Tests prove changed
limits, unrelated names, and both-name payloads remain analytical differences. The
first model-backed comparison exposed two plan-identity references; they are now
classified as derived only when each equals its own embedded plan's digest. A mismatched
reference remains an analytical failure. No baseline was recaptured to hide differences.

Full files read for this checkpoint include the six edited feature design/task documents,
`rdam/machine.py`, `rdam/ingest/contracts/preparation.py`, both ingest export modules,
the preparation/service/subdivision/validation modules, both public-surface modules,
the edited tests, all seven edited `tools/production_ingest` modules, and
`scripts/rst_diag.py`. This was a canonical-name migration, not a complete quality audit
of every inherited helper or existing mocked test in those files.

The earlier compatibility-bearing full run completed with 1,568 passed and 56 skipped
in 313.99 seconds. That result is historical, not proof of the clean-break checkout.
The clean-break full run completed with **1,571 passed, 56 skipped in 318.41 seconds**.
It collected before the final comparator-reference test was added; that test passed in
the 15-test comparator run and in the subsequent 1,490-test fast run. T018 and T022
are verified for this checkpoint. Feature 017 remains
incomplete: T023 onward (except the previously measured T073) still requires implementation
and verification. The unresolved Markdown lint and clean-install limitations above remain.
