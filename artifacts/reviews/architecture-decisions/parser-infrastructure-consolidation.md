# Decision: shared parser infrastructure

## Decision

Consolidate behaviorally identical, non-parameter infrastructure while retaining DMRST and UniRST neural class identities and parameter names.

## Compatibility constraints

- Released `state_dict` keys, pickle/import aliases, inference maths, and relation inventories must not change.
- Family-specific casing and multi-corpus behavior remain explicit.

## Implemented migration

- Metric arithmetic and empty-input policy use one typed kernel.
- Device probing, device selection, dtype selection, and PyTorch import ordering use one runtime authority.
- Both predictors use the shared dtype/device boundary.
- Batch slicing no longer materializes one list per field.
- Segmenter/parser correctness repairs are mirrored with family-specific regression coverage.

## Deliberate non-migration

The neural modules and segmenter classes remain at their historical import paths. Merging those class definitions would create checkpoint/pickle compatibility risk without an additional runtime benefit.
