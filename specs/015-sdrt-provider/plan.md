# Implementation Plan: SDRT Provider

**Branch**: `015-sdrt-provider` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Add an independently callable, LLM-assisted SDRT provider under `rdam.sdrt`. The model proposes EDUs, CDUs, and labelled edges; deterministic Pydantic models validate exact source spans, identity/reference integrity, membership and relation acyclicity, connectivity, structural-class consistency, and the computable right frontier. The existing shared LLM boundary supplies explicit bounded retry evidence.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Pydantic 2, Pydantic AI 2.37
**Testing**: pytest via Pixi
**Target Platform**: one local macOS machine; installable Python package
**Project Type**: single Python package
**Performance Goal**: deterministic graph validation linear in nodes plus edges
**Constraints**: production code cannot import offline/dev/workbench dependencies; capability discovery cannot construct a model client; no theory-collapsing common result
**Scale/Scope**: one source per call, bounded by the existing local-machine request contract

## Constitution Check

- Native theory boundary is preserved: pass.
- Contracts fail closed and never repair model output: pass.
- Capability inspection is side-effect-free: pass.
- Production package boundary remains clean: pass.
- Tests use deterministic model doubles; live services are not required for contract proof: pass.

## Project Structure

```text
rdam/sdrt/
├── __init__.py
├── graph.py
└── provider.py

tests/sdrt/
├── __init__.py
├── test_graph.py
└── test_provider.py
```

## Design Decisions

1. Preserve relation labels as validated non-empty strings while closing the theory-defining structural class to `coordinating` or `subordinating`; SDRT corpora do not share one universal relation inventory.
2. Represent EDUs and CDUs as distinct types in one graph. CDU membership participates in connectivity and may itself be a relation endpoint.
3. Compute right-frontier eligibility from textual introduction order, the most recent EDU, reverse subordinating ancestry, and completed CDUs. Reject a post-initial EDU if none of its incoming attachments originates on that frontier.
4. Perform exact source-slice validation in the provider after structural output validation, because the source is request context rather than model output.
5. Reuse `StructuredAnalyst` so retry policy, provider-specific implicit-retry disabling, deadlines, and attempt evidence remain one canonical shared implementation.

## Delivery Phases

1. Specify the native graph and research authority.
2. Write deterministic invalid/valid graph tests, then implement the model.
3. Write provider/capability/failure tests, then implement the provider.
4. Integrate into the seven-provider production composition in Feature 006.
5. Run feature analysis and repository gates; record exact evidence.

## Success Gates

- `pixi run pytest tests/sdrt -q`
- `pixi run lint`
- `pixi run typecheck`
- `pixi run -e default production-boundary`
- `$speckit-analyze` returns no critical, high, or medium findings for Feature 015.

## Complexity Tracking

No constitution violations or justified exceptions.
