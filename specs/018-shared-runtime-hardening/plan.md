# Implementation Plan: Shared Runtime Hardening

**Branch**: `018-shared-runtime-hardening` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Harden the existing aggregate runtime without changing native formalisms or source ingest: unify canonical identity, freeze JSON inputs, centralize composition helpers, correct LLM identity/deadline behavior, add deterministic four-worker execution, and provide a clean-revision-only opt-in result cache.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Pydantic 2.13, Pydantic AI 2.37, RFC 8785, `httpx2` 2.12
**Testing**: pytest, coverage.py branch coverage, deterministic isolated-workspace mutation runner via Pixi
**Target Platform**: one local macOS machine
**Constraints**: aggregate/native `1.0.0`; historical readability; no provider base class; no hidden cache; no source-pipeline or trained-model changes

## Architecture

1. `rdam/_canonical.py` owns all canonical JSON/I-JSON/SHA-256 primitives; machine and RST compatibility surfaces re-export or call it.
2. `rdam/_immutable_json.py` owns recursively immutable native JSON containers; contract field validators copy/freeze and serializers restore ordinary wire values.
3. `rdam/_provenance.py` owns installed/build/checkout revision resolution; `rdam.rst._provenance` is a compatibility re-export.
4. `rdam/_provider_provenance.py` owns small composition functions, never inheritance.
5. `rdam/_llm.py` owns canonical model identity, locked agent creation, SDK configuration, and one async timeout budget.
6. `rdam/_execution.py` owns the public policy; `rdam/_result_cache.py` owns private atomic persistence/single flight; `rdam/machine.py` owns deterministic orchestration and contract checks.

## Delivery Phases

1. Establish authority, causal baseline, and immutable/canonical contracts.
2. Centralize provenance/provider helpers and standardize four LLM providers.
3. Correct model identity, timeout, cancellation, clients, and lazy construction.
4. Implement bounded parallel execution, shared provider locks, cache identity, atomic storage, validation, and single flight.
5. Add branch-complete and mutation verification, tooling tasks, architecture docs, and Graphify hygiene.
6. Run all acceptance gates and record exact evidence.

## Constitution Check

- Native theory boundaries remain separate: pass.
- Solo-local scale and explicit cache path: pass.
- No warning suppression, blanket recovery, or fabricated evidence: pass.
- Production imports contain no dev/offline dependency: pass.
- Feature 017 and format/source behavior remain untouched: pass.

## Success Gates

The authoritative gate list is the user-approved list in [quickstart.md](quickstart.md); `test-all` runs only when configured local model releases are present.
