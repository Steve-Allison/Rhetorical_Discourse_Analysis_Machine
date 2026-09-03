# Quickstart: Validate the Walton Provider

**Feature**: 014 | **Date**: 2026-09-03

```bash
pixi run pytest tests/walton -q
```

Expected: every scheme passes the catalogue and exact-role matrix; every question-state
invariant, deterministic model proposal, typed failure, capability, provenance, attempt,
and machine-independence test passes without a real request.

```bash
pixi run lint
pixi run typecheck
pixi run -e default production-boundary
```

Expected: zero findings. The marked live-model test is supplementary and is run only
when the configured provider is genuinely reachable.
