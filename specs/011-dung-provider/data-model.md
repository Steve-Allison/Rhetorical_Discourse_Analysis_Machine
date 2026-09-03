# Data Model: Dung Abstract Argumentation Provider

## ArgumentationFramework

- `arguments`: non-empty ordered tuple of unique non-empty strings
- `attacks`: set of ordered argument-name pairs

Invariant: every attack endpoint belongs to `arguments`.

## Semantics

- `grounded`: one least complete extension
- `complete`: every complete extension
- `preferred`: inclusion-maximal complete extensions
- `stable`: complete extensions that attack every argument outside them

Serialization orders extension members by supplied argument order and extension lists by
cardinality followed by that order.

## Dung native payload

- validated framework
- `input_origin`: `supplied` or `explicitly_derived`
- optional exact upstream technique/result identity
- four extension collections
- exhaustive algorithm name, version, and capacity

## Failure states

- missing structure: aggregate unavailability
- malformed framework: `invalid_argumentation_framework`
- excessive size: `framework_exceeds_declared_capacity`
- undeclared formalism: `formalism_not_declared`

Every provider failure is non-retryable.
