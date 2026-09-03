# Quickstart: Validate the Toulmin Provider

**Feature**: 013 | **Date**: 2026-09-03

```bash
pixi run pytest tests/toulmin -q
```

Expected: native-layout validation, empty analysis, declaration, provenance, typed
guards, deterministic model seams, and attempt-budget tests all pass without a real
network request.

```bash
pixi run lint
pixi run typecheck
pixi run -e default production-boundary
```

Expected: no code-quality, type, ownership, dependency, or workbench-import findings.

The slow live-model test is evidence only when the configured external model is actually
reachable. A missing credential is a valid `model_unavailable` capability, but Feature
006 SC-012 is satisfied only in the supported production composition where all required
provider configurations resolve.
