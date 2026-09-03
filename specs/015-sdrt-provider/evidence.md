# Evidence: SDRT Provider

**Observed**: 2026-09-03 | **Feature**: 015

| Requirement group | Implementation | Causal proof |
|---|---|---|
| Native EDU/CDU graph (FR-001–FR-004) | `rdam/sdrt/graph.py` | Exact spans, explicit membership, non-adjacent/CDU scope, and structural-class tests. |
| Graph validity (FR-005–FR-009) | Native validators | Dangling/self references, membership and relation cycles, connectivity, mixed-class, exact-source, and right-frontier counterexamples. |
| Independent evidenced provider (FR-010–FR-012) | `rdam/sdrt/provider.py`, `rdam/_llm.py` | Lazy capability, deterministic model seam, typed outcomes, attempts, provenance, and withholding tests. |

The membership-cycle tests found and fixed a real defect: cycle detection had inferred
CDUs from an identifier prefix. Validation now derives the CDU identity set from the
actual graph, and counterexamples with `group_alpha`/`group_beta` are refused.

The graph contract follows the primary SDRT description of acyclic EDU/CDU graphs,
coordinating/subordinating relations, and the right-frontier constraint:
<https://aclanthology.org/W13-4002/>.

## Observed checks

- `pixi run pytest tests/sdrt -q`: **21 passed in 1.24s**.
- Combined provider/machine deterministic suite: **233 passed, 2 deselected in 3.26s**.
- Ruff: **All checks passed**.
- Pyright strict: **0 errors, 0 warnings, 0 informations**.
- Production boundary: **valid**, zero violations.
- Cross-artifact analysis: 12 requirements, 7 success criteria, and 12 tasks; zero unresolved ambiguity, duplication, constitution conflict, or unmapped work.
