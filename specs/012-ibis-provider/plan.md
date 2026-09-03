# Implementation Plan: IBIS Provider

**Feature**: `012-ibis-provider` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Converge the existing deterministic gIBIS provider, close public-constructor invariant
gaps, retain exact typed-link and attachment validation, and certify its non-judgemental
map and aggregate integration.

## Technical Context

**Language/Version**: Python 3.14

**Dependencies**: Python standard library and `rdam` aggregate contracts only

**Storage**: None

**Testing**: pytest through Pixi; exhaustive grammar-table tests and causal malformed cases

**Target Platform**: One local machine

**Constraints**: Structured input only; no extraction, repair, scoring, network, model, or offline dependency

## Constitution Check

- Real grammar/provider code is exercised exhaustively and through the aggregate machine.
- Changed Python remains strictly typed with no suppressions.
- Direct immutable structures suit the solo-local scale.
- IBIS remains a native map and is never collapsed into Dung or another formalism.

Pre-design and post-design result: **PASS**.

## Project Structure

```text
rdam/ibis/                         # grammar, native structure, map, provider
tests/ibis/                        # exhaustive grammar and integration tests
specs/012-ibis-provider/           # authority, design, tasks, evidence
```

**Structure Decision**: Retain `rdam.ibis`; create no top-level `ibis` package or shared graph abstraction.

## Complexity Tracking

No constitution violation or new subsystem is required.
