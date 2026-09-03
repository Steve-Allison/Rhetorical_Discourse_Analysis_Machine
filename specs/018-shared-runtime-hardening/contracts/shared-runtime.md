# Contract: Shared Runtime

1. Contract records are closed, frozen, recursively immutable, RFC 8785 canonical, and SHA-256 digest verified.
2. Native technique payload vocabulary remains provider-owned and opaque to the machine.
3. A newly available provider declaration carries complete package/version/source/model/licence provenance; historical persisted provenance may omit only source revision.
4. LLM providers share model identity, text guards, attempt evidence, error mapping, and one wall-clock deadline, while native validators remain provider-owned.
5. Parallel completion never changes aggregate order. Typed failures are values; implementation defects remain exceptions.
6. A provider instance processes at most one call at a time. Separate provider instances may overlap up to the execution policy.
7. Persistent caching exists only when a directory is explicit, only for clean exact revisions, and only for validated successes.
8. A cache hit has no weaker validation than a fresh result. Any mismatch removes the entry, warns, and triggers recomputation.
9. Aggregate and native wire contracts remain `1.0.0`.
10. Feature 018 owns no source preparation, format parsing, harvest, universal ingest, or trained-model behavior.
