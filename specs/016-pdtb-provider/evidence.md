# Evidence: PDTB Provider

**Observed**: 2026-09-03 | **Feature**: 016

| Requirement group | Implementation | Causal proof |
|---|---|---|
| Seven native relation types and senses (FR-001–FR-007) | `rdam/pdtb/relations.py` | Exhaustive type matrix, exact shipped leaf vocabulary, multiple-sense, and evidence-field tests. |
| Source and argument integrity (FR-008–FR-011) | Native validators | Discontinuous spans, direction, mismatch, overlap, duplicate identity, unknown sense, and type/evidence counterexamples. |
| Independent evidenced provider (FR-012–FR-013) | `rdam/pdtb/provider.py`, `rdam/_llm.py` | Lazy capability, deterministic model seam, typed outcomes, attempts, provenance, and withholding tests. |

The native vocabulary and type-specific rules were checked against the official PDTB-3
annotation manual: <https://catalog.ldc.upenn.edu/docs/LDC2019T05/PDTB3-Annotation-Manual.pdf>.

## Observed checks

- `pixi run pytest tests/pdtb -q`: **28 passed in 1.24s**.
- Combined provider/machine deterministic suite: **233 passed, 2 deselected in 3.26s**.
- Ruff: **All checks passed**.
- Pyright strict: **0 errors, 0 warnings, 0 informations**.
- Production boundary: **valid**, zero violations.
- Cross-artifact analysis: 13 requirements, 7 success criteria, and 12 tasks; zero unresolved ambiguity, duplication, constitution conflict, or unmapped work.

## Current convergence proof

The 2026-09-03 convergence audit reproduced three contract defects before the fix:
Pydantic accepted string and boolean offsets as integers, trimmed a mismatched proposed quote
into an exact source match, and allowed mutation of collections inside frozen models. Six causal
counterexamples failed before implementation. The repaired contract also refuses surrounding
whitespace on inferred connectives instead of silently trimming it.

- `pixi run pytest tests/pdtb -q`: **35 passed in 1.75s** on the final delivery candidate.
- Focused Ruff: **All checks passed**.
- Focused Pyright strict: **0 errors, 0 warnings, 0 informations**.
- `pixi run lint`: **All checks passed**.
- `pixi run typecheck`: **0 errors, 0 warnings, 0 informations**.
- `pixi run mdlint`: **206 files linted, 0 issues**.
- `pixi run ontology-validate`: **exit 0**; schema and data validation found no issues,
  the framework projection matched, and the configured `_meta` naming warning remained visible.
- Default production boundary: **valid**, 137 modules, zero violations.
- Production-environment boundary: **valid**, 137 modules, zero violations.
- `pixi run test`: **1348 passed, 134 deselected in 37.70s**.
- `pixi run test-all`: **1426 passed, 56 skipped in 245.97s**.
- Current cross-artifact analysis: **13 functional requirements, 7 success criteria,
  and 17 tasks; 100% mapped, with zero unresolved findings or constitution conflicts**.

The skipped tests require optional live/model resources; no live-service result is claimed.
