# Research: Shared Runtime Hardening

## Decisions

### Canonical identity

The machine and RST had equivalent but duplicated RFC 8785/SHA-256 implementations. One internal kernel now owns projection, I-JSON validation, canonical bytes, semantic digests, and byte/file digests. Existing import surfaces remain compatibility routes, so valid serialized bytes do not change.

### Immutable JSON

Pydantic's frozen model setting does not freeze nested dictionaries/lists. Copying into recursively immutable native-container subclasses prevents both caller-after-construction mutation and mutation through the record while preserving JSON and existing `dict`/`list` consumer expectations.

### Deadline

A stopwatch checked only before retry sleeps cannot bound an active request or structured-output retries. The only correct whole-budget mechanism is async execution inside one `asyncio.timeout`; external `CancelledError` remains outside the mapped failure algebra.

### Parallelism

Technique calls are independent, but completion order is not contract order. Futures therefore collect by technique and the aggregate is assembled from request order. Provider call locks are process-wide by concrete instance, so two machines sharing one provider cannot race its lazy/runtime state.

### Cache

Only a clean exact revision makes a successful result reproducible enough for reuse. The native result is already a canonical digest-verified envelope, so a second cache contract would be redundant. Atomic replace, owner-only permissions, per-key single flight, and full revalidation are sufficient at one-person/one-machine scale; TTLs and distributed coordination are unnecessary.

## Rejected Alternatives

- Provider base class: unnecessary coupling across native techniques.
- Hidden default cache directory: surprising persistence and paid-call semantics.
- Thread cancellation wrappers for LLM requests: cannot reliably stop the active async transport.
- Contract `1.1.0`: no wire-shape or semantic-envelope migration is needed.
- Generalized ingest changes: explicitly deferred to Feature 017.
