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
