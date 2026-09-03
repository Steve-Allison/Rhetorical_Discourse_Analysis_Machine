# Implementation Plan: Walton Provider

**Branch**: `014-walton-provider` | **Date**: 2026-09-03 |
**Spec**: [spec.md](spec.md)

## Summary

Audit and complete `rdam.walton` as a native scheme-and-critical-question analyser. The
versioned catalogue deterministically validates model proposals; unreported questions
remain open, addressed questions retain source-grounded notes, capability is lazy, and
the shared LLM boundary supplies independently bounded and observable attempts.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Pydantic v2, Pydantic AI 2.37, `rdam` machine contracts

**Storage**: None; immutable native result contracts

**Testing**: exhaustive parameterized pytest over the catalogue, deterministic Pydantic
AI function models, one marked live-model acceptance, Ruff, Pyright, boundary inspection

**Target Platform**: one local machine; external access only during analysis

**Project Type**: production Python library sub-package

**Performance Goals**: zero client construction during capability inspection; finite
attempt budgets; catalogue validation deterministic for every supported scheme

**Constraints**: no forced scheme, no invented answer to an open question, no workbench
import, no silent retry, no cross-technique semantic flattening

**Scale/Scope**: one provider and one versioned supported scheme set

## Constitution Check

| Principle | Gate |
|---|---|
| I. Evidence Before Claims | Every catalogue-wide claim is exhaustively parameterized; current results are recorded. |
| II. One Production Quality Bar | Changed Python passes shared strict type, lint, and test gates without suppression. |
| III. Solo-Local Simplicity and Scope Fidelity | One direct provider and one shared LLM boundary; no workflow infrastructure. |
| IV. Honest Verification and Reproducible Evidence | External behaviour is driven through Pydantic AI's model seam; live calls are explicit and marked. |
| V. Canonical Contracts and Current Specifications | Feature 014 owns the scheme set/result; Feature 006 owns aggregation; shared retry design uses current library documentation. |

All design gates pass. No exception is required.

## Project Structure

```text
specs/014-walton-provider/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/native-result.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md

rdam/
├── _llm.py
└── walton/
    ├── __init__.py
    ├── schemes.py
    └── provider.py

tests/walton/
├── test_schemes.py
└── test_provider.py
```

**Structure Decision**: native catalogue and validation stay inside `rdam.walton`;
provider-neutral attempt machinery stays in `rdam._llm` as the shared proven boundary.

## Implementation Phases

1. Prove catalogue totality and role/question invariants exhaustively.
2. Prove model proposals cannot bypass or repair the native validator.
3. Consume the shared observable retry/evidence contract completed by Feature 013.
4. Prove capability, provenance, independence, and full quality gates.

## Complexity Tracking

No constitution violations.
