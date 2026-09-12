# Validation guide: DocLang decoder refactor

Status: implemented validation commands. Recorded measurements and semantic differences are in [implementation-results.md](implementation-results.md).

## Prerequisites

Run from the repository root using the installed Pixi binary. The examples use `pixi` on PATH; on this machine its verified path is `/Users/steveallison/.pixi/bin/pixi`.

Use the locked default environment. No paid models, downloaded weights or new package installation is required for the initial decoding checks. A lock/spec update is a separate explicit decision if Phase A proves it necessary.

## Baseline already observed during planning

```sh
pixi run --locked pytest tests/ingest/test_doclang_text_walker.py tests/ingest/test_doclang_fixture_parity.py tests/ingest/production_ingest/test_doclang_ingest.py tests/ingest/production_ingest/test_doclang_complex.py -q
```

Observed: `98 passed in 0.85s`, exit 0, on 2026-09-12. This is not the full production or new-decoder suite.

The installed 0.7.3 validator was also run against upstream-main `ok_track_minimal.dclg`; it rejected `track` at XSD validation. Keep that release/main boundary explicit when refreshing fixtures.

## Phase-specific execution

After Phase B/C adds the private types:

```sh
pixi run --locked pytest tests/ingest/test_doclang_document.py tests/ingest/test_doclang_decoder.py tests/ingest/test_doclang_text_walker.py -q
```

Expected: exact fragment round-trips, all text/tails accounted for, shared document ownership, failure isolation and correct typed table facts. Test malformed XML and schema-invalid XML separately; well-formedness is not schema validation.

After direct inventory dispatch:

```sh
pixi run --locked pytest tests/ingest/test_doclang_decoder.py tests/ingest/test_doclang_identity.py tests/ingest/production_ingest/test_doclang_ingest.py tests/ingest/production_ingest/test_doclang_complex.py tests/ingest/production_ingest/test_native_anchors.py tests/ingest/production_ingest/test_upstream_conformance.py -q
pixi run --locked production-ingest-determinism
pixi run --locked pytest tests/machine tests/interfaces -q -m 'not slow and not live'
```

Expected: field-by-field parity under the compatibility contract, public machine/source integration, unchanged table-evidence projections and failure behaviour. Run against real internal code; do not replace the decoder/mapper with stubs.

## Mutation and final regression checks

Repair the mutation runner before relying on it. A missing source target, broken import, timeout or collection error must fail the runner rather than count as a killed mutant.

```sh
pixi run --locked pytest tests/production_boundary/test_rst_mutation_verdict.py -q
pixi run --locked rst-format-test
pixi run --locked production-ingest-test
pixi run --locked rst-format-coverage
pixi run --locked rst-mutation-test
pixi run --locked lint
pixi run --locked typecheck
pixi run --locked test
pixi run --locked mdlint
pixi run --locked production-boundary
```

Update format task lists and coverage targets for the new modules/tests before running these gates. The repaired runner requires a clean causal baseline and a test-call failure without setup/collection errors.

Successful evidence consists of actual exit codes and test counts, no unexplained comparison differences, all intended mutants causally detected, coverage over moved code and a passing import/ownership boundary. Do not infer wheel certification from the source-boundary command.

## Performance comparison

Use the real-world form and deterministic schema-valid inputs built from the raw/wrapped list/table fixtures. Test standalone XML and equivalent valid archives. Retain originals and use identical bytes for both revisions.

- Record node/cell counts, input size, Python/dependency versions and machine.
- Perform one warmup, then at least five measured runs per case on each revision; alternate baseline/candidate when practical.
- Profile the real preparation call: separate official validation from RDAM tree construction, path indexing, table decoding and mapping.
- Report every elapsed measurement and a process-memory measure that accounts for native lxml allocations; Python-only allocation tracing is insufficient for total XML memory.
- Verify one RDAM main-tree construction and one path-index construction per decode, and elimination of cell-by-cell prefix rescanning.
- Run the existing reference preparation thresholds as a regression check, but do not call those generic thresholds a DocLang-specific performance proof.

```sh
pixi run --locked pytest tests/ingest/test_doclang_decoder.py -q -k archive_uses_one_rdam
pixi run --locked production-ingest-performance
```

Investigate repeated candidate timings or memory use outside the baseline's observed variation. Report a speedup only if the measured distributions support it. Structural simplification is independently checkable even if official validation dominates total latency.

## Final review

```sh
graphify update .
git diff --check
git status --short
```

Inspect the code diff, changed source identities and the exact semantic differences. Confirm no new public shape, no `docling-nlp` dependency, no permanent legacy fallback, and no unrelated source-form migration. These commands do not authorize committing, publishing or creating a release.
