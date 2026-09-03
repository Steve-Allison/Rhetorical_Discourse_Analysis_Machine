# Feature 009 — Gate Evidence

**Reconciled**: 2026-09-03

The historical `rst/rdam_rst` layout and 2026-09-02 counts are superseded. The live
adapter is `rdam.rst.provider.RstProvider` inside the one `rdam` distribution.

## Defects found and fixed

- Local capability treated manifest presence as availability without proving manifest
  shape, runtime compatibility, membership, file size, or content hashes.
- A release identifier could escape its configured store.
- Invalid local releases could inherit the published weights licence.
- Local release validation was repeated and its parser family was not retained.
- A release changed after declaration leaked `ModelReleaseError` instead of a typed,
  non-retryable provider failure.
- During implementation, the deterministic success-path test caught removal of the
  `json` import while the adapter still decoded canonical ingest bytes.

The initial seven causal counterexamples failed before the release-validation
implementation (`7 failed, 11 passed, 1 deselected`). Separate missing-member, size,
and same-size hash probes complete the final invariant matrix. The deterministic
canonical-envelope test exposed the missing import before the final green run.

## Final gates

| Gate | Command | Observed result |
|---|---|---|
| RST adapter | `pixi run pytest tests/rst/test_provider.py -q -m 'not slow'` | **24 passed, 1 deselected in 3.59s** |
| RST and aggregate | `pixi run pytest tests/rst tests/machine -q -m 'not slow'` | **79 passed, 1 deselected in 3.41s** |
| Published parser smoke | exact `TestRealParser` node | **1 passed in 11.46s** |
| Production API contract | `pixi run production-api-contract` | **379 passed in 17.22s** |
| Fast suite | `pixi run test` | **1299 passed, 134 deselected in 35.74s** |
| Complete suite | `pixi run test-all` | **1377 passed, 56 skipped in 229.61s** |
| Ruff | `pixi run lint` | **All checks passed** |
| Pyright strict | `pixi run typecheck` | **0 errors, 0 warnings, 0 informations** |
| Markdown | `pixi run mdlint` | **0 issues across 188 linted files** |
| Production source boundary | `pixi run --environment default production-boundary` | **valid**, 137/137 production files, zero violations |
| Model-free import | `pixi run --environment default production-import-check` | **valid**, editable distribution, no weight load |

Cross-artifact analysis covers 13 functional requirements, 7 success criteria, and 10
tasks with 100% coverage and zero ambiguity, duplication, constitution conflict, or
unmapped work.
