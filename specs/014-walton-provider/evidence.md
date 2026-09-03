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

## Current convergence verification

- Native-catalogue/open-note red phase: **5 failed, 98 passed** before implementation.
- `pixi run pytest tests/walton -q`: **118 passed, 1 skipped in 1.37s** after enforcing
  `Scheme` invariants and forbidding notes on open critical questions.
- Focused Ruff and strict Pyright: clean; **0 errors, 0 warnings, 0 informations**.
- Repository Ruff: **All checks passed**.
- Repository strict Pyright: **0 errors, 0 warnings, 0 informations**.
- Markdown: **206 files linted, 43 governed exclusions, 0 issues**.
- Ontology: exit 0; schema and bindings validated and the framework projection matched
  its vendored authority. The configured ignored `_meta` naming warning remained visible.
- Source boundary: default and production environments each reported **valid: true**,
  137 production modules/files, and zero violations.
- Fast suite: **1,339 passed, 134 deselected in 35.52s**.
- Complete suite: **1,417 passed, 56 skipped in 238.33s**.
- Live external-model execution remains opt-in and was not run or claimed.
