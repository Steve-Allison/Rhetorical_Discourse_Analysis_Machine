# Feature 018 Evidence

## Status — 2026-09-04

The implementation and regression repairs are present in the working tree based
on `1a707088ac46fb17390d8911adcedddc317e9c1b`. Final certification is **not
complete**: the corrected runtime has not yet been committed and double-built.
T023 and T025 remain open. No commit or push has been made in this pass.

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
| `shared-runtime-coverage` | `120 passed in 1.51s`; six modules, `308 statements`, `98 branches`, `100.00%` |
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

## Build and installation — distinguish the source revisions

Before the repairs made this checkout dirty, `build-production --evidence-dir
specs/018-shared-runtime-hardening/build-evidence` completed the reproducible
double-build from clean commit `1a707088ac46fb17390d8911adcedddc317e9c1b`.
The JSON files in `build-evidence/` identify that **pre-repair** source exactly.

- Wheel: `dist/6.0.0/rdam-6.0.0-py3-none-any.whl`, SHA-256
  `15c5e8692a92eb2630d7c6ee9224447addcaba2844f886886026c7501ebc20b3`.
- Sdist: `dist/6.0.0/rdam-6.0.0.tar.gz`, SHA-256
  `b71a7c81ee926139282aba2cef3fde519c9051df67abdfb62b4e309c66fecbc0`.
- `validate-production-artifacts`: `valid: true`, `artifact_valid: true`,
  `149` production modules/files.
- Fresh core and formats installs of that wheel both passed, with `pip_check:
  passed`, `offline_distributions_absent: true`, network disabled during
  acceptance, real model execution, and CLI semantic parity. The command used
  `--model-store /Users/steveallison/.cache/isanlp_rst/model-releases
  --release-id gumrrg-eb1d5745f3a1` with `--full`.

The current corrected-source build attempt fails with:

```text
RuntimeError: production artifacts require a completely clean worktree
```

A local commit was requested so that the corrected source can be double-built,
artifact-validated, and exercised in fresh core/formats installs. That approval
is outstanding. The pre-repair wheel is not claimed to certify the repair.

## Graph and scope

The AST-only Graphify update completed without paid semantic extraction:
`12,355 nodes`, `25,847 edges`, `1,145 communities`. Full JSON inspection counted
`6,255` source nodes under `rdam/` and zero `isanlp_rst/` source paths. Community
names were deterministically refreshed by hub where membership changed; semantic
document extraction was not run.

`graphify-out/cache/last_query_stamp` remains untracked and ignored by
`.gitignore:40`. No Feature 017 specification, ingest implementation, format
fixture, trained architecture, or inference mathematics was changed.

The earlier evidence's absent ModernBERT target and UniRST loading failure are
historical observations, not current blockers: explicit existing-release
clean-install acceptance and the final full suite now pass. No external
publication is part of this task.

SpecKit post-execution hook check: `.specify/extensions.yml` is absent; no
extension hook is registered. Completion remains gated by T023/T025, not a hook.

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
