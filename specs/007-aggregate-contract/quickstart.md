# Quickstart: Aggregate Analysis Contract

## Focused contract proof

```bash
pixi run pytest tests/machine -q
```

Expected: request, result, failure, capability, lineage, canonical serialization, and
seven-provider composition tests pass without loading an inference model or client.

## Ontology and boundary proof

```bash
pixi run ontology-validate
pixi run --environment default production-boundary
pixi run --environment default production-import-check
```

Expected: provider bindings validate, the packaged projection matches Central, no
production import reaches `workbench`, and every public technique module imports without
constructing a provider.

## Static and repository gates

```bash
pixi run lint
pixi run typecheck
pixi run mdlint
pixi run test
```

Record exact observed counts in `evidence/gates.md`; do not reuse historical counts.
