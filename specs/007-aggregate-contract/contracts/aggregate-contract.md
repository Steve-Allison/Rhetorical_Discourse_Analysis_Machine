# Aggregate Contract

## Capability

- Exactly seven boundary techniques appear, in canonical order.
- Every technique CURIE and structured-input flag is canonical.
- Capability inspection reads declarations only and constructs no inference client.
- Withholding one provider changes only that provider's capability entry.

## Request

- Requested boundaries, structured inputs, and formalism choices are unique.
- Text identity equals the submitted text bytes when text is present.
- Structured input is accepted only for Dung and IBIS.
- An explicit derivation names a carried upstream result about the same source.

## Execution

- Each requested technique receives at most one call; the machine never retries.
- Absence and configuration unavailability are explicit unavailable outcomes.
- Only `ProviderError` is translated; unexpected exceptions propagate.
- A provider success is accepted only when its provider, contract, provenance, source,
  formalism, and technique agree with the declaration and request.
- A provider failure is accepted only when its technique, provider, and operation agree
  with the invoked provider; otherwise the machine emits a deterministic contract
  violation for the requested boundary.

## Result and lineage

- Native payloads remain opaque and unmodified.
- One provider's failure never suppresses another provider's success.
- Lineage is recorded only for an explicitly declared derivation whose consumer
  succeeded.
- Every lineage identity agrees exactly with the carried upstream and consumer results.
- Canonical serialization verifies semantic digests on write and read.

## Boundary

- Production code imports no `workbench` module, directly or transitively.
- Built artifacts admit only the `rdam/` import root and distribution metadata.
- Framework identities are regenerated from the vendored Central authority.
