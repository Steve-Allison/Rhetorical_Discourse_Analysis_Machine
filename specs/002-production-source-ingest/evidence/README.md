# Feature 002 Evidence

This directory contains text-free, reproducible evidence for production source
ingest. It must never contain private source text, training corpora, model
weights, Gold annotations that reveal protected content, or machine-local
credentials.

Permitted records contain source IDs, cryptographic digests, byte and item
counts, policy decisions by stable item ID, metric values, timings, package and
model identities, gate outcomes, and inspection decisions. Private source files
and detailed annotations remain under the explicitly supplied local
`--gold-root`.

Every JSON record validates against `evidence-schema.json`, identifies the exact
candidate and authority digests it measures, and uses UTC timestamps only for
execution evidence. A changed candidate or authority requires a new record; an
existing result is never edited to make a gate pass.
