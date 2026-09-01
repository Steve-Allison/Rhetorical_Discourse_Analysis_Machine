# Contract: Capability Declaration and Framework Identity

**Feature**: 006 | **Authority**: [spec.md](../spec.md) FR-002, FR-012, FR-014, FR-020, SC-005, SC-007, SC-010

## Identity binding

1. Every capability declaration names its technique by canonical identifier from
   `coe:artifact/narrative/analytical_frameworks_taxonomy` (Central_Configs, registered
   2026-08-31):
   `…/discourse_structure_framework/rst`, `…/erst`, `…/pdtb`, `…/sdrt`;
   `…/argumentation_framework/toulmin`, `…/walton`, `…/dung`, `…/ibis`.
2. The binding is **identity only**. Native relation inventories, role sets, semantics
   families, and result payloads are provider-owned and versioned by the provider's own
   contract (FR-012, FR-013). Central's simplified vocabulary profiles (e.g. the
   registered `argument_role` annotation set) never constrain a native contract.
3. `coe:` identifiers are referenced, never redefined locally (Central consumer
   contract). The vendored distribution under `ontology/vendor/central-configs/` is the
   resolution source.
4. A boundary and its provider bind to exactly one technique identity. A provider
   additionally declares one or more **formalisms** — the result-kinds it natively emits
   — each carrying its own canonical identity from the same scheme and its own capability
   state. This is how one provider serves a sibling concept without a second boundary:
   the RST provider binds to `…/rst` and declares `rst_tree → …/rst` and
   `erst_graph → …/erst` (ruling recorded in [data-model.md](../data-model.md)
   §Formalism). A formalism is never a stub: an undeclared or unloaded result-kind
   reports `unavailable` with a stable reason, exactly as a provider does.

## Capability states (FR-020)

Every technique the machine knows about reports exactly one of:

| State | Payload | Rules |
|---|---|---|
| `available` | contract version, provider provenance | Only reachable via a `promote` PromotionDecision. |
| `unavailable` | stable `reason` | Enumerated reasons, stable across releases: `no_promoted_implementation`, `withheld`, `retired`, `replaced`, `missing_structured_input` (Dung/IBIS requests lacking their required input, FR-016/FR-017). Never a stub, dummy analysis, or fabricated structure (SC-007). |
| `failed` | typed error | Per-request. Never suppresses another provider's success (FR-014, SC-005). |

## Retryability classification (machine-wide standard)

The RST provider's failure contract (`isanlp_rst/ingest/contracts/failure.py`) sets the
standard every provider and the machine layer inherit:

1. **No internal retries, ever.** A failure happens exactly once and propagates as a
   typed result. No provider, and no machine layer, loops, backs off, or re-attempts.
2. **Every `failed` outcome carries a retryability classification** —
   `retryable` | `not_retryable` | `unknown` — as a mandatory field with no default.
   The classification is information for the caller, who alone decides whether to
   re-invoke; the machine never acts on it.
3. **`unavailable` is never retryable.** Unavailability changes only through an
   external state change (installation, configuration, promotion), so re-asking
   without one is defined to return the same answer — claiming otherwise is a
   contract validation error, exactly as the RST failure contract already enforces.
4. **Deterministic failures are `not_retryable`** (validation, malformed or
   unsupported input, identity contradiction): providers are deterministic by
   construction, so a retry reproduces the failure. `unknown` is reserved for
   unexpected internal failures where transience is possible but unproven.
   `retryable` may be claimed only where a provider demonstrates genuine transience —
   no provider does today, and the burden of proof sits with the claimant.

## Transient-boundary retry standard (binding on every future provider)

The current machine contains no transient boundary and therefore no retry executor —
adding one before a transient boundary exists is forbidden dead machinery. The first
provider that crosses such a boundary (an LLM API for Toulmin/Walton-class analysis,
network acquisition, any remote dependency) MUST implement retry exactly as follows,
at that boundary only:

1. **Scope**: retry wraps only the transient operation, never deterministic
   computation. The set of errors treated as transient is explicit, enumerated, and
   tested — never a blanket exception catch.
2. **Shape**: bounded attempts, exponential backoff with full jitter, and an overall
   deadline; server-provided signals (e.g. `Retry-After`) are honoured when present.
3. **Two classes for LLM-backed providers, never conflated**: *transport retries*
   (rate limits, 5xx, network — the shape above) and *structured-output validation
   retries* (invalid native structure → bounded re-prompt carrying the validation
   error). Each class has its own bound and budget.
4. **Idempotency precondition**: an operation may be retried only if a repeat cannot
   double-apply or fork semantic identity — satisfied machine-wide by the
   semantic-identity and cache design, and re-verified per provider at promotion.
5. **No silent retries**: every attempt is recorded in execution evidence (attempt
   count, per-attempt cause, delays, total elapsed). A successful result that retried
   shows its retries; exhaustion yields the typed failure carrying the full attempt
   trail, with retryability classified per this contract.
6. **Excluded by scale ruling** (FR-028): circuit breakers, hedged requests, and
   retry queues — no failure mode in a one-person, one-machine system justifies them.

Promotion evidence for any provider with a transient boundary MUST include tests of
this policy under simulated transient faults (external systems are the one legitimate
mock target under the project's test-honesty rules).

## Aggregate behaviour

1. An aggregate request over N techniques returns N explicit outcomes — successful native
   results preserved untouched, every unavailable or failed technique represented with
   its state and reason (FR-014).
2. Capability reporting is side-effect-free and never triggers model downloads or
   expensive initialization (spec edge case: import-time work is a promotion-evidence
   concern, not a capability-query cost).
3. Withholding or replacing one provider leaves every other technique's declared
   capability byte-identical (SC-010 acceptance check).
