# Decision: eRST runtime and workbench boundary

## Decision

Move promotion-only receipts out of `rdam` and into `workbench.promotion`; retain only contracts required to validate and load an existing runtime checkpoint in `rdam.rst.contracts.erst`.

## Compatibility constraints

- Do not change the current checkpoint manifest wire schema or trained tensor architecture.
- Production must not import `workbench`.
- Offline production-boundary tooling may import the workbench promotion contract because it is not shipped in the wheel.

## Implemented migration

- `PromotionReceipt` now lives in `workbench/promotion/contracts.py`.
- Promotion code and repository-only boundary tooling import that authority.
- The production model-loading public surface no longer exports the offline receipt.

## Verification

The fast suite covers promotion/boundary collection, and the production-boundary gate proves no production-to-workbench import.
