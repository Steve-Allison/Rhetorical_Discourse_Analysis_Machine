# Feature 006 — Evidence

**Observed**: 2026-09-03

| Evidence | Proves |
|---|---|
| [`rst-surface-audit.md`](rst-surface-audit.md) | Live `rdam.rst` public surface and classified analytical preservation. |
| [`boundary-audit.md`](boundary-audit.md) | Single-package ownership and production/workbench separation. |
| [`identity-binding-audit.md`](identity-binding-audit.md) | All canonical technique/formalism identities resolve to Central authority. |
| [`../checklists/requirements.md`](../checklists/requirements.md) | Final documentary and executable acceptance ledger. |

## Final observed gates

- Complete suite: **1348 passed, 56 skipped in 227.32s**.
- Deterministic provider/machine suite: **233 passed, 2 deselected in 3.26s**.
- RST format suite: **242 passed in 5.62s**.
- RST ingest coverage: **443 passed**, **91.80%** aggregate branch coverage.
- RST mutation gate: **5/5 critical mutants killed**.
- Production API contract: **379 passed in 16.82s**.
- Ruff: **All checks passed**; Pyright strict: **0 errors, 0 warnings, 0 informations**.
- Production boundary and model-free import check: **valid**, zero violations.
- Markdown lint: **0 issues in 0 files**.
- Ontology schema/data validation: **no issues**; identity projection matches Central authority. LinkML lint retains its pre-existing `_meta` naming warning and exits successfully.

The final import gate caught and fixed one stale assertion that constructed the newly
defaulted RST parser while claiming to load no weights. It now imports every technique
module and `rdam.machine` without constructing a provider.

The 56 skips are deliberate and visible: 54 local RST-release matrix cases declare an
incompatible `>=4,<5` runtime range, and two live LLM probes require explicit opt-in.
Neither category is presented as runtime proof.
