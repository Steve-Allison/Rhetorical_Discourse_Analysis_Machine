# Feature 018 Evidence

## Status — 2026-09-04

The implementation and regression repairs are committed in `335c397`; the
post-commit graph refresh is `8f7635bee967b12cb8564a911c9aa177b742a0eb`.
The corrected source has passed reproducible double-build, artifact validation,
and full fresh-install acceptance in both core and formats environments.
All 25 implementation tasks are complete, including T023 and T025.
The owner authorized local commits only. Nothing has been pushed or published.

## Repairs and causal proof

- Instruction-decorated unknown/empty/dirty revisions could incorrectly become
  cacheable. The regression first produced `3 failed, 3 passed, 18 deselected`;
  eligibility now checks the underlying source revision as well as the dirty
  suffix. Tests exercise the real machine and persistent cache.
- Instruction-binding tests cover clean, dirty, unknown, and empty source
  revisions independently of the actual checkout's Git state. The original
  coverage failure was `99.50%`; the corrected gate reports `100.00%`.
- Mutation testing now requires passing unmodified causal tests, then test-call
  failures without collection/setup errors. Only the deadline-removal mutation
  accepts timeout as its intended failure mode. A seventh mutation tests the
  instruction-decorated revision regression.
- Installed `pydantic-ai-slim` 2.37.0 metadata requires `tiktoken>=0.12.0` for
  the OpenAI extra. The existing `>=0.13,<0.14` constraint now belongs to core
  dependencies, and the ownership and installed-acceptance checks agree. The
  regression failed before the correction and passes afterward. Pixi generated
  the lock update; no dependency version upgrade was requested.
- Clean-install no longer embeds a nonexistent ModernBERT release. Its caller
  supplies the actual local store and release explicitly.
- Current Feature 017 authority is preserved: declared provider parallel safety,
  canonical machine-level ingest, and the owner-approved clean API break.

## Current source checks

Commands use `pixi run --locked` unless otherwise stated.

| Gate | Observed result |
| --- | --- |
| `lint` | `All checks passed!` |
| `typecheck` | `0 errors, 0 warnings, 0 informations`; includes the new tests and repaired acceptance/mutation tools |
| `test` | `1647 passed, 147 deselected in 59.69s` |
| `test-stress` | `14 passed in 138.03s (0:02:18)` |
| `shared-runtime-test` | `337 passed, 3 deselected in 7.65s` |
| `shared-runtime-coverage` | `120 passed in 1.52s` on the committed source; six modules, `308 statements`, `98 branches`, `100.00%` |
| `shared-runtime-mutation-test` | `7/7 critical mutants killed`, including the final timeout-classification rerun |
| New regression files | `20 passed in 0.04s` |
| `production-api-contract` | `450 passed in 41.48s` |
| `production-boundary` | `valid: true`, `149` production modules/files, `violations: []` |
| `production-import-check` | `valid: true`, `canonical_ingest: true`, `editable_source: true`; this certifies no wheel |
| `mdlint` | `Summary: 0 issues in 0 files`; `247` Markdown files linted |
| `git diff --check` | Exit 0, no output |

An intermediate `test-all` run passed with `1737 passed, 56 skipped in 420.84s`.
It predates the tokenizer regression and is not the final full-suite result.
The final `test-all -rs` run reports **`1738 passed, 56 skipped in 421.02s
(0:07:01)`**, with zero failures. Of the skips, 54 are smoke cases for older
model releases explicitly declaring `>=4,<5` package compatibility (not RDAM 6),
and two are paid live-model tests requiring `RDAM_RUN_LIVE_MODEL_TESTS=1`.
The compatible model-backed integration and stress cases ran successfully.

## Corrected-source build and installation

`build-production --evidence-dir
specs/018-shared-runtime-hardening/build-evidence` completed the reproducible
double-build from clean commit `8f7635bee967b12cb8564a911c9aa177b742a0eb`,
tree `072da539de1f7a2ea1f2442aaefeb570c09f4e45`. The two builds produced
identical wheel and sdist bytes (`reproducible: true`). The JSON files in
`build-evidence/` now identify this corrected source, replacing the pre-repair
build records. No tag or external publication was requested.

- Wheel: `dist/6.0.0/rdam-6.0.0-py3-none-any.whl`, SHA-256
  `f3e25f2edb46135fa3a671bdb9b7d01451305fe16e29e6228d19f83d23e09588`
  (`651318` bytes).
- Sdist: `dist/6.0.0/rdam-6.0.0.tar.gz`, SHA-256
  `1cafee284e76e5370e5d28ab1e28aff1694f668381e66b7df48c76fabf36d925`
  (`579458` bytes).
- `validate-production-artifacts`: `valid: true`, `promoted_release.valid: true`,
  `149` production modules/files, `violations: []`, and wheel
  `record_verified: true`. Embedded provenance names the clean build commit above.
- All `149` wheel Python files were byte-compared with the tested source:
  `source_mismatches: []`, `valid: true`.
- Fresh core and formats acceptance passed against this exact wheel with
  `--model-store /Users/steveallison/.cache/isanlp_rst/model-releases
  --release-id gumrrg-eb1d5745f3a1` and `--full`.

Both environments reported `valid: true`, `pip_check: passed`,
`offline_distributions_absent: true`, `network_disabled: true`, and
`cli_semantic_parity: true`. Each loaded four model components and passed seven
analysis validation checks. The formats environment prepared all six source
forms; core correctly advertised only text and EDUs as available. Both imported
the installed wheel from fresh temporary environments outside the checkout and
checked all 211 public-surface entries.

Both environments produced analysis identity
`5bc1c7d0d99be99a6e76a35dd49e62f128ef8f24af93b04255247ff83eaab789`
and parser-result identity
`55173021cf1a61b6e511142385b5c35397237c149df3631fa79d361cc542aaba`.
The clean-install command exited 0 with top-level `valid: true`.

The pre-commit build attempt failed with:

```text
RuntimeError: production artifacts require a completely clean worktree
```

The owner subsequently approved the local commit, and the clean corrected-source
build above resolves that blocker. The pre-repair wheel is not used for final
certification.

## Graph and scope

The AST-only Graphify update completed without paid semantic extraction:
`12,355 nodes`, `25,847 edges`, `1,145 communities`. Full JSON inspection counted
`6,255` source nodes under `rdam/` and zero `isanlp_rst/` source paths. Community
names were deterministically refreshed by hub where membership changed; semantic
document extraction was not run.

The subsequent post-commit hook snapshot committed in `8f7635b` contains
`12,375 nodes`, `25,791 edges`, and `1,146 communities`; its production-node
count remains `6,255`, with zero obsolete `isanlp_rst/` source paths.

`graphify-out/cache/last_query_stamp` remains untracked and ignored by
`.gitignore:40`. No Feature 017 specification, ingest implementation, format
fixture, trained architecture, or inference mathematics was changed.

The earlier evidence's absent ModernBERT target and UniRST loading failure are
historical observations, not current blockers: explicit existing-release
clean-install acceptance and the final full suite now pass. No external
publication is part of this task.

SpecKit post-execution hook check: `.specify/extensions.yml` is absent; no
extension hook is registered. T023/T025 are complete. Commits following the
build contain completion records and generated graph outputs only; no runtime,
test, tool, or dependency change was made after the certified build.

## Read scope

Read in full: the Feature 018 specification, plan, tasks, research, data model,
contract, checklist, quickstart, and evidence; the Feature 017 specification;
`pyproject.toml`; `rdam/contracts.py`, `rdam/machine.py`, `rdam/_execution.py`,
`rdam/_provenance.py`, `rdam/_provider_provenance.py`, and
`rdam/_result_cache.py`; the modified and new regression files;
`tools/shared_runtime_mutation_test.py`; and the production-boundary authority,
dependency, build, clean-install, and installed-acceptance modules. The Pixi lock
was regenerated by Pixi, not manually edited. Graph counts came from parsing the
complete JSON, not reading its semantic report as proof of tested behavior.
