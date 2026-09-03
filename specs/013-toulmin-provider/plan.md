# Implementation Plan: Toulmin Provider

**Branch**: `013-toulmin-provider` | **Date**: 2026-09-03 |
**Spec**: [spec.md](spec.md)

## Summary

Audit and complete the existing `rdam.toulmin` provider as a native, LLM-assisted
Toulmin analyser. Keep claim, grounds, warrant, backing, qualifier, and rebuttal distinct;
accept only deterministic contract-valid proposals; make capability side-effect-free;
and make output and transport attempts separately bounded and observable.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Pydantic v2, Pydantic AI 2.37, the machine contracts in `rdam`

**Storage**: None; results are immutable in-memory contracts with canonical serialization

**Testing**: pytest through Pixi, Pydantic AI function-model seams for the external
boundary, one explicitly slow live-model acceptance, Ruff, Pyright, production boundary

**Target Platform**: one local machine; external model access only during analysis

**Project Type**: production Python library sub-package

**Performance Goals**: capability inspection performs zero model calls; all attempt
budgets are finite and evidenced; native validation is deterministic

**Constraints**: no argument generation, no fabricated warrants, no silent retries, no
workbench dependency, no client construction during capability reporting

**Scale/Scope**: one provider, one formalism, one configured model identity per instance

## Constitution Check

| Principle | Gate |
|---|---|
| I. Evidence Before Claims | Existing implementation is audited against this feature; current focused and full gate results are recorded. |
| II. One Production Quality Bar | Changed Python is fully typed and passes shared lint/type/test gates without suppressions. |
| III. Solo-Local Simplicity and Scope Fidelity | One direct provider and one shared LLM boundary; no queue, worker, tenant, or control plane. |
| IV. Honest Verification and Reproducible Evidence | External calls use the framework's model seam in ordinary tests; the real network is exercised only by the marked live acceptance. |
| V. Canonical Contracts and Current Specifications | This feature owns Toulmin semantics; Feature 006 owns machine semantics; current Pydantic AI retry documentation was verified before design. |

All gates pass at design time. No complexity exception is required.

## Project Structure

```text
specs/013-toulmin-provider/
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
└── toulmin/
    ├── __init__.py
    ├── argument.py
    └── provider.py

tests/toulmin/
├── test_argument.py
└── test_provider.py
```

**Structure Decision**: retain the single-package technique boundary. Native semantics
stay in `rdam.toulmin`; only provider-neutral LLM transport/output machinery stays in
`rdam._llm` because Toulmin, Walton, SDRT, and PDTB are proven callers.

## Implementation Phases

1. Lock the native layout and result contract with exhaustive validation tests.
2. Correct shared retry execution/evidence and add causal simulated-transport tests.
3. Audit declaration, capability, provenance, machine integration, and independence.
4. Run focused and shared quality gates; cross-check spec, plan, and tasks.

## Complexity Tracking

No constitution violations.
