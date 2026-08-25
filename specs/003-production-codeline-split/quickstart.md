# Quickstart: Production and Offline Boundaries

These commands are the target operator contract.

## Production

```bash
pixi install --environment production --locked
pixi run --environment production production-boundary
pixi run --environment production production-smoke
```

Build and validate the exact publication candidate:

```bash
pixi run --environment offline build-production
pixi run --environment offline validate-production-artifacts
pixi run --environment production production-clean-install
```

These commands build wheel and sdist, inspect both exact artifacts, then independently install the wheel into core-only and formats-enabled environments outside the repository. The installed candidate runs all promoted parser variants, serialization/reload, hierarchy, eRST, optional adapters, and frozen parity checks without offline packages.

## Offline workbench

```bash
pixi install --environment offline --locked
pixi run --environment offline offline-smoke
```

The offline smoke executes every retained command to a bounded help or causal test boundary and emits strict hashed receipts. It does not claim model quality.

## Promote a model locally

```bash
pixi run --environment offline promote-model --candidate /absolute/candidate --store /absolute/release-store
```

The command returns the immutable release path and JSON receipt. Production receives the promoted directory, never the workbench or training directory.

## Dependency rule

`offline_workbench` and `research_harness` may import `isanlp_rst`. `isanlp_rst` never imports either offline namespace, repository scripts, or tests.

## Offline import migration

Moved corpus, trainer, evaluation, experiment, and benchmark imports use `offline_workbench.*`. Runtime parser, adapter, contract, safe model-load, and analysis imports remain under `isanlp_rst.*`. No production compatibility shim points into offline code.
