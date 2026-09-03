# Quickstart: Dung Abstract Argumentation Provider

```bash
pixi run pytest tests/dung -q
pixi run lint
pixi run typecheck
pixi run --environment default production-boundary
pixi run test
```

Expected: exact semantics/property tests pass, aggregate integration returns typed native
outcomes, static checks are clean, and the production boundary reports zero violations.
