# Implementation Plan: PDTB Provider

**Branch**: `016-pdtb-provider` | **Date**: 2026-09-03 | **Spec**: [spec.md](spec.md)

## Summary

Add an independently callable, LLM-assisted PDTB-3 provider under `rdam.pdtb`. Deterministic models preserve binary source-grounded arguments, all seven relation types, type-specific connective evidence, multiple senses, and the exact PDTB-3 leaf hierarchy. The shared LLM boundary supplies bounded retry and attempt evidence.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Pydantic 2, Pydantic AI 2.37
**Testing**: pytest via Pixi
**Target Platform**: one local macOS machine; installable Python package
**Project Type**: single Python package
**Performance Goal**: deterministic validation linear in relations plus spans
**Constraints**: no offline/dev/workbench production imports; no client construction during capability inspection; no hierarchy invented beyond PDTB-3
**Scale/Scope**: one source per call under the shared bounded request contract

## Constitution Check

- Native PDTB technique semantics are preserved: pass.
- Exact source claims fail closed: pass.
- Capability reporting is side-effect-free: pass.
- Production environment boundary remains clean: pass.
- Deterministic tests establish the contract without live-service dependence: pass.

## Project Structure

```text
rdam/pdtb/
├── __init__.py
├── relations.py
└── provider.py

tests/pdtb/
├── __init__.py
├── test_relations.py
└── test_provider.py
```

## Design Decisions

1. Encode the official PDTB-3 leaf sense labels as a closed `StrEnum`, with no aliases or PDTB-2 legacy labels.
2. Encode all seven official relation types and apply type-specific evidence/sense rules deterministically.
3. Represent arguments and explicit/AltLex evidence as ordered lists of exact spans so discontinuous annotations survive.
4. Preserve Arg1/Arg2 labels independently of textual order, matching PDTB-3 intra-sentential subordinate conventions.
5. Perform exact source-slice checks in the provider, after Pydantic structure validation and before result construction.
6. Reuse `StructuredAnalyst` for one canonical transport/output attempt policy.

## Delivery Phases

1. Freeze the official manual-derived native contract.
2. Add causal tests for all relation types, senses, spans, and invalid combinations; implement the native model.
3. Add deterministic provider/capability/failure tests; implement the provider.
4. Integrate with Feature 006's supported production composition.
5. Analyse and run all focused/cross-repository gates; record exact proof.

## Success Gates

- `pixi run pytest tests/pdtb -q`
- `pixi run lint`
- `pixi run typecheck`
- `pixi run -e default production-boundary`
- `$speckit-analyze` returns no critical, high, or medium findings for Feature 016.

## Complexity Tracking

No constitution violations or justified exceptions.
