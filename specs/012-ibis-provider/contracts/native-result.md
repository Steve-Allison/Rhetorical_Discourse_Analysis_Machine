# Contract: IBIS Native Result

## Request

Structured input contains ordered `nodes` (`id`, `kind`, `text`) and `links` (`from`,
`relation`, `to`). Raw text is never a fallback.

## Validation

All native value and mapping construction paths enforce node, link, grammar, uniqueness,
and exact attachment rules. Invalid input is refused, never repaired.

## Result

The provider returns the validated native structure, deterministic deliberation map,
`input_origin`, `extraction: null`, and `grammar: gibis-v1`. Caller-authored derivation
also records its exact upstream technique and SHA-256 result identity.

## Failure

Missing structure is aggregate unavailability. Grammar/shape violations and undeclared
formalism are stable non-retryable failures.
