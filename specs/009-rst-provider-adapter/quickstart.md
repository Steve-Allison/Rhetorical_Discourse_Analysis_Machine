# Quickstart: RST Provider Adapter

## Deterministic adapter proof

```bash
pixi run pytest tests/rst tests/machine -q -m "not slow"
```

Expected: published/local configuration, immutable-release validation, formalism states,
typed failures, exact aggregate envelope, and lazy composition tests pass without loading
a published model.

## RST preservation and boundary proof

```bash
pixi run production-api-contract
pixi run --environment default production-boundary
pixi run --environment default production-import-check
```

Expected: canonical ingest/serialization contracts pass, source boundary is clean, and
public imports construct no model.

## Static and full fast gates

```bash
pixi run lint
pixi run typecheck
pixi run mdlint
pixi run test
```

Record exact observed results in `evidence/gates.md`. Slow real-model execution is a
separate gate and must not be claimed unless actually run with a compatible release.
