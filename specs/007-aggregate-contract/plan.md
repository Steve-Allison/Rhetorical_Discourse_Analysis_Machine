# Implementation Plan: Aggregate Analysis Contract

**Feature**: `007-aggregate-contract` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Converge the already-delivered aggregate layer onto the current single-package `rdam`
architecture, then strengthen the trust boundary so caller-supplied records and provider
successes/failures cannot misstate technique, provider, contract, provenance, source, or
lineage identity. Preserve native technique payloads as opaque data and preserve the
machine's no-retry, no-suppression, side-effect-free capability behavior.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Pydantic 2, RFC 8785 canonical JSON, LinkML application profile

**Storage**: Canonical JSON records supplied by callers; no database

**Testing**: pytest through Pixi, Ruff, Pyright strict, ontology and production-boundary gates

**Target Platform**: One local macOS machine; installable `rdam` Python distribution

**Project Type**: Single Python package with independently callable technique subpackages

**Performance Goals**: Aggregate validation linear in outcomes and lineage references;
capability inspection constructs no inference model or client

**Constraints**: No native payload normalization; no machine retries; no `workbench`
imports or distributable members; canonical Central identities are referenced, not copied

**Scale/Scope**: Seven technique boundaries and the eRST formalism in one process

## Constitution Check

- **Evidence before claims**: causal counterexample tests precede contract changes; gate
  counts are recorded only after execution.
- **One production quality bar**: changed Python is typed Python 3.14 and must pass Ruff
  and strict Pyright without suppression.
- **Solo-local simplicity**: direct immutable models and one in-process machine; no
  service, queue, registry, role, or distributed abstraction.
- **Honest verification**: deterministic internal tests use real contracts; doubles only
  stand in for external inference providers.
- **Canonical contracts**: `rdam.contracts`, the vendored Central projection, and provider
  declarations remain the single authorities for their facts.

Pre-design and post-design result: **PASS**, with no justified exceptions.

## Project Structure

```text
rdam/
├── contracts.py                 # aggregate request/result/failure/lineage invariants
├── frameworks.py                # packaged projection of canonical framework identities
├── machine.py                   # independent execution and production composition
└── serialization.py             # canonical, digest-verified persistence

ontology/
├── data/rdam-providers.yaml
├── schema/rdam.linkml.yaml
└── vendor/central-configs/

tools/production_boundary/       # ownership, import closure, artifact membership

tests/
├── machine/
└── integration/test_production_boundary.py
```

**Structure Decision**: Extend the live root `rdam` package only. The obsolete
`machine/rdam` multi-package layout in the historical feature record is not recreated.

## Complexity Tracking

No constitution violation or additional abstraction is required.
