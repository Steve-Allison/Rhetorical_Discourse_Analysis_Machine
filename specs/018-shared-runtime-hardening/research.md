# Research: Shared Runtime Hardening

These decisions record the original implementation. Feature 017 subsequently
introduced the owner-approved clean ingest API break and declaration-driven
parallel safety; current authority is reconciled in [spec.md](spec.md#current-authority-2026-09-04).

## Decisions

### Canonical identity

The machine and RST had equivalent but duplicated RFC 8785/SHA-256 implementations. One internal kernel now owns projection, I-JSON validation, canonical bytes, semantic digests, and byte/file digests. Existing import surfaces remain compatibility routes, so valid serialized bytes do not change.

### Immutable JSON

Pydantic's frozen model setting does not freeze nested dictionaries/lists. Copying into recursively immutable native-container subclasses prevents both caller-after-construction mutation and mutation through the record while preserving JSON and existing `dict`/`list` consumer expectations.

### Deadline

A stopwatch checked only before retry sleeps cannot bound an active request or structured-output retries. The only correct whole-budget mechanism is async execution inside one `asyncio.timeout`; external `CancelledError` remains outside the mapped failure algebra.

### Parallelism

Technique calls are independent, but completion order is not contract order. Futures therefore collect by technique and the aggregate is assembled from request order. Provider call locks are process-wide by concrete instance for providers declaring `serialized`; Feature 017 replaced the original blanket locking with measured, declared parallel safety.

### Cache

Only a clean exact revision makes a successful result reproducible enough for reuse. The native result is already a canonical digest-verified envelope, so a second cache contract would be redundant. Atomic replace, owner-only permissions, per-key single flight, and full revalidation are sufficient at one-person/one-machine scale; TTLs and distributed coordination are unnecessary.

The final pass found that appending an instructions digest could conceal an
unknown source revision. Eligibility now checks the underlying source revision
as well as the outer dirty marker. Deterministic clean/dirty/unknown tests cover
instruction binding independently of the checkout's current Git state.

### Dependency ownership

The installed `pydantic-ai-slim` OpenAI extra requires `tiktoken`. It therefore
belongs in core production dependencies, not the offline-only set. The boundary
and clean-install checks now agree with installed requirement metadata; a
regression test checks all three against the project dependency declaration.

### Mutation evidence

Each mutation runs only after the same causal tests pass unmodified in the
isolated workspace. A normal kill requires a pytest test-call failure without
collection/setup errors; an enforced timeout can kill the deadline mutant.
Infrastructure failures are not evidence that a regression was detected.

## Rejected Alternatives

- Provider base class: unnecessary coupling across native techniques.
- Hidden default cache directory: surprising persistence and paid-call semantics.
- Thread cancellation wrappers for LLM requests: cannot reliably stop the active async transport.
- Contract `1.1.0`: no wire-shape or semantic-envelope migration is needed.
- Generalized ingest changes: explicitly deferred to Feature 017.
