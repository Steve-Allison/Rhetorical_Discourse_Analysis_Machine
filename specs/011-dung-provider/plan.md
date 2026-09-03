# Implementation Plan: Dung Abstract Argumentation Provider

**Feature**: `011-dung-provider` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Converge the existing deterministic Dung provider against a decision-closed contract,
strengthen invariant enforcement at every public construction path, verify exact bounded
semantics causally, and certify aggregate-machine integration without changing algorithms.

## Technical Context

**Language/Version**: Python 3.14

**Dependencies**: Python standard library and `rdam` aggregate contracts only

**Storage**: None

**Testing**: pytest through Pixi; exhaustive and seeded property tests

**Target Platform**: One local machine

**Constraints**: Exact deterministic evaluation; positive bounded capacity; no raw-text
derivation, network, model, offline dependency, or approximation

## Constitution Check

- Evidence is causal: known cases, all 512 three-node graphs, seeded random graphs, and
  malformed counterexamples exercise real semantics/provider code.
- Changed Python retains strict types and receives no checker suppression.
- The bounded exhaustive algorithm is direct and appropriate to one local analyst.
- Native Dung structures remain distinct from every other technique.

Pre-design and post-design result: **PASS**.

## Project Structure

```text
rdam/dung/                          # framework, semantics, provider, exports
tests/dung/                         # formal and aggregate-machine tests
specs/011-dung-provider/            # authority, design, tasks, evidence
```

**Structure Decision**: Retain the existing `rdam.dung` boundary; add no shared
abstraction or compatibility package.

## Complexity Tracking

No constitution violation or new subsystem is required.
