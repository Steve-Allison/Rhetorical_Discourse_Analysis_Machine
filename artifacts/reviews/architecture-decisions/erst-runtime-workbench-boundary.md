# Decision: eRST runtime and workbench boundary

## Owner direction, 2026-09-06

Move eRST out of production and retain it in the workbench for testing and evaluation.
This supersedes the earlier decision to retain runtime checkpoint contracts in `rdam`.

## Ownership

`workbench/erst/` owns signal detection, candidate generation, neural scoring,
decoding, RS4 conversion, checkpoint loading, research contracts and experimental
parser completion. Existing training, corpus, promotion and evaluation consumers
import that authority. The production tree converter lives at `rdam/rst/converter.py`.

`rdam.rst.Parser`, `RstProvider` and production ingest support `rst_tree` only.
Production has no eRST checkpoint option, bundle discovery, completion method or
`erst-result` schema advertisement. The wheel and sdist exclude the workbench.

## Compatibility

Passive analysis and inference data contracts remain in production to validate
and read saved reports without executing or importing experimental code. Canonical
ontology identities and trained primary RST architecture remain unchanged.
The move does not assert eRST accuracy, a trained bundle, or release readiness.

## Verification

Source import checks, production capability/configuration rejection tests, retained
eRST tests, schema parity and clean wheel installation check the boundary.
Actual results are reported after those checks run; this decision is not a test receipt.
