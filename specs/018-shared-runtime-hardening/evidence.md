# Feature 018 Evidence

Evidence below is from the final checkout. Passing a gate for an existing built
artifact is distinguished from certifying the uncommitted Feature 018 source.

## Shared-runtime proof

- Pre-change focused baseline: `174 passed, 3 deselected`.
- `pixi run shared-runtime-test`: `258 passed, 3 deselected in 6.47s`.
- `pixi run shared-runtime-coverage`: `96 passed`; all six shared-runtime
  modules reached `298 statements, 96 branches, 100.00%`.
- `pixi run shared-runtime-mutation-test`: all `6/6` critical mutants killed.
- Graphify force refresh: `13,971 nodes`, `27,173 edges`, `663 communities`;
  all `6,245` production source nodes resolve under `rdam/`, with zero obsolete
  `isanlp_rst/` source paths and zero production paths outside `rdam/`.
- `graphify-out/cache/last_query_stamp` is deleted and ignored by `.gitignore`;
  `git check-ignore --no-index -v` resolves it to `.gitignore:39`.

## Passing acceptance gates

- `pixi run lint`: `All checks passed!`.
- `pixi run typecheck`: `0 errors, 0 warnings, 0 informations`.
- `pixi run test`: `1462 passed, 134 deselected in 37.92s`.
- `pixi run test-stress`: `6 passed in 40.82s`.
- `pixi run production-api-contract`: `397 passed in 23.13s`.
- `pixi run production-boundary`: `valid: true`, `144` files and `144`
  production modules scanned, no violations.
- `pixi run production-import-check`: `valid: true`; editable-source import
  boundary passed.
- `pixi run validate-production-artifacts`: `valid: true`, `artifact_valid:
  true`, `144` files and `144` production modules scanned.
- `git diff --check`: passed with no output.

The artifact validator reports source commit
`d4d59c003a85d56fb802df3c08e797153572f578`. It therefore validates the
previously built wheel and sdist, not the current uncommitted Feature 018 tree.

## Blocked or failing acceptance gates

- `pixi run build-production`: failed with `RuntimeError: production artifacts
  require a completely clean worktree`. The checkout contains the requested
  Feature 018 implementation plus pre-existing and concurrent work that must
  not be discarded.
- `pixi run -e production production-clean-install`: failed because configured
  release `modernbert-v1-a52b70fbc1a3` is not a real local directory;
  `rdam.rst.model_loading.release.ModelReleaseError: model release must be a
  real local directory`.
- `pixi run test-all`: the configured UniRST release
  `unirst-9407970f1d9d@cpu` is present but incompatible with the current
  `ParsingNet`; loading fails with unexpected `encoder.segmenters.*` state-dict
  keys. The run was stopped after the same fixture-construction failure repeated
  and established the prerequisite defect.

Feature 018 implementation and its causal tests are complete. Final production
certification remains open until the worktree can be built cleanly and compatible
local model releases are installed. No universal-source, Docling, DocLang,
Markdown, harvest, preparation, or new `rdam/ingest/` behavior was introduced by
Feature 018.
