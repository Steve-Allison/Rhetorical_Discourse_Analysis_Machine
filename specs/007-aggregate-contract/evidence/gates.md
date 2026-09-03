# Feature 007 — Gate Evidence

**Observed**: 2026-09-03

## Defects found and fixed

- Aggregate lineage previously validated only the upstream digest/technique and could
  carry false consumer/upstream provider, contract, or model metadata.
- Structured inputs could be attached to text-native techniques.
- Persisted capability entries could carry a false CURIE or structured-input mode.
- Provider successes could misstate provider contract version or provenance.
- Typed provider failures could name another technique/provider/operation and be accepted.

Each defect now has a causal counterexample that failed before the implementation fix.

## Final gates

| Gate | Command | Observed result |
|---|---|---|
| Aggregate contract | `pixi run pytest tests/machine -q` | **55 passed in 2.98s** |
| Framework and boundary suites | `pixi run pytest tests/machine/test_frameworks.py tests/integration/test_production_boundary.py tests/production_boundary -q` | **36 passed in 3.92s** |
| Fast suite | `pixi run test` | **1299 passed, 134 deselected in 35.74s** |
| Complete suite | `pixi run test-all` | **1377 passed, 56 skipped in 229.61s** |
| Ruff | `pixi run lint` | **All checks passed** |
| Pyright strict | `pixi run typecheck` | **0 errors, 0 warnings, 0 informations** |
| Markdown | `pixi run mdlint` | **0 issues in 0 files** |
| Ontology | `pixi run ontology-validate` | Schema/data valid; projection matches Central; pre-existing `_meta` naming warning only |
| Production source boundary | `pixi run --environment default production-boundary` | **valid**, 137/137 production files, zero violations |
| Model-free import | `pixi run --environment default production-import-check` | **valid**, editable distribution, no provider construction |

Cross-artifact analysis covers 15 functional requirements, 7 success criteria, and 11
tasks with zero unresolved ambiguity, duplication, constitution conflict, or unmapped
work. The current root `rdam` topology is the only live topology in this feature.
