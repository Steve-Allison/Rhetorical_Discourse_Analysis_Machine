# Production source ingest: current-practice comparison

**Evidence date:** 25 August 2026

**Scope:** small-volume, solo-local production RST analysis of real-world
sources; model training and research data preparation are excluded.

**Decision rule:** no architectural label, test count or vendor comparison is
sufficient for promotion. The built candidate must pass every frozen-source,
quality, provenance, structure, clean-install and direct-inspection gate with
no waiver.

## Bounded comparison

| Capability | Pre-Feature 002 production path | Feature 002 candidate | Promotion evidence |
|---|---|---|---|
| Public surface | Separate Markdown, Docling and DocLang entry points, envelopes and caches | One `isanlp_rst.ingest` service; old surfaces absent | Built-wheel public-surface and payload checks |
| Source contract | Format identification and adapter-specific validation | Strict source identity separated from current-contract validation | Current Docling/DocLang records plus every-form Gold execution |
| Content selection | Format knobs and flatten-first inclusion | Complete inventory followed by one immutable `AUTHORED_PROSE_V1` policy | Exact item/disposition match against adjudicated Gold |
| Non-prose material | Could enter prose or be flattened into format-specific results | Tables, cells, code, formulae, pictures, raw markup, metadata and assets retained as anchored side channels | Complex-content conformance and direct inspection |
| Structure | Mostly post-hoc boundary annotation | Source structure controls deterministic recursive subdivision before inference | Complete tree, local/macro origin and structural-violation gates |
| Provenance | Useful format-native mappings but separate schemas | Reversible prepared segments plus native anchors for every analysis node and relation | 100% source, prepared-text and analysis-anchor coverage after reload |
| Long sources | Adapter character ceilings or flat-parser risk | Parser-capacity-derived recursive subdivision; no truncation route | One-million-character correctness/performance gate |
| Determinism/cache | Independent format caches with incomplete identity | RFC-8785 semantic identity, released-model bytes, atomic verified local cache | Ten-run equality, mutation, corruption and interruption gates |
| Quality comparison | No immutable per-source production promotion | Frozen wheel/model/source/scorer identities; per-source EDU and Parseval non-regression | 12 RST-Gold sources plus 23-source inspection |
| Runtime isolation | Production and development lived in one repository with unclear package proof | Training/evaluation remain repository-only; production imports are one-way | Wheel installed outside repository with offline modules unavailable |

## Current external contract baseline

- Docling Core 2.92.0 is the current PyPI release. The candidate is pinned to
  the 2.92 line and validates/traverses all four governed schema-1.10.0
  specimens through the current `DoclingDocument` API.
- DocLang 0.7.3 is the current PyPI release. The local set matches all 42
  current upstream valid fixtures at commit
  `6d3b3d3c195d1f63333c5c5fcba8da17937a33bd` byte-for-byte.
- Current DocLang `.dclx` is an OPC package, not a bare ZIP. The candidate
  enforces content types, the root document relationship, bounded ZIP safety,
  relative asset resolution and page-image bounds.

Authorities:
[Docling Core on PyPI](https://pypi.org/project/docling-core/),
[DocLang on PyPI](https://pypi.org/project/doclang/), and
[the current DocLang specification](https://github.com/doclang-project/doclang/blob/6d3b3d3c195d1f63333c5c5fcba8da17937a33bd/spec.md).

## Claim boundary

The intended result is world-class source preparation for this project’s
actual scale: correctness, source fidelity and inspectable analytical quality
over throughput infrastructure. “SOTA” is used only in the bounded engineering
sense of current upstream contract compliance plus measured improvement over
the frozen production path. It is not a claim that one ingest architecture is
universally best, nor a claim about retraining or model architecture.

Candidate measurements and the final decision are populated only by the
immutable-wheel promotion run. Until `promotion-decision.json` passes, this
document describes the candidate and its gates, not a promoted result.
