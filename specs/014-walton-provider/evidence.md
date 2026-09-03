# Evidence: Walton Provider

**Observed**: 2026-09-03 | **Feature**: 014

| Requirement group | Implementation | Tests |
|---|---|---|
| Catalogue and exact roles (FR-001..FR-003) | `rdam/walton/schemes.py` | Exhaustive parameterization in `tests/walton/test_schemes.py` |
| Critical questions (FR-004..FR-006) | Native instance validator and derived open set | None/one/all addressed, source-note, index, duplicate, and empty-analysis matrix |
| Proposal validation and failures (FR-007, FR-010, FR-011) | `rdam/walton/provider.py`, `rdam/_llm.py` | Deterministic success/failure plus shared attempt tests |
| Capability, identity, provenance, independence (FR-008, FR-009, FR-012) | Model-bearing provider id, source digest, scheme-set id | Lazy-client, provenance, payload-evidence, and withholding tests |

The scheme set now has one exported canonical identity used by provider identity and
payloads. Blank-role and one-addressed-question complement checks run over every scheme,
not one example. Successes and exhausted failures carry separate output and transport
attempt evidence.

## Observed checks

- `pixi run pytest tests/walton -m 'not slow' -q`: **113 passed, 1 deselected**.
- Combined provider/machine deterministic suite: **233 passed, 2 deselected in 3.26s**.
- Shared `pixi run lint`: **All checks passed**.
- Shared `pixi run typecheck`: **0 errors, 0 warnings, 0 informations**.
- Shared `pixi run -e default production-boundary`: **valid: true**, 137 production
  modules/files, zero violations.
- Cross-artifact analysis: 12 requirements and 8 success criteria map to 9 tasks; zero
  ambiguity, duplication, constitution conflict, or unmapped task.

The opt-in live-model test is skipped unless `RDAM_RUN_LIVE_MODEL_TESTS=1`; live
service execution was not performed and is not claimed.
