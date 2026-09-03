# Evidence: Toulmin Provider

**Observed**: 2026-09-03 | **Feature**: 013

| Requirement group | Implementation | Tests |
|---|---|---|
| Native core and optional elements (FR-001..FR-005) | `rdam/toulmin/argument.py` | `tests/toulmin/test_argument.py` |
| Proposal validation and typed outcomes (FR-006, FR-010) | `rdam/toulmin/provider.py`, `rdam/_llm.py` | Deterministic function-model and failure cases |
| Capability, identity, provenance, independence (FR-007..FR-009, FR-012) | Provider and aggregate contracts | Declaration, lazy-client, provenance, and withholding tests |
| Separate bounded attempts (FR-011) | `rdam/_llm.py` | Exhaustion, Retry-After, deadline, output exhaustion, SDK retry-disable, and success-evidence tests |

The audit found one real defect: `transport_retries` was stored but unused and provider
SDK defaults could retry invisibly. The shared boundary now disables SDK retries, owns a
bounded full-jitter transport loop with Retry-After/deadline handling, keeps output and
transport budgets separate, and propagates attempt counts into successes and failures.

## Observed checks

- `pixi run pytest tests/toulmin -m 'not slow' -q`: **31 passed, 1 deselected**.
- Combined provider/machine deterministic suite: **233 passed, 2 deselected in 3.26s**.
- `pixi run lint`: **All checks passed**.
- `pixi run typecheck`: **0 errors, 0 warnings, 0 informations**.
- `pixi run -e default production-boundary`: **valid: true**, 137 production
  modules/files, zero violations.
- Cross-artifact analysis: 12 requirements and 7 success criteria map to 10 tasks; zero
  ambiguity, duplication, constitution conflict, or unmapped task.

The opt-in live-model test is skipped unless `RDAM_RUN_LIVE_MODEL_TESTS=1`; live
service execution was not performed and is not claimed.
