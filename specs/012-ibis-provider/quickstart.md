# Quickstart: IBIS Provider

```bash
pixi run pytest tests/ibis -q
pixi run lint
pixi run typecheck
pixi run --environment default production-boundary
pixi run test
```

Expected: the exhaustive grammar and provider suites pass, static checks are clean, and
the production boundary reports zero violations.
