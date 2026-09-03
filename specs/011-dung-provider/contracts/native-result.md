# Contract: Dung Native Result

## Request

The provider accepts `ProviderRequest.structured_input` shaped as:

```json
{"arguments": ["a", "b"], "attacks": [["a", "b"]]}
```

Raw text is not a fallback input. `derived_from`, when present, is caller-authored lineage.

## Result

The native payload contains the validated framework, input origin, grounded/complete/
preferred/stable extensions, and the exhaustive algorithm declaration. A derived result
also contains the exact upstream technique and SHA-256 result identity.

## Ordering

Argument order is preserved. Attacks are lexically ordered for serialization. Extension
members follow argument order; extension collections follow size then argument order.

## Failure

Invalid structure, invalid capacity, capacity excess, and formalism mismatch are explicit,
deterministic, non-retryable conditions. No partial or approximate extension is returned.
