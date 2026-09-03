# Data Model: Aggregate Analysis Contract

## Provider declaration

One immutable declaration names a boundary technique, its canonical Central CURIE,
provider id, contract version, provenance, structured-input requirement, overall
capability, and one or more formalism declarations. An available capability must name
the same provider and contract version.

## Technique capability

One machine-level projection for each of the seven boundaries, in canonical order. Its
CURIE and structured-input flag are derived from the framework registry. It carries the
provider's formalism declarations when a provider is registered.

## Aggregate request

One exact source identity, optional exact text, a unique ordered set of requested
boundary techniques, optional per-technique formalism choices, and structured inputs
only for Dung or IBIS. Explicit derivations carry the exact upstream native result they
name; the machine never manufactures them.

## Native technique result

One provider-owned JSON payload plus technique/formalism identity, exact source,
provider id, provider contract version, provider provenance, and a computed semantic
digest. The machine validates the envelope but never interprets the payload.

## Provider failure

One typed failure for the provider's own boundary technique and `analyse` operation,
with provider id, retryability, stable code, exception type, message template, and
parameters. A malformed typed failure is replaced by a deterministic machine contract
failure; an unexpected exception still propagates as a bug.

## Aggregate analysis

One exact source, one explicit outcome per represented technique, zero or more exact
lineage references, and a computed semantic digest. Every lineage reference must agree
with the carried consumer and upstream results on technique, provider id, provider
contract version, upstream digest, and upstream model identity.

## State transitions

```text
provider declaration -> available | unavailable(reason)
request + available provider -> result | failed(provider failure)
request + absent/unavailable provider -> unavailable(reason)
validated outcomes + exact lineage -> aggregate analysis -> canonical persisted bytes
```
