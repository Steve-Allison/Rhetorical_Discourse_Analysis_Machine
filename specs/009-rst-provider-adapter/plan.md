# Implementation Plan: RST Provider Adapter

**Feature**: `009-rst-provider-adapter` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Converge the RST adapter onto the current `rdam.rst.provider` authority and strengthen
local-release capability so `available` means a safe, compatible, byte-validated release
rather than mere manifest presence. Preserve the exact production-ingest outcome as the
opaque native payload, keep capability/model loading lazy, and map expected release and
ingest failures into the aggregate failure algebra without hiding internal bugs.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: `rdam` aggregate contracts, Pydantic 2, Torch/Transformers RST runtime

**Storage**: Optional immutable local model-release directory and optional analysis cache

**Testing**: pytest through Pixi, real production contracts with tiny local release fixtures,
Ruff, Pyright strict, production boundary and RST preservation gates

**Target Platform**: One local macOS machine; CPU/MPS chosen by the parser runtime

**Project Type**: Adapter inside the single `rdam` package

**Performance Goals**: Published-version capability is constant-time; local-release
validation occurs once per provider and model construction remains deferred until analysis

**Constraints**: No inference-math changes; no native envelope reinterpretation; no
network/model load during capability inspection; no broad exception translation

**Scale/Scope**: DMRST and UniRST published versions plus explicit immutable local releases,
with `rst_tree` and optional `erst_graph` formalisms

## Constitution Check

- Causal release-corruption and failure tests precede provider changes.
- Changed code remains typed Python 3.14 without suppressions.
- One direct adapter is retained; no registry/service abstraction is introduced.
- Capability and runtime claims are separated and verified by observed gates.
- `rdam.rst` remains the canonical ingest/parser authority; the adapter copies no schema.

Pre-design and post-design result: **PASS**, no exception required.

## Project Structure

```text
rdam/rst/
├── provider.py                  # machine-facing adapter
├── parser.py                    # canonical parser façade
├── ingest/                      # canonical source and result authority
└── model_loading/release.py     # immutable release validation authority

tests/rst/test_provider.py       # adapter-specific causal and integration tests
tests/machine/                   # aggregate interaction tests
```

**Structure Decision**: Modify only the live `rdam.rst` subpackage and its tests. The
obsolete `rst/rdam_rst` separate-distribution layout is not recreated.

## Complexity Tracking

No constitution violation or additional subsystem is needed.
