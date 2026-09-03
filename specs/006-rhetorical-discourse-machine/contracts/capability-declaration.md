# Contract: Capability Declaration and Typed Outcomes

**Reconciled**: 2026-09-03.

## Identity binding

Each provider boundary declares one canonical concept from
`coe:artifact/narrative/analytical_frameworks_taxonomy`:

- discourse: RST, PDTB, SDRT;
- argumentation: Toulmin, Walton, Dung, IBIS.

The RST provider additionally declares the eRST formalism and its sibling canonical
identity. Framework identities are referenced through the packaged Central projection,
never redefined locally.

## Standing states

| State | Payload and rule |
|---|---|
| `available` | Stable provider id, contract version, provenance, formalism declarations. The configured provider can run. |
| `unavailable` | Exactly one stable reason: `not_implemented`, `model_unavailable`, or `missing_structured_input`. No stub result. |

Capability inspection reads configuration and source identity only. It cannot download
or load a model, construct an LLM client, perform inference, or touch the network.

## Per-request outcomes

Each requested technique produces exactly one:

- `result`: a provider-native result consistent with its declaration and source;
- `unavailable`: the standing or request-input reason;
- `failed`: a typed `ProviderFailure` with operation, code, exception type,
  retryability, and privacy-safe parameters.

The machine catches only `ProviderError`. Unexpected exceptions are bugs and propagate.
One outcome cannot suppress or rewrite another.

## Retry classification and ownership

The aggregate machine performs no retry. Deterministic input/native-contract failures
are `not_retryable`. LLM-backed providers delegate only their remote operation to the
shared `StructuredAnalyst`, which owns bounded transport and structured-output attempts.
It reports actual output and transport attempt counts on success and exhaustion, disables
implicit provider-SDK retries, and classifies only enumerated transient failures as
retryable.

## Supported composition

`rdam.production_machine()` registers RST, PDTB, SDRT, Toulmin, Walton, Dung, and IBIS in
canonical order. With a resolvable configured LLM model, `Machine.capabilities()` reports
exactly seven `available` techniques while constructing no inference client.
